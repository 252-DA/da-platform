package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/url"
	"regexp"
	"strings"
	"sync"
	"time"
)

var videoIDPattern = regexp.MustCompile(`^[a-zA-Z0-9_-]{11}$`)
var languagePattern = regexp.MustCompile(`^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})?$`)

type snapshot struct {
	transcript Transcript
	expires    time.Time
}

// Snapshots bind selections to the exact caption text the caller read. This
// pilot deliberately has no course/user writes. It is one local service instance.
type Service struct {
	provider Provider
	mu       sync.Mutex
	snaps    map[string]snapshot
	capacity int
	ttl      time.Duration
}

func NewService(provider Provider) *Service {
	return &Service{provider: provider, snaps: make(map[string]snapshot), capacity: 32, ttl: 30 * time.Minute}
}

func normalizeLanguage(language string) (string, error) {
	if language == "" {
		language = "vi"
	}
	if !languagePattern.MatchString(language) {
		return "", fmt.Errorf("language must be a caption language code, e.g. vi or en")
	}
	return language, nil
}

func (s *Service) Search(ctx context.Context, in SearchInput) (SearchResult, error) {
	in.Query = strings.TrimSpace(in.Query)
	if len(in.Query) < 2 || len(in.Query) > 500 {
		return SearchResult{}, fmt.Errorf("query must contain 2 to 500 bytes")
	}
	if in.Limit == 0 {
		in.Limit = 5
	}
	if in.Limit < 1 || in.Limit > 10 {
		return SearchResult{}, fmt.Errorf("limit must be 1 to 10")
	}
	var err error
	in.Language, err = normalizeLanguage(in.Language)
	if err != nil {
		return SearchResult{}, err
	}
	return s.provider.Search(ctx, in)
}

func (s *Service) Transcript(ctx context.Context, in TranscriptInput) (TranscriptPage, error) {
	if !videoIDPattern.MatchString(in.VideoID) {
		return TranscriptPage{}, fmt.Errorf("video_id must be an 11-character YouTube ID")
	}
	language, err := normalizeLanguage(in.Language)
	if err != nil {
		return TranscriptPage{}, err
	}
	if in.Limit == 0 {
		in.Limit = 60
	}
	if in.FromCue < 0 || in.Limit < 1 || in.Limit > 100 {
		return TranscriptPage{}, fmt.Errorf("from_cue must be nonnegative and limit must be 1 to 100")
	}
	var transcript Transcript
	if in.TranscriptID != "" {
		transcript, err = s.getSnapshot(in.TranscriptID)
		if err != nil {
			return TranscriptPage{}, err
		}
		if transcript.VideoID != in.VideoID || transcript.Language != language {
			return TranscriptPage{}, fmt.Errorf("transcript snapshot does not match video_id and language")
		}
	} else {
		transcript, err = s.provider.Transcript(ctx, in.VideoID, language)
		if err != nil {
			return TranscriptPage{}, err
		}
		if len(transcript.Cues) == 0 || len(transcript.Cues) > 10000 {
			return TranscriptPage{}, fmt.Errorf("transcript must contain 1 to 10000 cues")
		}
		transcript.VideoID, transcript.Language = in.VideoID, language
		var lastStart int64 = -1
		for i := range transcript.Cues {
			cue := &transcript.Cues[i]
			cue.Index = i
			if cue.StartMS < 0 || cue.EndMS <= cue.StartMS || cue.StartMS < lastStart || len(cue.Text) > 4000 || strings.TrimSpace(cue.Text) == "" {
				return TranscriptPage{}, fmt.Errorf("invalid caption cue at index %d", i)
			}
			lastStart = cue.StartMS
		}
		transcript.ID = ""
		encoded, _ := json.Marshal(transcript)
		if len(encoded) > 4<<20 {
			return TranscriptPage{}, fmt.Errorf("transcript exceeds the pilot's 4 MiB snapshot limit")
		}
		transcript.ID = digest(encoded)
		s.putSnapshot(transcript)
	}
	if in.FromCue >= len(transcript.Cues) {
		return TranscriptPage{}, fmt.Errorf("from_cue exceeds transcript length")
	}
	end, chars := in.FromCue, 0
	for end < len(transcript.Cues) && end-in.FromCue < in.Limit {
		if chars+len(transcript.Cues[end].Text) > 20000 {
			break
		}
		chars += len(transcript.Cues[end].Text)
		end++
	}
	page := TranscriptPage{TranscriptID: transcript.ID, VideoID: transcript.VideoID, Language: transcript.Language, Source: transcript.Source, Cues: transcript.Cues[in.FromCue:end], TotalCues: len(transcript.Cues)}
	if end < len(transcript.Cues) {
		page.NextCue = &end
	}
	return page, nil
}

func (s *Service) Segment(_ context.Context, in SegmentInput) (Segment, error) {
	transcript, err := s.getSnapshot(in.TranscriptID)
	if err != nil {
		return Segment{}, err
	}
	if in.FirstCue < 0 || in.LastCue < in.FirstCue || in.LastCue >= len(transcript.Cues) {
		return Segment{}, fmt.Errorf("select an ordered range of existing cue indices")
	}
	if len(strings.TrimSpace(in.Title)) == 0 || len(in.Title) > 300 || len(strings.TrimSpace(in.Reason)) == 0 || len(in.Reason) > 2000 {
		return Segment{}, fmt.Errorf("title (1–300 bytes) and reason (1–2000 bytes) are required")
	}
	start := transcript.Cues[in.FirstCue].StartMS
	end := transcript.Cues[in.LastCue].EndMS
	texts := make([]string, 0, in.LastCue-in.FirstCue+1)
	for _, cue := range transcript.Cues[in.FirstCue : in.LastCue+1] {
		// Captions can overlap. Retain the full end of every selected cue.
		end = max(end, cue.EndMS)
		texts = append(texts, cue.Text)
	}
	text := strings.Join(texts, " ")
	if end-start > 300000 || len(text) > 20000 {
		return Segment{}, fmt.Errorf("select an excerpt no longer than 5 minutes and 20000 bytes")
	}
	// YouTube takes whole seconds; include the complete boundary captions.
	params := url.Values{"start": {fmt.Sprint(start / 1000)}, "end": {fmt.Sprint((end + 999) / 1000)}, "cc_load_policy": {"1"}, "cc_lang_pref": {transcript.Language}, "playsinline": {"1"}, "rel": {"0"}}
	segment := Segment{
		SegmentID: digest([]byte(fmt.Sprintf("%s:%d:%d", transcript.ID, in.FirstCue, in.LastCue))),
		VideoID:   transcript.VideoID, TranscriptID: transcript.ID, Source: transcript.Source, Language: transcript.Language,
		Title: in.Title, Reason: in.Reason, FirstCue: in.FirstCue, LastCue: in.LastCue,
		StartMS: start, EndMS: end, Text: text,
		WatchURL: fmt.Sprintf("https://www.youtube.com/watch?v=%s&t=%ds", transcript.VideoID, start/1000),
		EmbedURL: "https://www.youtube.com/embed/" + transcript.VideoID + "?" + params.Encode(),
	}
	if transcript.Source == "fixture" {
		// Synthetic captions must never be presented as evidence about a real video.
		segment.WatchURL, segment.EmbedURL = "", ""
	}
	return segment, nil
}

func digest(data []byte) string {
	hash := sha256.Sum256(data)
	return hex.EncodeToString(hash[:])
}

func (s *Service) putSnapshot(transcript Transcript) {
	s.mu.Lock()
	defer s.mu.Unlock()
	now := time.Now()
	for key, snap := range s.snaps {
		if !snap.expires.After(now) {
			delete(s.snaps, key)
		}
	}
	if _, exists := s.snaps[transcript.ID]; !exists && len(s.snaps) >= s.capacity {
		var oldest string
		var expiry time.Time
		for key, snap := range s.snaps {
			if oldest == "" || snap.expires.Before(expiry) {
				oldest, expiry = key, snap.expires
			}
		}
		delete(s.snaps, oldest)
	}
	s.snaps[transcript.ID] = snapshot{transcript: transcript, expires: now.Add(s.ttl)}
}

func (s *Service) getSnapshot(id string) (Transcript, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	snap, ok := s.snaps[id]
	if !ok || !snap.expires.After(time.Now()) {
		delete(s.snaps, id)
		return Transcript{}, fmt.Errorf("TRANSCRIPT_EXPIRED: fetch the transcript again and reselect cue indices")
	}
	return snap.transcript, nil
}
