package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"html"
	"io"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

type commandRunner func(context.Context, ...string) ([]byte, error)

type YouTubeProvider struct {
	APIKey  string
	APIBase string
	Client  *http.Client
	Run     commandRunner
}

func NewYouTubeProvider(apiKey, binary string) *YouTubeProvider {
	// Bound expensive extraction calls independently of HTTP/MCP concurrency.
	slots := make(chan struct{}, 2)
	return &YouTubeProvider{
		APIKey: apiKey, APIBase: "https://www.googleapis.com/youtube/v3",
		Client: &http.Client{Timeout: 20 * time.Second},
		Run: func(ctx context.Context, args ...string) ([]byte, error) {
			ctx, cancel := context.WithTimeout(ctx, 90*time.Second)
			defer cancel()
			select {
			case slots <- struct{}{}:
				defer func() { <-slots }()
			case <-ctx.Done():
				return nil, ctx.Err()
			}
			common := []string{"--ignore-config", "--no-playlist", "--no-progress", "--no-warnings", "--socket-timeout", "15", "--retries", "1", "--extractor-retries", "1"}
			cmd := exec.CommandContext(ctx, binary, append(common, args...)...)
			cmd.WaitDelay = 2 * time.Second
			var stdout limitedBuffer
			cmd.Stdout, cmd.Stderr = &stdout, io.Discard
			if err := cmd.Run(); err != nil {
				if ctx.Err() != nil {
					return nil, fmt.Errorf("YOUTUBE_TIMEOUT: extraction exceeded the request deadline")
				}
				if errors.Is(err, exec.ErrNotFound) {
					return nil, fmt.Errorf("YTDLP_MISSING: install yt-dlp or run the video Docker image")
				}
				return nil, fmt.Errorf("YOUTUBE_UNAVAILABLE: extraction failed; captions may be absent or YouTube may limit this server")
			}
			return stdout.Bytes(), nil
		},
	}
}

type limitedBuffer struct{ bytes.Buffer }

func (b *limitedBuffer) Write(p []byte) (int, error) {
	if b.Len()+len(p) > 4<<20 {
		return 0, fmt.Errorf("extractor output exceeds 4 MiB")
	}
	return b.Buffer.Write(p)
}

func (p *YouTubeProvider) Search(ctx context.Context, in SearchInput) (SearchResult, error) {
	if p.APIKey != "" {
		return p.searchAPI(ctx, in)
	}
	data, err := p.Run(ctx, "--flat-playlist", "--dump-single-json", "--skip-download", "--", fmt.Sprintf("ytsearch%d:%s", in.Limit, in.Query))
	if err != nil {
		return SearchResult{}, err
	}
	var response struct {
		Entries []struct {
			ID          string `json:"id"`
			Title       string `json:"title"`
			Channel     string `json:"channel"`
			Description string `json:"description"`
		} `json:"entries"`
	}
	if err := json.Unmarshal(data, &response); err != nil {
		return SearchResult{}, fmt.Errorf("YOUTUBE_RESPONSE_INVALID: cannot read search results")
	}
	result := SearchResult{Source: "youtube-yt-dlp", Videos: []Video{}}
	for _, entry := range response.Entries {
		if videoIDPattern.MatchString(entry.ID) {
			result.Videos = append(result.Videos, Video{VideoID: entry.ID, Title: entry.Title, Channel: entry.Channel, Description: entry.Description, WatchURL: watchURL(entry.ID)})
		}
		if len(result.Videos) == in.Limit {
			break
		}
	}
	return result, nil
}

func (p *YouTubeProvider) searchAPI(ctx context.Context, in SearchInput) (SearchResult, error) {
	params := url.Values{"part": {"snippet"}, "type": {"video"}, "q": {in.Query}, "maxResults": {fmt.Sprint(in.Limit)}, "relevanceLanguage": {strings.Split(in.Language, "-")[0]}, "videoEmbeddable": {"true"}, "videoSyndicated": {"true"}}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, p.APIBase+"/search?"+params.Encode(), nil)
	if err != nil {
		return SearchResult{}, err
	}
	// Keep the key out of URL-based access logs and error messages.
	req.Header.Set("X-Goog-Api-Key", p.APIKey)
	response, err := p.Client.Do(req)
	if err != nil {
		return SearchResult{}, fmt.Errorf("YOUTUBE_UNAVAILABLE: search API request failed")
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return SearchResult{}, fmt.Errorf("YOUTUBE_API_ERROR: HTTP %d; check API key, API enablement and quota", response.StatusCode)
	}
	var body struct {
		Items []struct {
			ID struct {
				VideoID string `json:"videoId"`
			} `json:"id"`
			Snippet struct {
				Title        string `json:"title"`
				ChannelTitle string `json:"channelTitle"`
				Description  string `json:"description"`
			} `json:"snippet"`
		} `json:"items"`
	}
	if err := json.NewDecoder(io.LimitReader(response.Body, 1<<20)).Decode(&body); err != nil {
		return SearchResult{}, fmt.Errorf("YOUTUBE_RESPONSE_INVALID: cannot read search results")
	}
	result := SearchResult{Source: "youtube-data-api", Videos: []Video{}}
	for _, item := range body.Items {
		if videoIDPattern.MatchString(item.ID.VideoID) {
			result.Videos = append(result.Videos, Video{VideoID: item.ID.VideoID, Title: html.UnescapeString(item.Snippet.Title), Channel: html.UnescapeString(item.Snippet.ChannelTitle), Description: html.UnescapeString(item.Snippet.Description), WatchURL: watchURL(item.ID.VideoID)})
		}
	}
	return result, nil
}

func (p *YouTubeProvider) Transcript(ctx context.Context, videoID, language string) (Transcript, error) {
	dir, err := os.MkdirTemp("", "da-youtube-captions-")
	if err != nil {
		return Transcript{}, err
	}
	defer os.RemoveAll(dir)
	_, err = p.Run(ctx, "--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", "^"+regexp.QuoteMeta(language)+"$", "--sub-format", "json3", "--output", filepath.Join(dir, "captions.%(ext)s"), "--", watchURL(videoID))
	if err != nil {
		return Transcript{}, err
	}
	path := filepath.Join(dir, "captions."+language+".json3")
	file, err := os.Open(path)
	if err != nil {
		if os.IsNotExist(err) {
			return Transcript{}, fmt.Errorf("TRANSCRIPT_UNAVAILABLE: no %s captions; choose another language or video", language)
		}
		return Transcript{}, err
	}
	defer file.Close()
	data, err := io.ReadAll(io.LimitReader(file, (8<<20)+1))
	if err != nil || len(data) > 8<<20 {
		return Transcript{}, fmt.Errorf("TRANSCRIPT_TOO_LARGE: captions exceed 8 MiB")
	}
	cues, err := parseJSON3(data)
	if err != nil {
		return Transcript{}, err
	}
	return Transcript{VideoID: videoID, Language: language, Source: "youtube-captions", Cues: cues}, nil
}

func parseJSON3(data []byte) ([]Cue, error) {
	var body struct {
		Events []struct {
			Start    int64 `json:"tStartMs"`
			Duration int64 `json:"dDurationMs"`
			Segments []struct {
				Text string `json:"utf8"`
			} `json:"segs"`
		} `json:"events"`
	}
	if err := json.Unmarshal(data, &body); err != nil {
		return nil, fmt.Errorf("TRANSCRIPT_INVALID: invalid JSON3 captions")
	}
	cues := []Cue{}
	for _, event := range body.Events {
		var text strings.Builder
		for _, segment := range event.Segments {
			text.WriteString(segment.Text)
		}
		cleaned := strings.Join(strings.Fields(html.UnescapeString(text.String())), " ")
		if cleaned == "" || event.Duration <= 0 {
			continue // Window-control events are not spoken captions; never invent times.
		}
		if event.Start < 0 || event.Start > 7*24*60*60*1000 || event.Duration > 300000 {
			return nil, fmt.Errorf("TRANSCRIPT_INVALID: invalid caption timestamp")
		}
		cues = append(cues, Cue{StartMS: event.Start, EndMS: event.Start + event.Duration, Text: cleaned})
	}
	sort.SliceStable(cues, func(i, j int) bool { return cues[i].StartMS < cues[j].StartMS })
	for i := range cues {
		cues[i].Index = i
	}
	if len(cues) == 0 {
		return nil, fmt.Errorf("TRANSCRIPT_UNAVAILABLE: captions contain no timed speech")
	}
	return cues, nil
}

func watchURL(videoID string) string { return "https://www.youtube.com/watch?v=" + videoID }

// This provider is opt-in, explicitly synthetic, and never returns playable URLs.
type DemoProvider struct{}

func (DemoProvider) Search(_ context.Context, _ SearchInput) (SearchResult, error) {
	return SearchResult{Source: "fixture", Videos: []Video{{VideoID: "demo0000001", Title: "[DEMO] Deadlock và bốn điều kiện Coffman", Channel: "Dữ liệu giả lập", Description: "Chỉ kiểm tra luồng MCP và chọn đoạn; đây không phải kết quả tìm YouTube thật."}}}, nil
}

func (DemoProvider) Transcript(_ context.Context, videoID, language string) (Transcript, error) {
	if videoID != "demo0000001" {
		return Transcript{}, fmt.Errorf("demo mode only supports demo0000001")
	}
	if language != "vi" {
		return Transcript{}, fmt.Errorf("demo fixture only contains vi captions")
	}
	return Transcript{VideoID: videoID, Language: language, Source: "fixture", Cues: []Cue{
		{StartMS: 0, EndMS: 12000, Text: "Bài học hôm nay giới thiệu quản lý tài nguyên trong hệ điều hành."},
		{StartMS: 252000, EndMS: 270000, Text: "Deadlock xảy ra khi các tiến trình chờ tài nguyên do nhau giữ và không thể tiếp tục."},
		{StartMS: 270000, EndMS: 310000, Text: "Bốn điều kiện Coffman gồm loại trừ tương hỗ, giữ và chờ, không thu hồi, và chờ vòng tròn."},
		{StartMS: 310000, EndMS: 348000, Text: "Ví dụ tiến trình A giữ khóa thứ nhất và chờ khóa thứ hai, còn B giữ khóa thứ hai và chờ khóa thứ nhất."},
		{StartMS: 348000, EndMS: 378000, Text: "Một cách phòng tránh là quy định thứ tự lấy khóa để phá điều kiện chờ vòng tròn."},
		{StartMS: 378000, EndMS: 400000, Text: "Phần tiếp theo chuyển sang thuật toán lập lịch CPU."},
	}}, nil
}
