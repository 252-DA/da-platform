package main

import (
	"context"
	"fmt"
	"net/url"
	"strings"
	"sync"
	"testing"
	"time"
)

type fakeProvider struct {
	DemoProvider
	calls int
	mu    sync.Mutex
}

func (p *fakeProvider) Transcript(_ context.Context, id, language string) (Transcript, error) {
	p.mu.Lock()
	p.calls++
	p.mu.Unlock()
	return Transcript{VideoID: id, Language: language, Source: "youtube-captions", Cues: []Cue{
		{StartMS: 252250, EndMS: 270250, Text: "Deadlock definition"},
		{StartMS: 270250, EndMS: 310100, Text: "The four Coffman conditions"},
		{StartMS: 300000, EndMS: 309000, Text: "Overlapping caption"},
	}}, nil
}

func TestTranscriptSnapshotAndSegmentBoundaries(t *testing.T) {
	ctx := context.Background()
	provider := &fakeProvider{}
	s := NewService(provider)
	page, err := s.Transcript(ctx, TranscriptInput{VideoID: "M7lc1UVf-VE", Limit: 1})
	if err != nil || page.NextCue == nil || *page.NextCue != 1 || page.TotalCues != 3 {
		t.Fatalf("first page: %+v %v", page, err)
	}
	second, err := s.Transcript(ctx, TranscriptInput{VideoID: "M7lc1UVf-VE", TranscriptID: page.TranscriptID, FromCue: *page.NextCue, Limit: 2})
	if err != nil || provider.calls != 1 || second.NextCue != nil || second.Cues[0].Index != 1 {
		t.Fatalf("pagination must reuse the snapshot: %+v, calls=%d, err=%v", second, provider.calls, err)
	}
	input := SegmentInput{TranscriptID: page.TranscriptID, FirstCue: 0, LastCue: 2, Title: "Coffman conditions", Reason: "Transcript explicitly names the four conditions."}
	segment, err := s.Segment(ctx, input)
	if err != nil {
		t.Fatal(err)
	}
	parsed, _ := url.Parse(segment.EmbedURL)
	if segment.StartMS != 252250 || segment.EndMS != 310100 || parsed.Query().Get("start") != "252" || parsed.Query().Get("end") != "311" {
		t.Fatalf("timestamps must include boundary cues and use absolute seconds: %+v", segment)
	}
	if !strings.Contains(segment.Text, "Coffman") || !strings.Contains(segment.WatchURL, "t=252s") {
		t.Fatalf("missing evidence or source link: %+v", segment)
	}
	input.Title = "Different label for the same source range"
	again, _ := s.Segment(ctx, input)
	if again.SegmentID != segment.SegmentID {
		t.Fatal("source range must have a stable identity")
	}
	for _, wrong := range []SegmentInput{
		{TranscriptID: "invented", FirstCue: 0, LastCue: 1, Title: "x", Reason: "x"},
		{TranscriptID: page.TranscriptID, FirstCue: -1, LastCue: 1, Title: "x", Reason: "x"},
		{TranscriptID: page.TranscriptID, FirstCue: 2, LastCue: 1, Title: "x", Reason: "x"},
		{TranscriptID: page.TranscriptID, FirstCue: 0, LastCue: 99, Title: "x", Reason: "x"},
	} {
		if _, err := s.Segment(ctx, wrong); err == nil {
			t.Fatalf("accepted fabricated or invalid selection: %+v", wrong)
		}
	}
	if _, err := s.Transcript(ctx, TranscriptInput{VideoID: "M7lc1UVf-VE", Language: "en", TranscriptID: page.TranscriptID}); err == nil {
		t.Fatal("must not mix caption languages within a snapshot")
	}
}

func TestSnapshotExpiryEvictionAndDurationLimit(t *testing.T) {
	s := NewService(DemoProvider{})
	s.capacity = 1
	s.putSnapshot(Transcript{ID: "old", VideoID: "demo0000001", Cues: []Cue{{StartMS: 0, EndMS: 301000, Text: "too long"}}})
	if _, err := s.Segment(context.Background(), SegmentInput{TranscriptID: "old", Title: "x", Reason: "x"}); err == nil {
		t.Fatal("must reject clips over five minutes")
	}
	s.putSnapshot(Transcript{ID: "new"})
	if _, err := s.getSnapshot("old"); err == nil {
		t.Fatal("oldest snapshot must be evicted at capacity")
	}
	s.ttl = -time.Second
	s.putSnapshot(Transcript{ID: "expired"})
	if _, err := s.getSnapshot("expired"); err == nil {
		t.Fatal("expired transcript must not produce a stale selection")
	}
}

func TestInputValidationAndConcurrentReaders(t *testing.T) {
	s := NewService(&fakeProvider{})
	ctx := context.Background()
	for _, input := range []TranscriptInput{{VideoID: "https://localhost/admin"}, {VideoID: "M7lc1UVf-VE", Language: "../../en"}, {VideoID: "M7lc1UVf-VE", Limit: 101}, {VideoID: "M7lc1UVf-VE", FromCue: -1}} {
		if _, err := s.Transcript(ctx, input); err == nil {
			t.Fatalf("accepted unsafe input: %+v", input)
		}
	}
	var wg sync.WaitGroup
	for i := 0; i < 20; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			page, err := s.Transcript(ctx, TranscriptInput{VideoID: "M7lc1UVf-VE"})
			if err != nil {
				t.Error(err)
				return
			}
			if _, err := s.Segment(ctx, SegmentInput{TranscriptID: page.TranscriptID, FirstCue: 0, LastCue: 1, Title: "x", Reason: "x"}); err != nil {
				t.Error(err)
			}
		}()
	}
	wg.Wait()
}

func TestDemoNeverClaimsRealVideoEvidence(t *testing.T) {
	s := NewService(DemoProvider{})
	page, err := s.Transcript(context.Background(), TranscriptInput{VideoID: "demo0000001"})
	if err != nil {
		t.Fatal(err)
	}
	segment, err := s.Segment(context.Background(), SegmentInput{TranscriptID: page.TranscriptID, FirstCue: 1, LastCue: 4, Title: "Coffman", Reason: "fixture"})
	if err != nil || segment.Source != "fixture" || segment.WatchURL != "" || segment.EmbedURL != "" {
		t.Fatal(fmt.Sprintf("demo is not real source evidence: %+v %v", segment, err))
	}
}
