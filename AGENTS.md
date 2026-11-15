# da-platform — Memory kiến trúc (đọc từ CODE, snapshot 2026-11-15)

File này là bản đồ code-level của toàn hệ thống, được tổng hợp bằng cách đọc
trực tiếp source (docs/ có thể trễ hơn code). Khi sửa kiến trúc, cập nhật lại
file này. Sơ đồ chi tiết: `.archify/index.html` (đối chiếu code 19/10/2026);
wiki theo bounded context: `codewiki-docs/`.

## 1. Bức tranh tổng

LMS tự động tạo micro-content & quiz bằng GenAI, nhúng vào LMS ngoài (Canvas
là chính, cũng hỗ trợ Open edX/Moodle) qua **LTI 1.3**. Meta-repo gồm nhiều
git submodule (xem `.gitmodules`; quy tắc submodule sống còn ở README.md).

Luồng chính:
```
Canvas (LMS) --LTI 1.3 launch--> web (Next.js BFF, port 3001->3000)
  web: verify id_token, tạo session Redis, ký JWT (bff-jwt, key web/keys/)
  --gRPC + JWT--> core-api:50051 (host 50052)  [contract: contracts/proto/core_api.proto]
core-api (NestJS, port 4000): Prisma -> Postgres 18 (uuidv7!), BullMQ -> Redis
  --enqueue--> worker (Python, BullMQ) --kết quả--> queue worker_results --> core-api ghi DB
  --outbox_events (PG LISTEN/NOTIFY)--> queue outbox_relay --> outbox-worker
      --project--> Qdrant (vector 1024-dim) + Neo4j (graph heading/concept)
embedding-service: process DUY NHẤT giữ model BGE-M3, gRPC 50061->50051
mcp-service (FastMCP :8001/mcp): learning-context tools cho ai-tutor + content-gen worker
ai-tutor (FastAPI :8010): chatbot 3 chế độ vector/tools/graph, không DB
```

Infra (docker-compose.yml dev): postgres:18-alpine (DB `chunking`), redis:7,
qdrant v1.12.1 (collection `documents`), minio (pgsty image, API 9100/console
9101), neo4j:5-community. Secret qua Infisical: luôn chạy `scripts/dc ...`
thay `docker compose`. Dev reload: `scripts/dev_reload.py` mount source nóng.

## 2. Từng repo / service

### core-api/ (NestJS 11 + Fastify, Prisma 7, BullMQ) — nhánh master
- Trung tâm nghiệp vụ, nơi DUY NHẤT ghi các bảng domain ("worker tính,
  core-api ghi"). 54 model trong `prisma/schema.prisma` (cần PG18 vì uuidv7).
- `src/grpc/grpc-server.service.ts`: gRPC server ~75 RPC, mọi RPC đều qua
  `BffJwtService` (verify JWT từ web) rồi dispatch sang domain service.
- Modules: `auth` (authz theo `course_memberships` + role `administrator`
  trong `lms_user_mappings`), `lti` (LaunchSync, assignment settings),
  `course`, `curriculum` (import đề cương Canvas, `curriculum-writer`,
  stable-uuid), `document` (upload session MinIO, canvas sync:
  `canvas-document-sync`, `canvas-sync-jobs`, queue `canvas_sync`),
  `lesson`, `review` (duyệt card/quiz draft), `quiz` (quiz-set service 841
  dòng — làm bài, chấm; `answer-grading.ts` queue riêng), `ags` (LTI
  Assignment&Grades: đẩy điểm về Canvas, token service, recovery POSTING),
  `roster` (NRPS sync), `essay-processor` (LTI Asset Processor chấm bài
  luận file), `micro-content` (lớn nhất, 1116 dòng service: CRUD, video,
  attempts, grading), `video-asset` (DAM), `chat` (lưu hội thoại/rating/
  mode chatbot), `learning-agent` (BKT: `bkt.ts`, `planner.ts`,
  `review-schedule.ts`, mastery theo LO; `review-queue.ts` dẫn xuất lịch ôn
  từ evidence; `summary` trả kèm `plan` của planner + `review` từng LO),
  `model-settings` (binding task->model profile), `content-generation` (nhận
  request sinh quiz/card),
  `outbox` (relay sang BullMQ), `worker-results` (registry handler theo
  kind, `@WorkerResultHandler`).
- Queue BullMQ (producer ở core-api): `document_processing`,
  `content_generation`, `answer_grading`, `essay_grading`, `canvas_sync`,
  `micro_content_video`, `outbox_relay`; consumer: `worker_results`.
- Outbox: trigger PG bắn kênh `outbox_channel`; LISTEN + fallback poll 15s,
  debounce 50ms, claim batch 10, lock PROCESSING quá 10 phút coi như chết,
  retry backoff 2^n giây, lỗi lần thứ 10 -> DEAD_LETTER.
- worker_results: concurrency 1, handler phải idempotent (chỉ áp dụng khi
  dòng còn trạng thái chờ); `onFinalFailure` chạy TRONG process() để gỡ
  dòng chờ; có `salvageEnvelope` cứu envelope lỗi format.
- Canvas REST client: `canvas/canvas-api.client.ts`; rewrite public URL ->
  internal khi CANVAS_API_URL nội bộ; compose map `canvas.docker:host-gateway`
  (Canvas chặn host.docker.internal bằng Blocked hosts).
- Test: `pnpm test` (jest). Env dev: PORT=4000, GRPC_PORT=50051.

### web/ (Next.js 16, React 19, pnpm) — nhánh main
- **CẢNH BÁO (web/AGENTS.md): Next.js này có breaking change so với kiến
  thức sẵn có — đọc `node_modules/next/dist/docs/` trước khi viết code.**
- BFF thuần: không DB riêng; session LTI trong Redis (`lib/session.ts`,
  sliding TTL + trần SESSION_MAX_AGE, cookie httpOnly + fallback `sid`).
- `lib/core-api.ts`: gRPC client tới core-api, mỗi call ký JWT
  (`lib/bff-jwt.ts`, key `web/keys/bff-to-core.pem`, kid `bff-2026-05`).
- `lib/tutor.ts`: HTTP/SSE tới ai-tutor `/v1/tutor/messages`, timeout 120s.
- Routes: `/lti/login` + `/lti/launch` (OIDC+launch), `/lti/deep-link`
  (composer chọn bài), `/lti/asset-processor` + `/lti/essay-report`,
  `/.well-known/jwks.json`; UI instructor `/manage/{dashboard,curriculum,
  documents,lessons,review,quizzes,micro-content,media,models,chat}`; UI
  learner `/learn/{dashboard,courses,lessons,quizzes,micro-content}`;
  `/api/*` là BFF proxy. `lib/lti-roles.ts` map role LTI ->
  instructor/learner/ta/administrator.
- Learning agent FE (15/11): `/learn/courses/[id]/mastery` (người học tự xem
  qua GetLearnerSummary), `/manage/mastery` (GV: kho luyện theo LO + ma trận
  SV × LO qua GetCourseMastery, chi tiết 1 SV qua ?userId). Types dùng chung:
  `lib/mastery.ts`; nav item "mastery" trong instructor-nav. planner.ts và
  review-schedule.ts đã nối vào GetLearnerSummary (15/11 chiều): summary trả
  thêm `plan` (Decision của planner) và `review` (lịch ôn Leitner dẫn xuất,
  quan sát sau mốc đạt coi như lần ôn); FE learner hiển thị thẻ gợi ý + hạn
  ôn. Vẫn stateless từ quiz_attempts — chưa có sự kiện xem nguồn
  (sourceViews=0) và tạm dừng đợt (paused=false) nên R2 chỉ kích theo số quan
  sát, R3 coi mọi chuỗi sai là "từ lần xem nguồn gần nhất".

### worker/ (Python 3.10+, uv, BullMQ python) — nhánh master
- 6 runner (`worker/runners/`): document, enrichment, content_generation,
  answer_grading, micro_content_video, outbox. Entry `dev_reload` trong dev.
- `use_cases/`: run_pipeline (parse->chunk->embed->store), run_enrichment,
  generate_curriculum_quiz, generate_lesson_cards, generate_micro_outline/
  quiz, generate_video_script, render_micro_content_video (slide + edge-tts
  + ffmpeg), grade_short_answers, grade_essay_submission,
  grade_micro_content_answers, extract_relations (knowledge graph PG),
  curriculum_import, verification (kiểm chứng câu hỏi — judge KHÁC model
  sinh). `prompts/` tách riêng từng loại.
- Kết quả về core-api qua `services/result_publisher.py` (id theo trạng
  thái: RUNNING/SUCCEEDED/FAILED, retry gửi lại cùng id, BullMQ bỏ trùng).
- Lỗi format payload -> `UnrecoverableError` (không retry).

### packages-ai/ = document-chunk (Python lib, clean architecture) — nhánh dev
- `domain/ports` (parser, chunker, embedder, vector_store, graph_store,
  metadata_store, job_queue, llm_client...) + `adapters/` (parsers: PyMuPDF
  fast-path, Docling OCR optional extra `ocr`, docx/pptx/markdown; chunkers:
  heading/structural/llamaindex; embedders: bge local / grpc remote; graph:
  neo4j/noop; metadata: postgres_*; storage: minio) + `application/use_cases`
  (process_document, search_chunks, course_tools...) + `delivery/`
  (grpc/http/mcp — LEGACY, chỉ còn chạy dưới profile `legacy`, sẽ xóa theo
  docs/embedding-service-migration.md §9).

### ai-sdk/ = ai-runtime-sdk — nhánh master
- Model runtime provider-neutral. `src/ai_runtime/catalog.py` là NƠI DUY
  NHẤT khai báo model: profile name -> provider (gemini/deepseek/
  openai-compatible), key chỉ giữ TÊN biến env. Tasks: quiz_generation,
  quiz_verification, quiz_regeneration, enrichment, tutor. Admin đổi binding
  qua `/manage/models` (bảng `llm_model_bindings`), thắng env. MCP client:
  `ai_runtime/mcp/learning_context.py`.

### ai-tutor/ (FastAPI :8010) — nhánh master
- Chatbot bám tài liệu khóa học, 3 mode: `vector` (1 search + 1 LLM call),
  `tools` (model tự gọi tool, tối đa 5), `graph` (tools + get_relations, tối
  đa 6). Giao thức tool TỰ ĐỊNH NGHĨA bằng JSON thuần (`agent.py`), không
  dùng function-calling provider -> 2 provider chạy giống nhau; nhắc lại tối
  đa 2 lần nếu sai format. Không DB: mọi dữ liệu qua tools của mcp-service.

### mcp-service/ (FastMCP :8001/mcp)
- Tools: retrieve_quiz_context, search_course_chunks, get_document_page,
  list_course_documents, get_course_outline, get_neighbor_chunks,
  get_concept_relations. Embedding qua GrpcEmbedder (không load BGE local),
  không dùng Neo4j.

### embedding-service/ (gRPC :50061->50051)
- Process duy nhất giữ BGE-M3 (~3GB RAM, fp16, dim 1024); backend thay thế:
  OpenAI-compatible embeddings API (`MODEL__BACKEND=openai`). Health check
  gRPC health probe. Proto: `da_platform.embedding.v1` (service-sdk/proto,
  generated vào service-sdk).

### service-sdk/ = da_service_sdk
- gRPC client SDK cho embedding-service (generated pb2 + client + models),
  dùng bởi worker/mcp-service.

### video-mcp/ (Go)
- MCP server YouTube: search_youtube_videos, get_youtube_transcript,
  create_youtube_segment (<=5 phút). Có REST /api/* tương đương + preview
  HTML + token auth. Compose riêng: docker-compose.video.yml.

### document-inspector/ (FastAPI :8002, profile `tools`)
- Dev-only: soi parse/chunk document, không DB/embedding.

### contracts/ (root, không phải submodule)
- `proto/core_api.proto`: contract DUY NHẤT giữa web và core-api (mount vào
  cả hai: /app/proto). `proto/llm_model_catalog.json`: danh mục profile.
- `integration-events/v1/*.json`: JSON schema mọi event qua queue
  (envelope, document-processing-*, content-generation-*,
  *-grading-requested/result, micro-content-*, curriculum-import-result...).
- `artifacts/v1/`, `fixtures/v1/valid/`. Kiểm: `scripts/check_grpc_contract.py`,
  `scripts/check_content_schema.py`, `scripts/check_model_catalog.py`.

### worker kết quả & event flow (tóm tắt)
core-api enqueue (BullMQ) -> worker xử lý -> publish `worker_results`
(envelope JSON theo contracts) -> core-api WorkerResultsProcessor áp vào DB
-> ghi outbox_events -> OutboxService relay -> outbox_relay queue ->
outbox-worker project Qdrant/Neo4j.

## 3. Tích hợp Canvas

- Fork ở `../canvas-lms` (KHÔNG nằm trong meta-repo), branch `do-an-canvas`,
  origin = github.com/canxphung/canvas-lms. Chỉnh sửa local gồm 2 commit:
  1. `e73bc58` S3 path-style addressing cho MinIO (config/amazon_s3.yml,
     file_store.yml, `lib/canvas/aws.rb`, s3_backend.rb + spec).
  2. `dac5031` RCE nginx config + docker-compose.rce.yml + đổi MinIO sang
     image pgsty.
  Còn lại là merge upstream Instructure. Canvas dev chạy port 3000 trên
  host; core-api gọi CANVAS_API_URL=http://canvas.docker:3000.
- core-api đồng bộ từ Canvas REST: syllabus (curriculum import), modules ->
  document placement, files (canvas-document-sync, auto-sync interval
  900s, cooldown sau launch 120s), NRPS roster, AGS writeback điểm +
  submission URL cho SpeedGrader, Asset Processor nhận bài luận qua
  `/lti/asset-processor` + notices.
- Setup: docs/canvas_lti_setup.md; scripts tiện ích: scripts/canvas-doctor,
  scripts/canvas_service_user.rb; env mẫu `.env.canvas.example`.
- `../da-lti-handoff/`: ghi chú handoff (binh.md, thien.md). Cũng có
  `../da-platform-qb` (question bank?).

## 4. Deploy & vận hành

- `deploy/docker-compose.prod.yml`: image GHCR theo IMAGE_TAG, KHÔNG publish
  port nào (chỉ cloudflared ra ngoài), object storage = Cloudflare R2 (vẫn
  biến MINIO__*), mỗi service một PG role riêng (deploy/postgres/roles.sql),
  mọi secret bắt buộc (`:?`). `deploy.sh <tag>` triển khai.
- Observability: deploy/docker-compose.observability.yml (Prometheus +
  Grafana + Loki + Alloy); metrics port 909x per service; tracing OTLP off
  mặc định.
- Backup: deploy/backup.sh. Tunnel: deploy/cloudflared.da-platform.yml.
- Compose dev tắt IPv6 trong mọi container (tránh treo DNS AAAA).

## 5. Quy ước khi sửa code

- Code comment/log chủ yếu tiếng Việt — giữ nguyên phong cách đó.
- Proto thay đổi: sửa `contracts/proto/core_api.proto` (không sửa bản copy
  trong core-api/web — đã mount chung), thêm method vào `web/src/lib/
  core-api.ts` type CoreMethod + handler trong grpc-server.service.ts.
- Event mới qua queue: thêm JSON schema vào contracts/integration-events/v1
  + fixture valid, handler đăng ký `@WorkerResultHandler` trong module domain.
- Model mới: chỉ thêm profile vào ai-sdk catalog.py + llm_model_catalog.json,
  KHÔNG hardcode provider/model ở nơi khác.
- Test: core-api `pnpm test`; web `pnpm test:lti`; python repos `uv run
  pytest` (mỗi repo có .venv riêng); video-mcp `go test ./...`.
- Env mẫu: `.env.team.example`, `.env.canvas.example`, `.env.tailscale.example`.
  Secret thật qua Infisical (`.infisical.json`), không commit .env.
- report/: LaTeX báo cáo LVTN (bản chính `lvtn_en/`), không liên quan runtime.

## 6. Những điểm dễ sai / đã biết

- Submodule mặc định detached HEAD — phải `git switch <branch>` trước khi
  code; commit repo con TRƯỚC rồi mới bump pointer ở root.
- Không hạ Postgres xuống 17 (schema cần uuidv7).
- Judge chấm/kiểm câu hỏi phải KHÁC model sinh câu hỏi
  (docs/quiz-generation-redesign.md §7.8).
- Chế độ graph của chatbot đọc `knowledge_relations` trong POSTGRES, khác
  graph Neo4j (projection heading/concept từ outbox-worker).
- grpc-server/http-api/mcp-server trong packages-ai là LEGACY (profile
  `legacy`), bề mặt đã chuyển về core-api/mcp-service.
- Theo archify review (19/10): queue micro-content script/render chưa có
  consumer đủ, payload chấm micro-content chưa khớp parser worker — kiểm
  lại code mới nhất trước khi tin.
