-- =============================================================================
-- Phân quyền PostgreSQL theo ranh giới dữ liệu
-- (docs/ke-hoach-ranh-gioi-du-lieu.md mục 3, 6; cách triển khai:
-- docs/phan-quyen-postgres.md).
--
-- Mỗi service một role đăng nhập:
--   lms_core_app    core-api: ghi mọi bảng nghiệp vụ, chỉ đọc bảng AI.
--   lms_ai_worker   mọi worker Python: ghi bảng AI, chỉ đọc đúng các bảng nghiệp
--                   vụ nó cần; outbox_events giới hạn bằng RLS theo event_type.
--   lms_mcp_reader  mcp-service: chỉ đọc, phiên mặc định read-only.
--
-- Chạy bằng tài khoản quản trị (superuser hoặc owner các bảng; ở dev là
-- `postgres`), trên DB của app, SAU `prisma migrate deploy`:
--
--   psql "$ADMIN_DATABASE_URL" -X -v ON_ERROR_STOP=1 \
--        -v core_password="$LMS_CORE_APP_PASSWORD" \
--        -v worker_password="$LMS_AI_WORKER_PASSWORD" \
--        -v mcp_password="$LMS_MCP_READER_PASSWORD" \
--        -f deploy/postgres/roles.sql
--
-- Cả script là một transaction và chạy lại được. PHẢI chạy lại sau mỗi
-- migration: grant được tính lại từ bảng phân loại bên dưới, bảng mới chưa
-- phân loại được coi là bảng nghiệp vụ và in WARNING. Khi chạy lại không cần
-- truyền mật khẩu: biến nào vắng thì mật khẩu role đó giữ nguyên (role chưa có
-- thì bắt buộc). Tuỳ chọn -v migrator=<role chạy migration> (mặc định: người
-- chạy script) cho ALTER DEFAULT PRIVILEGES.
--
-- Kiểm chứng sau khi chạy: deploy/postgres/roles_check.sql.
-- =============================================================================

\set ON_ERROR_STOP on

-- event_type worker được ghi vào outbox, cùng transaction với dữ liệu AI:
--   HEADING_GRAPH_PROJECT  _pipeline_core.py → upsert_chunks_with_outbox (sau khi index chunk)
--   CONCEPT_GRAPH_PROJECT  run_enrichment.py → persist_concept_enrichment
-- DOCUMENT_DELETED do core-api ghi (document.service.ts softDelete). Đường Python
-- còn ghi nó (PostgresDocumentRepository.delete) là gRPC/HTTP legacy: RLS chặn.
\set worker_event_types 'ARRAY[''HEADING_GRAPH_PROJECT'', ''CONCEPT_GRAPH_PROJECT'']::text[]'

BEGIN;

-- Bật RLS và tạo lại policy cần khoá ACCESS EXCLUSIVE trên outbox_events. Đợi
-- quá 5s thì bỏ cả script (chạy lại sau) thay vì để core-api xếp hàng sau khoá.
SET LOCAL lock_timeout = '5s';

SELECT current_database() AS dbname \gset
\if :{?migrator}
\else
SELECT current_user AS migrator \gset
\endif

DO $$
BEGIN
  IF to_regclass('public._prisma_migrations') IS NULL
     OR to_regclass('public.outbox_events') IS NULL THEN
    RAISE EXCEPTION 'Chưa áp migration (thiếu _prisma_migrations hoặc outbox_events): chạy prisma migrate deploy trước';
  END IF;
END $$;

-- 1. Role ---------------------------------------------------------------------
-- Role là đối tượng cấp cluster: dùng chung cho mọi DB trên cùng server.
-- CREATE ROLE mặc định đã NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION
-- NOBYPASSRLS; không ALTER lại các thuộc tính đó để admin không phải superuser
-- vẫn chạy lại được, nhưng kiểm ở cuối mục này.

SELECT NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lms_core_app')   AS core_missing,
       NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lms_ai_worker')  AS worker_missing,
       NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lms_mcp_reader') AS mcp_missing \gset

\if :core_missing
  \if :{?core_password}
    CREATE ROLE lms_core_app LOGIN PASSWORD :'core_password';
  \else
    DO $$ BEGIN RAISE EXCEPTION 'lms_core_app chưa có: truyền -v core_password=...'; END $$;
  \endif
\elif :{?core_password}
  ALTER ROLE lms_core_app PASSWORD :'core_password';
\endif

\if :worker_missing
  \if :{?worker_password}
    CREATE ROLE lms_ai_worker LOGIN PASSWORD :'worker_password';
  \else
    DO $$ BEGIN RAISE EXCEPTION 'lms_ai_worker chưa có: truyền -v worker_password=...'; END $$;
  \endif
\elif :{?worker_password}
  ALTER ROLE lms_ai_worker PASSWORD :'worker_password';
\endif

\if :mcp_missing
  \if :{?mcp_password}
    CREATE ROLE lms_mcp_reader LOGIN PASSWORD :'mcp_password';
  \else
    DO $$ BEGIN RAISE EXCEPTION 'lms_mcp_reader chưa có: truyền -v mcp_password=...'; END $$;
  \endif
\elif :{?mcp_password}
  ALTER ROLE lms_mcp_reader PASSWORD :'mcp_password';
\endif

-- mcp-service chỉ đọc: lỡ sau này có grant ghi nhầm thì phiên vẫn từ chối ghi.
ALTER ROLE lms_mcp_reader SET default_transaction_read_only = on;

DO $$
DECLARE
  bad text;
BEGIN
  -- BYPASSRLS làm RLS outbox vô hiệu; SUPERUSER bỏ qua mọi grant.
  SELECT string_agg(rolname, ', ') INTO bad
    FROM pg_roles
   WHERE rolname IN ('lms_core_app', 'lms_ai_worker', 'lms_mcp_reader')
     AND (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb OR rolreplication
          OR NOT rolcanlogin);
  IF bad IS NOT NULL THEN
    RAISE EXCEPTION 'Role có thuộc tính sai (superuser/bypassrls/createrole/createdb/replication/nologin): %', bad;
  END IF;
  -- Thành viên của role khác thì thừa hưởng quyền ngoài script này.
  SELECT string_agg(m.rolname || ' ∈ ' || g.rolname, ', ') INTO bad
    FROM pg_auth_members am
    JOIN pg_roles m ON m.oid = am.member
    JOIN pg_roles g ON g.oid = am.roleid
   WHERE m.rolname IN ('lms_core_app', 'lms_ai_worker', 'lms_mcp_reader');
  IF bad IS NOT NULL THEN
    RAISE EXCEPTION 'Role app không được là thành viên role khác: %', bad;
  END IF;
END $$;

-- 2. Database, schema ---------------------------------------------------------
GRANT CONNECT ON DATABASE :"dbname" TO lms_core_app, lms_ai_worker, lms_mcp_reader;
GRANT USAGE ON SCHEMA public TO lms_core_app, lms_ai_worker, lms_mcp_reader;
-- Schema chỉ migration (tài khoản quản trị) được đổi: không role app nào tạo
-- bảng, hàm, view. PG15+ đã bỏ CREATE của PUBLIC; REVOKE lại cho DB nâng cấp từ bản cũ.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM lms_core_app, lms_ai_worker, lms_mcp_reader;

-- 3. Bảng phân loại -----------------------------------------------------------
-- domain: core   = nghiệp vụ, chỉ core-api ghi;
--         ai     = dữ liệu dẫn xuất của AI, chỉ worker ghi, core-api đọc;
--         outbox = outbox_events, core-api toàn quyền, worker theo RLS.
-- worker: none | read (SELECT) | write (SELECT/INSERT/UPDATE/DELETE)
--         | append (SELECT/INSERT, sổ chỉ ghi thêm) | outbox (SELECT/INSERT/DELETE + RLS).
-- mcp:    SELECT cho mcp-service.
-- Quyền core-api suy từ domain: core/outbox → SELECT/INSERT/UPDATE/DELETE, ai → SELECT.
-- Danh sách đọc của worker/mcp lấy từ code (ghi ở cột phải); thêm truy vấn mới
-- vào bảng khác thì sửa ở đây rồi chạy lại.
CREATE TEMP TABLE lms_table_domain (
  table_name text PRIMARY KEY,
  domain     text NOT NULL,
  worker     text NOT NULL DEFAULT 'none',
  mcp        boolean NOT NULL DEFAULT false,
  CHECK ((domain = 'core'   AND worker IN ('none', 'read'))
      OR (domain = 'ai'     AND worker IN ('write', 'append'))
      OR (domain = 'outbox' AND worker = 'outbox'))
) ON COMMIT DROP;

INSERT INTO lms_table_domain (table_name, domain, worker, mcp) VALUES
  -- Dữ liệu AI ------------------------------------------------------------------
  ('chunks',                       'ai',     'write',  true),  -- pipeline ghi; mcp: trang, láng giềng, search
  ('chunk_lo_mappings',            'ai',     'write',  true),  -- MapChunksToLos; mcp: list_chunks_for_lo
  ('concepts',                     'ai',     'write',  false), -- persist_concept_enrichment
  ('chunk_concepts',               'ai',     'write',  false), -- persist_concept_enrichment
  ('knowledge_relations',          'ai',     'write',  true),  -- extract_relations; mcp: find_relations
  ('llm_usage_logs',               'ai',     'append', false), -- record_llm_usage; core-api đọc ở trang model
  ('outbox_events',                'outbox', 'outbox', false),
  -- Nghiệp vụ, worker/mcp đọc ------------------------------------------------------
  ('courses',                      'core',   'read',   true),  -- _course_uuid, get_curriculum, replace_relations
  ('chapters',                     'core',   'read',   true),  -- get_curriculum, list_chapter_lo_links, list_los_by_chapter
  ('learning_outcomes',            'core',   'read',   true),  -- như trên + list_los_by_assessment
  ('chapter_los',                  'core',   'read',   true),  -- list_chapter_lo_links, list_los_by_chapter
  ('assessments',                  'core',   'read',   true),  -- get_curriculum, list_los_by_assessment
  ('lo_assessments',               'core',   'read',   false), -- list_los_by_assessment (lo_context)
  ('documents',                    'core',   'read',   true),  -- get_document_context/status/placement, guard trước khi ghi chunk
  ('llm_model_bindings',           'core',   'read',   false), -- ModelBindingStore: model admin chọn trên web
  -- Nghiệp vụ, chỉ core-api ----------------------------------------------------------
  ('lms_user_mappings',            'core',   'none',   false),
  ('lms_course_ref',               'core',   'none',   false),
  ('lti_resource_links',           'core',   'none',   false),
  ('lti_line_items',               'core',   'none',   false),
  ('course_memberships',           'core',   'none',   false),
  ('course_goals',                 'core',   'none',   false),
  ('course_sessions',              'core',   'none',   false),
  ('curriculum_extraction_issues', 'core',   'none',   false),
  ('curriculum_imports',           'core',   'none',   false),
  ('lessons',                      'core',   'none',   false),
  ('lesson_cards',                 'core',   'none',   false),
  ('quiz_sets',                    'core',   'none',   false),
  ('quiz_set_sessions',            'core',   'none',   false),
  ('quiz_items',                   'core',   'none',   false),
  ('quiz_attempts',                'core',   'none',   false),
  ('review_audit_logs',            'core',   'none',   false),
  ('essay_processors',             'core',   'none',   false),
  ('essay_submissions',            'core',   'none',   false),
  ('content_generation_requests',  'core',   'none',   false),
  ('micro_contents',               'core',   'none',   false),
  ('micro_content_questions',      'core',   'none',   false),
  ('micro_content_progress',       'core',   'none',   false),
  ('micro_content_attempts',       'core',   'none',   false),
  ('micro_content_answers',        'core',   'none',   false),
  ('chat_settings',                'core',   'none',   false),
  ('chat_conversations',           'core',   'none',   false),
  ('chat_runs',                    'core',   'none',   false), -- + ai-tutor/scripts/chat_eval.py (công cụ admin)
  ('video_assets',                 'core',   'none',   false),
  ('canvas_sync_runs',             'core',   'none',   false), -- CanvasDocumentSyncService (core-api); worker/mcp không đụng
  -- Chưa service nào ghi (2026-11-07); để mặc định là nghiệp vụ ------------------------
  ('videos',                       'core',   'none',   false),
  ('video_segments',               'core',   'none',   false),
  ('transcript_segments',          'core',   'none',   false),
  ('card_video_attachments',       'core',   'none',   false),
  ('flashcard_reviews',            'core',   'none',   false),
  ('chat_messages',                'core',   'none',   false),
  ('learning_events',              'core',   'none',   false),
  ('youtube_search_cache',         'core',   'none',   false),
  ('user_llm_quota',               'core',   'none',   false), -- nếu sau này worker trừ hạn mức khi gọi LLM thì đổi
  ('scope_llm_quota',              'core',   'none',   false);

DO $$
DECLARE
  missing text;
  extra   text[];
BEGIN
  -- Bảng đổi tên/xoá trong migration: dừng để người chạy sửa danh sách, thay vì
  -- âm thầm mất quyền.
  SELECT string_agg(table_name, ', ' ORDER BY table_name) INTO missing
    FROM lms_table_domain
   WHERE to_regclass(format('public.%I', table_name)) IS NULL;
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'Bảng trong danh sách phân loại không còn trong DB: %. Sửa deploy/postgres/roles.sql.', missing;
  END IF;

  -- Bảng mới chưa phân loại: coi là nghiệp vụ (core-api ghi, worker/mcp không thấy).
  SELECT array_agg(c.relname::text ORDER BY c.relname) INTO extra
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname = 'public'
     AND c.relkind IN ('r', 'p')
     AND NOT c.relispartition
     AND c.relname <> '_prisma_migrations'
     AND NOT EXISTS (SELECT FROM lms_table_domain d WHERE d.table_name = c.relname);
  IF extra IS NOT NULL THEN
    RAISE WARNING 'Bảng chưa phân loại, tạm coi là nghiệp vụ của core-api: %. Thêm vào lms_table_domain trong deploy/postgres/roles.sql.',
      array_to_string(extra, ', ');
    INSERT INTO lms_table_domain (table_name, domain) SELECT unnest(extra), 'core';
  END IF;
END $$;

-- 4. Grant --------------------------------------------------------------------
-- Thu hết rồi cấp lại theo bảng phân loại: chạy lại sau khi đổi phân loại thì
-- quyền cũ không sót lại. Trong cùng transaction nên không có lúc nào service
-- thấy mình mất quyền.
REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM lms_core_app, lms_ai_worker, lms_mcp_reader;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM lms_core_app, lms_ai_worker, lms_mcp_reader;

DO $$
DECLARE
  r record;
BEGIN
  FOR r IN SELECT * FROM lms_table_domain ORDER BY table_name LOOP
    IF r.domain IN ('core', 'outbox') THEN
      EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON public.%I TO lms_core_app', r.table_name);
    ELSE
      EXECUTE format('GRANT SELECT ON public.%I TO lms_core_app', r.table_name);
    END IF;

    CASE r.worker
      WHEN 'read' THEN
        EXECUTE format('GRANT SELECT ON public.%I TO lms_ai_worker', r.table_name);
      WHEN 'write' THEN
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON public.%I TO lms_ai_worker', r.table_name);
      WHEN 'append' THEN
        EXECUTE format('GRANT SELECT, INSERT ON public.%I TO lms_ai_worker', r.table_name);
      WHEN 'outbox' THEN
        -- SELECT vì DELETE … WHERE phải đọc cột; RLS (mục 5) giới hạn dòng.
        EXECUTE format('GRANT SELECT, INSERT, DELETE ON public.%I TO lms_ai_worker', r.table_name);
      ELSE
        NULL;
    END CASE;

    IF r.mcp THEN
      EXECUTE format('GRANT SELECT ON public.%I TO lms_mcp_reader', r.table_name);
    END IF;
  END LOOP;

  -- View (v_current_learning_outcomes, chưa code nào dùng): core-api chỉ đọc.
  -- Không cấp ghi: view tự cập nhật được sẽ ghi xuống bảng gốc bằng quyền owner.
  FOR r IN
    SELECT c.relname
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'public' AND c.relkind IN ('v', 'm')
  LOOP
    EXECUTE format('GRANT SELECT ON public.%I TO lms_core_app', r.relname);
  END LOOP;
END $$;

-- Hiện chưa có sequence (id dùng uuidv7()); cấp sẵn cho core-api nếu migration thêm.
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO lms_core_app;

-- Bảng do migration sau này tạo (owner :migrator) có ngay quyền cho core-api,
-- để core-api không gãy trong khoảng giữa `migrate deploy` và lần chạy lại script.
-- Worker và mcp không có default: bảng mới chỉ tới tay họ khi được thêm vào
-- danh sách trên rồi chạy lại. Bảng AI mới vì vậy tạm thời core-api ghi được
-- cho tới lần chạy lại — lý do phải chạy lại sau mỗi migration.
ALTER DEFAULT PRIVILEGES FOR ROLE :"migrator" IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO lms_core_app;
ALTER DEFAULT PRIVILEGES FOR ROLE :"migrator" IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO lms_core_app;

-- 5. RLS trên outbox_events ---------------------------------------------------
-- Worker ghi sự kiện của mình cùng transaction với chunks (transactional outbox),
-- nhưng không được tạo lệnh chấm bài/sinh nội dung, không đọc được payload của
-- core-api (grading_input có bài làm), không xoá sự kiện core-api đang relay.
-- Không FORCE: owner (tài khoản migration) và superuser vẫn bỏ qua RLS.
SELECT relrowsecurity AS outbox_rls_on FROM pg_class WHERE oid = 'public.outbox_events'::regclass \gset
\if :outbox_rls_on
\else
ALTER TABLE outbox_events ENABLE ROW LEVEL SECURITY;
\endif

-- Bật RLS mà thiếu policy thì core-api thấy bảng rỗng: policy toàn quyền.
DROP POLICY IF EXISTS outbox_core_app_all ON outbox_events;
CREATE POLICY outbox_core_app_all ON outbox_events
  FOR ALL TO lms_core_app
  USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS outbox_ai_worker_select ON outbox_events;
CREATE POLICY outbox_ai_worker_select ON outbox_events
  FOR SELECT TO lms_ai_worker
  USING (event_type = ANY (:worker_event_types));

-- Dòng mới phải là sự kiện chờ relay của tài liệu, đúng như
-- _append_outbox_event_cursor ghi; không giả được dòng đã xử lý.
DROP POLICY IF EXISTS outbox_ai_worker_insert ON outbox_events;
CREATE POLICY outbox_ai_worker_insert ON outbox_events
  FOR INSERT TO lms_ai_worker
  WITH CHECK (event_type = ANY (:worker_event_types)
              AND status = 'PENDING'
              AND aggregate_type = 'document');

-- Chỉ xoá sự kiện PENDING cùng loại (_delete_pending_outbox_cursor); dòng
-- PROCESSING đang được core-api relay thì không đụng.
DROP POLICY IF EXISTS outbox_ai_worker_delete ON outbox_events;
CREATE POLICY outbox_ai_worker_delete ON outbox_events
  FOR DELETE TO lms_ai_worker
  USING (event_type = ANY (:worker_event_types) AND status = 'PENDING');

COMMIT;

\echo 'roles.sql: xong. Kiểm chứng: psql ... -f deploy/postgres/roles_check.sql'
