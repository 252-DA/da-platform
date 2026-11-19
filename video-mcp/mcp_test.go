package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestMCPHTTPWorkflow(t *testing.T) {
	server := httptest.NewServer(newHandler(NewService(DemoProvider{}), "demo", ""))
	defer server.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	client := mcp.NewClient(&mcp.Implementation{Name: "workflow-test", Version: "1"}, nil)
	session, err := client.Connect(ctx, &mcp.StreamableClientTransport{Endpoint: server.URL + "/mcp"}, nil)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()
	tools, err := session.ListTools(ctx, nil)
	if err != nil || len(tools.Tools) != 3 {
		t.Fatalf("tools=%+v error=%v", tools, err)
	}
	call := func(name string, arguments any, out any) {
		t.Helper()
		result, err := session.CallTool(ctx, &mcp.CallToolParams{Name: name, Arguments: arguments})
		if err != nil {
			t.Fatal(err)
		}
		if result.IsError {
			t.Fatalf("%s: %+v", name, result.Content)
		}
		data, err := json.Marshal(result.StructuredContent)
		if err != nil {
			t.Fatal(err)
		}
		if err := json.Unmarshal(data, out); err != nil {
			t.Fatal(err)
		}
	}
	var search SearchResult
	call("search_youtube_videos", map[string]any{"query": "deadlock"}, &search)
	if len(search.Videos) != 1 {
		t.Fatalf("%+v", search)
	}
	var page TranscriptPage
	call("get_youtube_transcript", map[string]any{"video_id": search.Videos[0].VideoID}, &page)
	var segment Segment
	call("create_youtube_segment", SegmentInput{TranscriptID: page.TranscriptID, FirstCue: 1, LastCue: 4, Title: "Coffman", Reason: "Cues explain the four conditions and prevention."}, &segment)
	if segment.StartMS != 252000 || segment.EndMS != 378000 || !strings.Contains(segment.Text, "Coffman") || segment.Source != "fixture" {
		t.Fatalf("incorrect grounded segment: %+v", segment)
	}
	bad, err := session.CallTool(ctx, &mcp.CallToolParams{Name: "create_youtube_segment", Arguments: SegmentInput{TranscriptID: page.TranscriptID, FirstCue: 1, LastCue: 99, Title: "x", Reason: "x"}})
	if err != nil || !bad.IsError {
		t.Fatalf("invalid cues must return MCP tool error: %+v %v", bad, err)
	}
}

func TestHTTPRejectsCrossOriginRequestsAndRequiresConfiguredToken(t *testing.T) {
	handler := newHandler(NewService(DemoProvider{}), "demo", "secret")
	for _, input := range []struct {
		host, origin, auth string
		want               int
	}{
		{"localhost:8002", "", "", http.StatusUnauthorized},
		{"localhost:8002", "https://evil.example", "Bearer secret", http.StatusForbidden},
		{"evil.example:8002", "", "Bearer secret", http.StatusForbidden},
		{"localhost:8002", "http://localhost:8002", "Bearer secret", http.StatusOK},
	} {
		req := httptest.NewRequest("POST", "http://"+input.host+"/api/search", strings.NewReader(`{"query":"deadlock"}`))
		req.Header.Set("Origin", input.origin)
		req.Header.Set("Authorization", input.auth)
		rec := httptest.NewRecorder()
		handler.ServeHTTP(rec, req)
		if rec.Code != input.want {
			t.Errorf("%+v: got %d, body=%s", input, rec.Code, rec.Body)
		}
	}
}
