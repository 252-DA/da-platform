# Phân quyền PostgreSQL theo ranh giới dữ liệu

Ngày: 2026-11-08. Thuộc đợt 2 (R) của [ke-hoach-ranh-gioi-du-lieu.md](ke-hoach-ranh-gioi-du-lieu.md).
**Chưa bật ở đâu.** Tài liệu này mô tả cách bật; người dùng tự áp lên dev/prod.

Hiện mọi service nối DB bằng tài khoản quản trị (`postgres` ở compose local, `app`
ở DB dev trên fedoralap). Sau khi bật, mỗi service một role, và PostgreSQL từ chối
mọi câu ghi vào bảng không thuộc service đó.

| File | Việc |
|---|---|
| [deploy/postgres/roles.sql](../deploy/postgres/roles.sql) | Tạo role, grant theo bảng phân loại, RLS cho `outbox_events`. Idempotent, một transaction. |
| [deploy/postgres/roles_check.sql](../deploy/postgres/roles_check.sql) | 126 phép kiểm: mỗi role làm được việc của mình, bị chặn ở bảng khác, khoá ngoại, NOTIFY. |
| [deploy/postgres/docker-compose.db-roles.yml](../deploy/postgres/docker-compose.db-roles.yml) | Override đổi DSN của core-api, 6 worker, mcp-service sang role mới. |
| [core-api/prisma.config.ts](../core-api/prisma.config.ts) | CLI Prisma đọc `MIGRATION_DATABASE_URL` trước, rơi về `DATABASE_URL`. |

## 1. Ba role

| Role | Service | Quyền |
|---|---|---|
| `lms_core_app` | core-api | Ghi mọi bảng nghiệp vụ; chỉ đọc bảng AI; toàn quyền `outbox_events`. |
| `lms_ai_worker` | 6 worker Python (`common-env`) | Ghi bảng AI; chỉ đọc 8 bảng nghiệp vụ; `outbox_events` theo RLS. Không đọc bài làm (`quiz_attempts`, `essay_submissions`…). |
| `lms_mcp_reader` | mcp-service | Chỉ đọc 9 bảng; phiên mặc định `default_transaction_read_only = on`. |

Không role nào có `CREATE` trên schema, `TRUNCATE`, `SUPERUSER`, `BYPASSRLS`. Không
role nào đọc được `_prisma_migrations`. ai-tutor không nối DB; script
`ai-tutor/scripts/chat_eval.py import` ghi `chat_runs` nên chạy bằng `lms_core_app`
hoặc tài khoản quản trị.

## 2. Bảng phân loại

S = SELECT, I/U/D = INSERT/UPDATE/DELETE. Nguồn: bảng `lms_table_domain` trong
`roles.sql` (sửa ở đó, không sửa ở đây).

| Bảng | Miền | core_app | ai_worker | mcp_reader | Code đọc/ghi |
|---|---|---|---|---|---|
| `chunks` | AI | S | SIUD | S | pipeline, `soft_delete_document_chunks`; mcp: trang, láng giềng |
| `chunk_lo_mappings` | AI | S | SIUD | S | `MapChunksToLos`; mcp: `list_chunks_for_lo` |
| `concepts`, `chunk_concepts` | AI | S | SIUD | – | `persist_concept_enrichment` |
| `knowledge_relations` | AI | S | SIUD | S | `extract_relations`; mcp/chat: đồ thị quan hệ |
| `llm_usage_logs` | AI | S | SI | – | `record_llm_usage` (sổ chỉ ghi thêm); core-api đọc ở trang model |
| `outbox_events` | outbox | SIUD | SID + RLS | – | xem mục 3 |
| `documents` | nghiệp vụ | SIUD | S | S | `get_document_context/status/placement`, guard trước khi ghi chunk, `CourseDocumentIndex` |
| `courses` | nghiệp vụ | SIUD | S | S | `_course_uuid`, `get_curriculum`, `replace_relations` |
| `chapters`, `learning_outcomes`, `chapter_los`, `assessments` | nghiệp vụ | SIUD | S | S | `get_curriculum`, `list_chapter_lo_links`, `list_los_by_chapter/assessment` |
| `lo_assessments` | nghiệp vụ | SIUD | S | – | `list_los_by_assessment` (`lo_context` khi sinh quiz) |
| `llm_model_bindings` | nghiệp vụ | SIUD | S | – | `ModelBindingStore` (model admin chọn trên web) |
| 28 bảng nghiệp vụ còn lại¹ | nghiệp vụ | SIUD | – | – | chỉ core-api |
| 10 bảng chưa ai ghi² | nghiệp vụ (tạm) | SIUD | – | – | chưa có code |
| `v_current_learning_outcomes` (view) | – | S | – | – | chưa code nào dùng |
| `_prisma_migrations` | quản trị | – | – | – | chỉ tài khoản migration |

¹ `lms_user_mappings, lms_course_ref, lti_resource_links, lti_line_items,
course_memberships, course_goals, course_sessions, curriculum_extraction_issues,
curriculum_imports, lessons, lesson_cards, quiz_sets, quiz_set_sessions, quiz_items,
quiz_attempts, review_audit_logs, essay_processors, essay_submissions,
content_generation_requests, micro_contents, micro_content_questions,
micro_content_progress, micro_content_attempts, micro_content_answers, chat_settings,
chat_conversations, chat_runs, video_assets`. Tổng: 6 AI + outbox + 8 + 28 + 10 = 53 bảng.

² `videos, video_segments, transcript_segments, card_video_attachments,
flashcard_reviews, chat_messages, learning_events, youtube_search_cache,
user_llm_quota, scope_llm_quota`. Chưa service nào ghi (quét 2026-11-07). Nếu sau này
worker trừ hạn mức LLM vào `user_llm_quota`/`scope_llm_quota` thì phải đổi phân loại.

## 3. RLS trên `outbox_events`

Worker ghi sự kiện của mình cùng transaction với `chunks` (transactional outbox), nên
vẫn được INSERT/DELETE, nhưng chỉ với hai `event_type`:

| event_type | Ai ghi |
|---|---|
| `HEADING_GRAPH_PROJECT` | `_pipeline_core.py` → `upsert_chunks_with_outbox` |
| `CONCEPT_GRAPH_PROJECT` | `run_enrichment.py` → `persist_concept_enrichment` |

Policy:
- `outbox_core_app_all`: core-api mọi lệnh, mọi dòng.
- `outbox_ai_worker_select`: worker chỉ thấy dòng thuộc hai loại trên — không đọc được
  payload lệnh chấm bài (có `grading_input`).
- `outbox_ai_worker_insert`: dòng mới phải là hai loại trên, `status = 'PENDING'`,
  `aggregate_type = 'document'`.
- `outbox_ai_worker_delete`: chỉ xoá dòng `PENDING` của hai loại trên; dòng
  `PROCESSING` core-api đang relay thì không.

Không `FORCE ROW LEVEL SECURITY`: owner (tài khoản migration) và superuser bỏ qua RLS,
nên migration và thao tác tay không đổi. Trigger NOTIFY chạy bằng quyền người INSERT,
`pg_notify`/`LISTEN` không cần quyền: đã kiểm worker INSERT đánh thức listener của
`lms_core_app`. `DOCUMENT_DELETED` do core-api ghi (`document.service.ts`).

## 4. Điều kiện trước khi bật

1. Code đợt 0–2 đang chạy trên môi trường đó: worker không còn ghi bảng nghiệp vụ.
   Bật trên code cũ thì worker gãy ngay (ghi `documents`, `quiz_attempts`…).
2. Đã áp đủ migration (DB dev 2026-11-08 mới có 16/21; thiếu `video_assets_dam` và 5
   migration ngày 2026-11-07).
3. Không chạy profile `legacy` (`grpc-server`, `http-api`, `mcp-server`) bằng role mới:
   chúng còn ghi bảng nghiệp vụ (mục 8).
4. **Dừng mọi core-api bản cũ trước khi áp migration `20261107120000_data_boundary_hardening`**,
   kể cả bản của thành viên khác trên DB chung và bản cũ còn lại lúc rolling deploy.
   Outbox mới giành lại sự kiện `PROCESSING` theo `locked_at` (thời điểm nhặt); bản cũ
   giành lại theo `occurred_at` (thời điểm tạo) nên cướp lại ngay sự kiện bản mới vừa
   nhặt và relay trùng (chấm lại bài, sinh lại câu hỏi). Migration cố ý giữ `FAILED`
   trong CHECK `outbox_events.status` để bản cũ lỡ còn chạy thì ghi `FAILED` không bị
   Postgres chặn, nhưng dòng `FAILED` do bản cũ để lại không được relay lại (xử lý như
   dead letter, bằng tay). Thứ tự: dừng bản cũ → áp migration → chạy bản mới.
5. Migration báo `WARNING: CHECK ... còn N dòng vi phạm dữ liệu cũ` nghĩa là dữ liệu
   dev còn dòng không suy ra được đáp án (vd `MCQ_SINGLE` có `correct_answer` là
   `null`). Constraint vẫn có hiệu lực với dòng mới nhưng chưa `VALIDATE`: sửa hoặc
   xoá mềm dòng đó (dòng đã xoá mềm được miễn khỏi CHECK hình dạng đáp án) rồi chạy
   `ALTER TABLE <bảng> VALIDATE CONSTRAINT <tên>`. Trong lúc đó UPDATE lên dòng hỏng
   (trừ việc sửa lại đáp án hay xoá mềm) bị constraint từ chối.

## 5. Các bước, theo thứ tự an toàn

**a. Sinh mật khẩu** (hex để nhúng thẳng vào URL) và lưu vào Infisical env `dev` với tên
`LMS_CORE_APP_PASSWORD`, `LMS_AI_WORKER_PASSWORD`, `LMS_MCP_READER_PASSWORD`:
```bash
openssl rand -hex 24
```

**b. Áp migration bằng tài khoản quản trị.** Khi core-api đã chạy bằng `lms_core_app`,
`prisma migrate deploy` với `DATABASE_URL` của container sẽ báo `permission denied for
schema public`. Truyền URL quản trị chỉ cho lệnh đó, không đặt vào env của core-api:
```bash
# DB local (docker-compose.yml)
docker compose exec -e MIGRATION_DATABASE_URL=postgresql://postgres:postgres@postgres:5432/chunking \
  core-api npx prisma migrate deploy
# DB remote qua Infisical (biến nở bên trong infisical run)
infisical run --env=dev -- sh -c 'docker compose exec \
  -e MIGRATION_DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${DB_HOST}:5432/${POSTGRES_DB}" \
  core-api npx prisma migrate deploy'
```

**c. Chạy `roles.sql`** bằng chính tài khoản chạy migration (owner bảng), trên đúng DB
của app. Role là đối tượng cấp cluster: tạo một lần cho cả server.
```bash
# Trên máy DB (fedoralap), qua socket trong container postgres:
docker exec -i <container-postgres> psql -U app -d app -X -v ON_ERROR_STOP=1 \
  -v core_password=... -v worker_password=... -v mcp_password=... < deploy/postgres/roles.sql
# Từ máy dev, qua một container psql dùng một lần (không cần cài psql):
infisical run --env=dev -- sh -c 'docker run --rm -i postgres:18-alpine psql \
  "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${DB_HOST}:5432/${POSTGRES_DB}" -X -v ON_ERROR_STOP=1 \
  -v core_password="$LMS_CORE_APP_PASSWORD" -v worker_password="$LMS_AI_WORKER_PASSWORD" \
  -v mcp_password="$LMS_MCP_READER_PASSWORD" -f -' < deploy/postgres/roles.sql
```
Container dùng một lần phải tới được `DB_HOST` (Tailscale); không được thì chạy cách
thứ nhất trên máy DB. Chạy từ thư mục gốc repo. Mật khẩu đi qua `ALTER ROLE … PASSWORD`; nếu server bật `log_statement = ddl/all` thì
mật khẩu vào log — truyền chuỗi SCRAM đã băm (`SCRAM-SHA-256$…`) thay cho mật khẩu thô
nếu cần. Script cần lock `outbox_events` (bật RLS, tạo lại policy); đợi quá 5 giây thì
tự huỷ, chạy lại sau.

**d. Kiểm.** Đầy đủ trên DB tạm hoặc bản sao:
`psql … -X -v ON_ERROR_STOP=1 -f deploy/postgres/roles_check.sql` (exit 0, dòng cuối
`roles_check: tất cả đạt`). Trên DB dev đang có core-api chạy, thêm `-v skip_notify=1`:
mục 1–8 chạy trong một transaction rồi ROLLBACK; riêng mục 9 COMMIT thật một dòng outbox.
Thử đăng nhập từng role: `psql "postgresql://lms_mcp_reader:…@host/db" -c 'select current_user'`.

**e. Đổi DSN từng service một**, thêm override vào cuối `COMPOSE_FILE` trong `.env`:
```bash
COMPOSE_FILE=docker-compose.yml:docker-compose.remote-db.yml:deploy/postgres/docker-compose.db-roles.yml
```
Override đổi DSN của cả nhóm; muốn đi từng bước thì chỉ tạo lại service đang đổi,
service khác giữ container cũ (DSN cũ) cho tới khi được tạo lại:
1. `scripts/dc up -d --no-deps mcp-service` (chỉ đọc, rủi ro thấp nhất), thử chatbot ba chế độ.
2. `scripts/dc up -d --no-deps outbox-worker enrichment-worker`, rồi `document-worker`
   (upload một tài liệu), rồi `content-generation-worker answer-grading-worker micro-content-video-worker`.
3. `scripts/dc up -d --no-deps core-api` cuối cùng (relay outbox, chấm bài, nạp đề cương).

Sau mỗi bước, theo dõi:
```bash
scripts/dc logs -f --since 10m <service> | grep -iE 'permission denied|row-level security|read-only transaction'
```

**f. Rollback**: bỏ override khỏi `COMPOSE_FILE`, `scripts/dc up -d <service>`. DSN về
tài khoản quản trị, mà tài khoản đó bỏ qua grant và RLS, nên không cần gỡ role. Muốn gỡ
hẳn (bằng tài khoản quản trị):
```sql
DROP POLICY outbox_core_app_all ON outbox_events;      -- và 3 policy outbox_ai_worker_*
ALTER TABLE outbox_events DISABLE ROW LEVEL SECURITY;
DROP OWNED BY lms_core_app, lms_ai_worker, lms_mcp_reader;  -- grant + default privileges, ở từng DB
DROP ROLE lms_core_app, lms_ai_worker, lms_mcp_reader;
```

## 6. Sau mỗi migration: chạy lại `roles.sql`

Không cần truyền lại mật khẩu (biến vắng thì giữ mật khẩu cũ). Script thu hết quyền rồi
cấp lại theo bảng phân loại, trong một transaction.
- Bảng mới chưa phân loại: `WARNING … tạm coi là nghiệp vụ` — core-api ghi được, worker
  và mcp không thấy. Thêm vào `lms_table_domain` nếu là bảng AI hoặc worker/mcp cần đọc.
- Bảng trong danh sách bị đổi tên/xoá: `ERROR`, không đổi gì; sửa danh sách rồi chạy lại.
- Giữa `migrate deploy` và lần chạy lại, `ALTER DEFAULT PRIVILEGES` cho core-api sẵn
  quyền ghi trên bảng mới (tạo bởi role chạy migration, mặc định là người chạy script;
  khác thì truyền `-v migrator=<role>`). Bảng AI mới vì vậy tạm thời core-api ghi được —
  lý do phải chạy lại.
- Code worker/mcp bắt đầu đọc bảng nghiệp vụ mới: sửa cột `worker`/`mcp` rồi chạy lại,
  trước khi deploy code đó.

## 7. Chạy test tích hợp dưới role

```bash
# core-api: handler chạy bằng lms_core_app; spec tài liệu mồi chunks bằng URL quản trị
U=postgresql://lms_core_app:…@localhost:55432/<db>
OUTBOX_IT_DATABASE_URL=$U GRADING_IT_DATABASE_URL=$U CONTENT_GENERATION_IT_DATABASE_URL=$U \
CURRICULUM_IT_DATABASE_URL=$U VIDEO_RESULT_IT_DATABASE_URL=$U DOCUMENT_RESULT_IT_DATABASE_URL=$U \
DOCUMENT_RESULT_IT_SEED_DATABASE_URL=postgresql://postgres:…@localhost:55432/<db> \
  npx jest --runInBand integration.spec
# worker: TEST_SQL_DSN = role worker, TEST_SQL_ADMIN_DSN = quản trị (mồi dữ liệu core-api)
TEST_SQL_DSN=postgresql://lms_ai_worker:…@… TEST_SQL_ADMIN_DSN=postgresql://postgres:…@… \
  .venv/bin/python -m pytest tests/integration --no-cov -q -p no:cacheprovider
```
Các test tích hợp cũ của packages-ai (`test_chunk_lo_mapping`, `test_curriculum_*`,
`test_concept_enrichment_store`, `test_document_placement_store`) mồi đề cương và
`documents` bằng chính store, nên chỉ chạy được bằng tài khoản quản trị.

## 8. Còn mở, rủi ro khi bật trên dev

- Đường Python legacy sẽ lỗi quyền dưới role worker (đã kiểm): `upsert_document`,
  `update_document_status`, `set_document_chapter`, `delete()` (RLS chặn
  `DOCUMENT_DELETED`), `append_outbox_event` với loại khác hai loại trên,
  `list_lesson_cards`, `list_quiz_items`; tức `ProcessDocument/EnqueueDocument/
  DeleteDocument/GetCards/GetQuiz` của gRPC/HTTP legacy, và `MetadataStoreDocumentReporter`
  — reporter mặc định khi `PipelineCore`/`MapChunksToLosUseCase` không được truyền
  reporter. Worker luôn truyền reporter qua `worker_results`.
- `chunks.document_id` là `ON DELETE RESTRICT`: tài liệu có chunk không xoá cứng được
  với mọi role. core-api chỉ soft-delete nên không ảnh hưởng. Hành động `ON DELETE`
  (SET NULL sang `llm_usage_logs`, CASCADE sang `knowledge_relations`) chạy bằng quyền
  owner nên core-api xoá dòng nghiệp vụ vẫn được.
- PUBLIC vẫn có `TEMP` trên database và `CONNECT` vào các DB khác của server (vd
  `postgres`): role app (trừ phiên read-only của mcp) tạo được bảng tạm trong phiên
  của mình. Vô hại với dữ liệu app; không thu để khỏi đụng role khác.
- Mỗi worker mở tối đa `SQL__POOL_SIZE` (5) kết nối; role không đặt `CONNECTION LIMIT`.
- Prisma không quản RLS/policy; `migrate deploy` không kiểm drift. Migration nào
  `DROP`/tạo lại `outbox_events` sẽ mất policy cho tới khi chạy lại `roles.sql`.
