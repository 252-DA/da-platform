# Kế hoạch tạo video micro-content từ slide của chương

Viết ngày 15/11/2026, dựa trên đọc code (`worker`, `core-api/src/micro-content`, `web/src/app/{manage,learn}/micro-content`), dev DB (chỉ đọc) và trao đổi cùng ngày. Kế hoạch này chưa có dòng code nào.

Cập nhật cùng ngày: giai đoạn A đã chạy xong. Kết quả và những chỗ kế hoạch phải đổi nằm ở §10; các bước B1–B6, §7 và §8 đã sửa theo.

## 0. Tóm tắt

- **Mục tiêu:** giảng viên chọn bộ slide của một chương, hệ thống tách nó thành các nội dung, mỗi nội dung thành một micro-content gồm video 2–4 phút và 2–4 câu hỏi củng cố. Video và câu hỏi đều bám đúng các trang slide nguồn.
- **Giữ nguyên phần dựng video** (ảnh slide + giọng đọc + ghép ffmpeg). Phần phải làm là bốn việc: tách nội dung, sinh kịch bản bám nguồn, sinh câu hỏi, và gắn micro-content với nguồn và LO.
- **Ba việc AI mới chạy trong worker sinh nội dung sẵn có**, nơi đang sinh quiz, và dùng lại vòng kiểm chứng nguồn của nó. Không thêm MediaCMS hay Marsha.
- **Bản thử đã chạy, chưa đụng schema** (§5 giai đoạn A, kết quả ở §10): tách 3 bộ slide thật, sinh kịch bản cho 3 nội dung, dựng 1 video thật. Bạn xem kết quả rồi quyết định làm tiếp giai đoạn B.
- **Cần bạn:** nghe video thử, chốt 6 câu ở §8, và chạy một migration ở giai đoạn B.

Từ dùng trong tài liệu:

| Từ | Nghĩa |
|---|---|
| Bộ slide | Một tài liệu bài giảng của một chương (`documents`, `role = lecture`) |
| Nội dung | Một dải trang liền nhau trong bộ slide, nói về một ý. Mỗi nội dung thành một micro-content |
| Kịch bản | JSON gồm các cảnh, lưu ở `micro_contents.ai_script` |
| Cảnh | Một màn hình của video: tiêu đề, các gạch đầu dòng, lời đọc |

## 1. Hiện trạng

Kiểm ngày 15/11 trên nhánh `feat/chatbot-three-modes`.

| Phần | Trạng thái | Chỗ xem |
|---|---|---|
| Dựng video từ kịch bản | Có. Mỗi cảnh: ảnh 1280×720 (Pillow) + giọng edge-tts, ghép bằng ffmpeg, đưa lên MinIO, báo `READY`/`FAILED` về core-api | [render_micro_content_video.py](../worker/worker/use_cases/render_micro_content_video.py) |
| Sinh kịch bản | Chưa phải AI. core-api ghi mẫu 3 cảnh cố định, chỉ chèn tên chủ đề. Worker nhận `MICRO_CONTENT_SCRIPT_REQUESTED` và bỏ qua | [micro-content.service.ts:415](../core-api/src/micro-content/micro-content.service.ts#L415), [micro_content_video_worker.py:123](../worker/worker/runners/micro_content_video_worker.py#L123) |
| PDF → kịch bản | Luật cứng, không LLM: chữ to nhất làm tiêu đề, ghép gạch đầu dòng thành lời đọc, giữ tối đa 4 gạch đầu dòng mỗi cảnh | [pdf_script_extractor.py](../worker/worker/services/pdf_script_extractor.py) |
| Giọng đọc lỗi | Nếu edge-tts lỗi, worker ghi âm thanh im lặng rồi vẫn báo `READY` | [tts_client.py:129](../worker/worker/services/tts_client.py#L129) |
| Phụ đề, mốc thời gian cảnh | Chưa có. Bảng `video_assets` đã có cột `vtt_subtitles_key`, `transcript_text`, `transcript_status` nhưng không ai ghi | `core-api/prisma/schema.prisma` |
| Gắn micro-content với nguồn | Chưa có. `micro_contents` không có cột tài liệu, trang, chương hay LO | `core-api/prisma/schema.prisma` |
| Trang giảng viên | Có: sửa kịch bản từng cảnh, chọn giọng, nghe thử, bấm dựng video, soạn câu hỏi | [video-panel.tsx](../web/src/app/manage/micro-content/[id]/edit/video-panel.tsx) |
| Trang học viên | Có: phát MP4, báo tiến độ mỗi ~10 giây, mở khóa câu hỏi, nộp bài. Không có phụ đề | [player.tsx](../web/src/app/learn/micro-content/[id]/player.tsx) |
| Đếm tiến độ xem | Lỗi: khi vị trí phát không tiến, toàn bộ thời gian trôi qua vẫn được cộng, nên để yên trang cũng đạt đủ phần trăm | [micro-content-attempt.service.ts:106](../core-api/src/micro-content/micro-content-attempt.service.ts#L106) |
| Nối với Learning Agent | Chưa có. `core-api/src/learning-agent` không nhắc tới micro-content | |
| Đẩy điểm về Canvas | Chưa có. `core-api/src/ags` không nhắc tới micro-content | |
| Mở micro-content từ Canvas | Bị chặn. `web` đã nhận `target_kind = micro_content`, nhưng ràng buộc CHECK của `lti_resource_links.target_kind` và DTO của core-api chỉ nhận 5 loại cũ (phát hiện ở A1) | [launch-sync.dto.ts:56](../core-api/src/lti/dto/launch-sync.dto.ts#L56), `core-api/prisma/migrations/0_init/migration.sql` dòng 78 |
| Kết quả câu tự luận ngắn trên trang học viên | Thiếu. core-api chấm xong nhưng trang không tự hỏi lại kết quả, và mở lại trang cũng không tải lượt làm cũ (phát hiện ở A1) | [questions.tsx](../web/src/app/learn/micro-content/[id]/questions.tsx), [page.tsx](../web/src/app/learn/micro-content/[id]/page.tsx) |

Dữ liệu trên dev DB (đếm trước giai đoạn A; sau A1 có thêm một micro-content thử, xem §10.1):

| Thứ | Số |
|---|---|
| Micro-content | 3 bản nháp, cả 3 `video_status = NONE` |
| `video_assets`, câu hỏi, lượt làm, tiến độ | 0 |
| Bộ slide bài giảng đã lập chỉ mục | 10 |
| Liên kết chunk–LO | 2039 dòng cho 562 chunk và 13 LO, tức trung bình khoảng 3,6 LO mỗi chunk |

Chưa có video nào đi hết luồng trên dev. Ngày 05/11 tôi mới chạy thử phần dựng trong container: 2 cảnh ra video 13,8 giây, dựng mất 10,9 giây, có giọng thật.

Tiêu đề đã bóc từ slide (`chunks.heading_path`) không đủ tin để tách nội dung:
- `Ch1_Big Data Intro.pdf`: mục "Veracity" ôm trang 16–33, tức hơn nửa bộ slide.
- `Spark.pdf`: "Python" và "Java" thành hai mục riêng, mỗi mục khoảng 150 ký tự; còn "Spark Essentials: Actions" ôm trang 29–44.

## 2. Phạm vi

Đã chốt ngày 15/11:
- Mỗi nội dung trong bộ slide của một chương là một micro-content.
- Hình ảnh: đích là mức cao nhất, nhưng trước mắt làm được gì thì làm.
- Video giảng viên tự upload (nhận dạng giọng nói, tóm tắt) để sau.
- Bạn có toàn quyền với phần micro-content, kể cả code của Bình.

Ngoài phạm vi:
- MediaCMS, Marsha, HLS nhiều mức bitrate. Video 2–4 phút phát MP4 thẳng từ MinIO/R2 là đủ.
- Tìm đoạn YouTube ([youtube-video-pilot.md](youtube-video-pilot.md)).
- Lesson card và enrichment.
- Hành động "gợi ý xem micro-content" của Learning Agent. Kế hoạch này chỉ đưa kết quả làm bài vào mô hình người học (bước B6).

## 3. Luồng đích

Phía giảng viên:
1. Vào trang quản lý micro-content, chọn một bộ slide của chương, bấm đề xuất nội dung.
2. Hệ thống trả về danh sách nội dung: tên, dải trang, tóm tắt một câu, LO gợi ý. Mỗi nội dung đã là một micro-content nháp.
3. Giảng viên sửa tên, dải trang, LO; xóa cái thừa; thêm cái thiếu.
4. Với từng nội dung (hoặc chọn nhiều), bấm sinh kịch bản. Kịch bản về ở dạng nháp, mỗi cảnh ghi rõ lấy từ trang nào và có qua kiểm chứng hay không.
5. Giảng viên đọc, sửa câu chữ, nghe thử giọng, rồi bấm dựng video.
6. Bấm sinh câu hỏi củng cố, sửa nếu cần.
7. Xem thử video, xuất bản, gắn vào module Canvas.

Phía học viên: mở micro-content trong Canvas, xem video có phụ đề, xem đủ phần trăm quy định thì mở câu hỏi, làm và nhận kết quả. Kết quả được tính vào mức nắm LO tương ứng.

Đường đi qua các service:

```
web (giảng viên)
  │ gRPC
  ▼
core-api ── ghi content_generation_requests + outbox ──▶ hàng đợi sinh nội dung
  ▲                                                        │
  │ CONTENT_GENERATION_RESULT (worker tính, core-api ghi)  ▼
  └────────────────────────────────────────── worker sinh nội dung
                                               ├─ micro_outline : tách bộ slide thành nội dung
                                               ├─ video_script  : sinh kịch bản + kiểm chứng
                                               └─ micro_quiz    : sinh câu hỏi + kiểm chứng

core-api ── MICRO_CONTENT_RENDER_REQUESTED ──▶ worker video (đã có) ──▶ MinIO
  ▲                                              │
  └────────── MICRO_CONTENT_VIDEO_RESULT ────────┘
```

Lý do đặt ba việc AI ở worker sinh nội dung thay vì worker video:
- Worker sinh nội dung đã có model LLM, sổ chi phí, vòng kiểm chứng nguồn và vòng đời yêu cầu (đang chạy, xong, lỗi, thử lại) ([content_generation_worker.py](../worker/worker/runners/content_generation_worker.py)).
- Worker video chạy từng job một vì dựng video ngốn CPU. Đặt lời gọi LLM ở đó thì sinh kịch bản phải xếp hàng sau các lần dựng.

## 4. Thay đổi dữ liệu

Một migration duy nhất, chỉ thêm cột và nới ràng buộc.

### 4.1 Bảng `micro_contents`

| Cột mới | Kiểu | Ý nghĩa |
|---|---|---|
| `source_document_id` | uuid, null, FK `documents` | Bộ slide nguồn |
| `source_page_from`, `source_page_to` | int, null | Dải trang của nội dung |
| `lo_id` | uuid, null, FK `learning_outcomes` | LO chính của nội dung |
| `position` | int, mặc định 0 | Thứ tự trong bộ slide |
| `script_status` | varchar(20), mặc định `NONE` | `NONE`, `GENERATING`, `READY` (có nháp để duyệt), `FAILED` |
| `script_error` | text, null | Lỗi lần sinh kịch bản gần nhất |
| `script_request_id` | uuid, null | Yêu cầu sinh kịch bản đang chờ. Kết quả mang id khác thì bỏ, giống cách `ai_render_id` chặn kết quả dựng cũ |

Chương không cần cột riêng: lấy từ `documents.chapter_code`.

### 4.2 Kịch bản (`ai_script`)

Mỗi cảnh hiện có `title`, `bullets`, `narration`, `voice`. Thêm:

| Khóa mới trong cảnh | Ý nghĩa |
|---|---|
| `source_pages` | Các trang slide mà cảnh dựa vào |
| `source_chunk_ids` | Các chunk nguồn, để kiểm chứng và truy vết |
| `check` | Kết luận kiểm chứng: `{status: VERIFIED / FLAGGED / INCONCLUSIVE, reason}` |
| `visual` | Hình của cảnh (§6). Không có thì dùng slide chữ như hiện nay |

Contract lệnh dựng (`micro-content-render-requested.json`) không cấm khóa thừa trong cảnh, nên worker video hiện tại vẫn nhận được kịch bản mới. Vẫn nên cập nhật contract để ghi lại các khóa này.

### 4.3 Bảng `video_assets`

| Cột | Việc |
|---|---|
| `vtt_subtitles_key`, `transcript_text`, `transcript_status` | Đã có, bắt đầu ghi ở bước B4 |
| `scene_timeline` (mới, jsonb, null) | Mốc bắt đầu và kết thúc của từng cảnh, để người học nhảy cảnh |

### 4.4 Bảng `content_generation_requests`

Cột `type` có ràng buộc CHECK (đang nhận `quiz`, `card`, `relations`). Nới thêm `micro_outline`, `video_script`, `micro_quiz`.

### 4.5 Bảng `lti_resource_links`

Ràng buộc `lti_resource_links_target_kind_check` đang nhận `lesson`, `card`, `quiz_set`, `chat`, `video`. Nới thêm `micro_content`, nếu không thì không mở được micro-content từ Canvas (§10.1).

## 5. Các bước

### Giai đoạn A: bản thử, chưa đụng schema

Mục đích là biết sớm chất lượng có chấp nhận được không, trước khi bỏ công làm schema và giao diện.

**A1. Chạy thông luồng hiện có một lần**
- Việc: tạo một micro-content, nhập tay kịch bản 2 cảnh, dựng, thêm 2 câu hỏi, xuất bản, mở bằng tài khoản học viên trong Canvas, xem và nộp bài.
- Xong khi: dev DB có 1 `video_assets` ở `READY`, 1 dòng tiến độ, 1 lượt làm có điểm. Có danh sách những chỗ gãy.

**A2. Thử tách nội dung**
- Việc: một script chạy trong container worker, đọc chunk của bộ slide (chỉ đọc), gom theo trang, gọi LLM, in ra danh sách nội dung. Không ghi DB.
- Chạy trên `Spark.pdf` (57 trang), `Ch1_Big Data Intro.pdf` (33 trang), `MapReduce.pdf` (82 trang).
- Xong khi: bạn đọc ba danh sách và thấy cách tách dùng được, hoặc chỉ ra sai ở đâu để sửa prompt.

**A3. Thử sinh kịch bản và dựng một video thật**
- Việc: lấy 3 nội dung từ kết quả A2, sinh kịch bản kèm kiểm chứng, in ra để đọc. Chọn 1 kịch bản, đưa qua phần dựng hiện có, lấy file MP4.
- Xong khi: bạn xem video đó và đọc ba kịch bản, rồi quyết định có làm giai đoạn B không.

### Giai đoạn B: làm thật

**B1. Schema và liên kết nguồn**
- core-api: migration theo §4; sửa `schema.prisma`; trả các cột mới qua gRPC (`contracts/proto/core_api.proto`).
  (ghi chú 2026-11-16: kênh web→core-api nay là HTTP REST — "trả qua gRPC" đọc là "trả qua API HTTP `/api/*` của core-api (controller + DTO, gọi từ `web/src/lib/core-api.ts`)"; phần gRPC chỉ còn giá trị lịch sử.)
- core-api: thêm `micro_content` vào danh sách `targetKind` của [launch-sync.dto.ts](../core-api/src/lti/dto/launch-sync.dto.ts), đi cùng ràng buộc ở §4.5.
- Xong khi: tạo và đọc được micro-content có nguồn, LO và thứ tự; `LaunchSync` với `targetKind = micro_content` không còn lỗi 23514.
- Phụ thuộc: bạn chạy `prisma migrate deploy`. Chạy migration trước khi đưa code core-api mới lên, vì core-api chạy ở chế độ watch và truy vấn sẽ lỗi nếu thiếu cột.

**B2. Tách bộ slide thành nội dung**
- worker: use case mới cho loại `micro_outline`.
  - Đầu vào: `course_id`, `document_id`.
  - Gom chunk theo `page_number`, tạo bản tóm lược từng trang (tiêu đề + khoảng 200 ký tự đầu). Đưa đủ danh sách trang từ 1 đến trang cuối, kể cả trang không có chunk nào: theo báo cáo A2, trang chỉ có hình đôi khi không có chunk.
  - LLM trả danh sách nội dung: tên, trang đầu, trang cuối, tóm tắt một câu; kèm các trang bỏ qua (bìa, mục lục, cảm ơn, tài liệu tham khảo).
  - Code kiểm: dải trang nằm trong tài liệu, đúng thứ tự, không chồng nhau, mỗi dải 2–15 trang, tối đa 20 nội dung. Dải nào quá ít chữ thì gắn nhãn "ít chữ" thay vì bỏ.
- LO gợi ý: cùng lời gọi LLM đó chọn một LO cho mỗi nội dung từ danh sách LO lá của khóa học (mã + phát biểu). LO của chương được đánh dấu là ưu tiên nhưng không giới hạn cứng. Code kiểm mã LO trả về có trong danh sách.
  - Cách cũ trong bản đầu của kế hoạch (đếm LO xuất hiện nhiều nhất trong liên kết chunk–LO) là sai. Trên dev, liên kết này ở mức tài liệu: mọi chunk của một tài liệu mang đủ mọi LO của chương, nên đếm lúc nào cũng hòa (§10.2).
  - Không giới hạn cứng theo chương vì `documents.chapter_code` có thể sai (§10.2).
- core-api: khi nhận kết quả, tạo mỗi nội dung một micro-content nháp (`video_source = AI`) kèm LO gợi ý.
- Tách lại một bộ slide đã tách: chỉ thay các bản nháp chưa có kịch bản, video hay câu hỏi; bản đã có thì giữ.
- web: trong trang quản lý micro-content, thêm chỗ chọn bộ slide và danh sách nội dung nhóm theo bộ slide, sửa được tên, dải trang, LO.
- Xong khi: từ `Spark.pdf` ra danh sách micro-content nháp, sửa dải trang và LO được trên giao diện.

**B3. Sinh kịch bản bám nguồn**
- core-api: `requestScript` thôi ghi mẫu cố định. Thay vào đó tạo một yêu cầu loại `video_script` (id micro-content, tài liệu, dải trang, LO, số cảnh mong muốn, ngôn ngữ, ghi chú của giảng viên), đặt `script_status = GENERATING`. Thôi phát `MICRO_CONTENT_SCRIPT_REQUESTED`.
- worker: use case mới, anh em với sinh lesson card ([generate_lesson_cards.py](../worker/worker/use_cases/generate_lesson_cards.py)):
  1. Lấy các chunk trong dải trang, theo thứ tự. Kèm phát biểu LO và tên nội dung liền trước, liền sau để kịch bản không dạy lại phần khác.
  2. Model viết kịch bản theo chuỗi câu hỏi: cảnh đầu nêu câu hỏi trọng tâm; các cảnh giữa lần lượt trả lời từng câu hỏi con (hiện tượng, các thành phần, từng thành phần, quan hệ giữa chúng); cảnh cuối trả lời câu hỏi trọng tâm và dẫn sang phần câu hỏi.
  3. Giới hạn: 4–8 cảnh; mỗi cảnh tối đa 4 gạch đầu dòng; lời đọc 40–110 từ, do code kiểm (ở A3 có một cảnh 122 từ lọt qua). Với tốc độ ước lượng 0,38 giây mỗi từ đang dùng trong code, video dài khoảng 2–4 phút; A3 đo được khoảng 0,35 giây mỗi từ. Nội dung ít chữ thì video ngắn hơn 2 phút, không ép cho đủ dài.
  4. Code kiểm: trang và chunk nguồn của mỗi cảnh phải nằm trong dải được cấp.
  5. Model thứ hai kiểm từng cảnh: mọi ý trong lời đọc có trong chunk nguồn không. Cảnh không đạt được viết lại, số lượt có giới hạn ([verification.py](../worker/worker/use_cases/verification.py)).
     - Ở A3, model kiểm cho qua cả những câu không có trong nguồn (§10.3). Lời nhắc cho model kiểm phải hỏi riêng từng loại: số liệu, tên riêng và khẳng định mới so với nguồn. Mức cho phép diễn giải là câu 6 ở §8.
  5a. Mỗi micro-content tự đứng được: kịch bản không nhắc "bài trước" hay "bài sau". Tên nội dung liền kề chỉ dùng để model biết không dạy lấn sang, không được đưa vào lời đọc (ở A3 cảnh mở đầu có câu "Trong bài trước, chúng ta đã so sánh…").
  5b. Từ tiếng Anh: chỉ giữ tên riêng và thuật ngữ chưa có từ Việt quen dùng (Spark, RDD, executor). Từ thông thường thì dịch (ở A3 kịch bản để nguyên "abstraction", "collection"). Chốt sau khi bạn nghe video thử, câu 1 ở §8.
  6. Chuẩn hóa lời đọc cho giọng máy bằng `normalize_for_tts` sẵn có (đổi ký hiệu và từ viết tắt thành văn nói).
- core-api: nhận kết quả, ghi `ai_script`, đặt `script_status = READY`. Bỏ kết quả nếu `script_request_id` không khớp.
- Micro-content không có nguồn: nếu có LO thì lấy đoạn nguồn theo LO như sinh quiz ([lo_context.py](../worker/worker/use_cases/lo_context.py)); không có cả hai thì từ chối và yêu cầu chọn nguồn hoặc nhập kịch bản tay.
- web: trong trình sửa kịch bản, hiện trạng thái đang sinh hoặc lỗi; mỗi cảnh hiện trang nguồn (bấm mở đúng trang slide) và cảnh báo nếu cảnh bị gắn cờ. Giảng viên phải bấm xác nhận từng cảnh bị gắn cờ trước khi dựng.
- Tab trích kịch bản từ PDF giữ nguyên, làm đường dự phòng không cần LLM.
- Model: bước đầu dùng lại hai task đã có trong trang chọn model, `quiz_generation` để viết và `quiz_verification` để kiểm.
- Xong khi: với 3 nội dung của `Spark.pdf`, kịch bản hợp lệ, mọi cảnh có trang nguồn trong dải, kết luận kiểm chứng được lưu và hiện trên giao diện.

**B4. Dựng video: sửa lỗi và thêm phụ đề**
- worker:
  - Giọng đọc lỗi thì báo lỗi, không ghi âm thanh im lặng. Bản im lặng chỉ dùng khi bật rõ bằng biến môi trường cho test.
  - Sửa lệnh dựng từng cảnh trong [video_composer.py](../worker/worker/services/video_composer.py): bỏ `-loop 1` đi với `-shortest`, thay bằng thời lượng tường minh (`-t` bằng thời lượng tiếng cộng một quãng nghỉ định sẵn, tiếng được đệm im lặng cho đủ dài). Hiện hình chạy quá tiếng 1,5–2 giây mỗi cảnh và để lại quãng hổng trong track tiếng (§10.3).
  - Ghi mốc thời gian từng cảnh bằng cách cộng dồn thời lượng từng clip cảnh đo bằng ffprobe, không cộng thời lượng file MP3. `duration_ms` của video cũng lấy từ file MP4 cuối.
  - Sinh phụ đề VTT theo câu. Trước tiên thử lấy mốc thời gian từ edge-tts khi stream; nếu không lấy được thì chia thời lượng cảnh theo số ký tự của từng câu.
  - Đưa file VTT lên cạnh file MP4; kết quả `READY` mang thêm khóa VTT, lời đọc gộp và mốc cảnh.
- core-api: nhận các khóa mới trong `MICRO_CONTENT_VIDEO_RESULT` ([micro-content-video-result.handler.ts](../core-api/src/micro-content/micro-content-video-result.handler.ts)), ghi vào `video_assets`. Cập nhật contract `micro-content-video-result.json`.
- core-api: sửa đếm tiến độ, chỉ cộng thời gian khi vị trí phát tiến lên.
- web: route trả phụ đề có kiểm quyền như route stream; thêm phụ đề và danh sách cảnh vào trình phát.
- Xong khi: ngắt mạng lúc dựng thì video `FAILED` kèm lỗi rõ; video `READY` có phụ đề hiện trong trình phát và khớp tiếng ở cảnh cuối; track tiếng và track hình của file MP4 dài bằng nhau, không có quãng hổng; để yên trang không làm tăng tiến độ.

**B5. Câu hỏi củng cố**
- core-api: yêu cầu loại `micro_quiz` (id micro-content, số câu, loại câu).
- worker: dùng lại phần viết và kiểm của sinh quiz, nhưng đoạn nguồn là các chunk trong dải trang của nội dung thay vì truy hồi theo LO. Kèm kịch bản đã duyệt để câu hỏi hỏi đúng điều video đã nói.
- Loại câu: `MCQ_SINGLE` và `TRUE_FALSE` trước, vì chấm tự động trong core-api.
- `SHORT_ANSWER`: A1 cho thấy core-api và worker chấm được, nhưng trang học viên không bao giờ hiện kết quả cuối (§10.1). Lỗi này có sẵn với cả câu giảng viên tự soạn. Nếu làm (câu 3 ở §8): thêm route `web` gọi `GetMicroContentResult` đã có sẵn, trang hỏi lại vài giây một lần khi còn `PENDING`, và tải lượt làm gần nhất khi mở lại trang.
- core-api: ghi vào `micro_content_questions`. Giảng viên sửa trong trang soạn câu hỏi sẵn có.
- Xong khi: sinh 3 câu cho một nội dung, câu nào cũng dẫn nguồn trong dải trang và qua kiểm chứng; học viên nộp bài nhận điểm tự động.

**B6. Đưa kết quả ra ngoài**
- Learning Agent: khi một lượt làm được chấm xong, ghi từng câu thành một quan sát cho `lo_id` của micro-content, giống câu quiz.
- Canvas: sau khi B1 gỡ chặn `target_kind`, chạy thử cả đường: gắn micro-content vào module qua Deep Linking, mở bằng tài khoản học viên trong Canvas. A1 mới thử trang học viên bằng phiên có sẵn, chưa đi qua Canvas. Có đẩy điểm về Canvas hay không là câu 3 ở §8.
- Xong khi: sau một lượt làm, mức nắm LO của học viên thay đổi trong mô hình người học; học viên mở được micro-content từ module Canvas.

## 6. Hình ảnh: ba mức

Kịch bản là đầu vào chung của cả ba mức. Mỗi cảnh có khóa `visual`; phần dựng không vẽ được thì lùi về mức 1.

| Mức | Hình của cảnh | Cần thêm | Trạng thái |
|---|---|---|---|
| 1 | Slide chữ tự sinh: tiêu đề + gạch đầu dòng | Không | Đã có |
| 2 | Chính trang slide gốc làm hình, lời giảng do AI viết | Lệnh dựng mang khóa file nguồn; worker dùng PyMuPDF vẽ trang thành ảnh 1280×720. Chỉ áp dụng cho nguồn PDF; PPTX phải đổi sang PDF trước, chưa có sẵn | Làm sau B4 |
| 3 | Hoạt hình sơ đồ (mảng, chuỗi bước, cây, đồ thị, ngăn xếp, luồng) | Đưa các mẫu hình của `video-lms` về chạy cạnh worker. Hiện repo đó nằm trên máy WSL, không phải git repo, máy hay offline | Chưa đánh giá: thời gian dựng mỗi cảnh, Manim chạy trong container |

Mức 2 đáng làm sớm vì ít công mà người học thấy đúng slide thầy cô dùng trên lớp, gồm cả hình và biểu đồ mà mức 1 không có.

## 7. Rủi ro

| Rủi ro | Mức | Cách giảm |
|---|---|---|
| Slide tiếng Anh, lời giảng tiếng Việt: giọng Việt đọc sai thuật ngữ Anh (Spark, MapReduce) | Cao | Video thử đã có, chờ bạn nghe. Phương án: lời giảng tiếng Anh với giọng Anh, hoặc đổi máy đọc. Xem câu 1 ở §8 |
| Model kiểm chứng dễ dãi: A3 báo 17/17 cảnh đạt, nhưng đọc tay 2 kịch bản thấy có câu ngoài nguồn vẫn qua (§10.3) | Cao | Sửa lời nhắc của model kiểm (B3 mục 5); giảng viên vẫn duyệt kịch bản trước khi dựng; thử model kiểm mạnh hơn bản lite |
| `documents.chapter_code` trên dev sai với phần lớn bộ slide, vì lấy theo module Canvas mà file đang nằm nhầm module (`Spark.pdf` ở chương 4, `MapReduce.pdf` ở chương 3, chương đúng là 8) | Trung bình | B2 không giới hạn LO theo chương. Việc riêng của bạn: xếp lại file vào đúng module trên Canvas dev. Sinh quiz theo LO cũng chịu ảnh hưởng của lỗi dữ liệu này |
| edge-tts gọi dịch vụ đọc của trình duyệt Edge, không có cam kết dịch vụ; có thể bị chặn hoặc giới hạn đúng lúc demo | Trung bình | Lỗi phải nổi lên thành `FAILED` (B4). Giao diện `TtsClient` cho phép thay máy đọc; VieNeu-TTS chạy máy mình đã dựng thử bên `video-lms` |
| Slide ít chữ, nhiều hình: không đủ nguồn để viết kịch bản | Trung bình | Gắn nhãn "ít chữ" ở bước tách; bước sinh kịch bản từ chối thay vì bịa |
| LLM tách nội dung sai ranh giới | Trung bình | Giảng viên sửa dải trang; đánh giá trên 3 bộ slide ở A2 |
| `page_number` của chunk chỉ là trang đầu của chunk, nên lọc theo dải trang có thể lệch một trang | Thấp | Với nguồn PDF có thể đọc lại chữ từng trang bằng PyMuPDF |
| Model kiểm chứng mặc định là `gemini-3.1-flash-lite` trên khóa Gemini miễn phí. Giới hạn lượt mỗi ngày của model này tôi chưa kiểm; A3 gọi 3 lượt không lỗi. Sinh cả chương có thể hết lượt | Trung bình | Trước khi chạy loạt, gán task kiểm chứng sang model trả phí ở trang chọn model |
| Dựng tuần tự từng video: theo số đo 05/11, dựng nhanh hơn thời lượng video một chút, nên 10 video 3 phút mất khoảng 25 phút | Thấp | Chấp nhận; tăng số worker video nếu cần |
| Nhánh của Bình còn sửa `micro_contents` | Thấp | Báo Bình về migration trước khi anh ấy merge tiếp |

## 8. Câu cần bạn chốt

Sau giai đoạn A chưa câu nào được chốt. Câu 6 là câu mới, sinh ra từ kết quả A3.

1. **Ngôn ngữ lời giảng khi slide tiếng Anh.** Đề xuất: tiếng Việt, giữ nguyên thuật ngữ Anh. Việc của bạn: nghe `a3_spark_rdd.mp4` (đường dẫn ở §10). Khi nghe, để ý hai thứ riêng nhau: giọng đọc tên riêng (RDD, SparkContext, JVM, Clojure) và giọng đọc từ Anh thông thường mà kịch bản để nguyên (abstraction, collection). Loại sau sửa được bằng lời nhắc, loại trước thì không.
2. **Cảnh không qua kiểm chứng sau các lượt viết lại.** Đề xuất: giữ lại đúng vị trí và gắn cờ cho giảng viên xử lý. Khác với quiz (câu không đạt bị bỏ), vì bỏ một cảnh làm đứt mạch kịch bản. A3 không có cảnh nào bị gắn cờ, nên nhánh này chưa được thử.
3. **Điểm bài củng cố có đẩy về sổ điểm Canvas không.** Đề xuất: chưa, chỉ đưa vào mô hình người học. Kèm một quyết định nhỏ: có sửa trang học viên để hiện kết quả câu tự luận ngắn không (B5). Đề xuất: có, vì đây là lỗi có sẵn với cả câu giảng viên tự soạn; ước lượng thô của tôi là nửa ngày.
4. **Một nội dung gắn một LO chính hay nhiều LO.** Đề xuất: một LO chính, LLM gợi ý ở B2, giảng viên đổi được.
5. **Tên trang và tên nút mới.** Tôi không đặt. Agent chạy giai đoạn A gợi ý: nút "Tạo từ bộ slide" hoặc "Đề xuất nội dung"; vùng "Nội dung đề xuất từ slide"; nút "Sinh kịch bản" và "Sinh câu hỏi củng cố". Bạn chọn, sửa hoặc đặt tên khác.
6. **Lời giảng được đi xa nguồn tới đâu.** Slide ít chữ thì model tự thêm định nghĩa và diễn giải, và model kiểm cho qua (§10.3). Hai hướng:
   - (a) Chỉ nói lại điều slide có. Video của nội dung ít chữ sẽ ngắn và nghe như đọc slide.
   - (b) Cho diễn giải thêm, nhưng cấm số liệu, tên riêng và khẳng định mới; model kiểm soi đúng ba loại đó; giảng viên duyệt trước khi dựng.
   - Đề xuất: (b). Một video chỉ đọc lại slide thì không hơn gì tự đọc slide.

## 9. Thứ tự và công

Số ngày là ước lượng thô của tôi cho một người làm tập trung, chưa tính thời gian bạn duyệt.

| Bước | Phụ thuộc | Công |
|---|---|---|
| A1 chạy thông luồng hiện có | Không | Xong 15/11 |
| A2 thử tách nội dung | Không | Xong 15/11 |
| A3 thử kịch bản + 1 video | A2 | Xong 15/11 |
| *Bạn xem kết quả, chốt §8, quyết định làm tiếp* | A1–A3 | Đang chờ |
| B1 schema, gỡ chặn mở từ Canvas | Bạn chạy migration | 1 ngày |
| B2 tách nội dung | B1 | 2 ngày |
| B3 sinh kịch bản | B1 | 3–4 ngày |
| B4 sửa dựng video, phụ đề | Không | 2 ngày |
| B5 câu hỏi củng cố | B1, B3 | 2 ngày, thêm 0,5 ngày nếu sửa trang học viên cho câu tự luận ngắn |
| B6 Learning Agent, Canvas | B1, B5 | 1–2 ngày |
| Hình mức 2 | B3, B4 | 2 ngày |
| Hình mức 3 | Hình mức 2 | Chưa ước lượng được |

Lưu ý trước khi bắt đầu giai đoạn B: `core-api` đang có thay đổi chưa commit của phần Canvas, trong đó có `schema.prisma` và một migration. Nên commit phần đó trước để migration mới không lẫn vào.

## 10. Kết quả giai đoạn A (15/11)

Giai đoạn A do một agent khác (Antigravity) chạy theo kế hoạch này, không sửa code và không sửa schema. Báo cáo gốc và file kết quả nằm ngoài repo, trong thư mục `/Users/canxphung/.gemini/antigravity/brain/3ac68d08-fae0-4c8e-9a6c-c81c3370cf49/`:

| File | Nội dung |
|---|---|
| `phase-a-report.md` | Báo cáo gốc |
| `a2_outlines.json` | Danh sách nội dung tách từ 3 bộ slide |
| `a3_scripts.json` | 3 kịch bản kèm kết luận kiểm chứng |
| `a3_spark_rdd.mp4` | Video thử, 6 cảnh, 3 phút 17 giây |

Tôi kiểm lại các kết luận của báo cáo trên code, dev DB (chỉ đọc) và file video. Mỗi dòng dưới đây ghi rõ tôi tự kiểm hay lấy theo báo cáo.

### 10.1 A1: luồng hiện có

| Kết quả | Nguồn |
|---|---|
| Tạo, dựng, soạn câu hỏi, xuất bản, xem, nộp bài: chạy thông | Tự kiểm trên DB: 1 `video_assets` ở `READY` dài 16,83 giây, 2 câu hỏi, 1 dòng tiến độ, 1 lượt làm `GRADED` điểm 100 |
| Câu tự luận ngắn được chấm ở core-api trong khoảng 10 giây | Lượt làm `GRADED` tự kiểm trên DB; số giây theo báo cáo |
| Trang học viên không tự hiện kết quả chấm, mở lại trang cũng không tải lượt cũ | Tự kiểm bằng đọc code: `web` không có route gọi `GetMicroContentResult`, `questions.tsx` không hỏi lại, `page.tsx` chỉ tải micro-content |
| Mở từ Canvas bị chặn: `LaunchSync` với `micro_content` lỗi PostgreSQL 23514 | Ràng buộc và DTO tự kiểm (DB và code đều chỉ nhận 5 loại cũ); lần gọi lỗi theo báo cáo, tôi không gọi lại |
| Đếm tiến độ: giữ vị trí 0 trong 2,5 giây vẫn được cộng 16% | Theo báo cáo; dòng code gây lỗi vẫn như §1 |

A1 thử trang học viên bằng một phiên có sẵn, chưa mở từ Canvas, nên "mở bằng tài khoản học viên trong Canvas" của bước A1 chưa đạt.

Dữ liệu thử còn nằm trên dev: micro-content "A1 Thử nghiệm: Spark RDD cơ bản" (`01a1ddeb-ae28-72b5-9f27-b490334580cf`) đang `PUBLISHED` trong khóa CO3137, kèm 1 video, 2 câu hỏi, 1 lượt làm của "Sinh Viên Test". Chưa ai xóa.

### 10.2 A2: tách nội dung

| Bộ slide | Trang | Số nội dung | Trang bỏ qua |
|---|---|---|---|
| `Ch1_Big Data Intro.pdf` | 33 | 11 | 1 (bìa) |
| `MapReduce.pdf` | 82 | 13 | 1 (bìa), 82 |
| `Spark.pdf` | 57 | 13 | 1 (bìa) |

Số liệu theo báo cáo; tôi đọc danh sách, không chạy lại. Model dùng là `deepseek-chat`, mỗi bộ slide mất 6–11 giây.

- **Cách tách tốt hơn hẳn tiêu đề bóc sẵn.** Chuỗi "Example: Log Mining" của `Spark.pdf` (trang 35–51) thành 3 nội dung; "Python" và "Java" gộp làm một.
- **Chỗ cần bạn đọc kỹ ở `Ch1`:** dải trang 10–12 được đặt tên "Velocity, Variety, Veracity" nhưng trang 11 là về khối lượng dữ liệu (33 ZB năm 2018 lên 175 ZB năm 2025); "Veracity và Value" lại tách riêng ở trang 16–18, cách một nội dung khác. Tôi tự kiểm chữ của trang 10–12 trên DB.
- **Gợi ý LO bằng cách đếm liên kết chunk–LO không dùng được.** Tự kiểm trên DB: cả 59 chunk của `Spark.pdf` đều mang đúng hai LO (`L.O.1.3` và `L.O.4.3`), cả 75 chunk của `MapReduce.pdf` mang `L.O.1.2` và `L.O.4.2`, mọi dòng có `source = document`, `confidence = 0.50`. Tức liên kết được chép từ LO của chương xuống mọi chunk của tài liệu, không phân biệt chunk nào nói về gì.
- **Chương của tài liệu trên dev sai.** Tự kiểm trên DB: `Spark.pdf` mang chương 4 (Hệ thống khuyến nghị), `MapReduce.pdf` mang chương 3 (Giảm chiều dữ liệu), chương đúng là 8 (Map-Reduce & Spark). Lý do ghi trong DB là file nằm trong module Canvas của chương đó. `Ch2_LSH_lecture.pdf` và `Ch2_Data Streaming.pdf` cũng bị đổi chỗ cho nhau. Vì vậy LO chép xuống chunk cũng là LO của chương sai.

### 10.3 A3: kịch bản và video

Ba kịch bản, 17 cảnh, model viết `deepseek-chat`, model kiểm `gemini-3.1-flash-lite`. Báo cáo ghi 17/17 cảnh `VERIFIED` ngay vòng đầu, mỗi kịch bản mất 9–12 giây.

Tôi đọc tay 2 trong 3 kịch bản, đối chiếu từng câu với chữ của slide nguồn trên DB:

| Kịch bản | Nguồn | Lời đọc | Nhận xét |
|---|---|---|---|
| `Spark.pdf` trang 19–22 | Khoảng 2.400 ký tự | 535 từ, 6 cảnh | Gần như dịch từng câu của slide. Hai câu không có trong nguồn: "Trong bài trước, chúng ta đã so sánh Spark và MapReduce qua WordCount" (cảnh 1), và "Cluster manager chịu trách nhiệm quản lý các worker node và tài nguyên" (cảnh 3, lặp ở cảnh 6). Câu sau là model tự điền: chữ trên slide bị cắt cụt ở "The cluster manager responsible for" |
| `Ch1` trang 10–12 | 122 từ tiếng Anh | 389 từ, 5 cảnh | Các câu định nghĩa ("Velocity là tốc độ sinh ra và xử lý dữ liệu") và câu nêu hệ quả ("ảnh hưởng trực tiếp đến độ tin cậy của các phân tích và quyết định") là của model, slide không viết. Số liệu duy nhất của dải trang (33 ZB lên 175 ZB) không được dùng |

Kịch bản `MapReduce.pdf` tôi chưa đọc.

Kết luận: không câu nào tôi đọc trái với slide, nhưng `VERIFIED` ở đây chỉ nghĩa là không mâu thuẫn với nguồn, không phải mọi câu đều có trong nguồn. Với nội dung nhiều chữ, kịch bản là bản dịch slide; với nội dung ít chữ, phần lớn lời giảng là model tự diễn giải. Đây là lý do có câu 6 ở §8.

**Video thử `a3_spark_rdd.mp4`**, tự đo bằng ffprobe trong container worker video:

| Thứ | Số đo |
|---|---|
| Thời lượng file | 197,12 giây; 1280×720, H.264 25 hình/giây, AAC mono 24 kHz; 2,77 MB |
| Tổng thời lượng 6 file giọng đọc | 185,69 giây (theo báo cáo) |
| Track hình | 197,08 giây |
| Track tiếng | 186,07 giây âm thanh thật, trải trên 195,15 giây |
| Quãng hổng trong track tiếng | 5 quãng ở 5 chỗ chuyển cảnh, dài 1,55–2,10 giây, tổng 9,33 giây |
| Mốc bắt đầu cảnh thật | 0 / 28,9 / 62,7 / 90,7 / 133,6 / 162,2 giây |
| Mốc tính theo thời lượng giọng đọc | 0 / 27,2 / 59,4 / 85,4 / 126,2 / 152,7 giây |
| Thời gian dựng | 175 giây (theo báo cáo) |

- Nguyên nhân: lệnh dựng từng cảnh dùng ảnh lặp (`-loop 1`) với `-shortest`, hình chạy quá tiếng 1,5–2 giây rồi mới dừng. Khi ghép, mỗi cảnh bắt đầu theo độ dài phần hình, nên track tiếng có quãng hổng: ở mỗi chỗ chuyển cảnh có ít nhất 1,5–2 giây không có tiếng.
- Hệ quả 1: mốc cảnh và phụ đề tính từ thời lượng giọng đọc sẽ sớm dần, tới cảnh cuối sớm 9,5 giây. Báo cáo đã nêu.
- Hệ quả 2, báo cáo chưa nêu: trình phát nào đi đúng mốc thời gian thì tiếng vẫn khớp hình; trình phát nào phát liền các mẫu âm thanh thì tiếng chạy trước hình, cảnh cuối lệch khoảng 9 giây. Tôi chưa phát thử trên trình duyệt, nên chưa biết trình phát của trang học viên rơi vào trường hợp nào. Khi nghe video thử, bạn xem ở cảnh 6 tiếng có khớp slide không.
- Cách sửa ở B4.

Ghi chú nhỏ: bảng `llm_usage_logs` không có dòng nào cho các lượt gọi của A2 và A3 (12 giờ gần nhất chỉ có 1 lượt chấm câu trả lời), vì bản thử gọi model từ script, không qua đường ghi sổ của core-api. Chi phí A2–A3 vì vậy không nằm trong sổ.
