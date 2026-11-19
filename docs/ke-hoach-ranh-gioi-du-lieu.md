# Kế hoạch: ranh giới dữ liệu — mỗi bảng một service ghi

Ngày: 2026-11-07. Nhánh: `feat/chatbot-three-modes` (mọi repo con). Chưa commit.

Bản này thay cho kế hoạch 5 giai đoạn dán trong chat. Bản cũ chẩn đoán đúng phần lớn
nhưng có sai số liệu, sai tên trạng thái, và ba lỗ hổng làm gãy hệ thống nếu làm theo
nguyên văn. Mục 2 ghi những gì đã đối chiếu với code; mục 3 ghi những chỗ đổi so với bản cũ.

## 1. Mục tiêu

- Mỗi bảng nghiệp vụ chỉ một service được ghi. Worker Python không còn câu SQL ghi nào
  vào bảng của core-api; kết quả của worker đi về core-api qua hàng đợi, core-api ghi.
- Outbox của core-api không mất sự kiện khi Redis lỗi tạm thời, và không giành lại nhầm
  sự kiện vừa được nhặt.
- Ràng buộc dữ liệu nằm trong PostgreSQL (CHECK), không chỉ trong code.
- Quyền PostgreSQL theo từng service để cưỡng chế ranh giới — bật sau cùng, khi code đã
  không còn ghi chéo.

## 2. Hiện trạng đã đối chiếu (2026-11-07)

- 53 model Prisma, không có enum nào; mọi trạng thái là `VarChar`.
- Mọi service kết nối bằng `postgres` (superuser) vào DB `chunking`.
- 15 bảng bị cả TypeScript và Python ghi (14 nếu bỏ script eval của ai-tutor):
  `content_generation_requests, courses, curriculum_imports, documents, essay_submissions,
  lesson_cards, lessons, micro_content_answers, micro_content_attempts, micro_contents,
  outbox_events, quiz_attempts, quiz_items, video_assets` (+ `chat_runs` trong
  `ai-tutor/scripts/chat_eval.py`).
- 14 bảng chỉ Python ghi: `assessments, chapter_los, chapters, chunk_concepts,
  chunk_lo_mappings, chunks, concepts, course_goals, course_sessions,
  curriculum_extraction_issues, knowledge_relations, learning_outcomes, llm_usage_logs,
  lo_assessments`. 8 trong số đó (đề cương) là dữ liệu nghiệp vụ, không phải dữ liệu AI.
- Công thức điểm lượt nộp viết hai nơi và đang lệch: `submissionScore` dùng `Math.round`
  (`core-api/src/quiz/answer-grading.ts`), `MicroContentGradingStore` dùng `round()` của
  Python (làm tròn về số chẵn): trung bình 50.5 ra 51 bên TS, 50 bên Python.
- Worker tự mở khoá AGS (`release_graded_attempts`) bằng SQL chép thứ tự khoá của
  `lockAwaitingGroup`.
- Worker ghi sự kiện của chính nó vào `outbox_events` (`HEADING_GRAPH_PROJECT`,
  `CONCEPT_GRAPH_PROJECT`, `DOCUMENT_DELETED`) trong cùng transaction với `chunks`;
  core-api relay chúng sang hàng đợi `outbox_relay`.
- Outbox core-api: poll 5s; giành lại sự kiện `PROCESSING` theo `occurred_at` (thời điểm
  tạo, không phải thời điểm nhặt); `queue.add` lỗi thì `FAILED` và không bao giờ thử lại.
- Trạng thái thật: `ags_status` = `NOT_REQUIRED, AWAITING_GRADE, PENDING, POSTING, POSTED,
  FAILED`; nội dung = `GENERATED_DRAFT, REVIEWING, CHANGES_REQUESTED, APPROVED, PUBLISHED`.
- `quiz_items.correct_answer` đa hình nhưng có quy ước theo cột `type`
  (`core-api/src/quiz/question-types.ts`); `options` là cột riêng.
- `verify_and_refine` bỏ câu không đạt, không lưu kết luận của judge.
- `core_api.proto`: 88 RPC, 87 nhận `JsonRequest`, tất cả trả `JsonResponse`.
  (ghi chú 2026-11-16: kênh web→core-api nay là HTTP REST, proto này chỉ còn giá trị lịch sử.)

## 3. Đổi so với kế hoạch cũ

| Kế hoạch cũ | Làm thế này | Vì sao |
|---|---|---|
| Giai đoạn 1 (cưỡng chế quyền) làm đầu tiên | Làm **sau cùng**, dạng script tuỳ chọn | Cưỡng chế trước khi gỡ ghi chéo là worker gãy ngay |
| `outbox_events` chỉ core-api ghi | Worker vẫn được INSERT/DELETE, giới hạn bằng RLS theo `event_type` của nó | Worker cần ghi sự kiện cùng transaction với `chunks` (transactional outbox) |
| Không nhắc `documents` và 8 bảng đề cương | Đưa về core-api: trạng thái tài liệu qua kết quả, đề cương do core-api ghi khi áp dụng | Đây là dữ liệu nghiệp vụ, đang bị Python ghi |
| Native enum Prisma | CHECK constraint với **giá trị thật** | Enum đổi giá trị phải `ALTER TYPE`, sửa mọi literal; giá trị trong kế hoạch cũ sai (thiếu `REVIEWING`, `CHANGES_REQUESTED`; `NOT_APPLICABLE` không tồn tại) |
| `correct_answer` đổi sang `{kind, correct_index}` | Giữ dạng hiện tại, thêm CHECK theo `type` | Không phải migrate dữ liệu cũ và `grading_input` của bài đã nộp |
| Worker chỉ đọc qua view `v_*` | Worker được SELECT đúng các bảng nó đọc (liệt kê trong script) | Mục tiêu là cấm ghi; view thêm chỗ bảo trì mà không thêm an toàn |
| Callback bằng gRPC hoặc hàng đợi | Hàng đợi BullMQ `worker_results` | Bền khi core-api tắt; không phải cấp quyền gọi RPC nội bộ cho worker |
| Giai đoạn 4: typed proto cho 88 RPC | **Hoãn** | Không ảnh hưởng ranh giới dữ liệu; đụng toàn bộ `web` (có phần của thành viên khác) |
| Gộp Neo4j / `knowledge_relations` | **Hoãn**, cần người dùng quyết | `OutboxProjector` đã có sẵn; chọn kho graph là quyết định thiết kế |
| Viết lại `PostgresMetadataStore` thành pool + 3 repository | Xoá các hàm ghi bảng nghiệp vụ; giữ cấu trúc facade | Giá trị nằm ở việc bỏ quyền ghi; đổi cấu trúc là churn lớn trên 422 test |

## 4. Hợp đồng kết quả worker → core-api

- Hàng đợi BullMQ `worker_results`. Worker là producer (`bullmq` Python), core-api là
  consumer duy nhất (`@Processor`).
- Tên job = `kind`. Dữ liệu job:
  `{ result_id, kind, source_event_id, occurred_at, payload }`.
  `jobId = result_id`, sinh tất định từ nguồn (ví dụ `grading:<attempt_id>:<lần>`) để
  BullMQ chặn trùng khi worker gửi lại.
- Mỗi `kind` có JSON Schema trong `contracts/integration-events/v1/` kèm fixture được
  `packages-ai/tests/unit/test_contract_fixtures.py` kiểm.
- Handler bên core-api phải idempotent: chỉ áp dụng khi dòng đang ở trạng thái chờ
  (ví dụ `grading_status = 'PENDING'`); không bao giờ ghi đè trạng thái kết thúc.
- Worker chỉ hoàn tất job gốc sau khi đã đẩy kết quả thành công.
- Kết quả thất bại vĩnh viễn (handler/envelope ném `UnrecoverableError`, kể cả
  `InvalidWorkerResultError`, hoặc lỗi thường ở lần thử cuối của job) không được để dòng
  nghiệp vụ kẹt ở trạng thái chờ. Handler khai báo hook tuỳ chọn
  `onFinalFailure(envelope, error, ctx)`; processor gọi nó trong `process()`, trước khi
  ném lỗi cho BullMQ. Hook best-effort (không ném), đọc payload như dữ liệu chưa kiểm,
  chỉ chạm dòng còn chờ, idempotent. Quiz/micro-content: câu `PENDING` → `NEEDS_REVIEW`;
  essay: `QUEUED` → `FAILED`; đề cương: `QUEUED`/`EXTRACTING` → `FAILED`; video: asset
  `PROCESSING` → `FAILED`; tài liệu: → `ERROR` (hay về `INDEXED` với enrichment) theo
  generation + seq; sinh học liệu: request → `FAILED`; enrichment content: chỉ ghi log.
- Độ dài chuỗi trong payload tính theo code point (`worker-results/text-length.ts`), như
  JSON Schema `maxLength`, `varchar` của Postgres và phía Python; không dùng `.length`.
- Lệnh chấm điểm mang đủ dữ liệu cần chấm (snapshot `grading_input`), worker không đọc
  bảng bài làm.

## 5. Các đợt làm

**Đợt 0 — nền (song song)**
- F. Hạ tầng `worker_results`: publisher Python, processor core-api, schema envelope,
  stub handler cho từng `kind`.
- S. Migration + outbox: cột `locked_at/locked_by/next_retry_at`, index partial, thử lại
  có backoff → `DEAD_LETTER`, LISTEN/NOTIFY + poll dự phòng; cột
  `verification_status/verification_evidence` cho `quiz_items`, `lesson_cards`;
  CHECK constraint cho các cột trạng thái và `correct_answer` (kiểm dữ liệu dev trước).

**Đợt 1 — gỡ ghi chéo theo luồng (song song, file không chồng nhau)**
- G. Chấm điểm: quiz tự luận, micro-content, essay.
- C. Sinh học liệu: `lessons, quiz_items, lesson_cards, content_generation_requests`
  (cả đường enrichment), kèm hồ sơ kiểm chứng.
- I. Nạp đề cương: worker trả bản parse đầy đủ; core-api lưu và tự ghi 9 bảng đề cương
  khi áp dụng, rồi phát lệnh map lại chunk→LO cho worker.
- V. Video micro-content + trạng thái/vị trí tài liệu.

Trong đợt 1 không sửa các file repository dùng chung trong `packages-ai`; chỉ ngừng gọi.

**Đợt 2**
- R. Script role + grant + RLS, test trên DB tạm bằng chính các câu ghi của từng service.
- P. Dọn tầng Python: xoá hàm ghi bảng nghiệp vụ và 4 store của worker.

**Đợt 3** — chạy toàn bộ test, áp migration từ đầu trên DB tạm, review độc lập, sửa.

## 6. Tiêu chí xong

- Không còn câu `INSERT/UPDATE/DELETE` nào từ Python vào bảng nghiệp vụ (trừ
  `outbox_events` theo RLS và script eval).
- `submissionScore` chỉ còn một nơi.
- Test core-api, worker, packages-ai, mcp-service đều xanh (baseline: 368 / 241 / 422 / 6).
- Migration áp sạch từ DB rỗng (PG18) và áp được lên bản sao dữ liệu dev mà không vi
  phạm CHECK.
- Chạy script role trên DB tạm: mỗi service làm được đúng việc của nó và bị từ chối khi
  ghi bảng không thuộc nó.

## 7. Không làm trong đợt này

- Áp migration lên DB dev dùng chung, đổi DSN của stack dev sang role mới, sửa secret
  Infisical: người dùng tự làm hoặc cho phép riêng.
- Typed proto (Giai đoạn 4), gộp graph, viết lại cấu trúc `PostgresMetadataStore`.

## 8. Trạng thái (2026-11-10) — để review

Đợt 0–3 đã xong, **chưa commit**, chưa áp lên dev. Thay đổi nằm trong core-api, worker,
packages-ai (submodule) và contracts/, deploy/postgres/, docs/, mcp-service/ (superproject).

### Đã làm
- Hàng đợi `worker_results`: `worker/worker/services/result_publisher.py`,
  `core-api/src/worker-results/` (decorator + discovery, hook `onFinalFailure` khi kết quả
  thất bại vĩnh viễn, đếm độ dài theo code point).
- 8 handler kết quả: chấm quiz / micro-content / essay, sinh học liệu, enrichment, nạp đề
  cương (core-api tự ghi 9 bảng, `curriculum-writer.ts`), trạng thái tài liệu
  (`processing_generation` + `processing_seq` chống lùi), video (`ai_render_id`).
- Lệnh chấm điểm tự chứa; `submissionScore` chỉ còn ở `core-api/src/quiz/answer-grading.ts`.
- Outbox: `locked_at`, backoff `2^n` giây, `DEAD_LETTER` ở lần lỗi thứ 10, LISTEN/NOTIFY + poll 15s.
- Migration `20261107120000` (CHECK dạng `NOT VALID` → `VALIDATE` khi sạch, chuẩn hoá
  FILL_BLANK chuỗi), `130100`, `130200`, `130300`, `130400`.
- Python: xoá mọi hàm ghi bảng nghiệp vụ trong đường worker; test chặn tái phạm
  `worker/tests/unit/test_data_boundary_guard.py`; soft-delete chunks khi xoá tài liệu;
  tìm kiếm ẩn tài liệu đã xoá; bỏ job của lượt xử lý cũ.
- Phân quyền: `deploy/postgres/roles.sql`, `roles_check.sql`, `docker-compose.db-roles.yml`,
  hướng dẫn `docs/phan-quyen-postgres.md`. `core-api/prisma.config.ts` nhận `MIGRATION_DATABASE_URL`.

### Kiểm lại
- Unit: core-api `npx jest` (866 pass / 73 skip) + `npx tsc --noEmit`; worker 510 pass;
  packages-ai 476 pass; mcp-service 6 pass.
- DB rỗng PG18: `prisma migrate deploy` → `roles.sql` (chạy 2 lần) → `roles_check.sql`
  (73 ok, 52 bị chặn đúng).
- Tích hợp trên DB đó: 6 spec core-api chạy dưới `lms_core_app` (73/73; biến
  `*_IT_DATABASE_URL`, spec tài liệu cần thêm `DOCUMENT_RESULT_IT_SEED_DATABASE_URL` quản trị);
  packages-ai `TEST_SQL_DSN=... pytest tests/integration` (37/37); worker integration dưới
  `lms_ai_worker` với `TEST_SQL_ADMIN_DSN` (2/2).
- Hợp đồng: `core-api/src/worker-results/worker-result-contract.spec.ts` cho mọi fixture
  `contracts/fixtures/v1` qua bộ kiểm TS thật; test worker kiểm envelope sinh ra theo JSON Schema.

### Hành vi người dùng thấy thay đổi
- Trạng thái chỉ thành FAILED sau lượt thử cuối (sinh học liệu, video), không nhảy FAILED→RUNNING.
- Áp dụng đề cương ghi ngay (APPLIED), không parse lại; map chunk→LO chạy nền; không còn EXTRACTING.
- Video AI: object key `ai-<render_id>.mp4`, render muộn không đè video tải lên.
- Chấm micro-content trước đây không chạy (lỗi gọi hàm) — nay chạy; điểm tổng làm tròn kiểu `Math.round`.
- Enrichment trước đây luôn hỏng (FK `chunk_concepts` → `concepts`) — nay chạy, thẻ/câu nháp
  xuất hiện ở trang duyệt.
- Giảng viên sửa câu/thẻ AI → `verification_status` về UNVERIFIED.

### Rủi ro / chưa làm
- Dev cần: áp 6 migration (gồm `20261021201500_video_assets_dam` đang chờ), `prisma generate`
  trong container, restart core-api; dừng core-api bản cũ trước khi migrate; deploy worker
  trước core-api. Đến lúc đó outbox dev và nhiều luồng đang lỗi.
- Kết quả chấm chưa gắn `event_id` lệnh (cửa sổ đua hẹp khi chấm lại); báo chương không mang
  generation; job lượt cũ đang chạy dở vẫn có thể ghi chồng chunk; job stalled quá hạn không
  qua hook.
- Chưa chạy end-to-end trên stack thật (Redis + worker + core-api cùng lúc).
