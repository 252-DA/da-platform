# Quản lý video bằng MediaCMS (hướng B)

| | |
|---|---|
| Trạng thái | Đề xuất, **tạm dừng để đối chiếu**. Nhánh `origin/feat/micro-content-feature` (Bình, 04/11) đã có thiết kế DAM `video_assets` và lưu trữ Backblaze B2 (`docs/tai_lieu_ky_thuat_video_asset_dam.md`, `docs/tai_lieu_kien_truc_luu_tru_cloud_b2.md`), trùng phạm vi §4–§5. Phải đọc code đó, rồi đặt MediaCMS dưới `video_assets` thay vì mở rộng `videos`, hoặc bỏ hướng này. Chưa có code, chưa chạy thử MediaCMS |
| Ngày | 2026-11-05 |
| Phạm vi | `core-api` (schema `videos`, micro-content, RPC phát video), `worker` (worker video mới), `web` (route proxy HLS, trình phát cho học viên, trang quản lý), hạ tầng (MediaCMS chạy riêng), renderer `video-lms` |
| Liên quan | [ra-soat-bao-ve-2026-11-03.md](ra-soat-bao-ve-2026-11-03.md) §2B–C: các phần video còn thiếu. [youtube-video-pilot.md](youtube-video-pilot.md): video YouTube dùng `videos.is_youtube` |

---

## 0. Tóm tắt

- **Hai lớp, hai chủ.** Platform giữ phần *quản lý nội dung*: video thuộc khóa, chương, LO nào; kịch bản; trạng thái; ai duyệt; xuất bản; tiến độ học viên. MediaCMS chỉ làm phần *xử lý media*: lưu bản phát, chuyển mã, HLS, thumbnail, và (giai đoạn sau) nhận dạng giọng nói cho video tự upload.
- **MediaCMS chạy ẩn phía sau, không lộ ra người dùng.** Không dùng LTI, giao diện hay tài khoản người dùng của MediaCMS. Chỉ có một tài khoản dịch vụ gọi REST API. Học viên xem video qua trình phát của mình. BFF kiểm quyền rồi chuyển tiếp HLS từ MediaCMS.
- **MinIO giữ bản gốc (master MP4 + phụ đề VTT).** MediaCMS giữ bản đã chuyển mã. Nhờ vậy có thể đẩy lại vào MediaCMS, hoặc đổi sang backend khác chỉ bằng một adapter, mà không phải render lại.
- **Một bảng tài sản video: mở rộng bảng `videos` sẵn có** (hiện 0 dòng), thay vì để các cột video rải trong `micro_contents`. Mỗi lần render là một dòng mới, nên có phiên bản. Cảnh của video AI ghi vào `video_segments`, câu thoại ghi vào `transcript_segments`.
- **Làm luồng upload trước, render AI sau.** Luồng upload không cần renderer, nên làm trước thì có ngay trình phát cho học viên, phần mà rà soát 03/11 ghi là còn thiếu.

## 1. Mục tiêu và ngoài phạm vi

Mục tiêu:
1. Quản lý được hàng trăm video ngắn do AI sinh: trạng thái từng bước, lỗi, render lại, phiên bản, dọn file.
2. Phát ổn định cho học viên trong Canvas (iframe LTI): HLS nhiều mức bitrate, phụ đề, ghi tiến độ xem.
3. Dùng chung đường xử lý cho video giảng viên tự upload.
4. Không khóa chặt vào MediaCMS: đổi backend media chỉ cần một adapter mới.

Ngoài phạm vi:
- Cách sinh video (kịch bản, TTS, dựng cảnh): phần này do renderer `video-lms` lo. Tài liệu này chỉ định nghĩa hợp đồng với nó (§6.2).
- Video YouTube: giữ như [youtube-video-pilot.md](youtube-video-pilot.md), không đi qua MediaCMS.
- LTI của MediaCMS, plugin Moodle, giao diện MediaCMS cho giảng viên.

## 2. Kiến trúc

```
Canvas ──LTI──▶ web (Next.js BFF) ──gRPC──▶ core-api ──outbox──▶ BullMQ "micro_content_video"
                 │   ▲                         │                          │
   /api/videos/… │   │ playback token          │ Postgres: videos,        ▼
   (HLS, VTT)    │   │ (ký bởi core-api)       │ video_segments, …    worker: video_worker
                 ▼   │                         │                          │
        ┌───────────────────────┐              │            ┌─────────────┼──────────────┐
        │ MediaCMS (nội bộ)     │◀──REST: upload, poll, xóa ─┘             │              │
        │ nginx · Django ·      │                                         ▼              ▼
        │ Celery · ffmpeg · PG  │                              Renderer video-lms    MinIO
        └───────────────────────┘                              kịch bản → MP4 +      master.mp4,
                                                               mốc thời gian         captions.vtt
```

| Thành phần | Việc | Ghi chú |
|---|---|---|
| core-api | Nguồn sự thật: bảng `videos`, quyền, trạng thái micro-content, ký playback token | Đã có `requestRender`/`requestScript` phát outbox event |
| worker `video_worker` | Tiêu thụ queue `micro_content_video`: gọi renderer, ghi MinIO, đẩy MediaCMS, hỏi trạng thái encode, cập nhật `videos` | Mở rộng `micro_content_video_worker` của Bình (worker `origin/dev`, 17/10), hiện render rồi ghi thẳng MinIO và đặt `READY` |
| Renderer | Kịch bản → MP4 + mốc thời gian từng cảnh/câu | Bản tạm: renderer slide của Bình trong worker (Pillow + edge-tts + ffmpeg). Bản sau: `video-lms` (Manim, VieNeu-TTS) trên WSL, chưa tích hợp |
| MediaCMS | Chuyển mã h264, HLS, thumbnail; Whisper cho video upload (GĐ4) | Chỉ truy cập trong mạng nội bộ / Tailscale |
| MinIO | Bản gốc và phụ đề | Đã có presigned upload trong `micro-content-video.service.ts` |
| web | Proxy HLS/VTT có kiểm token, trình phát (hls.js), trang quản lý | Theo khuôn route `/api/documents/[id]/file` (chuyển tiếp Range) |

**Vì sao không dùng LTI của MediaCMS:** platform đã là LTI tool của Canvas. Thêm MediaCMS làm tool thứ hai thì có hai lần launch và hai hệ phân quyền. Ngoài ra, code LTI của MediaCMS viết cho Moodle (`lti/views.py` ghi "Flow: Moodle → …"), Canvas chưa có tài liệu.

## 3. MediaCMS: đã xác minh và chưa xác minh

Đọc mã nguồn bản **v9.4.0 (26/10/2026)**, giấy phép AGPL-3.0.

| Đã xác minh trong mã nguồn | Nguồn |
|---|---|
| Upload qua `POST /api/v1/media` (multipart `media_file`, `title`, `description`) | `docs/developers_docs.md` |
| API nhận Session, Basic và **Token** | `cms/settings.py` `REST_FRAMEWORK` |
| `GET /api/v1/media/{friendly_token}` trả `encoding_status`, `encodings_info`, `hls_info`, `subtitles_info`, `chapter_data`, `duration`, `thumbnail_url`, `poster_url`, `original_media_url`, `state` | `files/serializers.py` `SingleMediaSerializer` |
| Đổi trạng thái `private`/`unlisted` qua `POST /api/v1/media/user/bulk_actions` (`set_state`). Người thường không được đặt `public` | `files/views/media.py` |
| File `encoded/`, `hls/`, `original/` được nginx bảo vệ bằng `auth_request /_media_auth`. Media `public`/`unlisted` ai cũng tải được; `private` chỉ chủ sở hữu, người được chia sẻ và editor | `deploy/docker/nginx_http_only.conf`, `files/views/media_auth.py` |
| Có API chapters: `/api/v1/media/{token}/chapters` | `files/urls.py` |
| Whisper chạy local, phải dùng image `mediacms-full`, `WHISPER_MODEL = "base"` mặc định | `cms/settings.py` |
| LTI, SAML, RBAC đều tắt mặc định (`USE_LTI`, `USE_SAML`, `USE_RBAC = False`) | `cms/settings.py` |
| Cần tối thiểu 4 GB RAM, 2–4 CPU; đĩa ≈ 3 lần dung lượng video | README |

Chưa xác minh (để spike ở §10):
- `media_auth` lấy người dùng từ `request.user` (session Django). Chưa rõ nó có nhận Token/Basic khi BFF tải file HLS từ server không.
- Có webhook báo encode xong không. Chưa tìm thấy, nên mặc định là hỏi định kỳ (poll).
- Upload phụ đề bằng REST API. Mới thấy view form `add_subtitle`; mình không cần vì VTT tự phục vụ (§5.3).
- Kích hoạt Whisper bằng API, và chất lượng tiếng Việt.
- `MEDIA_IS_REVIEWED`, `PORTAL_WORKFLOW`, `CAN_ADD_MEDIA` cần đặt thế nào để media của tài khoản dịch vụ dùng được ngay, không phải chờ admin duyệt.

## 4. Mô hình dữ liệu

### 4.1 `videos` thành bảng tài sản video

Bảng `videos` đã có: `course_id`, `title`, `file_path`, `is_youtube`, `external_url`, `language`, `status`, cùng `video_segments` → `transcript_segments` và `card_video_attachments`. Thêm các cột:

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `source` | `AI` / `UPLOAD` / `YOUTUBE` | Video đến từ đâu (`is_youtube` giữ để tương thích) |
| `file_path` (đã có) | | Khóa MinIO của bản gốc: `videos/<course_id>/<video_id>/master.mp4` |
| `captions_object_key` | text, null | `videos/<course_id>/<video_id>/captions.vi.vtt` |
| `script_snapshot` | jsonb, null | Kịch bản đúng lúc render; phiên bản video gắn với phiên bản kịch bản |
| `media_provider` | text, null | `mediacms` |
| `media_ref` | text, null | `friendly_token` của MediaCMS |
| `media_uid` | text, null | uid 32 hex: tiền tố đường dẫn `hls/<uid>/…` |
| `hls_master_path` | text, null | Lấy từ `hls_info` |
| `duration_ms`, `thumbnail_path` | | Lấy từ MediaCMS sau khi encode |
| `failed_stage`, `error`, `attempts` | | Lỗi ở bước nào, thông điệp, số lần đã thử |
| `replaces_video_id` | uuid, null | Bản render này thay cho bản nào |
| `updated_at` | timestamptz | |

`micro_contents` thêm `video_id` (FK `videos`): bản đang dùng. Các cột `video_object_key`, `video_mime_type`, `video_size_bytes`, `video_duration_ms` chuyển sang `videos`, rồi bỏ sau một migration. `video_status` giữ làm bản tóm tắt cho giao diện hiện tại (`NONE`/`PROCESSING`/`READY`/`FAILED`), tính theo `videos.status` của bản đang dùng.

Code micro-content là của bạn cùng nhóm (nhánh `origin/dev`), nên migration này phải chốt với họ trước.

### 4.2 Trạng thái `videos.status`

```
AI:      QUEUED → RENDERING → INGESTING → ENCODING → READY
UPLOAD:  UPLOADING ─────────→ INGESTING → ENCODING → READY
bất kỳ bước nào → FAILED (failed_stage, error)      READY/FAILED → DELETING → (xóa mềm)
```

- `micro_contents.publish` vẫn chỉ cho xuất bản khi bản đang dùng ở `READY` (luật đã có, [micro-content.service.ts](../core-api/src/micro-content/micro-content.service.ts) ≈ dòng 272).
- **Render lại** tạo một dòng `videos` mới với `replaces_video_id`. Micro-content còn `DRAFT` thì tự chuyển sang bản mới khi bản mới `READY`. Đã xuất bản thì giảng viên bấm chọn dùng bản mới; bản cũ vẫn phát cho tới lúc đó.
- Video AI: mỗi cảnh là một `video_segments` (`start_ms`, `end_ms`, `title`), mỗi câu thoại là một `transcript_segments`. Dữ liệu lấy từ mốc thời gian renderer trả về. Chatbot, thẻ bài học (`card_video_attachments`) và tính năng nhảy tới cảnh dùng được ngay, không cần nhận dạng giọng nói.

## 5. Luồng

### 5.1 Video AI

1. Giảng viên sửa kịch bản. `saveScript` đã có.
2. `requestRender` (sửa): tạo dòng `videos` với `QUEUED` và `script_snapshot`, rồi phát `MICRO_CONTENT_RENDER_REQUESTED` kèm `video_id`. Outbox chuyển sang queue `micro_content_video` như hiện nay.
3. `video_worker`:
   1. `RENDERING`: `renderer.submit(script)`, sau đó `poll` tới khi xong. Kết quả là MP4 và mốc thời gian (§6.2).
   2. Ghi `master.mp4` và `captions.vi.vtt` (sinh từ mốc thời gian) vào MinIO; ghi `video_segments` và `transcript_segments`.
   3. `INGESTING`: `media.ingest(...)` lên MediaCMS, đặt trạng thái media theo kết quả spike S2, rồi lưu `media_ref` và `media_uid`.
   4. `ENCODING`: tạo job trễ, hỏi `media.status(ref)` mỗi 15–30 giây; quá 30 phút thì `FAILED`.
   5. `READY`: ghi `hls_master_path`, `duration_ms`, `thumbnail_path`.
4. Trang quản lý hiện từng bước, lỗi kèm nút render lại, và cho xem thử trước khi xuất bản.

### 5.2 Video giảng viên upload

1. `createUpload` (đã có): URL ký sẵn để PUT lên MinIO. Đổi khóa sang `videos/<course>/<video_id>/master.<ext>` và tạo dòng `videos` với `UPLOADING`.
2. `confirmUpload` (sửa): hiện đặt `READY` ngay. Đổi thành `INGESTING` và phát `VIDEO_INGEST_REQUESTED`.
3. `video_worker` chạy bước 3.3–3.5 như video AI.
4. GĐ4: bật Whisper cho video loại này, tải VTT từ `subtitles_info`, cắt thành `video_segments` và `transcript_segments`, rồi đưa vào luồng lập chỉ mục để chatbot và tóm tắt dùng.

### 5.3 Phát cho học viên

1. Trang micro-content gọi `GetVideoPlayback(videoId)`. core-api kiểm quyền:
   - học viên phải là thành viên khóa, và micro-content đã `PUBLISHED`;
   - giảng viên/TA được xem cả bản nháp.

   Đạt thì core-api trả **playback token**: HMAC gồm `video_id`, `user_id`, hạn khoảng 2 giờ.
2. Trình phát (hls.js; Safari dùng HLS sẵn có) mở `/api/videos/<id>/hls/<token>/master.m3u8`. Đường dẫn con trong playlist là tương đối, nên mọi segment tự mang theo `<token>`.
3. Route BFF kiểm token tại chỗ (không gọi core-api cho từng segment) và chỉ nhận đường dẫn thuộc `hls/<media_uid>/`, đuôi `.m3u8`, `.ts`, `.m4s`, `.mp4`. Sau đó route tải từ MediaCMS nội bộ và chuyển tiếp, giữ Range, `Cache-Control: private`.
4. Phụ đề: `/api/videos/<id>/captions/<token>.vtt` đọc thẳng từ MinIO.
5. Tiến độ xem ghi vào `micro_content_progress` như thiết kế hiện tại.

### 5.4 Xóa, render lại, đối soát

- Xóa micro-content hoặc bỏ một phiên bản: đặt `DELETING`, sau 7 ngày worker xóa trên MediaCMS và MinIO, rồi xóa mềm dòng.
- Mỗi ngày một job đối soát `videos` với danh sách media của tài khoản dịch vụ. Media mồ côi bị xóa; dòng `READY` mà mất media thì chuyển `FAILED` (`failed_stage = MISSING`).
- Thử lại: `INGESTING`/`ENCODING` lỗi do mạng thì thử tối đa 3 lần, giãn cách tăng dần. `RENDERING` lỗi thì không tự thử lại, giảng viên tự bấm.

## 6. Interface

### 6.1 `MediaBackend` (worker, Python)

```python
class MediaBackend(Protocol):
    def ingest(self, *, video_id: str, source_url: str, title: str, course_code: str) -> MediaRef: ...
    def status(self, ref: MediaRef) -> MediaStatus: ...   # ENCODING | READY | FAILED, hls_master_path, duration_ms, thumbnail_path, error
    def delete(self, ref: MediaRef) -> None: ...
    def captions(self, ref: MediaRef) -> list[CaptionTrack]: ...   # GĐ4, video upload có Whisper
```

`MediaCmsBackend` là adapter đầu tiên. Muốn tự làm bằng ffmpeg (hướng A) hoặc dùng dịch vụ cloud thì chỉ thêm adapter khác; core-api và web không đổi, vì web chỉ biết `hls_master_path` và `media_uid`.

### 6.2 `VideoRenderer` (worker ↔ `video-lms`)

```python
class VideoRenderer(Protocol):
    def submit(self, *, video_id: str, script: dict, options: dict) -> str: ...   # job id
    def poll(self, job_id: str) -> RenderStatus: ...   # RUNNING | DONE | FAILED
```

Khi `DONE`, renderer trả: URL tải MP4 (h264/AAC, 720p, `faststart`) và mốc thời gian:

```json
{"scenes": [{"index": 0, "title": "…", "start_ms": 0, "end_ms": 21400,
             "sentences": [{"text": "…", "start_ms": 0, "end_ms": 5200}]}]}
```

Đây là hợp đồng duy nhất cần chốt với bạn cùng nhóm làm `video-lms`. Hiện `video-lms` có API riêng, auth bằng header dev, chưa có endpoint kiểu này.

### 6.3 core-api và web

- RPC mới: `GetVideoPlayback`, `RetryVideo`, `UseVideoVersion`, `ListCourseVideos` (lọc theo khóa, chương, LO, trạng thái, nguồn). Cập nhật `contracts/proto/core_api.proto` và chạy `scripts/check_grpc_contract.py`.
- Web: route `/api/videos/[id]/hls/[token]/[...path]` và `/api/videos/[id]/captions/[token]`; component trình phát; trang `/manage/micro-content` thêm cột trạng thái theo bước, lỗi, phiên bản.

## 7. Bảo mật và cấu hình MediaCMS

- MediaCMS **không mở ra Internet**: không đi qua Cloudflare tunnel; chỉ mạng docker nội bộ, và Tailscale cho admin.
- Một tài khoản dịch vụ (editor). Token API lưu trong Infisical (`MEDIACMS_API_TOKEN`), không để trong `.env` máy cá nhân.
- Media đặt `private` nếu spike S2 cho thấy BFF tải được file HLS bằng tài khoản dịch vụ. Nếu không được thì dùng `unlisted` và dựa vào việc MediaCMS không lộ ra ngoài: đường dẫn chứa uid 32 hex, và lớp kiểm quyền thật nằm ở BFF.
- Cấu hình: `USE_LTI`, `USE_SAML`, `USE_RBAC` = False; `GLOBAL_LOGIN_REQUIRED` = True; chỉ tài khoản dịch vụ được upload; tắt bình luận và lượt thích; profile encode chỉ h264 360p và 720p để đỡ CPU. `USE_WHISPER_TRANSCRIBE` chỉ bật ở GĐ4, và khi đó cần image `mediacms-full`.
- Category MediaCMS đặt theo mã môn để admin dễ tìm khi vào giao diện MediaCMS. Không dùng category cho phân quyền.
- AGPL-3.0: chạy nguyên bản như một service riêng thì không phát sinh nghĩa vụ với mã của platform. Nếu sửa mã MediaCMS thì phải công bố phần sửa.

## 8. Triển khai và tài nguyên

- Một compose project riêng `mediacms`, với Postgres và Redis riêng, để nâng cấp độc lập và không đụng PG18 dùng chung. Ghim tag image: MediaCMS ra bản rất nhanh (9.2.1 → 9.4.0 trong ba tuần).
- Đặt ở máy hạ tầng chung (cùng nơi với Postgres/Qdrant/MinIO), không đặt trên Mac. Giới hạn số tiến trình encode của Celery ở 1–2 để không tranh CPU với cơ sở dữ liệu.
- Ước lượng đĩa (cần đo ở spike): video AI 2 phút 720p khoảng 15–30 MB. 100 video thì bản gốc khoảng 2–3 GB, cộng MediaCMS (×3) thành khoảng 8–12 GB.

## 9. Rủi ro

| Rủi ro | Mức | Cách giảm |
|---|---|---|
| HLS nhiều request qua Cloudflare tunnel, độ trễ 0,3–1,7 s/request (đo 2026-10-17): video lâu bắt đầu phát | Trung bình | Segment 6–10 s, trình phát tải trước; đo ở spike S5 |
| Renderer trên WSL tắt khi Windows không mở terminal | Cao cho demo | Chuyển renderer sang máy chạy ổn định; worker báo `FAILED` rõ ràng thay vì treo |
| Dữ liệu hai nơi (MinIO, MediaCMS) lệch nhau | Thấp | Job đối soát hằng ngày (§5.4) |
| Nâng cấp MediaCMS làm đổi API/trường | Trung bình | Ghim tag; adapter có test hợp đồng bằng JSON mẫu lấy từ spike |
| Whisper tiếng Việt kém hoặc quá chậm trên CPU | Trung bình (chỉ GĐ4) | Spike S4; có thể chạy Whisper trong worker thay vì MediaCMS |
| Schema micro-content đang do bạn cùng nhóm sửa | Trung bình | Chốt §4 với họ trước khi viết migration |

## 10. Spike trước khi code (1–2 ngày)

| # | Kiểm gì | Đạt khi |
|---|---|---|
| S1 | Dựng MediaCMS bằng compose; upload bằng Token API; đọc `encoding_status`/`hls_info` | Có JSON mẫu của một video 2 phút; biết thời gian encode 360p + 720p |
| S2 | BFF tải `hls/<uid>/master.m3u8` của media `private` từ server bằng tài khoản dịch vụ | Biết cách xác thực dùng được (Token, Basic hay session); chốt `private` hay `unlisted` |
| S3 | Cấu hình duyệt: media của tài khoản dịch vụ phát được ngay, không chờ admin | Biết đúng giá trị `MEDIA_IS_REVIEWED`, `PORTAL_WORKFLOW`, `CAN_ADD_MEDIA` |
| S4 | (cho GĐ4) Whisper `small`/`medium` trên một bài giảng tiếng Việt 10 phút | Có tỉ lệ lỗi ước lượng trên một đoạn mẫu và thời gian chạy |
| S5 | Phát HLS qua route proxy + Cloudflare tunnel trong iframe Canvas | Thời gian tới khung hình đầu và có bị khựng không |

## 11. Lộ trình

| GĐ | Nội dung | Xong khi |
|---|---|---|
| 0 | Spike S1–S3, S5 | Bảng §10 có kết quả; §3 và §7 cập nhật theo kết quả |
| 1 | Schema `videos` (§4), `MediaCmsBackend`, `video_worker` cho luồng upload, route proxy, trình phát cho học viên | Giảng viên upload MP4 5 phút → `READY` → học viên xem trong Canvas, tiến độ được ghi |
| 2 | `VideoRenderer` bản đầu bọc renderer slide của Bình (mốc thời gian theo cảnh lấy từ thời lượng TTS); sinh kịch bản bằng LLM bám tài liệu khóa; sau đó adapter `video-lms` | Kịch bản → video phát được, phụ đề khớp, có cảnh trong `video_segments` |
| 3 | Quản lý khi nhiều video: lọc, phiên bản, render lại, xóa trễ, đối soát | Render lại một video đã xuất bản mà học viên không bị gián đoạn |
| 4 | Whisper cho video upload → `transcript_segments` → lập chỉ mục | Chatbot trích được một đoạn video kèm mốc thời gian |

## 12. Câu hỏi cần chốt

1. Ai làm phần nào: video thuộc phần việc của bạn cùng nhóm; adapter MediaCMS, worker và trình phát giao cho ai.
2. Máy chạy MediaCMS và renderer: máy hạ tầng có đủ CPU/RAM cho encode và renderer không.
3. Giảng viên có cần vào giao diện MediaCMS không. Mặc định là không, mọi thao tác ở `/manage`.
4. Một video có dùng chung cho nhiều micro-content hoặc nhiều khóa không. Mặc định là không: một video thuộc một khóa.
