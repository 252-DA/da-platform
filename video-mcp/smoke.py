"""Exercise the Go server through the same Python MCP SDK used by AI workers.

Defaults to VIDEO_MODE=demo. --live makes real YouTube requests.
Requires the existing worker virtual environment.
"""

import argparse
import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main(url: str, live: bool, query: str, language: str) -> None:
    async with streamable_http_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == {
                "search_youtube_videos",
                "get_youtube_transcript",
                "create_youtube_segment",
            }

            async def call(name, arguments):
                result = await asyncio.wait_for(session.call_tool(name, arguments), timeout=105)
                if result.isError:
                    raise RuntimeError(str(result.content))
                return result.structuredContent

            search = await call("search_youtube_videos", {"query": query, "language": language, "limit": 3})
            if live:
                assert search["source"] != "fixture", "--live requires VIDEO_MODE=live"
                print(json.dumps(search, ensure_ascii=False, indent=2), flush=True)
                transcript = None
                for video in search["videos"]:
                    try:
                        transcript = await call("get_youtube_transcript", {
                            "video_id": video["video_id"], "language": language,
                        })
                        break
                    except RuntimeError as exc:
                        print(f"No transcript for {video['video_id']}: {exc}", flush=True)
                if transcript is None:
                    raise RuntimeError("Search succeeded but none of the candidates supplied captions")
                first, last = 0, 0
                title = "Integration test excerpt (not an AI recommendation)"
                reason = "First caption used only to verify source timestamps and embed generation."
            else:
                assert search["source"] == "fixture", "Run this smoke test against VIDEO_MODE=demo"
                transcript = await call("get_youtube_transcript", {
                    "video_id": search["videos"][0]["video_id"], "language": "vi",
                })
                first, last = 1, 4
                title = "Deadlock và bốn điều kiện Coffman"
                reason = "Các dòng 1–4 giải thích điều kiện, ví dụ và cách phá chờ vòng tròn."
            segment = await call(
                "create_youtube_segment",
                {
                    "transcript_id": transcript["transcript_id"],
                    "first_cue": first,
                    "last_cue": last,
                    "title": title,
                    "reason": reason,
                },
            )
            if live:
                assert segment["source"] == "youtube-captions" and segment["embed_url"]
                assert segment["start_ms"] == transcript["cues"][first]["start_ms"]
                assert segment["end_ms"] >= transcript["cues"][last]["end_ms"]
            else:
                assert segment["start_ms"] == 252000
                assert segment["end_ms"] == 378000
                assert segment["source"] == "fixture" and not segment["embed_url"]
            print(json.dumps(segment, ensure_ascii=False, indent=2))
            print("PASS: Python MCP client → Go MCP server → grounded segment")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8002/mcp")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--query", default="deadlock điều kiện Coffman")
    parser.add_argument("--language", default="vi")
    args = parser.parse_args()
    asyncio.run(main(args.url, args.live, args.query, args.language))
