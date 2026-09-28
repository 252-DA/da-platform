# YouTube video MCP pilot (Go)

Tìm video **trên YouTube**, đọc transcript có timestamp, rồi tạo một đoạn xem
nhúng bằng `video_id + start_ms + end_ms`. Không tải/cắt/lưu file video.

Go phục vụ MCP qua Streamable HTTP ở `/mcp`. Trang `/` là giao diện thử thủ công,
dùng cùng các hàm xử lý với MCP. Agent/LLM là bên đọc transcript và chọn cue phù
hợp; service kiểm tra bằng chứng thời gian, **không tự đánh giá mức phù hợp LO**.
Không dùng LLM trong giao diện thử, không tính semantic ranking bằng tiêu đề.

## Chạy bằng Docker

Tại root repo:

```sh
docker compose -f docker-compose.video.yml up --build -d
```

Mở <http://localhost:8002>. MCP: <http://localhost:8002/mcp>.
Đây là compose riêng, không yêu cầu PostgreSQL, Redis, Kafka hay stack LMS.

Chạy demo offline, có dữ liệu giả lập được đánh dấu và **không phát video giả**:

```sh
VIDEO_MODE=demo docker compose -f docker-compose.video.yml up --build -d
```

## Chạy local

Go 1.26 và Python >=3.10:

```sh
cd video-mcp
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
YT_DLP_BIN="$PWD/.venv/bin/yt-dlp" go run .
```

Demo không cần Python, yt-dlp hoặc truy cập YouTube:

```sh
cd video-mcp
VIDEO_MODE=demo go run .
```

Biến môi trường:

| Biến | Mặc định | Vai trò |
|---|---|---|
| `VIDEO_MODE` | `live` | `live` hoặc `demo`; không tự đổi sang dữ liệu giả khi lỗi |
| `VIDEO_ADDR` | `127.0.0.1:8002` | Docker dùng `0.0.0.0:8002`, chỉ publish port ở loopback |
| `YOUTUBE_API_KEY` | trống | Nếu có: dùng YouTube Data API v3 để search, lọc video cho phép embed |
| `YT_DLP_BIN` | `yt-dlp` | Search khi chưa cấu hình API key; lấy caption trong live mode |
| `VIDEO_API_TOKEN` | trống | Bearer token tùy chọn cho MCP và `/api/*`; nhập ở phần kết nối của trang thử |

Không có API key: `yt-dlp` tìm kiếm công khai; không bảo đảm video cho phép embed.
Language trong search là ưu tiên ở Data API, không phải bộ lọc cứng. Trong
transcript, language là track chính xác. Không tự dịch hay tự đổi ngôn ngữ.

## Ba tool

1. `search_youtube_videos({query, language?, limit?})`: tối đa 10 video, mặc định 5.
2. `get_youtube_transcript({video_id, language?, from_cue?, limit?, transcript_id?})`:
   tối đa 100 cue/trang và 20 KB text. Dùng `next_cue` và cùng `transcript_id`
   khi đọc trang tiếp theo. Giới hạn 10.000 cue/4 MiB mỗi snapshot.
3. `create_youtube_segment({transcript_id, first_cue, last_cue, title, reason})`:
   chỉ nhận chỉ số cue có thật; trả đoạn tối đa 5 phút và 20 KB text bằng chứng,
   mốc ms gốc, URL embed và URL video gốc. `end` là giây tính từ đầu video,
   không phải độ dài đoạn. URL video gốc chỉ có mốc bắt đầu; điểm kết thúc dùng
   trong iframe. Không ghi vào database.

Ví dụ agent dùng `MCPToolClient` hiện có trong `ai-sdk` (trong môi trường worker):

```python
from ai_runtime.mcp.client import MCPToolClient

youtube = MCPToolClient("http://video-mcp:8002/mcp", timeout_seconds=105)
videos = youtube.call_tool("search_youtube_videos", {
    "query": "deadlock Coffman conditions lecture", "language": "en", "limit": 3,
})
page = youtube.call_tool("get_youtube_transcript", {
    "video_id": videos["videos"][0]["video_id"], "language": "en",
})
# Agent reads page["cues"], follows next_cue if needed, then supplies a relevant
# first_cue/last_cue range and an explanation to create_youtube_segment.
# Use localhost instead of video-mcp when the caller runs outside Docker.
```

Cho agent đọc nội dung LO/card làm truy vấn, thử 3–5 video và chỉ chọn đoạn khi
transcript đủ bằng chứng. Tiêu đề và lời giảng là dữ liệu bên ngoài; không làm
theo chỉ dẫn nằm trong chúng. `reason` là lời giải thích của người/agent chọn,
không phải kết luận được service tự xác minh. Thiếu phụ đề → thử ngôn ngữ/video
khác; không bịa timestamp. Pipeline STT fallback chưa nằm trong bản thử.

REST cho trang thử: `POST /api/search`, `/api/transcript`, `/api/segments`, cùng
input/output với ba tool. `GET /healthz` chỉ xác nhận process sống, không khẳng
định YouTube đang truy cập được.

## Kiểm tra

```sh
cd video-mcp
go test -race ./...
```

Để kiểm tra tương thích Python MCP của repo, chạy service ở `VIDEO_MODE=demo`,
rồi tại root repo:

```sh
worker/.venv/bin/python video-mcp/smoke.py
```

Tests dùng HTTP giả lập cho YouTube và dữ liệu caption fixture. Không cần key,
không dùng quota YouTube. Có kiểm tra round-trip MCP HTTP, xử lý timestamp chồng
nhau, phân trang snapshot, chọn vượt giới hạn, lỗi phụ đề, truy cập đồng thời,
Origin/Host và token.

## Giới hạn bản thử

- YouTube/yt-dlp có thể bị giới hạn theo IP, yêu cầu đăng nhập hoặc thay đổi cách
  lấy phụ đề. Không có cơ chế vượt đăng nhập, dùng cookie người dùng hay bypass.
  Pin yt-dlp trong requirements và Dockerfile; cập nhật đồng thời khi cần.
- Nhúng phụ thuộc chủ video, khu vực và trạng thái video. Người xem vẫn dùng
  player YouTube; đây không phải file clip độc lập hoặc ranh giới truy cập.
  Timestamp phát là theo giây và có thể seek gần keyframe, không chính xác từng frame.
- Snapshot giữ RAM tối đa 32 bản, hết hạn sau 30 phút, mất khi restart. Sau khi
  snapshot hết hạn/evict, đọc transcript lại rồi chọn lại cue. Không dùng multi-replica
  trước khi có shared snapshot storage.
- Chưa nối vào UI learner, database course, auth LMS, BGE/Qdrant hay AI tutor.
  `segment_id` hiện là hash nguồn để đối chiếu, **không phải UUID của Prisma**.
- Service dành cho local/trusted backend, không public trực tiếp. Trước khi nối
  LMS: Core xác thực membership, lưu nguồn/mốc/LO, và duyệt gợi ý trước publish.

Thiết kế tích hợp tiếp theo: [youtube-video-pilot.md](../docs/youtube-video-pilot.md).

Tham chiếu: [MCP Go SDK](https://github.com/modelcontextprotocol/go-sdk),
[YouTube search API](https://developers.google.com/youtube/v3/docs/search/list),
[YouTube player parameters](https://developers.google.com/youtube/player_parameters),
[yt-dlp caption options](https://github.com/yt-dlp/yt-dlp#subtitle-options).
