package main

import (
	"context"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestSearchAPIUsesBoundedVideoSearch(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/search" || r.URL.Query().Get("type") != "video" || r.URL.Query().Get("videoEmbeddable") != "true" || r.URL.Query().Get("maxResults") != "3" || r.URL.Query().Get("relevanceLanguage") != "vi" {
			t.Errorf("unexpected search parameters: %s", r.URL)
		}
		if r.Header.Get("X-Goog-Api-Key") != "test-secret" || strings.Contains(r.URL.String(), "test-secret") {
			t.Error("API key should be sent in a header")
		}
		fmt.Fprint(w, `{"items":[{"id":{"videoId":"M7lc1UVf-VE"},"snippet":{"title":"A &amp; B","channelTitle":"Course","description":"Intro"}},{"id":{"videoId":"invalid"}}]}`)
	}))
	defer server.Close()
	p := NewYouTubeProvider("test-secret", "unused")
	p.APIBase = server.URL
	result, err := p.Search(context.Background(), SearchInput{Query: "deadlock", Language: "vi", Limit: 3})
	if err != nil || len(result.Videos) != 1 || result.Videos[0].Title != "A & B" {
		t.Fatalf("unexpected result: %+v %v", result, err)
	}
}

func TestYTDLPSearchCannotInterpretQueryAsShell(t *testing.T) {
	p := NewYouTubeProvider("", "unused")
	p.Run = func(_ context.Context, args ...string) ([]byte, error) {
		if args[len(args)-2] != "--" || args[len(args)-1] != "ytsearch2:$(touch /tmp/not-a-command)" {
			t.Fatalf("query must be one argument after option separator: %#v", args)
		}
		return []byte(`{"entries":[{"id":"M7lc1UVf-VE","title":"A"}]}`), nil
	}
	result, err := p.Search(context.Background(), SearchInput{Query: "$(touch /tmp/not-a-command)", Limit: 2})
	if err != nil || len(result.Videos) != 1 {
		t.Fatalf("%+v %v", result, err)
	}
}

func TestCaptionExtractionNeverDownloadsVideoAndCleansFiles(t *testing.T) {
	p := NewYouTubeProvider("", "unused")
	var tempDir string
	p.Run = func(_ context.Context, args ...string) ([]byte, error) {
		joined := strings.Join(args, " ")
		if !strings.Contains(joined, "--skip-download") || !strings.Contains(joined, "--sub-format json3") || !strings.Contains(joined, "--sub-langs ^vi$") {
			t.Fatalf("unsafe or unexpected extraction: %v", args)
		}
		for i, arg := range args {
			if arg == "--output" {
				tempDir = filepath.Dir(args[i+1])
			}
		}
		return nil, os.WriteFile(filepath.Join(tempDir, "captions.vi.json3"), []byte(`{"events":[{"tStartMs":252250,"dDurationMs":10000,"segs":[{"utf8":"Hello "},{"utf8":"world"}]}]}`), 0600)
	}
	result, err := p.Transcript(context.Background(), "M7lc1UVf-VE", "vi")
	if err != nil || len(result.Cues) != 1 || result.Cues[0].StartMS != 252250 || result.Cues[0].Text != "Hello world" {
		t.Fatalf("%+v %v", result, err)
	}
	if _, err := os.Stat(tempDir); !os.IsNotExist(err) {
		t.Fatal("temporary captions were not removed")
	}
	p.Run = func(context.Context, ...string) ([]byte, error) { return nil, nil }
	if _, err := p.Transcript(context.Background(), "M7lc1UVf-VE", "vi"); err == nil || !strings.Contains(err.Error(), "TRANSCRIPT_UNAVAILABLE") {
		t.Fatalf("missing captions should have a useful error: %v", err)
	}
}

func TestJSON3IgnoresWindowEventsAndPreservesTimes(t *testing.T) {
	cues, err := parseJSON3([]byte(`{"events":[{"tStartMs":1000,"dDurationMs":2000,"segs":[{"utf8":"line\n two &amp; three"}]},{"tStartMs":0,"dDurationMs":1000,"segs":[{"utf8":"first"}]},{"tStartMs":500,"segs":[{"utf8":"\n"}]},{"tStartMs":0,"dDurationMs":0,"segs":[{"utf8":"no timing"}]}]}`))
	if err != nil || len(cues) != 2 || cues[0].Text != "first" || cues[1].Text != "line two & three" || cues[1].EndMS != 3000 {
		t.Fatalf("%+v %v", cues, err)
	}
	if _, err := parseJSON3([]byte(`{"events":[{"tStartMs":-1,"dDurationMs":100,"segs":[{"utf8":"bad"}]}]}`)); err == nil {
		t.Fatal("negative timestamp accepted")
	}
}
