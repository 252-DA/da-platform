package main

import "context"

type SearchInput struct {
	Query    string `json:"query" jsonschema:"Topic or learning outcome to search on YouTube"`
	Language string `json:"language,omitempty" jsonschema:"Preferred language, e.g. vi or en; default vi"`
	Limit    int    `json:"limit,omitempty" jsonschema:"Number of videos, 1 to 10; default 5"`
}

type Video struct {
	VideoID     string `json:"video_id"`
	Title       string `json:"title"`
	Channel     string `json:"channel"`
	Description string `json:"description"`
	WatchURL    string `json:"watch_url"`
}

type SearchResult struct {
	Source string  `json:"source"`
	Videos []Video `json:"videos"`
}

type TranscriptInput struct {
	VideoID      string `json:"video_id" jsonschema:"YouTube video ID returned by search, not a URL"`
	Language     string `json:"language,omitempty" jsonschema:"Exact caption language, default vi; retry en explicitly if unavailable"`
	FromCue      int    `json:"from_cue,omitempty" jsonschema:"Zero-based cue offset; default 0"`
	Limit        int    `json:"limit,omitempty" jsonschema:"Cues per page, 1 to 100; default 60"`
	TranscriptID string `json:"transcript_id,omitempty" jsonschema:"For subsequent pages, reuse the snapshot ID returned by the first page"`
}

type Cue struct {
	Index   int    `json:"index"`
	StartMS int64  `json:"start_ms"`
	EndMS   int64  `json:"end_ms"`
	Text    string `json:"text"`
}

type Transcript struct {
	ID       string `json:"transcript_id"`
	VideoID  string `json:"video_id"`
	Language string `json:"language"`
	Source   string `json:"source"`
	Cues     []Cue  `json:"cues"`
}

type TranscriptPage struct {
	TranscriptID string `json:"transcript_id"`
	VideoID      string `json:"video_id"`
	Language     string `json:"language"`
	Source       string `json:"source"`
	Cues         []Cue  `json:"cues"`
	TotalCues    int    `json:"total_cues"`
	NextCue      *int   `json:"next_cue"`
}

type SegmentInput struct {
	TranscriptID string `json:"transcript_id" jsonschema:"Snapshot ID from get_youtube_transcript"`
	FirstCue     int    `json:"first_cue" jsonschema:"First relevant cue index, inclusive"`
	LastCue      int    `json:"last_cue" jsonschema:"Last relevant cue index, inclusive"`
	Title        string `json:"title" jsonschema:"Short title describing this excerpt"`
	Reason       string `json:"reason" jsonschema:"Explain how the cited transcript supports the learning topic; do not invent evidence"`
}

type Segment struct {
	SegmentID    string `json:"segment_id"`
	VideoID      string `json:"video_id"`
	TranscriptID string `json:"transcript_id"`
	Source       string `json:"source"`
	Language     string `json:"language"`
	Title        string `json:"title"`
	Reason       string `json:"reason"`
	FirstCue     int    `json:"first_cue"`
	LastCue      int    `json:"last_cue"`
	StartMS      int64  `json:"start_ms"`
	EndMS        int64  `json:"end_ms"`
	Text         string `json:"text"`
	WatchURL     string `json:"watch_url"`
	EmbedURL     string `json:"embed_url"`
}

type Provider interface {
	Search(context.Context, SearchInput) (SearchResult, error)
	Transcript(context.Context, string, string) (Transcript, error)
}
