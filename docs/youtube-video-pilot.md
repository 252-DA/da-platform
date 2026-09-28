# Video discovery: search trước, chọn đoạn sau

## Quyết định cho bản thử

- Go service mới: `video-mcp/`, endpoint MCP `/mcp`, port 8002.
- Nguồn là video YouTube bên ngoài, tìm theo LO hoặc nội dung card.
- “Cắt” là một đoạn phát nhúng: YouTube video ID + mốc đầu/cuối + transcript
  làm bằng chứng. Không tải video, FFmpeg, clip storage hoặc Kafka trong luồng này.
- Giao diện thử độc lập để kiểm tra search/caption/player trước khi sửa learner UI.
- Dùng YouTube Data API khi có key, yt-dlp cho tìm công khai khi chưa có key và
  lấy phụ đề. MCP là giao diện tool, không phải một search engine.

## Luồng tích hợp AI dự kiến

1. Core xác thực instructor và membership, lấy LO + card/chunk đã duyệt.
2. Agent tạo query ngắn, nêu rõ chủ đề, ngôn ngữ, mức giải thích mong muốn.
3. Gọi `search_youtube_videos`, giới hạn 3–5 ứng viên.
4. Gọi `get_youtube_transcript` trên các ứng viên phù hợp, đọc tiếp từng trang
   bằng cùng snapshot ID. Không có captions thì thử video khác. Bản thử chưa STT.
5. Agent chọn một dải cue liên tiếp giải thích đúng nội dung, đủ ngữ cảnh và
   không kéo sang chủ đề khác; nếu không có bằng chứng thì trả về không có gợi ý.
6. Gọi `create_youtube_segment`; backend xác minh cue và tính timestamp từ nguồn.
7. Instructor xem đoạn, đọc transcript/reason, rồi chọn gắn vào card.
8. Core lưu dữ liệu và learner phát iframe theo mốc đã chọn.

Bước 3–6 đã có tool; agent chọn ngữ nghĩa, tích hợp tutor, bước 1–2 và 7–8 là
phần tiếp theo. Trang thử thực hiện việc chọn cue thủ công. Không tuyên bố đã có
AI ranking hoặc cơ chế tự động lưu/publish.

## Ranh giới dữ liệu hiện có

- `videos.video_id` là UUID nội bộ; YouTube ID là chuỗi 11 ký tự. Không dùng lẫn.
- `videos.is_youtube=true`, `external_url` lưu URL chuẩn. `file_path` hiện bắt
  buộc; khi thêm persistence nên migration cho phép null với nguồn YouTube
  thay vì bịa đường dẫn MinIO. Cần lưu YouTube ID có ràng buộc chống trùng theo
  phạm vi course.
- `video_segments` đã có `start_ms`, `end_ms`, `title`. `clip_url` để null đối
  với đoạn nhúng. Bổ sung provenance: language, caption snapshot hash, cue range,
  lý do chọn, phiên bản selector và trạng thái duyệt.
- `transcript_segments` có thể lưu bằng chứng đã chọn. Bản thử đang dùng snapshot
  RAM; khi persistence cần xác định rõ đơn vị cue/segment và dedup.
- `card_video_attachments` dùng để gắn đoạn đã duyệt vào card.
- Không trộn caption lấy từ YouTube vào `documents`/Qdrant mà chưa có source type
  và filter quyền truy cập. Search YouTube này độc lập với search tài liệu nội bộ.

## Kafka và phần tải/cắt file sau này

Search tương tác và tạo URL nhúng không cần Kafka. Khi thực sự thêm STT, batch
index hoặc xuất clip lâu, thêm tác vụ bền vững qua outbox với contract riêng.
Không để lựa chọn broker chặn bản thử video discovery này.

## Chạy thử

Xem [video-mcp/README.md](../video-mcp/README.md) cho live/demo, MCP tools,
Docker/local và kiểm tra bằng Python client đang dùng trong worker.
