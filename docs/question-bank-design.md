# Ngân hàng câu hỏi và liên kết ngân hàng Canvas

| | |
|---|---|
| Trạng thái | Đề xuất. Đã chốt: chia sẻ theo môn (Q1). Spike GĐ2a đã chạy trên Canvas local ngày 2026-10-22 (§8.5); chưa có code |
| Ngày | 2026-10-22 |
| Phạm vi | `core-api` (schema, review, quiz-set, lesson, module ngân hàng mới, Canvas client), `packages-ai` (repository ghi `quiz_items`), `worker` (content-generation, enrichment), `web` (`/manage`) |
| Liên quan | [quiz-generation-redesign.md](quiz-generation-redesign.md): chống trùng, phân tích câu hỏi từ `quiz_attempts`. [canvas-module-quiz.md](canvas-module-quiz.md): giao đề qua LTI. [canvas_lti_setup.md](canvas_lti_setup.md): token Canvas API |

---

## 0. Tóm tắt

- **Hiện chưa có ngân hàng câu hỏi.** Câu sinh ra nằm trong `quiz_items`, mỗi câu gắn cứng với một khoá và một bài học (`lessons`) tự tạo theo LO. Không ghi ai là chủ, ai được dùng, chưa có phiên bản, không biết câu do yêu cầu nào hay model nào sinh ra. Vì vậy giảng viên không chia sẻ được câu hỏi, cũng không dùng lại được sang lớp hay học kỳ khác.
- **Đề xuất: ngân hàng trong hệ thống là nguồn gốc (source of truth); Canvas là nơi đẩy câu sang và kéo câu về qua adapter.** Chỉ hệ thống mình giữ được LO, Bloom, đoạn tài liệu nguồn, kết quả kiểm chứng và thống kê làm bài cho từng câu. Ngân hàng Classic của Canvas chỉ gắn Outcome ở mức cả ngân hàng, không có API ghi, còn New Quizzes không có trên Canvas mã nguồn mở.
- **Mô hình:**
  - `question_banks`: ngân hàng có chủ và phạm vi PRIVATE / COURSE / SUBJECT, kèm chia sẻ tường minh VIEW / USE / EDIT.
  - `quiz_items`: giữ bảng, thêm `bank_id`, nguồn gốc và tác giả.
  - `quiz_item_versions`: bản ghi bất biến, do trigger Postgres ghi để cả TypeScript lẫn Python không ghi sót.
  - `question_lms_links`: ánh xạ câu ↔ câu bên Canvas.
- **Chia sẻ:** người khác dùng câu qua quyền USE. Muốn sửa câu không phải của mình thì **fork** sang ngân hàng của mình. LO được map **theo mã** (`L.O.2.1`) sang khoá đích nên câu dùng được ở khoá khác.
- **Canvas, đã kiểm tra trên Canvas local:**
  - **Đọc** ngân hàng qua REST API, có từ 2026-01-16.
  - **Ghi** chỉ được bằng cách import gói QTI qua Content Migrations.
  - **Spike 2026-10-22 đạt** sau khi bật plugin `qti_converter`, không cần công cụ Python. Đủ 5 kiểu câu, chấm đúng, tiếng Việt và ký tự đặc biệt giữ nguyên, đẩy lại không nhân đôi.
  - Có hai điều kiện bắt buộc: tên ngân hàng phải ghi **trong từng item**, và luôn import với `overwrite_quizzes=true` (§8.5).
- **Chia sẻ theo môn** cần gỡ ràng buộc UNIQUE của `courses.code` trước (§6.4).
- **Lộ trình:** GĐ1 ngân hàng nội bộ (không phụ thuộc Canvas) → GĐ2 spike rồi làm xuất sang Canvas → GĐ3 nhập từ Canvas → sau: Moodle XML.

---

## 1. Hiện trạng

### 1.1 Luồng lưu hiện tại

```
(1) Theo LO
web ─► core-api content_generation_requests + outbox (1 transaction)
    ─► content-generation-worker ─► GenerateCurriculumQuizUseCase
        sinh ─► kiểm chứng/sửa ─► câu bị loại: chỉ ghi log
        ─► persist_curriculum_quiz_items: upsert lessons(course, LO) + INSERT quiz_items
           status=GENERATED_DRAFT, quiz_id = uuid5(LO | kiểu | nội dung)

(2) Theo tài liệu
enrichment-worker ─► RunEnrichmentUseCase ─► _replace_quiz_items_cursor
        xoá mềm câu chưa duyệt của tài liệu ─► INSERT câu mới (luôn MCQ_SINGLE, không bloom_level)

Sau khi lưu
review:   GENERATED_DRAFT ─(sửa)─► REVIEWING ─► APPROVED | CHANGES_REQUESTED
lesson:   xuất bản bài học ─► mọi câu APPROVED của bài ─► PUBLISHED (+ published_at)
quiz set: chép (snapshot) câu APPROVED|PUBLISHED vào quiz_sets.items (JSON)
```

Vị trí trong code:
- Ghi theo LO: `packages-ai/src/document_chunk/adapters/metadata/postgres_curriculum_repository.py:42`
- Ghi theo tài liệu: `packages-ai/src/document_chunk/adapters/metadata/postgres_enrichment_repository.py:384`
- Xuất bản bài học: `core-api/src/lesson/lesson.service.ts:104-115`
- Snapshot đề: `core-api/src/quiz/quiz-set.service.ts:191-233`
- Sửa câu khi duyệt: `core-api/src/review/review.service.ts:215-265`

### 1.2 Dữ liệu dev (đếm ngày 2026-10-22, đọc-only)

| | Số lượng |
|---|---|
| `quiz_items` còn sống | 76: 38 GENERATED_DRAFT, 7 CHANGES_REQUESTED, 6 APPROVED, 25 PUBLISHED |
| Kiểu câu | MCQ_SINGLE 50, MCQ_MULTI 16, FILL_BLANK 4, SHORT_ANSWER 4, TRUE_FALSE 2 |
| Khoá / LO có câu | 1 khoá (CO3137), 6 LO |
| `quiz_sets` | 8 (7 còn sống), tham chiếu 42 câu |
| `quiz_attempts` | 62 |
| `micro_content_questions` | 0 |
| Câu trùng nguyên văn trong cùng LO | 0 |

Ít dữ liệu, nên migration và backfill rẻ.

### 1.3 Vấn đề

| # | Vấn đề | Nguồn | Hệ quả |
|---|---|---|---|
| H1 | `quiz_items.course_id`, `lesson_id` NOT NULL; `lesson_id` trỏ bài học tự tạo theo (khoá, LO) | schema | câu không tồn tại ngoài một khoá; câu nhập từ ngoài chưa có LO thì không có chỗ chứa |
| H2 | Không có chủ sở hữu, phạm vi xem hay quyền dùng | schema | không chia sẻ được; ai là instructor của khoá cũng thấy và sửa được mọi câu |
| H3 | Sửa là ghi đè; bản trước chỉ còn trong `review_audit_logs.raw_changes` | `review.service.ts:215-265` | không xem được lịch sử; `quiz_attempts` không biết người học đã làm phiên bản nào |
| H4 | Có tính ra mà không lưu: `difficulty`, `model_id`, `lo_alignment_rationale`, kết luận verifier; câu bị loại chỉ có trong log | `generate_curriculum_quiz.py:389-445`, câu SQL ở H1 | không truy vết được, không đánh giá được chất lượng theo model |
| H5 | `content_generation_requests` chỉ lưu `generated_count`, không lưu `quiz_id` | schema | không biết câu nào do yêu cầu nào sinh |
| H6 | Chạy lại enrichment xoá mềm cả câu `REVIEWING` và `CHANGES_REQUESTED` | `postgres_enrichment_repository.py:392-401` | mất câu giảng viên đang sửa dở |
| H7 | `status` trộn hai việc: duyệt nội dung (APPROVED) và đã đưa vào bài học (PUBLISHED) | `lesson.service.ts:108` | khó mở rộng: câu được chia sẻ sang khoá khác thì "PUBLISHED" ở khoá nào? |
| H8 | `bloom_level` là mức được yêu cầu, chưa được đánh giá | đã đo 2026-10-08 | ngân hàng lọc theo Bloom sẽ sai lệch; cần tách `bloom_requested` và `bloom_assessed` |

---

## 2. Mục tiêu và ngoài phạm vi

**Mục tiêu**
1. Mỗi câu thuộc đúng một ngân hàng; ngân hàng có chủ, có phạm vi, có chia sẻ.
2. Lịch sử phiên bản bất biến; đề và lượt làm bài trỏ đến đúng phiên bản.
3. Lưu nguồn gốc của câu: AI sinh (yêu cầu nào, model nào, kết luận kiểm chứng), giảng viên viết tay, nhập từ Canvas, hay fork.
4. Dùng câu của khoá khác: map LO theo mã sang khoá đích.
5. Đẩy câu đã duyệt sang ngân hàng Classic của Canvas, và nhập ngân hàng Canvas có sẵn về hệ thống.

**Ngoài phạm vi**
- Item bank của New Quizzes: không có trên Canvas local, và API chỉ đọc (§3).
- Đồng bộ hai chiều thời gian thực. Ở đây chỉ có đẩy và kéo theo yêu cầu.
- Tạo quiz Canvas từ `quiz_sets`. Đề vẫn giao qua LTI của mình (§4, N4).
- Moodle. Thiết kế chừa chỗ cho adapter (`lms_type`), nhưng không làm.
- Phân tích câu hỏi theo CTT/IRT: đã nằm trong [quiz-generation-redesign.md](quiz-generation-redesign.md). Thiết kế này chỉ thêm `quiz_version_id` để phần đó tính được theo phiên bản.

---

## 3. Canvas cho phép gì

Kiểm tra trên source `~/lms/canvas-lms` (commit `e73bc5855b5`, 2026-08-04) và Canvas local đang chạy (`canvas-lms-web-1`) ngày 2026-10-22.

| Việc | Classic Quizzes | New Quizzes |
|---|---|---|
| Liệt kê ngân hàng | `GET /api/v1/question_banks?context_type=Course&context_id=…` | Item bank: API chỉ đọc |
| Đọc câu trong ngân hàng | `GET /api/v1/question_banks/:id/questions`, trả `question_name`, `question_type`, `question_text`, `answers`, `points_possible`, các comment. **Không trả `migration_id`** | — |
| Tạo ngân hàng, ghi câu | **Không có REST API.** Chỉ có `POST /api/v1/{courses\|accounts}/:id/content_migrations` với `migration_type=qti_converter`. API có tài liệu hoá `settings[question_bank_id]` và `settings[question_bank_name]`, **nhưng spike cho thấy cả hai bị bỏ qua** với gói QTI 2.1 (ngân hàng thành "No Name - <khoá>"). Tên ngân hàng phải ghi trong item (`instructureField name=question_bank`) | Không có API tạo item bank |
| Đẩy lại có nhân đôi không | Không, **nếu** `settings[overwrite_quizzes]=true`: importer khớp câu theo `migration_id` (lấy từ `identifier` của item) trong cùng context rồi cập nhật tại chỗ. Thiếu cờ này thì id đã tồn tại bị gắn tiền tố `<id migration>_` (`ContentImporterHelper.add_assessment_id_prepend`) ⇒ câu và ngân hàng bị nhân đôi | — |
| Gắn LO | Chỉ "Align Outcome" cho cả ngân hàng, qua giao diện. Khi chấm quiz Classic, Canvas cập nhật kết quả Outcome cho câu thuộc ngân hàng đã gắn Outcome (`app/models/quizzes/submission_grader.rb`, `track_outcomes`) | — |
| Chia sẻ trong Canvas | Ngân hàng cấp account; bookmark ngân hàng của khoá khác | Chia sẻ item bank cho user/khoá |
| Có trên Canvas local | Có | Không (`quizzes_next` tắt; New Quizzes là dịch vụ đóng) |

Nguồn trong source Canvas:
- API đọc: `app/controllers/assessment_question_banks_controller.rb:234-312`, thêm ở commit `e569b9ea38d` (2026-01-16, "Add question banks API endpoints"). Field trả về: `lib/api/v1/quiz_question.rb:24-50`.
- Tham số import: `app/controllers/content_migrations_controller.rb:307-316`. Route có cho cả account: `config/routes.rb:1605-1611`.
- Khớp `migration_id` khi import lại: `app/models/importers/assessment_question_importer.rb:41-48`.
- Đọc QTI: `gems/plugins/qti_exporter/lib/qti/`. QTI 2.x bỏ qua bước Python: `converter.rb:50-58`. Chọn kiểu câu: `assessment_item_converter.rb:298-372`. Tên ngân hàng theo từng câu qua `instructureField name=question_bank`: `assessment_item_converter.rb:171-175`.

**Trạng thái Canvas local:**
- Trước 2026-10-22: `PluginSetting qti_converter` = nil, `Qti.qti_enabled?` = false, `Qti.migration_executable` = nil. Thư mục `vendor/` không có `QTIMigrationTool`. Khi plugin tắt, import Common Cartridge cũng bỏ qua phần quiz (`lib/cc/importer/canvas/converter.rb:78`).
- Gói **QTI 1.2** bắt buộc qua công cụ Python. Gói **QTI 2.x** thì không (`converter.rb:53-55`).
- **2026-10-22:** đã bật plugin (§8.1) và chạy spike (§8.5). Container `canvas-lms-web-1` và `canvas-lms-jobs-1` đều đọc được setting mới.

**Classic Quizzes còn sống bao lâu:** Instructure chưa công bố ngày khai tử chính thức; một số trường tự đặt hạn riêng. Canvas mã nguồn mở không có New Quizzes, nên với Canvas local Classic là lựa chọn duy nhất.

---

## 4. Nguyên tắc thiết kế

- **N1. Ngân hàng của mình là nguồn gốc.** LMS chỉ nhận bản xuất và là nguồn nhập. Thông tin chỉ có ở phía mình (LO theo câu, Bloom, chunk nguồn, verifier, thống kê) không bao giờ phụ thuộc vào LMS.
- **N2. Một câu thuộc đúng một ngân hàng.** Đưa câu sang ngân hàng khác nghĩa là fork, không phải liên kết nhiều-nhiều. Canvas cũng làm vậy, nên ánh xạ đơn giản.
- **N3. Phiên bản bất biến, ghi ở tầng DB.** Ba nơi ghi `quiz_items` (Python × 2, TypeScript) sẽ không thể quên tạo phiên bản.
- **N4. Đề vẫn giao qua LTI của mình.** Chỉ đường này cho dữ liệu theo LO để chẩn đoán và bổ trợ. Xuất sang Canvas là để chia sẻ và để dùng được bên ngoài hệ thống.
- **N5. Tách "duyệt nội dung" khỏi "đang dùng ở đâu".** Trạng thái duyệt thuộc về câu; việc câu nằm trong bài học hay đề nào suy ra từ `lessons` và `quiz_sets`. Trong GĐ1 vẫn giữ `PUBLISHED` để không phá luồng bài học (§5.5).

---

## 5. Mô hình dữ liệu

### 5.1 Tổng quan

```
lms_user_mappings ──owner──► question_banks ◄── question_bank_shares (USER|COURSE, VIEW|USE|EDIT)
courses ──home_course──────►      │ 1
                                  │ n
content_generation_requests ──► quiz_items ──current_version──► quiz_item_versions (bất biến)
learning_outcomes ──lo_id───────►  │  ▲                              ▲
lessons (nullable) ─────────────►  │  └──forked_from_version─────────┘
                                   │
                                   ├──► question_lms_links (canvas: ext_bank_id, ext_question_id, migration_id)
quiz_sets.items[].version_id ──────┘
quiz_attempts.quiz_version_id ─────► quiz_item_versions
```

### 5.2 Bảng mới

```sql
CREATE TABLE question_banks (
  bank_id           uuid PRIMARY KEY DEFAULT uuidv7(),
  title             varchar(255) NOT NULL,
  description       text,
  -- NULL: ngân hàng mặc định của khoá, do mọi instructor của khoá cùng quản lý
  owner_id          uuid REFERENCES lms_user_mappings(internal_user_id),
  home_course_id    uuid NOT NULL REFERENCES courses(course_id),
  -- chép từ courses.code lúc tạo; dùng cho phạm vi SUBJECT
  subject_code      varchar(50),
  visibility        varchar(20) NOT NULL DEFAULT 'COURSE'
                    CHECK (visibility IN ('PRIVATE','COURSE','SUBJECT')),
  is_course_default boolean NOT NULL DEFAULT false,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  deleted_at        timestamptz
);
CREATE UNIQUE INDEX uq_question_bank_course_default
  ON question_banks (home_course_id) WHERE is_course_default AND deleted_at IS NULL;

CREATE TABLE question_bank_shares (
  bank_id      uuid NOT NULL REFERENCES question_banks(bank_id) ON DELETE CASCADE,
  grantee_type varchar(10) NOT NULL CHECK (grantee_type IN ('USER','COURSE')),
  grantee_id   uuid NOT NULL,
  role         varchar(10) NOT NULL CHECK (role IN ('VIEW','USE','EDIT')),
  granted_by   uuid NOT NULL REFERENCES lms_user_mappings(internal_user_id),
  created_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (bank_id, grantee_type, grantee_id)
);

CREATE TABLE quiz_item_versions (
  version_id       uuid PRIMARY KEY DEFAULT uuidv7(),
  quiz_id          uuid NOT NULL REFERENCES quiz_items(quiz_id),
  version_no       int  NOT NULL,
  type             varchar(30) NOT NULL,
  question         text NOT NULL,
  options          jsonb,
  correct_answer   jsonb NOT NULL,
  explanation      text,
  lo_id            uuid,
  bloom_level      int,
  source_chunk_ids uuid[] NOT NULL DEFAULT '{}',
  -- AI: {model_id, generation_request_id, difficulty, lo_alignment_rationale, verifier}
  -- người: {} hoặc {note}; nhập: {lms, ext_question_id}
  provenance       jsonb NOT NULL DEFAULT '{}',
  created_by       uuid REFERENCES lms_user_mappings(internal_user_id),  -- NULL = worker
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (quiz_id, version_no)
);

CREATE TABLE question_lms_links (
  link_id          uuid PRIMARY KEY DEFAULT uuidv7(),
  quiz_id          uuid NOT NULL REFERENCES quiz_items(quiz_id),
  version_id       uuid NOT NULL REFERENCES quiz_item_versions(version_id),
  direction        varchar(10) NOT NULL CHECK (direction IN ('EXPORT','IMPORT')),
  lms_type         varchar(20) NOT NULL DEFAULT 'canvas',
  lms_base_url     varchar(255) NOT NULL,
  lms_context_type varchar(10) NOT NULL CHECK (lms_context_type IN ('course','account')),
  lms_context_id   varchar(64) NOT NULL,
  ext_bank_id      varchar(64),
  ext_question_id  varchar(64),
  migration_id     varchar(255),
  synced_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (quiz_id, direction, lms_base_url, lms_context_type, lms_context_id)
);

CREATE TABLE question_bank_sync_jobs (
  job_id            uuid PRIMARY KEY DEFAULT uuidv7(),
  bank_id           uuid NOT NULL REFERENCES question_banks(bank_id),
  direction         varchar(10) NOT NULL CHECK (direction IN ('EXPORT','IMPORT')),
  requested_by      uuid NOT NULL REFERENCES lms_user_mappings(internal_user_id),
  target            jsonb NOT NULL,   -- context Canvas, cách chia ngân hàng, danh sách bank Canvas
  status            varchar(20) NOT NULL DEFAULT 'QUEUED'
                    CHECK (status IN ('QUEUED','RUNNING','WAITING_LMS','COMPLETED','FAILED')),
  lms_migration_ids jsonb NOT NULL DEFAULT '[]',
  counts            jsonb NOT NULL DEFAULT '{}',  -- {exported, updated, skipped, unsupported, failed}
  last_error        text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);
```

### 5.3 Thay đổi bảng cũ

```sql
ALTER TABLE quiz_items
  ADD COLUMN bank_id                uuid REFERENCES question_banks(bank_id),  -- NOT NULL sau backfill
  ADD COLUMN origin                 varchar(20) NOT NULL DEFAULT 'AI_GENERATED'
             CHECK (origin IN ('AI_GENERATED','MANUAL','CANVAS_IMPORT','FORK')),
  ADD COLUMN author_id              uuid REFERENCES lms_user_mappings(internal_user_id),
  ADD COLUMN updated_by             uuid REFERENCES lms_user_mappings(internal_user_id),
  ADD COLUMN generation_request_id  uuid REFERENCES content_generation_requests(request_id),
  ADD COLUMN provenance             jsonb NOT NULL DEFAULT '{}',
  ADD COLUMN forked_from_version_id uuid REFERENCES quiz_item_versions(version_id),
  ADD COLUMN current_version_id     uuid REFERENCES quiz_item_versions(version_id),
  ADD COLUMN bloom_assessed         int,
  ALTER COLUMN lesson_id DROP NOT NULL;   -- câu nhập/fork chưa thuộc bài học nào

CREATE INDEX idx_quiz_items_bank ON quiz_items (bank_id, status) WHERE deleted_at IS NULL;

ALTER TABLE quiz_attempts ADD COLUMN quiz_version_id uuid REFERENCES quiz_item_versions(version_id);
```

- Các cột nội dung (`type`, `question`, `options`, `correct_answer`, `explanation`, `lo_id`, `bloom_level`, `source_chunk_ids`) **được giữ** làm bản làm việc hiện tại, để code đọc `quiz_items` không phải đổi ngay. Phiên bản là lịch sử, không phải nơi đọc chính.
- Cột `bloom_level` hiện có được hiểu là `bloom_requested`. Đổi tên để sau, vì nhiều nơi đang đọc cột này.
- `QuizSnapshotItem` (`core-api/src/quiz/quiz-set.service.ts`) thêm field `version_id`. Snapshot vẫn chép nội dung như cũ, giờ biết thêm chính xác phiên bản nào.

### 5.4 Trigger ghi phiên bản

Mỗi lần nội dung đổi, kể cả lúc INSERT, ghi một dòng `quiz_item_versions` rồi trỏ `current_version_id` vào dòng đó.

```sql
CREATE FUNCTION quiz_items_write_version() RETURNS trigger AS $$
DECLARE v uuid;
BEGIN
  IF TG_OP = 'UPDATE' AND
     (NEW.type, NEW.question, NEW.options, NEW.correct_answer, NEW.explanation,
      NEW.lo_id, NEW.bloom_level, NEW.source_chunk_ids)
     IS NOT DISTINCT FROM
     (OLD.type, OLD.question, OLD.options, OLD.correct_answer, OLD.explanation,
      OLD.lo_id, OLD.bloom_level, OLD.source_chunk_ids) THEN
    RETURN NULL;  -- chỉ đổi status/current_version_id/...: không tạo phiên bản
  END IF;
  INSERT INTO quiz_item_versions (quiz_id, version_no, type, question, options, correct_answer,
         explanation, lo_id, bloom_level, source_chunk_ids, provenance, created_by)
  SELECT NEW.quiz_id, COALESCE(MAX(version_no), 0) + 1, NEW.type, NEW.question, NEW.options,
         NEW.correct_answer, NEW.explanation, NEW.lo_id, NEW.bloom_level, NEW.source_chunk_ids,
         NEW.provenance, NEW.updated_by
  FROM quiz_item_versions WHERE quiz_id = NEW.quiz_id
  RETURNING version_id INTO v;
  UPDATE quiz_items SET current_version_id = v WHERE quiz_id = NEW.quiz_id;
  RETURN NULL;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_quiz_items_version
  AFTER INSERT OR UPDATE ON quiz_items
  FOR EACH ROW EXECUTE FUNCTION quiz_items_write_version();
```

**Phải là AFTER, không được là BEFORE.** Cả hai đường ghi Python dùng `INSERT … ON CONFLICT DO UPDATE … WHERE status = 'GENERATED_DRAFT'`. Trigger BEFORE INSERT vẫn chạy cho dòng đề xuất **trước** khi Postgres phát hiện xung đột. Nếu dùng BEFORE, worker retry, hoặc lần ghi bị mệnh đề `WHERE` chặn, vẫn đẻ ra một phiên bản không có thật. AFTER trigger chỉ chạy cho thao tác thực sự xảy ra. Lệnh `UPDATE current_version_id` bên trong gọi lại trigger, nhưng bị nhánh "nội dung không đổi" chặn ngay.

Nơi ghi chỉ cần đặt `updated_by` và `provenance` trong cùng câu lệnh. Trigger sẽ chép hai cột này sang phiên bản.

### 5.5 Trạng thái

GĐ1 giữ nguyên các trạng thái hiện có, chỉ thêm `RETIRED`:

```
GENERATED_DRAFT ─(sửa)─► REVIEWING ─► APPROVED ─(xuất bản bài học)─► PUBLISHED
        │                    │            │                              │
        └─(từ chối)──► CHANGES_REQUESTED ◄┘                              │
                                                     RETIRED ◄───────────┘ (ẩn khỏi ngân hàng,
                                                                            đề cũ vẫn chạy nhờ snapshot)
```

- Snapshot của `quiz_sets` không đổi theo trạng thái: đề đã giao vẫn chạy với câu đã RETIRED, như hiện nay.
- `PUBLISHED` vẫn chỉ có nghĩa "đang nằm trong bài học đã xuất bản của khoá gốc" (`lesson.service.ts`). Câu dùng ở khoá khác thì luôn đi qua `quiz_sets`, không qua `lessons`, nên không cần `PUBLISHED` theo từng khoá.
- **Để sau:** tách `approved_version_id` khỏi `current_version_id`. Như vậy sửa một câu đã duyệt sẽ không rút câu đó khỏi bài học trong lúc chờ duyệt lại. Hiện nay sửa là chuyển sang REVIEWING ngay, thiết kế này giữ nguyên hành vi đó.

---

## 6. Quyền và chia sẻ

### 6.1 Quyền hiệu lực

`effectiveRole(user, bank)` lấy quyền **cao nhất** trong các nguồn sau:

| Nguồn | Quyền |
|---|---|
| `claims.scope = 'admin'` hoặc `lms_user_mappings.role = 'administrator'` | EDIT |
| `owner_id = user` | EDIT |
| Instructor của `home_course_id`, khi `owner_id IS NULL` (ngân hàng mặc định) hoặc `visibility = 'COURSE'` | EDIT |
| Instructor của một khoá có `courses.subject_code = question_banks.subject_code`, khi `visibility = 'SUBJECT'` (§6.4) | USE |
| `question_bank_shares` (USER = user, hoặc COURSE = khoá user đang là instructor) | role của dòng share |
| Learner | không thấy ngân hàng; chỉ thấy đề và bài học |

- **VIEW:** xem câu, đáp án, lịch sử.
- **USE:** thêm VIEW, đưa câu vào đề của mình, fork.
- **EDIT:** thêm USE, sửa, duyệt, RETIRED, chia sẻ (chỉ chủ hoặc admin mới đổi được `visibility`), xuất/nhập Canvas.

Đặt trong `core-api/src/question-bank/bank-access.ts`, dùng chung cho review, quiz-set, lesson. Phải thay đoạn kiểm tra `assertCourseAccess(claims, quiz.course_id, …)` hiện có trong review (`review.service.ts:281-290`): quyền sửa câu nay là quyền EDIT trên ngân hàng, không còn là quyền của khoá.

### 6.2 Dùng câu ở khoá khác (map LO theo mã)

Hiện `quiz-set.service.ts:191-200` chỉ nhận câu có `course_id = body.courseId` và LO thuộc chương. Đổi thành:
1. Câu phải thuộc ngân hàng mà user có quyền ≥ USE.
2. Nếu `quiz_items.course_id ≠ body.courseId`: tìm LO trong khoá đích có cùng `code`, `is_current = true`, `deleted_at IS NULL`. Snapshot ghi `lo_id` của **khoá đích**.
3. Không tìm được LO, hoặc LO không thuộc chương đã chọn: báo lỗi giống hiện nay ("Chỉ thêm các câu đã duyệt và thuộc LO của chương"), kèm mã LO bị thiếu.

Phiên bản CTĐT khác nhau (`academic_year`, `version`) **không** được tự map ở GĐ1. Hai LO cùng mã nhưng khác phiên bản vẫn coi là khớp, và giao diện cảnh báo khi `statement_vi` khác nhau.

### 6.3 Fork

`POST /api/question-banks/:bankId/items/:quizId/fork { targetBankId }`. Cần USE trên ngân hàng nguồn và EDIT trên ngân hàng đích.
- Tạo dòng `quiz_items` mới: nội dung = phiên bản hiện tại của câu nguồn; `origin = 'FORK'`; `forked_from_version_id` = phiên bản đó; `author_id` = người fork; `course_id` = `home_course_id` của ngân hàng đích; `lesson_id = NULL`.
- `lo_id` lấy theo luật §6.2 trong khoá đích. Thiếu thì để NULL, giao diện yêu cầu gắn LO trước khi duyệt.
- Trạng thái: APPROVED nếu câu nguồn ở APPROVED hoặc PUBLISHED, ngược lại GENERATED_DRAFT. Ghi `review_audit_logs` với action `FORK_QUIZ`.
- `quiz_id` dùng `uuidv7()`. **Không** dùng `uuid5(LO | nội dung)` như worker, vì như thế bản fork sẽ trùng id với câu nguồn khi cùng LO.

### 6.4 Mã môn: điều kiện để chia sẻ theo môn

**Quyết định 2026-10-22:** chia sẻ trong phạm vi cùng môn (các lớp, các học kỳ). Không làm cấp khoa.

**Vướng:** hiện chưa có khái niệm "môn" tách khỏi "khoá Canvas".
- LTI launch tạo mỗi khoá Canvas thành một dòng `courses` với `code = stableCourseCode(...)` (`core-api/src/lti/lti.service.ts:61-73`).
- Import đề cương ghi đè `code` bằng mã môn, ví dụ `CO3137` (`postgres_curriculum_repository.py:296-304`).
- `courses.code` lại là UNIQUE. Lớp Canvas thứ hai cùng môn import đề cương sẽ vi phạm ràng buộc này. Kết luận từ đọc code, chưa chạy thử.

**Đề xuất:**
- Thêm `courses.subject_code varchar(50)` (không unique, có index). Import đề cương ghi mã môn vào cột này **thay vì** ghi đè `code`. Backfill: `subject_code = code` cho các khoá mà `code` không bắt đầu bằng `canvas`.
- `_course_uuid` (`postgres_curriculum_repository.py:925-939`) hiện tra theo `code = mã môn`. Nó phải bỏ nhánh này và chỉ tra theo `course_id`, nếu không sẽ gộp hai lớp cùng môn vào một khoá.
- `question_banks.subject_code` chép từ `courses.subject_code` lúc tạo. Khớp phạm vi SUBJECT theo cột này.
- `learning_outcomes` vẫn theo từng khoá. Mỗi lớp import đề cương riêng nên có LO riêng, và luật map theo mã ở §6.2 nối chúng lại.

---

## 7. Luồng ghi

### 7.1 Sinh bằng AI

- `persist_curriculum_quiz_items`:
  - Trong cùng CTE: lấy ngân hàng mặc định của khoá, hoặc tạo nếu chưa có (`INSERT … ON CONFLICT` trên `uq_question_bank_course_default`). Ghi `bank_id`.
  - Ghi thêm `generation_request_id` và `author_id` = `requested_by` của yêu cầu.
  - Ghi `provenance` = `{model_id, difficulty, lo_alignment_rationale, verifier}`.
  - Use case cần nhận thêm `request_id`; `content_generation_worker.py` đã có `job.request_id`.
- Phạm vi yêu cầu (`scope`) được phép mang `bankId` (tuỳ chọn): sinh thẳng vào một ngân hàng cụ thể mà user có quyền EDIT. Không có thì dùng ngân hàng mặc định.
- **Câu bị verifier loại:** ghi vào `content_generation_requests` thêm cột `rejected jsonb`, gồm câu và lý do, không ghi vào ngân hàng. Đây là dữ liệu để đánh giá bộ sinh, không phải câu hỏi.
- `content_generation_requests` thêm `quiz_ids uuid[]`, đóng H5.
- `_replace_quiz_items_cursor` (enrichment):
  - Chỉ xoá mềm câu ở `GENERATED_DRAFT`, đóng H6.
  - Ghi `bank_id` của ngân hàng mặc định và `provenance.model_id`.

### 7.2 Giảng viên viết hoặc sửa

- `review.service.ts` khi sửa: đặt `updated_by = claims.sub` và `provenance = {}`. Trigger tự tạo phiên bản. `review_audit_logs` vẫn ghi như cũ, nhưng `raw_changes` chỉ cần `{before_version_id, after_version_id}`.
- Thêm `POST /api/question-banks/:id/items` cho câu viết tay: `origin = 'MANUAL'`, validate bằng `normalizeAnswerKey` có sẵn trong `core-api/src/quiz/question-types.ts`.

### 7.3 Chống trùng (mức tối thiểu)

Trước khi ghi câu mới (sinh, viết tay, nhập), so `lower(trim(question))` với các câu còn sống trong **cùng ngân hàng**. Trùng thì đánh dấu `provenance.duplicate_of`, không chặn. Chống trùng theo ngữ nghĩa bằng Qdrant (`quiz_item_index`) vẫn thuộc [quiz-generation-redesign.md](quiz-generation-redesign.md), chưa có trong code.

---

## 8. Xuất sang Canvas

### 8.1 Điều kiện trên Canvas local

1. **Bật plugin `qti_converter` — đã làm 2026-10-22** (được đồng ý). Lệnh dùng:
   ```ruby
   plugin = Canvas::Plugin.find(:qti_converter)
   ps = PluginSetting.find_or_initialize_by(name: "qti_converter")
   ps.settings = plugin.default_settings.with_indifferent_access.merge(enabled: "true")
   ps.save!
   ```
   Phải lưu **đủ** bộ setting mặc định: `PluginSetting.settings_for_plugin` trả nguyên setting đã lưu, không gộp với mặc định, mà QtiWorker cần `worker` và `provides`. Canvas dựng lại từ đầu thì phải chạy lại lệnh này.
2. **Token API còn hạn.** Token site-admin bị giới hạn 1 tuần. Token mới nạp vào core-api ngày 2026-10-22 hết hạn 2026-10-29 13:40 UTC. Xem [canvas_lti_setup.md](canvas_lti_setup.md).
3. `canvas-lms-jobs-1` phải đang chạy, vì content migration là delayed job. Trong spike, mỗi lần import mất 3–6 giây.

### 8.2 Cách chia ngân hàng bên Canvas

Mặc định **một ngân hàng Canvas cho mỗi LO**, tên `"<subject_code> · <lo_code> · <tên ngân hàng>"`. Lý do:
- Canvas không giữ LO theo từng câu.
- Chia theo LO giúp giảng viên tạo nhóm câu trong quiz Canvas ("lấy 3 câu từ ngân hàng L.O.2.1").
- Nếu gắn Outcome cho ngân hàng, Canvas tự tính mức đạt Outcome khi chấm quiz Classic (`track_outcomes`).

Tên ngân hàng nằm trong từng item, nên **một gói, một lần import** chứa được tất cả ngân hàng theo LO.

Lựa chọn khác: một ngân hàng Canvas cho cả ngân hàng của mình.

### 8.3 Gói QTI 2.1

```
bank-<bank_id>.zip
├── imsmanifest.xml      metadata/schema = "QTIv2.1 Package" (để Converter.is_qti_2 nhận ra)
└── items/
    └── daq-<quiz_id>.xml   một assessmentItem cho mỗi câu
```

- **`identifier` = `daq-<quiz_id>`** (theo câu, không theo phiên bản). Đẩy lại cùng identifier vào cùng khoá, kèm `overwrite_quizzes=true`, thì Canvas cập nhật đúng câu cũ và giữ nguyên id. Chỉ dùng ký tự `[A-Za-z0-9_-]`, vì Canvas thay `:` bằng `-`.
- **`title` = `"<lo_code> #<quiz_id>"`.** API đọc không trả `migration_id`, nên sau khi import, hệ thống khớp câu Canvas ↔ `quiz_id` bằng `question_name`, tức là title.
- **Tên ngân hàng: ghi trong từng item** bằng `<instructureMetadata><instructureField name="question_bank" value="…"/></instructureMetadata>` (`assessment_item_converter.rb:171-175`). `settings[question_bank_name]` và `settings[question_bank_id]` bị bỏ qua trong spike, nên không dùng.
- **Lời phương án bọc `<div class="text">`.** Không bọc thì Canvas chạy `clear_html` lên lời phương án, nên phương án như `<tag>` bị xoá thành "No answer text provided." (`choice_interaction.rb:111-125`).
- Lời câu hỏi để trong `<div>` đầu tiên của `itemBody`, đã escape XML. Canvas giữ nó dưới dạng HTML, nên `a &lt; b` hiển thị thành `a < b`.

Map kiểu câu:

| Kiểu của mình | QTI 2.1 | Kiểu Canvas nhận được | Ghi chú |
|---|---|---|---|
| MCQ_SINGLE | `choiceInteraction maxChoices=1`, một `correctResponse/value` | `multiple_choice_question` | đúng một đáp án ⇒ multiple choice (`choice_interaction.rb:104`) |
| MCQ_MULTI | `choiceInteraction maxChoices=0`, nhiều `value` | `multiple_answers_question` | |
| TRUE_FALSE | `choiceInteraction` 2 lựa chọn "Đúng"/"Sai" | `multiple_choice_question` | Canvas chỉ nhận true/false khi nhãn khớp `/true/`, `/false/` (`choice_interaction.rb:53-60`); chấm điểm vẫn tương đương |
| FILL_BLANK | `extendedTextInteraction`; mỗi cách viết chấp nhận là một `correctResponse/value` (`baseType="string"`) | `short_answer_question` ("Fill in the blank") | Canvas so khớp không phân biệt hoa thường |
| SHORT_ANSWER | `extendedTextInteraction`, không có `correctResponse`; bài mẫu và rubric đặt trong `modalFeedback identifier="general_fb"` | `essay_question` | không có đáp án ⇒ essay (`extended_text_interaction.rb:28-33`); `modalFeedback` thành `neutral_comments` để giảng viên chấm tay |

Ví dụ một item MCQ_SINGLE, đúng dạng đã import thành công trong spike:

```xml
<assessmentItem xmlns="http://www.imsglobal.org/xsd/imsqti_v2p1"
    identifier="daq-019a…" title="L.O.2.1 #019a…" adaptive="false" timeDependent="false">
  <instructureMetadata>
    <instructureField name="question_bank" value="CO3137 · L.O.2.1 · Ngân hàng chung"/>
  </instructureMetadata>
  <responseDeclaration identifier="RESPONSE" cardinality="single" baseType="identifier">
    <correctResponse><value>C2</value></correctResponse>
  </responseDeclaration>
  <outcomeDeclaration identifier="SCORE" cardinality="single" baseType="float"/>
  <itemBody>
    <div>HDFS lưu mỗi khối dữ liệu mặc định bao nhiêu bản sao?</div>
    <choiceInteraction responseIdentifier="RESPONSE" shuffle="false" maxChoices="1">
      <simpleChoice identifier="C1"><div class="text">1</div></simpleChoice>
      <simpleChoice identifier="C2"><div class="text">3</div></simpleChoice>
      <simpleChoice identifier="C3"><div class="text">5</div></simpleChoice>
      <simpleChoice identifier="C4"><div class="text">Tuỳ dung lượng đĩa</div></simpleChoice>
    </choiceInteraction>
  </itemBody>
  <responseProcessing template="http://www.imsglobal.org/question/qti_v2p1/rptemplates/match_correct"/>
</assessmentItem>
```

### 8.4 Trình tự gọi API

Chạy như job nền, theo mẫu outbox: `question_bank_sync_jobs` + sự kiện `QUESTION_BANK_EXPORT_REQUESTED`. Đặt trong core-api, vì `CanvasApiClient` ở đó.

```
1. Lọc câu: bank_id = X, status ∈ {APPROVED, PUBLISHED}, deleted_at IS NULL
2. Đóng một gói: mỗi item mang tên ngân hàng Canvas theo LO của nó (§8.2, §8.3)
3. POST /api/v1/courses/:canvas_course_id/content_migrations
     migration_type=qti_converter
     settings[overwrite_quizzes]=true          ← bắt buộc, kể cả lần đầu
     pre_attachment[name]=bank.zip, pre_attachment[size]=…
   → nhận upload_url + upload_params, id migration, progress_url
4. POST multipart lên upload_url
5. Theo dõi GET /api/v1/progress/:id tới completed | failed
   job ở trạng thái WAITING_LMS; đọc .../content_migrations/:id/migration_issues nếu có lỗi
6. GET /api/v1/question_banks?context_type=Course&context_id=… → các bank theo tên
   GET /api/v1/question_banks/:id/questions → khớp question_name "#<quiz_id>"
7. Upsert question_lms_links(direction=EXPORT, version_id = current_version_id lúc đóng gói)
8. counts = {exported, updated, unsupported, failed}; status = COMPLETED | FAILED
```

- `canvas_course_id`: lấy qua `CanvasApiClient.getCourseByLtiContext(lms_course_ref.lms_context_id)`, như import đề cương đang làm (`core-api/src/curriculum/curriculum-import.service.ts:46`).
- **Câu "Canvas đang cũ":** `question_lms_links.version_id ≠ quiz_items.current_version_id`. Giao diện hiện nút "Đẩy lại".
- **Câu đổi LO, hoặc ngân hàng đổi tên:** tên ngân hàng trong item đổi theo, nên Canvas **chuyển** câu sang ngân hàng mới mà vẫn giữ id (đã thấy trong spike S4). Ngân hàng cũ có thể còn lại rỗng.
- **Câu RETIRED sau khi đã đẩy:** GĐ2 không xoá bên Canvas. Importer chỉ xoá câu thừa khi import từ Blueprint (`migration.for_master_course_import?`, `assessment_question_importer.rb:58-68`), không phải trường hợp này. Giao diện liệt kê các câu này để giảng viên tự xoá.
- **Quyền:** chỉ người có EDIT trên ngân hàng, đồng thời là instructor của khoá đích, mới được xuất. Ở dev, token admin gọi thay; khi dùng thật thì chuyển sang OAuth2 theo từng giảng viên, như ghi chú trong `canvas-api.client.ts`.
- **Ngân hàng cấp account** (chia sẻ cho cả khoa ngay trong Canvas): cùng API với `accounts/:id`, cần quyền admin account. Để sau.

### 8.5 Spike GĐ2a: kết quả (2026-10-22)

**Cách chạy**
- Dữ liệu: 5 câu thật lấy từ dev DB (CO3137, L.O.1.1), mỗi kiểu một câu, cộng một câu tự tạo chứa `<`, `&`, `"`, `²`, `∑ᵢ` và tiếng Việt có dấu.
- Gói QTI 2.1 do một script Python đóng (theo đúng §8.3), import vào các khoá sandbox của Canvas local.
- **Token API đã hết hạn**, nên migration được tạo bằng `bin/rails runner`: `ContentMigration` + `Attachment`, rồi `queue_migration`. Đường xử lý vẫn là `QtiWorker` mà REST API dùng; chỉ khác bước tải file lên.

| # | Kiểm tra | Kết quả |
|---|---|---|
| S1 | Bật plugin, import gói QTI 2.1 | ✅ `imported` sau 3–6 giây, không có `migration_issues`, không tạo quiz nào |
| S2 | Kiểu câu | ✅ đúng bảng §8.3: `multiple_choice_question` (MCQ, Đúng/Sai), `multiple_answers_question`, `short_answer_question` (2 cách viết chấp nhận), `essay_question` (bài mẫu và rubric nằm ở `neutral_comments`) |
| S3 | Chấm điểm | ✅ chấm bằng `Quizzes::SubmissionGrader.score_question` trên dữ liệu đã import: MCQ đúng 1 / sai 0; multi đủ đáp án 1, tick tất cả 0; điền khuyết `BIG DATA` và `dữ liệu lớn` đúng, câu sai 0; essay `undefined` (chấm tay). **Chưa** làm bài qua giao diện người học |
| S4 | Import lại sau khi sửa 1 câu | ✅ **có điều kiện**: tên ngân hàng trong item + `overwrite_quizzes=true` ⇒ vẫn 6 câu, cùng id, lời câu sửa được cập nhật. ❌ không có `overwrite_quizzes` ⇒ id bị gắn tiền tố `5_daq-…`, thêm một ngân hàng trùng tên và 6 câu trùng. ❌ `settings[question_bank_name]` và `settings[question_bank_id]` bị bỏ qua ⇒ ngân hàng "No Name - <khoá>" |
| S5 | `question_name` | ✅ bằng title (`"L.O.1.1 #<quiz_id>"`). Ngày 2026-10-22, khi đã có token mới, gọi lại `GET /api/v1/question_banks/3/questions` từ core-api: trả 6 câu, đúng `question_name` và `question_type` |
| S6 | Tiếng Việt, ký tự đặc biệt, công thức | ✅ sau khi bọc phương án bằng `<div class="text">`. Lần đầu không bọc thì phương án `<tag>` bị mất |

**Chưa kiểm tra:**
- Luồng tải file `pre_attachment` qua REST API. Token mới đã có từ 2026-10-22; để làm trong GĐ2b.
- Làm quiz Classic qua giao diện người học.
- Câu có ảnh.
- Import vào account.

**Dữ liệu sandbox còn trên Canvas local:** 3 khoá "QTI spike (question bank) 2026-10-22", "QTI spike B1 2026-10-22", "QTI spike B2 2026-10-22", cùng các ngân hàng của chúng. Xoá được, không ảnh hưởng gì khác.

**Phương án dự phòng không còn cần**, ghi lại để tham khảo:
- Cài `QTIMigrationTool` rồi xuất QTI 1.2.
- Ghi câu qua Quiz Questions API vào một quiz ẩn.

---

## 9. Nhập từ Canvas

`POST /api/question-banks/:id/canvas-import { canvasBankIds: [...] }`. Cần EDIT trên ngân hàng đích.

```
1. GET /api/v1/question_banks?context_type=Course&context_id=<canvas course>&include_question_count=true
   (giao diện cho chọn ngân hàng)
2. Với mỗi ngân hàng được chọn: GET /api/v1/question_banks/:id/questions (phân trang)
3. Map kiểu; tạo quiz_items: origin=CANVAS_IMPORT, status=GENERATED_DRAFT, lo_id=NULL,
   lesson_id=NULL, provenance={lms:'canvas', ext_bank_id, ext_question_id}
4. question_lms_links(direction=IMPORT)
5. Gợi ý LO + Bloom bằng AI (job riêng, chỉ gợi ý); giảng viên xác nhận ở trang review
```

| Kiểu Canvas | Kiểu của mình | Ghi chú |
|---|---|---|
| `multiple_choice_question` | MCQ_SINGLE | đáp án đúng là `answers[].weight = 100` |
| `multiple_answers_question` | MCQ_MULTI | |
| `true_false_question` | TRUE_FALSE | |
| `short_answer_question` | FILL_BLANK | validator của mình đòi đúng một `____`; nếu đề chưa có thì thêm vào cuối và đánh dấu cần sửa |
| `essay_question` | SHORT_ANSWER | thiếu bài mẫu và rubric ⇒ chưa duyệt được tới khi giảng viên bổ sung |
| matching, numerical, calculated, multiple_dropdowns, fill_in_multiple_blanks, file_upload, text_only | không nhập | đếm vào `counts.unsupported`, liệt kê tên câu |

- `question_text` là HTML: chuyển sang văn bản thuần, giữ xuống dòng. Câu có ảnh (link file Canvas) được đánh dấu `provenance.has_images`. GĐ3 không tải ảnh về.
- Nhập lại cùng ngân hàng: nếu câu phía mình vẫn ở phiên bản đã nhập thì cập nhật; nếu đã có người sửa thì bỏ qua và báo xung đột.

---

## 10. API và giao diện

**core-api, module mới `question-bank`**

| Method | Path | Quyền |
|---|---|---|
| GET | `/api/question-banks?courseId=` | trả các ngân hàng có quyền ≥ VIEW |
| POST | `/api/question-banks` | instructor của `homeCourseId` |
| PATCH | `/api/question-banks/:id` | EDIT (`visibility`: chỉ chủ hoặc admin) |
| GET | `/api/question-banks/:id/items?lo=&type=&status=&origin=` | VIEW |
| POST | `/api/question-banks/:id/items` | EDIT |
| POST, DELETE | `/api/question-banks/:id/shares` | EDIT |
| POST | `/api/question-banks/:id/items/:quizId/fork` | USE nguồn + EDIT đích |
| GET | `/api/quiz-items/:id/versions` | VIEW |
| POST | `/api/question-banks/:id/canvas-export` | EDIT + instructor khoá đích |
| GET | `/api/canvas/question-banks?courseId=` | instructor |
| POST | `/api/question-banks/:id/canvas-import` | EDIT |
| GET | `/api/question-bank-sync-jobs/:id` | người tạo job |

Các endpoint review hiện có (`/api/review/quiz-items/:id/*`) giữ nguyên đường dẫn, chỉ đổi phần kiểm tra quyền (§6.1).

**web**
- `/manage/banks` (mới): danh sách ngân hàng theo nhóm "Của tôi / Của khoá / Được chia sẻ / Cùng môn". Trang chi tiết có bảng câu lọc theo LO, kiểu, trạng thái, nguồn gốc, và các nút chia sẻ, fork, xuất Canvas, nhập Canvas, lịch sử phiên bản.
- `/manage/review`: thêm bộ lọc ngân hàng; hiện nguồn gốc (AI, model, yêu cầu nào) cạnh mỗi câu.
- `/manage/quizzes/new` (Soạn đề): nguồn câu gồm cả các ngân hàng có quyền USE; báo LO không map được (§6.2).

---

## 11. Migration và backfill

Một migration Prisma, chạy trong một transaction:
1. Tạo các bảng ở §5.2, các cột ở §5.3 (`bank_id` tạm thời nullable), và function trigger, **chưa** bật trigger. Thêm `courses.subject_code` và backfill theo §6.4.
2. Tạo ngân hàng mặc định cho mỗi khoá có `quiz_items`: `owner_id NULL`, `visibility 'COURSE'`, `subject_code = courses.code`, `is_course_default = true`.
3. `UPDATE quiz_items SET bank_id = <ngân hàng mặc định của course_id>`.
4. Với mỗi câu: tạo `quiz_item_versions` số 1 từ nội dung hiện tại, `provenance = {"backfilled": true}`, rồi đặt `current_version_id`.
5. `quiz_sets.items[*].version_id` = phiên bản 1 của `quiz_id` nếu nội dung snapshot trùng với nội dung hiện tại; không trùng thì để NULL. Hiện chỉ có 1 lần `EDIT_QUIZ` trong audit, nên NULL rất hiếm.
6. `quiz_attempts.quiz_version_id`: để NULL cho dữ liệu cũ.
7. `ALTER COLUMN bank_id SET NOT NULL`; bật trigger.

Mặc định `author_id` = NULL cho dữ liệu cũ. Có thể suy ngược từ `content_generation_requests.requested_by` qua thời điểm tạo, nhưng không đáng làm với 76 câu.

Sau migration phải chạy `prisma generate` **trong container** core-api rồi restart: `node_modules` của core-api là volume, nên chạy generate trên host không có tác dụng với container.

---

## 12. Kế hoạch triển khai

| GĐ | Nội dung | Phụ thuộc | Tiêu chí xong |
|---|---|---|---|
| **1a** | Migration §11, trigger, ghi `bank_id`/`provenance`/`generation_request_id` ở 2 đường Python, sửa H6 | — | test repo Python: retry worker không tạo phiên bản thừa; enrichment chạy lại không đụng câu REVIEWING; test trigger: INSERT ⇒ v1, UPDATE nội dung ⇒ v2, UPDATE status ⇒ không tạo phiên bản |
| **1b** | `bank-access.ts`, module `question-bank`, review chuyển sang quyền ngân hàng, `version_id` trong snapshot, `quiz_version_id` trong attempt | 1a | spec: user không có quyền bị 403; USE được thêm câu vào đề nhưng không sửa được |
| **1c** | `courses.subject_code` + import đề cương ghi vào đó, bỏ tra theo mã trong `_course_uuid` (§6.4); fork, dùng câu khác khoá (map LO theo mã), phạm vi SUBJECT, `/manage/banks`, bộ lọc ở review, nguồn ở Soạn đề | 1b | e2e trên dev: khoá Canvas thứ hai cùng môn CO3137 import đề cương không lỗi; giảng viên khoá đó thấy ngân hàng SUBJECT của CO3137 và soạn đề với LO map đúng |
| **2a** | Spike QTI 2.1 (§8.5) | bật plugin Canvas | **xong 2026-10-22**: S1–S6 đạt; còn thiếu luồng tải file qua REST (cần token) |
| **2b** | Xuất sang Canvas (§8.3–8.4), job + giao diện | 2a, 1a, token Canvas mới | xuất ngân hàng CO3137 → Canvas có các ngân hàng theo LO; sửa 1 câu, đẩy lại ⇒ không nhân đôi |
| **3** | Nhập từ Canvas (§9) + gợi ý LO | 1b | nhập một ngân hàng Canvas viết tay có đủ 5 kiểu + 1 kiểu không hỗ trợ; báo cáo đếm đúng |
| sau | Moodle XML adapter; micro-content lấy câu từ ngân hàng; `approved_version_id`; chống trùng ngữ nghĩa; ngân hàng cấp account Canvas | | |

---

## 13. Rủi ro và câu hỏi mở

| # | Vấn đề | Đề xuất mặc định |
|---|---|---|
| Q1 | Chia sẻ tới đâu | **Đã chốt 2026-10-22: cùng môn.** PRIVATE / COURSE / SUBJECT và share tường minh; không làm cấp khoa |
| Q2 | **`courses.code` đang UNIQUE.** Import đề cương ghi mã môn (`CO3137`) vào `courses.code`, nên lớp Canvas thứ hai cùng môn sẽ đụng ràng buộc | Vì Q1 chọn cùng môn, việc này thành bắt buộc: thêm `courses.subject_code`, làm trong GĐ1c (§6.4) |
| Q3 | Bật `qti_converter` trên Canvas local | **Đã đồng ý và đã bật 2026-10-22** (§8.1) |
| Q4 | Token site-admin hết hạn mỗi tuần. Token mới nạp 2026-10-22 hết hạn 2026-10-29 13:40 UTC | tắt flag `site_admin_access_token_expiration` hoặc dùng user dịch vụ không phải site admin ([canvas_lti_setup.md](canvas_lti_setup.md)). Token hết hạn thì GĐ2b và các tính năng Canvas đang có (đồng bộ tài liệu, import đề cương) đều ngừng |
| Q5 | Importer QTI 2.1 của Canvas có thể kén định dạng | **Đã kiểm tra trong spike.** Có ba điểm kén: tên ngân hàng phải ở trong item; bắt buộc `overwrite_quizzes`; phương án phải bọc `div.text` |
| Q6 | Thống kê câu hỏi khi câu dùng ở nhiều khoá | chỉ hiện số tổng hợp (tỉ lệ đúng, độ phân biệt) theo phiên bản, không lộ danh tính người học khoá khác |
| Q7 | LO cùng mã nhưng khác phiên bản CTĐT | GĐ1 coi là khớp và cảnh báo khi phát biểu khác nhau; chưa tự map |
| Q8 | Classic Quizzes có thể bị bỏ khỏi canvas-lms mã nguồn mở về sau | ngân hàng của mình là nguồn gốc; adapter Canvas có thể bỏ mà không mất dữ liệu |
