-- =============================================================================
-- Kiểm chứng deploy/postgres/roles.sql: mỗi role làm được đúng việc của service
-- mình và bị từ chối khi ghi bảng không thuộc nó.
--
-- Chạy bằng tài khoản quản trị (superuser), sau roles.sql, nên trên DB tạm hoặc
-- bản sao:
--
--   psql "$ADMIN_DATABASE_URL" -X -v ON_ERROR_STOP=1 -f deploy/postgres/roles_check.sql
--
-- Mục 1–8 chạy trong một transaction rồi ROLLBACK: dữ liệu mồi không còn lại.
-- Mục 9 (NOTIFY) phải COMMIT thật một dòng outbox của worker rồi xoá ngay; trên
-- DB có core-api đang chạy thì core-api có thể relay dòng đó trước — bỏ mục này
-- bằng -v skip_notify=1. Mục 9 cần psql ≥ 16 (SHELL_ERROR), chạy `psql` con với
-- cùng host/port/user/db (mật khẩu qua PGPASSWORD hoặc .pgpass nếu cần).
--
-- Giả lập từng service bằng SET ROLE: quyền bảng và RLS áp như khi service đăng
-- nhập thật. default_transaction_read_only của lms_mcp_reader chỉ có hiệu lực
-- khi đăng nhập thật nên được kiểm qua cấu hình role.
--
-- Dòng "ok"/"chặn" là đạt; gặp FAIL thì dừng ngay, exit code 3. Câu SQL thử là
-- bản chép các câu thật trong code (đường dẫn ghi cạnh nhãn).
-- =============================================================================

\set ON_ERROR_STOP on
\set QUIET on
SET client_min_messages = notice;

BEGIN;

-- Chạy p_sql dưới role p_role; phải thành công (và đúng p_rows dòng nếu có).
CREATE FUNCTION pg_temp.expect_ok(p_role text, p_label text, p_sql text, p_rows bigint DEFAULT NULL)
RETURNS void LANGUAGE plpgsql AS $f$
DECLARE
  n bigint;
BEGIN
  BEGIN
    EXECUTE format('SET LOCAL ROLE %I', p_role);
    EXECUTE p_sql;
    GET DIAGNOSTICS n = ROW_COUNT;
    RESET ROLE;
  EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION 'FAIL  % [%]: % (SQLSTATE %)', p_label, p_role, SQLERRM, SQLSTATE;
  END;
  IF p_rows IS NOT NULL AND n <> p_rows THEN
    RAISE EXCEPTION 'FAIL  % [%]: % dòng, cần %', p_label, p_role, n, p_rows;
  END IF;
  RAISE NOTICE 'ok    % [%] (% dòng)', p_label, p_role, n;
END $f$;

-- Chạy p_sql dưới role p_role; phải lỗi đúng SQLSTATE (mặc định 42501
-- insufficient_privilege: cả "permission denied" lẫn vi phạm policy RLS).
-- Lỗi rollback subtransaction nên SET LOCAL ROLE cũng được hoàn lại.
CREATE FUNCTION pg_temp.expect_error(p_role text, p_label text, p_sql text,
                                     p_state text DEFAULT '42501', p_like text DEFAULT NULL)
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
  BEGIN
    EXECUTE format('SET LOCAL ROLE %I', p_role);
    EXECUTE p_sql;
  EXCEPTION WHEN OTHERS THEN
    IF SQLSTATE <> p_state OR (p_like IS NOT NULL AND SQLERRM NOT LIKE p_like) THEN
      RAISE EXCEPTION 'FAIL  % [%]: lỗi khác mong đợi: % (SQLSTATE %)', p_label, p_role, SQLERRM, SQLSTATE;
    END IF;
    RAISE NOTICE 'chặn  % [%]: %', p_label, p_role, SQLERRM;
    RETURN;
  END;
  RAISE EXCEPTION 'FAIL  % [%]: không bị chặn', p_label, p_role;
END $f$;

CREATE FUNCTION pg_temp.expect_true(p_ok boolean, p_label text)
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
  IF p_ok IS NOT TRUE THEN
    RAISE EXCEPTION 'FAIL  %', p_label;
  END IF;
  RAISE NOTICE 'ok    %', p_label;
END $f$;

-- 1. Cấu hình role, schema, RLS ---------------------------------------------
DO $$
DECLARE
  r text;
BEGIN
  FOREACH r IN ARRAY ARRAY['lms_core_app', 'lms_ai_worker', 'lms_mcp_reader'] LOOP
    PERFORM pg_temp.expect_true(
      EXISTS (SELECT FROM pg_roles WHERE rolname = r AND rolcanlogin
                AND NOT (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb OR rolreplication)),
      r || ': LOGIN, không superuser/bypassrls/createrole/createdb');
    PERFORM pg_temp.expect_true(has_database_privilege(r, current_database(), 'CONNECT'),
      r || ': CONNECT vào DB');
    PERFORM pg_temp.expect_true(has_schema_privilege(r, 'public', 'USAGE')
                                AND NOT has_schema_privilege(r, 'public', 'CREATE'),
      r || ': USAGE, không CREATE trên schema public');
  END LOOP;
  PERFORM pg_temp.expect_true(
    (SELECT 'default_transaction_read_only=on' = ANY (rolconfig) FROM pg_roles WHERE rolname = 'lms_mcp_reader'),
    'lms_mcp_reader: default_transaction_read_only=on');
  PERFORM pg_temp.expect_true(
    (SELECT relrowsecurity AND NOT relforcerowsecurity FROM pg_class WHERE oid = 'public.outbox_events'::regclass),
    'outbox_events: bật RLS, không FORCE (owner vẫn bỏ qua)');
END $$;

-- Dữ liệu mồi (quyền quản trị, bỏ qua RLS) ------------------------------------
INSERT INTO courses (course_id, code, name) VALUES
  ('c0de0000-0000-4000-8000-000000000c01', 'ROLES-CHECK-1', 'roles_check'),
  ('c0de0000-0000-4000-8000-000000000c02', 'ROLES-CHECK-2', 'roles_check: học phần để xoá');
INSERT INTO lms_user_mappings (internal_user_id, lms_sub, display_name, role) VALUES
  ('c0de0000-0000-4000-8000-000000000a01', 'roles-check-1', 'SV', 'learner'),
  ('c0de0000-0000-4000-8000-000000000a02', 'roles-check-2', 'SV', 'learner');
INSERT INTO learning_outcomes (lo_id, course_id, code, statement_vi) VALUES
  ('c0de0000-0000-4000-8000-000000000b01', 'c0de0000-0000-4000-8000-000000000c01', 'L.O.RC', 'Hiểu');
INSERT INTO lessons (lesson_id, course_id, lo_id, title) VALUES
  ('c0de0000-0000-4000-8000-000000000b02', 'c0de0000-0000-4000-8000-000000000c01',
   'c0de0000-0000-4000-8000-000000000b01', 'Bài');
INSERT INTO quiz_items (quiz_id, course_id, lesson_id, question, type, correct_answer) VALUES
  ('c0de0000-0000-4000-8000-000000000b03', 'c0de0000-0000-4000-8000-000000000c01',
   'c0de0000-0000-4000-8000-000000000b02', 'Câu', 'MCQ_SINGLE', '"A"');
INSERT INTO quiz_attempts (attempt_id, user_id, quiz_id, course_id, score, chosen_answer, is_correct) VALUES
  ('c0de0000-0000-4000-8000-000000000b04', 'c0de0000-0000-4000-8000-000000000a01',
   'c0de0000-0000-4000-8000-000000000b03', 'c0de0000-0000-4000-8000-000000000c01', 100, '"A"', true);
INSERT INTO documents (document_id, course_id, title, file_path, status) VALUES
  ('c0de0000-0000-4000-8000-000000000d01', 'c0de0000-0000-4000-8000-000000000c01', 'd1.pdf', 'documents/rc/d1.pdf', 'INDEXED'),
  ('c0de0000-0000-4000-8000-000000000d02', 'c0de0000-0000-4000-8000-000000000c01', 'd2.pdf', 'documents/rc/d2.pdf', 'QUEUED');
INSERT INTO chunks (chunk_id, document_id, course_id, content, sort_order, heading_path) VALUES
  ('c0de0000-0000-4000-8000-000000000e01', 'c0de0000-0000-4000-8000-000000000d01',
   'c0de0000-0000-4000-8000-000000000c01', 'chunk 1', 0, ARRAY['Chương 1']);
INSERT INTO curriculum_imports (import_id, course_id, source, file_name, storage_key) VALUES
  ('c0de0000-0000-4000-8000-000000000f01', 'c0de0000-0000-4000-8000-000000000c01', 'upload', 'dcmh.pdf', 'curricula/rc.pdf');
INSERT INTO outbox_events (event_id, event_type, aggregate_type, aggregate_id, payload, status) VALUES
  -- lệnh chấm bài của core-api, payload chứa bài làm
  ('c0de0000-0000-4000-8000-000000000101', 'ANSWER_GRADING_REQUESTED', 'quiz_attempt',
   'c0de0000-0000-4000-8000-000000000b04', '{"grading_input": "bài làm"}', 'PENDING'),
  -- sự kiện của worker đang được core-api relay
  ('c0de0000-0000-4000-8000-000000000102', 'HEADING_GRAPH_PROJECT', 'document',
   'c0de0000-0000-4000-8000-000000000d01', '{}', 'PROCESSING'),
  -- sự kiện của worker còn chờ
  ('c0de0000-0000-4000-8000-000000000103', 'HEADING_GRAPH_PROJECT', 'document',
   'c0de0000-0000-4000-8000-000000000d01', '{}', 'PENDING');
INSERT INTO llm_usage_logs (usage_id, user_id, course_id, provider, model, use_case, status) VALUES
  ('c0de0000-0000-4000-8000-000000000201', 'c0de0000-0000-4000-8000-000000000a01',
   'c0de0000-0000-4000-8000-000000000c01', 'gemini', 'check', 'roles_check', 'OK'),
  ('c0de0000-0000-4000-8000-000000000202', 'c0de0000-0000-4000-8000-000000000a02',
   'c0de0000-0000-4000-8000-000000000c02', 'gemini', 'check', 'roles_check', 'OK');

-- 2. lms_ai_worker: việc của worker ----------------------------------------------
DO $$
DECLARE
  t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['documents', 'courses', 'chapters', 'learning_outcomes', 'chapter_los',
                           'assessments', 'lo_assessments', 'llm_model_bindings'] LOOP
    PERFORM pg_temp.expect_ok('lms_ai_worker', 'đọc bảng nghiệp vụ ' || t, format('SELECT * FROM %I', t));
  END LOOP;

  -- postgres_document_repository.get_document_status / get_document_context
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'get_document_status', $q$
    SELECT status, NULL AS error_msg, file_path FROM documents
     WHERE document_id = 'c0de0000-0000-4000-8000-000000000d01' AND deleted_at IS NULL$q$, 1);
  -- postgres_chunk_repository: guard xoá rồi _upsert_chunks_cursor
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'upsert_chunks_with_outbox: guard documents', $q$
    SELECT EXISTS(SELECT 1 FROM documents WHERE document_id = 'c0de0000-0000-4000-8000-000000000d01'
                     AND deleted_at IS NULL)$q$, 1);
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'upsert_chunks_with_outbox: INSERT chunks … ON CONFLICT', $q$
    INSERT INTO chunks (chunk_id, document_id, course_id, content, heading_path, page_number, sort_order, language)
    SELECT 'c0de0000-0000-4000-8000-000000000e02'::uuid, 'c0de0000-0000-4000-8000-000000000d01'::uuid,
           d.course_id, 'chunk 2', ARRAY['Chương 1'], 1, 1, 'vi'
      FROM documents d
     WHERE d.document_id = 'c0de0000-0000-4000-8000-000000000d01'::uuid AND d.deleted_at IS NULL
    ON CONFLICT (chunk_id) DO UPDATE SET
      document_id = EXCLUDED.document_id, course_id = EXCLUDED.course_id, content = EXCLUDED.content,
      heading_path = EXCLUDED.heading_path, page_number = EXCLUDED.page_number,
      sort_order = EXCLUDED.sort_order, language = EXCLUDED.language, deleted_at = NULL$q$, 1);
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'upsert_chunks_with_outbox: replace_chunks soft-delete', $q$
    UPDATE chunks SET deleted_at = now()
     WHERE document_id = 'c0de0000-0000-4000-8000-000000000d01'::uuid AND deleted_at IS NULL
       AND NOT (chunk_id = ANY(ARRAY['c0de0000-0000-4000-8000-000000000e02']::uuid[]))$q$, 1);
  -- postgres_outbox_repository._append_outbox_event_cursor (cùng transaction với chunks)
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'outbox INSERT HEADING_GRAPH_PROJECT', $q$
    INSERT INTO outbox_events (event_id, event_type, aggregate_type, aggregate_id, payload, status, retry_count, last_error)
    VALUES ('c0de0000-0000-4000-8000-000000000111'::uuid, 'HEADING_GRAPH_PROJECT', 'document',
            'c0de0000-0000-4000-8000-000000000d01'::uuid, '{"replace_chunks": true}'::jsonb, 'PENDING', 0, NULL)$q$, 1);
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'outbox INSERT CONCEPT_GRAPH_PROJECT', $q$
    INSERT INTO outbox_events (event_id, event_type, aggregate_type, aggregate_id, payload, status, retry_count, last_error)
    VALUES ('c0de0000-0000-4000-8000-000000000112'::uuid, 'CONCEPT_GRAPH_PROJECT', 'document',
            'c0de0000-0000-4000-8000-000000000d01'::uuid, '{}'::jsonb, 'PENDING', 0, NULL)$q$, 1);
  -- _delete_pending_outbox_cursor: xoá đúng 2 dòng PENDING cùng loại; dòng PROCESSING còn nguyên
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'outbox DELETE PENDING cùng loại', $q$
    DELETE FROM outbox_events
     WHERE aggregate_id = 'c0de0000-0000-4000-8000-000000000d01'::uuid
       AND UPPER(event_type) = 'HEADING_GRAPH_PROJECT' AND status = 'PENDING'$q$, 2);
  -- MapChunksToLos: delete_inferred_chunk_lo_mappings + upsert_chunk_lo_mappings
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'upsert_chunk_lo_mappings', $q$
    INSERT INTO chunk_lo_mappings (chunk_id, lo_id, confidence, source, provenance)
    VALUES ('c0de0000-0000-4000-8000-000000000e02'::uuid, 'c0de0000-0000-4000-8000-000000000b01'::uuid, 0.8, 'heading', 'inferred')
    ON CONFLICT (chunk_id, lo_id) DO UPDATE SET
      confidence = GREATEST(EXCLUDED.confidence, chunk_lo_mappings.confidence),
      source = EXCLUDED.source,
      provenance = CASE WHEN chunk_lo_mappings.provenance = 'confirmed' THEN 'confirmed' ELSE EXCLUDED.provenance END$q$, 1);
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'list_chunks_for_lo', $q$
    SELECT c.chunk_id FROM chunk_lo_mappings clm
      JOIN chunks c ON c.chunk_id = clm.chunk_id
      JOIN documents d ON d.document_id = c.document_id
     WHERE clm.lo_id = 'c0de0000-0000-4000-8000-000000000b01'::uuid
       AND c.deleted_at IS NULL AND d.deleted_at IS NULL
     ORDER BY (d.role = 'reference'), clm.confidence DESC$q$, 1);
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'delete_inferred_chunk_lo_mappings', $q$
    DELETE FROM chunk_lo_mappings clm USING chunks c
     WHERE c.chunk_id = clm.chunk_id AND c.document_id = 'c0de0000-0000-4000-8000-000000000d01'::uuid
       AND clm.provenance <> 'confirmed'$q$, 1);
  -- persist_concept_enrichment: concepts trước, rồi thay chunk_concepts
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'persist_concept_enrichment: concepts', $q$
    INSERT INTO concepts (id, name, canonical_name, slug, domain, category, language, updated_at)
    VALUES ('rc-concept', 'Đạo hàm', 'dao ham', 'dao-ham', 'math', 'other', 'vi', NOW())
    ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, canonical_name = EXCLUDED.canonical_name,
      slug = EXCLUDED.slug, domain = EXCLUDED.domain, category = EXCLUDED.category,
      language = COALESCE(EXCLUDED.language, concepts.language), updated_at = NOW()$q$, 1);
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'persist_concept_enrichment: xoá chunk_concepts cũ', $q$
    DELETE FROM chunk_concepts WHERE chunk_id IN (
      SELECT chunk_id FROM chunks WHERE document_id = 'c0de0000-0000-4000-8000-000000000d01'::uuid
         AND deleted_at IS NULL)$q$, 0);
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'persist_concept_enrichment: chunk_concepts', $q$
    INSERT INTO chunk_concepts (chunk_id, concept_id, confidence, source, updated_at)
    VALUES ('c0de0000-0000-4000-8000-000000000e02'::uuid, 'rc-concept', 0.9, 'heading', NOW())
    ON CONFLICT (chunk_id, concept_id) DO UPDATE SET confidence = EXCLUDED.confidence,
      source = EXCLUDED.source, updated_at = NOW()$q$, 1);
  -- extract_relations → replace_relations
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'replace_relations: _resolve_course', $q$
    SELECT course_id::text FROM courses WHERE code = 'ROLES-CHECK-1' OR course_id = 'c0de0000-0000-4000-8000-000000000c01'::uuid LIMIT 1$q$, 1);
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'replace_relations: DELETE', $q$
    DELETE FROM knowledge_relations WHERE chunk_id = ANY(ARRAY['c0de0000-0000-4000-8000-000000000e02']::uuid[])$q$, 0);
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'replace_relations: INSERT', $q$
    INSERT INTO knowledge_relations (course_id, document_id, chunk_id, source_label, source_key, relation_type,
                                     target_label, target_key, evidence_quote, page_number, extraction_version, model)
    VALUES ('c0de0000-0000-4000-8000-000000000c01'::uuid, 'c0de0000-0000-4000-8000-000000000d01'::uuid,
            'c0de0000-0000-4000-8000-000000000e02'::uuid, 'Đạo hàm', 'dao ham', 'defines', 'Giới hạn', 'gioi han',
            'trích dẫn', 1, 'v1', 'check')
    ON CONFLICT DO NOTHING$q$, 1);
  -- record_llm_usage
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'record_llm_usage', $q$
    INSERT INTO llm_usage_logs (user_id, course_id, provider, model, use_case, prompt_tokens, completion_tokens,
                                cost_usd, latency_ms, status, trace_id)
    VALUES (NULL, 'c0de0000-0000-4000-8000-000000000c01'::uuid, 'gemini', 'check', 'answer_grading', 10, 5, 0, 12, 'OK', NULL)$q$, 1);
  -- outbox_projector DOCUMENT_DELETED: soft-delete chunks của tài liệu đã xoá
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'DOCUMENT_DELETED: soft-delete chunks', $q$
    UPDATE chunks SET deleted_at = now()
     WHERE document_id = 'c0de0000-0000-4000-8000-000000000d02'::uuid AND deleted_at IS NULL$q$, 0);
END $$;

-- 3. lms_ai_worker: bị chặn -------------------------------------------------------
DO $$
BEGIN
  PERFORM pg_temp.expect_error('lms_ai_worker', 'INSERT quiz_attempts', $q$
    INSERT INTO quiz_attempts (user_id, quiz_id, course_id, score, chosen_answer, is_correct)
    VALUES ('c0de0000-0000-4000-8000-000000000a01', 'c0de0000-0000-4000-8000-000000000b03',
            'c0de0000-0000-4000-8000-000000000c01', 0, '"B"', false)$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'UPDATE quiz_attempts (grading cũ)', $q$
    UPDATE quiz_attempts SET score = 0, grading_status = 'GRADED'
     WHERE attempt_id = 'c0de0000-0000-4000-8000-000000000b04'$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'SELECT quiz_attempts (không đọc bài làm)', $q$
    SELECT * FROM quiz_attempts$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'INSERT documents', $q$
    INSERT INTO documents (course_id, title, file_path, status)
    VALUES ('c0de0000-0000-4000-8000-000000000c01', 'x.pdf', 'documents/rc/x.pdf', 'QUEUED')$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'UPDATE documents status (update_document_status cũ)', $q$
    UPDATE documents SET status = 'INDEXED' WHERE document_id = 'c0de0000-0000-4000-8000-000000000d02'$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'UPDATE documents chapter (set_document_chapter cũ)', $q$
    UPDATE documents SET chapter_code = '1', chapter_provenance = 'content'
     WHERE document_id = 'c0de0000-0000-4000-8000-000000000d01'$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'INSERT lessons', $q$
    INSERT INTO lessons (course_id, lo_id, title)
    VALUES ('c0de0000-0000-4000-8000-000000000c01', 'c0de0000-0000-4000-8000-000000000b01', 'x')$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'UPDATE lessons', $q$
    UPDATE lessons SET title = 'x' WHERE lesson_id = 'c0de0000-0000-4000-8000-000000000b02'$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'INSERT quiz_items', $q$
    INSERT INTO quiz_items (course_id, lesson_id, question, type, correct_answer)
    VALUES ('c0de0000-0000-4000-8000-000000000c01', 'c0de0000-0000-4000-8000-000000000b02', 'x', 'MCQ_SINGLE', '"A"')$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'UPDATE quiz_items', $q$
    UPDATE quiz_items SET question = 'x' WHERE quiz_id = 'c0de0000-0000-4000-8000-000000000b03'$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'INSERT curriculum_imports', $q$
    INSERT INTO curriculum_imports (course_id, source, file_name, storage_key)
    VALUES ('c0de0000-0000-4000-8000-000000000c01', 'upload', 'x.pdf', 'curricula/x.pdf')$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'UPDATE curriculum_imports', $q$
    UPDATE curriculum_imports SET status = 'READY' WHERE import_id = 'c0de0000-0000-4000-8000-000000000f01'$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'UPDATE content_generation_requests (cũ)', $q$
    UPDATE content_generation_requests SET status = 'RUNNING'$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'INSERT chapters (upsert_curriculum cũ)', $q$
    INSERT INTO chapters (course_id, code, title, sort_order)
    VALUES ('c0de0000-0000-4000-8000-000000000c01', '1', 'x', 1)$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'UPDATE lesson_cards (persist_enrichment_batch cũ)', $q$
    UPDATE lesson_cards SET deleted_at = now()$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'UPDATE llm_usage_logs (sổ chỉ ghi thêm)', $q$
    UPDATE llm_usage_logs SET cost_usd = 0$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'DELETE llm_usage_logs', $q$
    DELETE FROM llm_usage_logs$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'TRUNCATE chunks', $q$TRUNCATE chunks CASCADE$q$);
  PERFORM pg_temp.expect_error('lms_ai_worker', 'CREATE TABLE', $q$CREATE TABLE public.roles_check_x (id int)$q$);
  -- RLS: chỉ HEADING_GRAPH_PROJECT / CONCEPT_GRAPH_PROJECT, PENDING, aggregate document
  PERFORM pg_temp.expect_error('lms_ai_worker', 'outbox INSERT ANSWER_GRADING_REQUESTED', $q$
    INSERT INTO outbox_events (event_type, aggregate_type, aggregate_id, payload, status)
    VALUES ('ANSWER_GRADING_REQUESTED', 'quiz_attempt', 'c0de0000-0000-4000-8000-000000000b04', '{}', 'PENDING')$q$,
    '42501', '%row-level security%');
  PERFORM pg_temp.expect_error('lms_ai_worker', 'outbox INSERT DOCUMENT_DELETED (delete() legacy)', $q$
    INSERT INTO outbox_events (event_type, aggregate_type, aggregate_id, payload, status)
    VALUES ('DOCUMENT_DELETED', 'document', 'c0de0000-0000-4000-8000-000000000d01', '{}', 'PENDING')$q$,
    '42501', '%row-level security%');
  PERFORM pg_temp.expect_error('lms_ai_worker', 'outbox INSERT dòng giả đã xử lý', $q$
    INSERT INTO outbox_events (event_type, aggregate_type, aggregate_id, payload, status)
    VALUES ('HEADING_GRAPH_PROJECT', 'document', 'c0de0000-0000-4000-8000-000000000d01', '{}', 'PROCESSED')$q$,
    '42501', '%row-level security%');
  PERFORM pg_temp.expect_error('lms_ai_worker', 'outbox INSERT aggregate khác document', $q$
    INSERT INTO outbox_events (event_type, aggregate_type, aggregate_id, payload, status)
    VALUES ('HEADING_GRAPH_PROJECT', 'quiz_attempt', 'c0de0000-0000-4000-8000-000000000b04', '{}', 'PENDING')$q$,
    '42501', '%row-level security%');
  PERFORM pg_temp.expect_error('lms_ai_worker', 'outbox UPDATE', $q$
    UPDATE outbox_events SET status = 'PENDING'$q$, '42501', '%permission denied%');
  -- RLS lọc dòng: không thấy, không xoá được sự kiện của core-api hay dòng đang relay
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'outbox không thấy payload lệnh chấm bài', $q$
    SELECT payload FROM outbox_events WHERE event_type = 'ANSWER_GRADING_REQUESTED'$q$, 0);
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'outbox DELETE sự kiện core-api: 0 dòng', $q$
    DELETE FROM outbox_events WHERE event_id = 'c0de0000-0000-4000-8000-000000000101'$q$, 0);
  PERFORM pg_temp.expect_ok('lms_ai_worker', 'outbox DELETE dòng PROCESSING: 0 dòng', $q$
    DELETE FROM outbox_events WHERE event_id = 'c0de0000-0000-4000-8000-000000000102'$q$, 0);
  PERFORM pg_temp.expect_true(
    (SELECT count(*) = 2 FROM outbox_events
      WHERE event_id IN ('c0de0000-0000-4000-8000-000000000101', 'c0de0000-0000-4000-8000-000000000102')),
    'quản trị: hai dòng outbox trên vẫn còn');
END $$;

-- 4. lms_mcp_reader: chỉ đọc --------------------------------------------------
DO $$
DECLARE
  t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['courses', 'chapters', 'learning_outcomes', 'chapter_los', 'assessments',
                           'documents', 'chunks', 'chunk_lo_mappings', 'knowledge_relations'] LOOP
    PERFORM pg_temp.expect_ok('lms_mcp_reader', 'đọc ' || t, format('SELECT * FROM %I', t));
  END LOOP;
  -- postgres_course_knowledge_repository._edges_touching (get_concept_relations)
  PERFORM pg_temp.expect_ok('lms_mcp_reader', 'find_relations', $q$
    SELECT kr.relation_id FROM knowledge_relations kr
      JOIN chunks c ON c.chunk_id = kr.chunk_id AND c.deleted_at IS NULL
      JOIN documents d ON d.document_id = kr.document_id AND d.deleted_at IS NULL AND d.lms_published IS NOT FALSE
     WHERE kr.course_id = 'c0de0000-0000-4000-8000-000000000c01'::uuid
       AND (kr.source_key = ANY(ARRAY['dao ham']) OR kr.target_key = ANY(ARRAY['dao ham']))$q$, 1);

  FOREACH t IN ARRAY ARRAY['outbox_events', 'quiz_attempts', 'llm_usage_logs', 'lo_assessments',
                           'llm_model_bindings', 'concepts', 'lms_user_mappings'] LOOP
    PERFORM pg_temp.expect_error('lms_mcp_reader', 'SELECT ' || t, format('SELECT * FROM %I', t));
  END LOOP;
  PERFORM pg_temp.expect_error('lms_mcp_reader', 'INSERT chunks', $q$
    INSERT INTO chunks (document_id, course_id, content, sort_order)
    VALUES ('c0de0000-0000-4000-8000-000000000d01', 'c0de0000-0000-4000-8000-000000000c01', 'x', 9)$q$);
  PERFORM pg_temp.expect_error('lms_mcp_reader', 'UPDATE documents', $q$
    UPDATE documents SET title = 'x'$q$);
  PERFORM pg_temp.expect_error('lms_mcp_reader', 'DELETE knowledge_relations', $q$
    DELETE FROM knowledge_relations$q$);
  PERFORM pg_temp.expect_error('lms_mcp_reader', 'INSERT chunk_lo_mappings', $q$
    INSERT INTO chunk_lo_mappings (chunk_id, lo_id)
    VALUES ('c0de0000-0000-4000-8000-000000000e01', 'c0de0000-0000-4000-8000-000000000b01')$q$);
  PERFORM pg_temp.expect_error('lms_mcp_reader', 'INSERT outbox_events', $q$
    INSERT INTO outbox_events (event_type, aggregate_type, payload) VALUES ('HEADING_GRAPH_PROJECT', 'document', '{}')$q$);
  PERFORM pg_temp.expect_error('lms_mcp_reader', 'INSERT llm_usage_logs', $q$
    INSERT INTO llm_usage_logs (provider, model, use_case, status) VALUES ('x', 'x', 'x', 'OK')$q$);
  PERFORM pg_temp.expect_error('lms_mcp_reader', 'CREATE TABLE', $q$CREATE TABLE public.roles_check_x (id int)$q$);
END $$;

-- 5. lms_core_app: việc của core-api -------------------------------------------
DO $$
DECLARE
  t text;
BEGIN
  PERFORM pg_temp.expect_ok('lms_core_app', 'INSERT documents', $q$
    INSERT INTO documents (document_id, course_id, title, file_path, status)
    VALUES ('c0de0000-0000-4000-8000-000000000d03', 'c0de0000-0000-4000-8000-000000000c01',
            'd3.pdf', 'documents/rc/d3.pdf', 'QUEUED')$q$, 1);
  PERFORM pg_temp.expect_ok('lms_core_app', 'UPDATE documents (kết quả xử lý)', $q$
    UPDATE documents SET status = 'INDEXED', chapter_code = '1', chapter_provenance = 'content'
     WHERE document_id = 'c0de0000-0000-4000-8000-000000000d03'$q$, 1);
  PERFORM pg_temp.expect_ok('lms_core_app', 'UPDATE quiz_attempts (kết quả chấm)', $q$
    UPDATE quiz_attempts SET score = 50, grading_status = 'GRADED'
     WHERE attempt_id = 'c0de0000-0000-4000-8000-000000000b04'$q$, 1);
  PERFORM pg_temp.expect_ok('lms_core_app', 'UPDATE curriculum_imports', $q$
    UPDATE curriculum_imports SET status = 'READY' WHERE import_id = 'c0de0000-0000-4000-8000-000000000f01'$q$, 1);
  PERFORM pg_temp.expect_ok('lms_core_app', 'INSERT chapters (curriculum-writer)', $q$
    INSERT INTO chapters (course_id, code, title, sort_order)
    VALUES ('c0de0000-0000-4000-8000-000000000c01', '1', 'Chương 1', 1)$q$, 1);

  FOREACH t IN ARRAY ARRAY['chunks', 'chunk_lo_mappings', 'concepts', 'chunk_concepts',
                           'knowledge_relations', 'llm_usage_logs', 'outbox_events'] LOOP
    PERFORM pg_temp.expect_ok('lms_core_app', 'đọc ' || t, format('SELECT * FROM %I', t));
  END LOOP;
  -- outbox.service.ts claim(): thấy cả sự kiện của worker
  PERFORM pg_temp.expect_ok('lms_core_app', 'outbox INSERT ANSWER_GRADING_REQUESTED', $q$
    INSERT INTO outbox_events (event_id, event_type, aggregate_type, aggregate_id, payload)
    VALUES ('c0de0000-0000-4000-8000-000000000121', 'ANSWER_GRADING_REQUESTED', 'quiz_attempt',
            'c0de0000-0000-4000-8000-000000000b04', '{}')$q$, 1);
  -- Lọc event_id ngay trong CTE: chạy trên DB có dữ liệu thật thì không khoá
  -- dòng outbox nào ngoài dòng mồi.
  PERFORM pg_temp.expect_ok('lms_core_app', 'outbox claim FOR UPDATE SKIP LOCKED', $q$
    WITH due AS (
      SELECT event_id FROM outbox_events
       WHERE ((status = 'PENDING' AND next_retry_at <= now())
              OR (status = 'PROCESSING' AND COALESCE(locked_at, occurred_at) < now() - '10 minutes'::interval))
         AND event_id IN ('c0de0000-0000-4000-8000-000000000101', 'c0de0000-0000-4000-8000-000000000112',
                          'c0de0000-0000-4000-8000-000000000121')
       ORDER BY next_retry_at, occurred_at
       FOR UPDATE SKIP LOCKED)
    UPDATE outbox_events o SET status = 'PROCESSING', locked_at = now(), locked_by = 'roles_check'
      FROM due WHERE o.event_id = due.event_id
    RETURNING o.event_id$q$, 3);
  -- document.service.ts softDelete: xoá mọi PENDING của tài liệu (kể cả loại của worker)
  PERFORM pg_temp.expect_ok('lms_core_app', 'outbox INSERT HEADING_GRAPH_PROJECT để softDelete xoá', $q$
    INSERT INTO outbox_events (event_id, event_type, aggregate_type, aggregate_id, payload)
    VALUES ('c0de0000-0000-4000-8000-000000000122', 'HEADING_GRAPH_PROJECT', 'document',
            'c0de0000-0000-4000-8000-000000000d01', '{}')$q$, 1);
  PERFORM pg_temp.expect_ok('lms_core_app', 'softDelete: DELETE PENDING của tài liệu', $q$
    DELETE FROM outbox_events WHERE aggregate_id = 'c0de0000-0000-4000-8000-000000000d01' AND status = 'PENDING'$q$, 1);
  PERFORM pg_temp.expect_ok('lms_core_app', 'softDelete: INSERT DOCUMENT_DELETED', $q$
    INSERT INTO outbox_events (event_type, aggregate_type, aggregate_id, payload)
    VALUES ('DOCUMENT_DELETED', 'document', 'c0de0000-0000-4000-8000-000000000d01', '{}')$q$, 1);
  PERFORM pg_temp.expect_ok('lms_core_app', 'softDelete: UPDATE documents deleted_at', $q$
    UPDATE documents SET deleted_at = now() WHERE document_id = 'c0de0000-0000-4000-8000-000000000d01'$q$, 1);
END $$;

-- 6. lms_core_app: bị chặn ở bảng AI ---------------------------------------------
DO $$
BEGIN
  PERFORM pg_temp.expect_error('lms_core_app', 'INSERT chunks', $q$
    INSERT INTO chunks (document_id, course_id, content, sort_order)
    VALUES ('c0de0000-0000-4000-8000-000000000d03', 'c0de0000-0000-4000-8000-000000000c01', 'x', 0)$q$);
  PERFORM pg_temp.expect_error('lms_core_app', 'UPDATE chunks', $q$UPDATE chunks SET deleted_at = now()$q$);
  PERFORM pg_temp.expect_error('lms_core_app', 'DELETE chunks', $q$DELETE FROM chunks$q$);
  PERFORM pg_temp.expect_error('lms_core_app', 'INSERT chunk_lo_mappings', $q$
    INSERT INTO chunk_lo_mappings (chunk_id, lo_id)
    VALUES ('c0de0000-0000-4000-8000-000000000e01', 'c0de0000-0000-4000-8000-000000000b01')$q$);
  PERFORM pg_temp.expect_error('lms_core_app', 'UPDATE chunk_lo_mappings', $q$
    UPDATE chunk_lo_mappings SET provenance = 'confirmed'$q$);
  PERFORM pg_temp.expect_error('lms_core_app', 'INSERT concepts', $q$
    INSERT INTO concepts (id, name, canonical_name, slug) VALUES ('x', 'x', 'x', 'x')$q$);
  PERFORM pg_temp.expect_error('lms_core_app', 'DELETE chunk_concepts', $q$DELETE FROM chunk_concepts$q$);
  PERFORM pg_temp.expect_error('lms_core_app', 'DELETE knowledge_relations', $q$DELETE FROM knowledge_relations$q$);
  PERFORM pg_temp.expect_error('lms_core_app', 'INSERT llm_usage_logs', $q$
    INSERT INTO llm_usage_logs (provider, model, use_case, status) VALUES ('x', 'x', 'x', 'OK')$q$);
  PERFORM pg_temp.expect_error('lms_core_app', 'UPDATE llm_usage_logs', $q$UPDATE llm_usage_logs SET cost_usd = 0$q$);
  PERFORM pg_temp.expect_error('lms_core_app', 'SELECT _prisma_migrations', $q$SELECT * FROM _prisma_migrations$q$);
  PERFORM pg_temp.expect_error('lms_core_app', 'TRUNCATE quiz_attempts', $q$TRUNCATE quiz_attempts$q$);
  PERFORM pg_temp.expect_error('lms_core_app', 'CREATE TABLE', $q$CREATE TABLE public.roles_check_x (id int)$q$);
END $$;

-- 7. Khoá ngoại xuyên miền ---------------------------------------------------------
-- Hành động ON DELETE chạy bằng quyền owner bảng con, nên core-api xoá dòng nghiệp
-- vụ vẫn SET NULL/CASCADE được sang bảng AI mà không cần quyền ghi bảng đó.
DO $$
BEGIN
  PERFORM pg_temp.expect_ok('lms_core_app', 'DELETE lms_user_mappings → llm_usage_logs.user_id SET NULL', $q$
    DELETE FROM lms_user_mappings WHERE internal_user_id = 'c0de0000-0000-4000-8000-000000000a02'$q$, 1);
  PERFORM pg_temp.expect_ok('lms_core_app', 'DELETE courses → llm_usage_logs.course_id SET NULL', $q$
    DELETE FROM courses WHERE course_id = 'c0de0000-0000-4000-8000-000000000c02'$q$, 1);
  PERFORM pg_temp.expect_true(
    (SELECT user_id IS NULL AND course_id IS NULL FROM llm_usage_logs
      WHERE usage_id = 'c0de0000-0000-4000-8000-000000000202'),
    'quản trị: llm_usage_logs đã SET NULL');
  PERFORM pg_temp.expect_ok('lms_core_app', 'xoá cứng tài liệu chưa có chunk', $q$
    DELETE FROM documents WHERE document_id = 'c0de0000-0000-4000-8000-000000000d02'$q$, 1);
  -- chunks.document_id là ON DELETE RESTRICT: tài liệu có chunk không xoá cứng được,
  -- với mọi role (core-api chỉ soft-delete; worker soft-delete chunks khi nhận DOCUMENT_DELETED).
  PERFORM pg_temp.expect_error('lms_core_app', 'xoá cứng tài liệu có chunk (FK RESTRICT)', $q$
    DELETE FROM documents WHERE document_id = 'c0de0000-0000-4000-8000-000000000d01'$q$, '23001');
END $$;

-- 8. Ma trận quyền cuối cùng (để đối chiếu với bảng phân loại trong roles.sql) ------
\set QUIET off
\pset footer off
SELECT c.relname AS "bảng",
       concat_ws('', CASE WHEN has_table_privilege('lms_core_app', c.oid, 'SELECT') THEN 'S' END,
                     CASE WHEN has_table_privilege('lms_core_app', c.oid, 'INSERT') THEN 'I' END,
                     CASE WHEN has_table_privilege('lms_core_app', c.oid, 'UPDATE') THEN 'U' END,
                     CASE WHEN has_table_privilege('lms_core_app', c.oid, 'DELETE') THEN 'D' END) AS core_app,
       concat_ws('', CASE WHEN has_table_privilege('lms_ai_worker', c.oid, 'SELECT') THEN 'S' END,
                     CASE WHEN has_table_privilege('lms_ai_worker', c.oid, 'INSERT') THEN 'I' END,
                     CASE WHEN has_table_privilege('lms_ai_worker', c.oid, 'UPDATE') THEN 'U' END,
                     CASE WHEN has_table_privilege('lms_ai_worker', c.oid, 'DELETE') THEN 'D' END) AS ai_worker,
       CASE WHEN has_table_privilege('lms_mcp_reader', c.oid, 'SELECT') THEN 'S' ELSE '' END AS mcp_reader,
       CASE WHEN c.relrowsecurity THEN 'RLS' ELSE '' END AS ghi_chu
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm')
 ORDER BY (has_table_privilege('lms_ai_worker', c.oid, 'INSERT')) DESC,
          (has_table_privilege('lms_ai_worker', c.oid, 'SELECT')) DESC,
          c.relname;
\set QUIET on

ROLLBACK;

-- 9. NOTIFY: worker INSERT outbox đánh thức listener của core-api -----------------
-- Trigger outbox_events_notify_insert chạy bằng quyền người INSERT (worker);
-- pg_notify không cần quyền gì. Listener là một psql con LISTEN dưới role
-- lms_core_app; thông báo chỉ tới sau COMMIT nên mục này phải ghi thật.
\if :{?skip_notify}
\echo 'roles_check: bỏ mục 9 (NOTIFY) theo -v skip_notify'
\else
SELECT '/tmp/roles_check_notify_' || pg_backend_pid() AS notify_file \gset
\setenv ROLES_CHECK_NOTIFY_FILE :notify_file
\setenv PGHOST :HOST
\setenv PGPORT :PORT
\setenv PGUSER :USER
\setenv PGDATABASE :DBNAME
\! (psql -X -c 'SET ROLE lms_core_app' -c 'LISTEN outbox_channel' -c 'SELECT pg_sleep(3)' > "$ROLES_CHECK_NOTIFY_FILE" 2>&1 &)
SELECT pg_sleep(1) \g /dev/null
BEGIN;
SET LOCAL ROLE lms_ai_worker;
INSERT INTO outbox_events (event_id, event_type, aggregate_type, aggregate_id, payload, status, retry_count, last_error)
VALUES ('c0de0000-0000-4000-8000-000000000199', 'HEADING_GRAPH_PROJECT', 'document',
        'c0de0000-0000-4000-8000-000000000d99', '{"roles_check": true}', 'PENDING', 0, NULL);
COMMIT;
DELETE FROM outbox_events WHERE event_id = 'c0de0000-0000-4000-8000-000000000199';
\! sleep 3; grep -q 'Asynchronous notification "outbox_channel"' "$ROLES_CHECK_NOTIFY_FILE"; s=$?; rm -f "$ROLES_CHECK_NOTIFY_FILE"; exit $s
\if :SHELL_ERROR
DO $$ BEGIN RAISE EXCEPTION 'FAIL  NOTIFY: listener lms_core_app không nhận outbox_channel sau INSERT của lms_ai_worker'; END $$;
\else
\echo 'ok    NOTIFY outbox_channel: worker INSERT → listener lms_core_app nhận được'
\endif
\endif

\echo 'roles_check: tất cả đạt'
