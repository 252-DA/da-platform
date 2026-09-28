# Thiết kế lại pipeline sinh quiz — `QuizGen v2`

| | |
|---|---|
| Trạng thái | Giai đoạn 0 đã triển khai (2026-09-24); giai đoạn 1–3 vẫn là đề xuất |
| Ngày | 2026-09-21 |
| Phạm vi | `worker` (content-generation, enrichment), `packages-ai` (LO mapper, retrieval, LLM usage), `core-api` (contract, review, quiz), `contracts` |
| Liên quan | [chunking-redesign.md](chunking-redesign.md): quiz lấy nội dung qua `heading_path` và chunk, nên hai thiết kế bổ trợ nhau |

---

## 0. Tóm tắt

- **Hiện trạng: sinh quiz là điều phối prompt, không có thuật toán.** Chọn nội dung nào để hỏi, kiểm soát mức Bloom, chọn đáp án nhiễu (distractor), độ khó, vị trí đáp án đúng, chống trùng: tất cả giao cho một prompt. Cơ chế "kiểm tra" là để chính model đó tự chấm, và kết quả chấm không có quyền chặn.
- **Nền dữ liệu đang gãy.** `chunk_lo_mappings` là nguồn context duy nhất cho **cả hai** đường sinh quiz, nhưng **không có code production nào ghi vào bảng này**: `MapChunksToLosUseCase` chỉ được khai báo trong container mà không nơi nào gọi. Theo code, sinh quiz theo LO sẽ báo "No grounded source chunks", còn enrichment tốn token sinh xong rồi `INSERT` không chèn được dòng nào mà không báo lỗi.
- **Lỗi đã chạy thử:** mọi câu sinh theo LO đều lưu **`bloom_level = 2`** bất kể LO ở mức nào. **Lỗi đọc code:** mọi bản ghi chi phí LLM của quiz vi phạm `CHECK` nên không bao giờ được lưu.
- **Nguyên tắc v2: "LLM viết, code quyết định".** LLM chỉ làm ba việc nó giỏi: viết câu hỏi, đề xuất đáp án nhiễu, chấm theo rubric. Mọi quyết định còn lại (chọn nội dung, phân bổ Bloom/độ khó, chọn distractor, xáo đáp án, chống trùng, kiểm bằng chứng) là code tất định và test được.
- **Kỹ thuật chính:**
  - map LO lai (heading + embedding);
  - **đơn vị kiến thức** (knowledge unit) và chọn theo **MMR** để phủ đều nội dung;
  - **blueprint** phân bổ Bloom × độ khó × vị trí đáp án;
  - **trích dẫn nguyên văn** bắt buộc cho mỗi câu;
  - sinh 6 ứng viên distractor rồi chọn 3 theo luật + **dải tương đồng ngữ nghĩa**;
  - **judge "giải trước, chấm sau"** bằng model khác;
  - **loại câu sai rồi sinh bù** thay vì lưu câu sai;
  - **phân tích câu hỏi** từ `quiz_attempts` theo lý thuyết trắc nghiệm cổ điển (CTT).
- **Chi phí ước tính gấp ~2.5–3 lần số token hiện tại mỗi câu** (khoảng 3 lần gọi LLM mỗi câu được chấp nhận), có trần ngân sách cứng cho mỗi request. Con số thật sẽ đo được sau khi sửa phần ghi usage.
- **Giai đoạn 0 làm được ngay, rẻ, giá trị cao:** nối LO mapper vào pipeline và backfill, sửa `bloom_level`, sửa ghi usage, `quiz_id` tất định, không lưu câu đã bị verifier loại, xáo đáp án.

---

## 1. Hiện trạng

### 1.1 Hai đường sinh quiz

```
(1) Theo LO: giảng viên yêu cầu
core-api POST content-generation ─► outbox CONTENT_GENERATION_REQUESTED {scope}
  ─► content-generation worker ─► GenerateCurriculumQuizUseCase
        resolve LO (chỉ lấy LO đầu tiên)
        context: MCP retrieve_quiz_context / fallback list_chunks_for_lo[:5]   ◄── chunk_lo_mappings
        LLM sinh N câu ─► LLM tự kiểm tra ─► sinh lại câu bị loại (≤ 2 vòng)
        lưu quiz_items (MCQ_SINGLE, GENERATED_DRAFT) ─► người duyệt ─► publish

(2) Theo section: tự động sau khi ingest tài liệu
enrichment worker ─► RunEnrichmentUseCase: mỗi section ─► LLM sinh 3–5 câu (không kiểm tra)
        lưu qua JOIN chunk_lo_mappings (lấy LO của chunk đầu tiên)                ◄── chunk_lo_mappings
```

### 1.2 Lỗi và thiếu sót

Cột "Nguồn": **chạy** = đã chạy thử bằng `.venv`; **code** = kết luận từ đọc code (kèm cách xác minh nếu cần).

**D: Nền dữ liệu**

| # | Vị trí | Vấn đề | Nguồn | Hệ quả |
|---|---|---|---|---|
| D1 | `packages-ai/.../container.py:309` | `MapChunksToLosUseCase` chỉ được khai báo; grep toàn repo không thấy delivery, worker hay core-api nào gọi nó hoặc ghi `chunk_lo_mappings` | code (xác minh: `SELECT count(*) FROM chunk_lo_mappings;`) | đường (1): `list_chunks_for_lo` trả rỗng → `Err("No grounded source chunks…")`. Đường (2): `INSERT … SELECT FROM lesson_row` ra 0 dòng → card/quiz đã sinh bị mất im lặng, **sau khi** bản nháp cũ đã bị soft-delete |
| D2 | `heuristic_lo_mapper.py:19-40` | Map chỉ theo số chương trong heading; regex chỉ nhận "Chương N" hoặc heading bắt đầu bằng số | code | mọi LO cùng chương nhận **toàn bộ** chunk của chương; heading "Bài 4", "Chapter 4", "Lecture 4" không được map; mức 0.9 cần ≥ 2 trong 4 từ đầu của LO xuất hiện trong heading, gần như không đạt |
| D3 | `contracts/integration-events/v1/content-generation-requested.json` so với `content-generation.service.ts:74-79` | Contract v1 định nghĩa `target`, `targets[]` (mỗi LO kèm `bloom_level`), `count_per_lo`, `additionalProperties: false`; core-api thực tế gửi `scope` tự do; worker đọc `scope` (`_parse_job`) | code | payload thật **không hợp lệ theo contract**. `test_contract_fixtures.py` chỉ validate fixture nên không phát hiện. core-api cho `type='card'` nhưng worker chỉ nhận `quiz` → mọi request card đều FAILED | **Phần lệch contract: ĐÃ XỬ LÝ 2026-09-28** — contract v1 sửa lại mô tả đúng `scope` (§6.3); envelope rút `required` về 5 field `OutboxService` thực gửi; fixture viết lại theo message thật và đã kiểm chạy lọt qua `_parse_job`/`_quiz_request`. Dạng `target/targets[]` chuyển thành bản đề xuất cho v2. **Phần `type='card'`: CHƯA xử lý** — core-api vẫn nhận `'card'` (`content-generation.service.ts:35`), worker vẫn ném lỗi với mọi type khác `'quiz'`, nên request card vẫn FAILED. Contract hiện ghi `enum: [card, quiz]` để mô tả đúng core-api, không phải để hợp thức hoá lỗi này.
| D4 | `generate_curriculum_quiz.py:164` → `postgres_curriculum_repository.py:537-548` | `bloom_level` của LO trong DB là INT; `str()` biến thành `"3"`; `_bloom_level("3")` không khớp bảng tên → mặc định 2 | **chạy** | **mọi câu sinh theo LO đều lưu `bloom_level = 2`**; prompt chỉ thấy `"Bloom level required: 3"` |

**C: Chọn nội dung**

| # | Vị trí | Vấn đề | Nguồn |
|---|---|---|---|
| C1 | `postgres_curriculum_repository.py:479`, `retrieve_quiz_context.py:156-189` | `ORDER BY confidence DESC` trên 2 giá trị (0.7/0.9) → thứ tự hoà tuỳ ý. Semantic chỉ sắp lại các chunk lọt top 20–100 của **cả khoá học**; fallback lấy `[:5]` | code |
| C2 | `generate_curriculum_quiz.py:148` | Target là chapter/assessment → chỉ sinh cho LO đầu tiên ("For MVP") | code |
| C3 | toàn pipeline | Không có khái niệm độ phủ: cùng LO → cùng top-5 context mỗi lần chạy → câu gần trùng; không chống trùng với ngân hàng câu đã có | code |

**G: Sinh câu**

| # | Vị trí | Vấn đề | Nguồn |
|---|---|---|---|
| G1 | `_build_prompt` | Bloom chỉ là một con số trong prompt; không định nghĩa, không động từ, không mẫu câu; không kiểm tra câu có đạt mức đó | code |
| G2 | `_build_prompt` | Distractor do LLM tự nghĩ hoàn toàn; không có luật chống gợi ý (độ dài, "tất cả đều đúng", đồng nghĩa với đáp án) | code |
| G3 | cả hai đường + `lesson.service.ts:64-71` | Không xáo đáp án (grep không thấy `shuffle`/`random`); core-api phục vụ các phương án theo đúng thứ tự đã lưu | code (đo: SQL ở §11.5) |
| G4 | `postgres_curriculum_repository.py` (INSERT) | Chỉ `MCQ_SINGLE`, dù schema hỗ trợ `MCQ_MULTI`, `TRUE_FALSE`, `FILL_BLANK` | code |
| G5 | `quiz_items` DDL | LLM tự gán `difficulty` nhưng bảng không có cột để lưu → mất; không hiệu chỉnh | code |
| G6 | `generate_curriculum_quiz.py:218` | `payload.questions[:count]`: LLM trả thiếu thì lưu thiếu, không sinh bù | code |

**V: Kiểm tra**

> Vòng verify + regenerate (`_verify_and_refine`, `_run_verifier`, `_run_regeneration`) cùng `_log_usage` và 5 test đi kèm hiện **chưa được commit** trong submodule `worker` (chỉ nằm trong working tree). 15/15 test của `test_generate_curriculum_quiz.py` pass trên working tree ngày 2026-09-21.

| # | Vị trí | Vấn đề | Nguồn |
|---|---|---|---|
| V1 | `_run_verifier` | Cùng model, cùng cấu hình tự chấm bài mình; chấm cả N câu trong một lần gọi | code |
| V2 | `generate_curriculum_quiz.py:474-479` | Câu vẫn bị loại sau khi hết lượt sửa **vẫn được lưu** (chỉ log warning); verifier lỗi thì coi như qua. Đây là **chủ ý** (docstring `_verify_and_refine`: người duyệt vẫn là cổng cuối; có test `test_verify_exhausts_retries_and_persists_last_attempt`, `test_verifier_error_does_not_block_persistence`). v2 đổi chính sách này (§7.8): câu sai về đúng/sai thì không đẩy sang người duyệt | code |
| V3 | `_build_verification_prompt` | Verifier thấy đáp án trước khi phán xét; không kiểm tra Bloom, bám LO, lộ đáp án, hay câu phụ thuộc ngữ cảnh ("theo đoạn trên…") | code |

**O: Vận hành**

| # | Vị trí | Vấn đề | Nguồn |
|---|---|---|---|
| O1 | `run_enrichment.py:177-186`, `:480-487` | Một section gọi LLM lỗi → dừng vòng lặp, chưa có gì được lưu, status vẫn `DONE` → mất toàn bộ card/quiz của tài liệu | code |
| O2 | `generate_curriculum_quiz.py:204,516,550`; `migration.sql:440` | Ghi `status="ok"`/`"error"`, CHECK chỉ cho `'OK','RATE_LIMITED','ERROR'` (so sánh phân biệt hoa thường) → mọi lần ghi usage thất bại (chỉ log warning). `ai_runtime` có trả `usage` token nhưng `ILLMClient.generate` chỉ trả text → token/cost luôn 0. Bảng `user_llm_quota`/`scope_llm_quota` tồn tại nhưng không code nào dùng | code |
| O3 | `generate_curriculum_quiz.py` (uuid4) + outbox `attempts: 5` | `quiz_id` ngẫu nhiên; worker `raise` khi lỗi → nếu lỗi sau bước lưu (ví dụ cập nhật request), retry sinh thêm một bộ câu trùng | code |
| O4 | `review.service.ts:138-156` | Reject → `CHANGES_REQUESTED` + lý do, nhưng không có vòng sinh lại; lý do reject không được dùng làm dữ liệu | code |
| O5 | `quiz_attempts` | Có `chosen_answer`, `is_correct`, `response_time_ms` cho từng câu, nhưng không có gì dùng để đánh giá chất lượng câu hỏi | code |

### 1.3 Nguyên nhân gốc

1. **Mọi quyết định sư phạm dồn vào một prompt.** Không phần nào test được.
2. **Không có đơn vị "kiến thức" để lập kế hoạch**, nên không đo được độ phủ và không chống trùng được.
3. **Kiểm tra dựa vào chính model sinh** và không có quyền chặn.
4. **Liên kết LO ↔ nội dung chưa bao giờ được nối vào pipeline.** Unit test mock `list_chunks_for_lo` nên không phát hiện.
5. **Không có vòng phản hồi.** Dữ liệu từ người duyệt và người học không quay về pipeline.

---

## 2. Ràng buộc từ hệ thống

| Ràng buộc | Nguồn | Hệ quả cho thiết kế |
|---|---|---|
| `quiz_items`: `type ∈ {MCQ_SINGLE, MCQ_MULTI, TRUE_FALSE, FILL_BLANK}`, `options JSONB`, `correct_answer JSONB`, `bloom_level INT 1–6`, `lesson_id NOT NULL` (một lesson cho mỗi `(course, lo)`), không có cột difficulty/metadata | `migration.sql:325` | metadata sinh câu cần một cột JSONB mới (§6.3) |
| Đáp án đúng lưu dạng **text** của phương án, chấm bằng `JSON.stringify(a) === JSON.stringify(b)` | `quiz.service.ts:7-9`, `:63` | xáo phương án **an toàn**. `MCQ_MULTI` cần chuẩn hoá thứ tự mảng trước khi bật; `FILL_BLANK` so khớp chính xác nên rất dễ chấm sai với tiếng Việt → để sau |
| Luồng duyệt: `GENERATED_DRAFT → REVIEWING/CHANGES_REQUESTED → APPROVED → PUBLISHED`; publish yêu cầu APPROVED | `review.service.ts`, `lesson.service.ts` | người duyệt là cổng cuối, nhưng v2 phải giảm việc cho họ, không đẩy việc sang họ |
| `content_generation_requests`: `status`, `generated_count`, `last_error` | `migration.sql:481` | kết quả thiếu câu báo qua `generated_count` < yêu cầu |
| LLM: một cấu hình duy nhất (`gemini-2.0-flash`, `temperature=0.2`); provider `gemini` / `openai-compatible` / `deepseek` qua `ai_runtime` | `infrastructure/config.py:159-169` | cần client thứ hai cho judge (§7.8); temperature riêng cho từng vai trò |
| Container content-generation hiện không có embedder | `worker/worker/container.py` | thêm `GrpcEmbedder` (embedding-service), không nạp model tại chỗ |
| Qdrant đã có vector chunk với payload `course_id` | `qdrant_adapter.py` | map LO bằng embedding không cần tính lại vector chunk |
| `quiz_attempts` lưu từng câu với `chosen_answer`, `is_correct`, `response_time_ms` | `migration.sql:370` | đủ dữ liệu cho phân tích câu hỏi (§7.11) |
| Contract v1 chỉ cho `style: "quiz"`, `count_per_lo ≤ 10`, `targets ≤ 20` | contract v1 | phân bổ theo `midterm`/`final` cần contract v2 (§13) |

---

## 3. Mục tiêu và phạm vi

| # | Mục tiêu | Đo bằng |
|---|---|---|
| QG1 | **Có căn cứ**: mọi câu có ít nhất một trích dẫn nguyên văn từ tài liệu nguồn, và đáp án được chứng minh bằng trích dẫn đó | 0 câu thiếu trích dẫn hợp lệ (kiểm tất định) |
| QG2 | **Đúng LO, đúng Bloom**: `bloom_level` lưu = mức được judge đánh giá; không vượt mức của LO | tỉ lệ khớp Bloom giữa judge và người chấm |
| QG3 | **Một đáp án đúng duy nhất**, distractor hợp lý và không gợi ý đáp án | lỗi đúng/sai do người chấm phát hiện ≤ 2% |
| QG4 | **Phủ đều, không trùng**: câu trải trên nhiều đơn vị kiến thức; không trùng ngân hàng câu | tỉ lệ trùng; độ phủ KU |
| QG5 | **Vị trí đáp án cân bằng** | tỉ lệ lớn nhất của một vị trí ≤ 35% |
| QG6 | **Tất định, idempotent, có ngân sách**: retry không sinh trùng; token/cost được ghi; có trần | usage log đầy đủ; 0 bản trùng khi retry |
| QG7 | **Vòng phản hồi**: dữ liệu duyệt và làm bài quay về đánh giá câu hỏi và prompt | dashboard cờ câu hỏi; tỉ lệ duyệt không sửa theo phiên bản prompt |
| QG8 | **Khớp contract v1** | test validate payload **thật** theo schema |

**Không làm:**
- **Kiểm tra thích ứng** (CAT/IRT chọn câu theo năng lực từng người học): cần ngân hàng câu đã hiệu chỉnh trước; để sau.
- **Chấm câu tự luận** hoặc câu ở mức Bloom 6 "Sáng tạo": không chấm tự động được bằng trắc nghiệm.
- **Fine-tune model.**
- **Câu hỏi có hình ảnh.**

---

## 4. Nguyên tắc thiết kế

1. **LLM viết, code quyết định.** LLM sinh *ứng viên*; code tất định lập kế hoạch, chọn, kiểm tra và sắp xếp.
2. **Không có bằng chứng thì không có câu hỏi.** Mỗi câu phải chỉ ra được đoạn nguyên văn chứng minh đáp án.
3. **Loại > sửa > lưu.** Câu sai bị bỏ và sinh bù; tối đa một lần sửa có mục tiêu; tuyệt đối không lưu câu đã bị loại vì lý do đúng/sai.
4. **Judge độc lập.** Dùng model khác (khuyến nghị khác họ model), temperature 0, **giải câu hỏi trước khi được thấy đáp án**.
5. **Ghi lại mọi thứ.** Trích dẫn, kế hoạch, phán quyết và token được lưu vào `generation_meta` để kiểm toán và để người duyệt đọc nhanh.
6. **Ngân sách cứng.** Mỗi request có trần số lần gọi và số token; vượt trần thì trả kết quả một phần kèm lý do.

---

## 5. Kiến trúc tổng thể

### 5.1 Các bước

```
                                          [LLM] = gọi model     [code] = tất định
S0  Chuẩn hoá request      [code]  contract v1: targets[] (lo_id, bloom), count_per_lo; ước tính ngân sách
S1  LO → kho nội dung      [code]  mapper lai heading + embedding (chạy lúc ingest, không chạy lúc sinh)
S2  Đơn vị kiến thức       [LLM]   trích KU từ chunk (cache theo content_hash)  →  [code] chọn KU bằng MMR
S3  Blueprint              [code]  mỗi slot: (KU, Bloom, loại câu, độ khó, vị trí đáp án)
S4  Sinh câu               [LLM]   stem + key + 6 ứng viên distractor + giải thích + trích dẫn
S5  Chọn distractor        [code]  luật + dải tương đồng ngữ nghĩa + đa dạng + chống gợi ý độ dài
S6  Kiểm tra               [code]  10 luật tất định  →  [LLM judge] giải trước, rồi chấm rubric
S7  Sửa / sinh bù          [LLM ≤1 lần/câu] hoặc thay distractor [code]; hết slot thì lấy KU dự phòng
S8  Lắp ráp và lưu         [code]  xáo theo kế hoạch, quiz_id uuid5, bloom = mức judge, generation_meta
S9  Vòng phản hồi          [code]  thống kê câu hỏi từ quiz_attempts + tín hiệu người duyệt  →  cờ, eval
```

### 5.2 Bố cục module

```
packages-ai/src/document_chunk/
├── adapters/curriculum/hybrid_lo_mapper.py     S1  (thay HeuristicLoMapper)
├── application/quizgen/
│   ├── models.py            KnowledgeUnit, BlueprintSlot, ItemDraft, JudgeVerdict, Budget
│   ├── bloom.py             bảng Bloom VI/EN: động từ, mẫu stem, loại KU/loại câu phù hợp (Phụ lục B)
│   ├── knowledge_units.py   S2a trích KU + kiểm trích dẫn + cache
│   ├── planner.py           S2b chọn KU (MMR) + S3 blueprint
│   ├── generator.py         S4
│   ├── distractors.py       S5
│   ├── validators.py        S6a
│   ├── judge.py             S6b
│   ├── assembler.py         S8
│   └── item_stats.py        S9 (hàm thuần: p-value, r_pb, phân tích distractor)
worker/worker/use_cases/generate_quiz_v2.py     điều phối S0–S8, vòng sinh bù, ngân sách
```

Logic nằm ở `packages-ai`, tách khỏi I/O, nên phần lớn test được bằng dữ liệu tay và LLM giả.

---

## 6. Mô hình dữ liệu

### 6.1 Kiểu nội bộ

```python
class KUType(str, Enum):
    DEFINITION = "definition"; FACT = "fact"; PROPERTY = "property"; PROCEDURE = "procedure"
    PRINCIPLE = "principle"; COMPARISON = "comparison"; EXAMPLE = "example"
    FORMULA = "formula"; CAUSE_EFFECT = "cause_effect"


@dataclass(frozen=True)
class KnowledgeUnit:
    ku_id: str                   # uuid5(chunk_id, content_hash, index, prompt_version)
    chunk_id: str
    course_id: str
    type: KUType
    statement: str               # mệnh đề tự đứng được, ≤ 40 từ
    evidence_quote: str          # đoạn NGUYÊN VĂN trong chunk, ≤ 300 ký tự (đã kiểm)
    key_terms: tuple[str, ...]
    embedding: list[float]


@dataclass(frozen=True)
class BlueprintSlot:
    slot_id: str                 # uuid5(request_id, lo_id, index): ổn định giữa các lần retry
    lo_id: str
    bloom_target: int            # 1–6, không vượt mức của LO
    item_type: str               # MCQ_SINGLE (giai đoạn 1)
    difficulty_target: str       # easy | medium | hard
    key_position: int            # 0–3
    ku: KnowledgeUnit


@dataclass
class ItemDraft:
    slot: BlueprintSlot
    stem: str
    key: str
    distractor_candidates: list[DistractorCandidate]   # 6 ứng viên, mỗi cái kèm misconception + why_wrong
    distractors: list[DistractorCandidate]              # 3 cái được chọn ở S5
    rationale: str
    evidence_quote: str
    verdict: JudgeVerdict | None = None
    flags: list[str] = field(default_factory=list)
    repairs: int = 0
```

### 6.2 Lưu ở đâu

| Dữ liệu | Nơi lưu | Lý do |
|---|---|---|
| Knowledge unit + vector | Qdrant collection mới `knowledge_units` (payload: `course_id`, `chunk_id`, `content_hash`, `type`, `statement`, `evidence_quote`, `prompt_version`) | schemaless, phía AI tự quản lý, không cần migration Prisma; phục vụ luôn MMR |
| Chỉ mục chống trùng câu hỏi | Qdrant collection `quiz_item_index` (vector của stem + key; payload `course_id`, `lo_id`, `quiz_id`, `ku_id`, `status`) | tìm câu gần trùng trong ngân hàng |
| Metadata sinh câu | **Migration Prisma:** `quiz_items.generation_meta JSONB NULL`, `quiz_items.difficulty VARCHAR(10) NULL` | người duyệt cần thấy trích dẫn và cờ; để kiểm toán |
| Thống kê câu hỏi | bảng mới `quiz_item_stats` (giai đoạn 3) | §7.11 |

Ví dụ `generation_meta`:

```json
{
  "pipeline": "quizgen-v2",
  "prompt_version": "2026-10-01",
  "generator_model": "gemini-2.0-flash",
  "judge_model": "deepseek-chat",
  "ku": {"id": "…", "type": "comparison", "statement": "…"},
  "evidence": {"chunk_id": "…", "quote": "…", "heading_path": ["Chương 2", "2.2 Khoá"], "page": 14},
  "blueprint": {"bloom_target": 2, "difficulty_target": "medium", "key_position": 2},
  "judge": {"solve_choice": 2, "bloom_assessed": 2, "lo_alignment": 5, "issues": []},
  "distractors": [{"text": "…", "misconception": "…", "sim_to_key": 0.71}],
  "repairs": 0,
  "flags": [],
  "tokens": {"prompt": 5210, "completion": 980}
}
```

### 6.3 Contract

> **Đảo thứ tự, 2026-09-28.** Contract v1 đã được sửa để **mô tả đúng payload
> hiện hành** (`scope`), vì một contract đang sai là rủi ro hiện tại: ai đọc nó
> để viết consumer mới sẽ code theo payload không bao giờ tới. Dạng
> `target/targets[]/count_per_lo/style` dưới đây giữ nguyên là **bản đề xuất
> chưa triển khai**, và khi làm sẽ là `contracts/integration-events/v2/` kèm
> migration + test tương thích — không sửa đè lên v1. Lý do không làm ngay:
> bảng `content_generation_targets` mà nó cần chưa tồn tại trong prisma, và
> contract v1 cũ không có chỗ cho `source_document_ids` (worker đang dùng thật),
> nên "sửa code cho khớp contract" là bất khả chứ không phải khó.

**Bản đề xuất — chưa triển khai** (`targets[]`, `count_per_lo`, `style`):
- **core-api** chịu trách nhiệm giải target thành danh sách LO, vì nó sở hữu bảng `chapters`, `learning_outcomes`, `lo_assessments`. Chapter → các LO của chapter; assessment → các LO trong `lo_assessments`.
- **Worker** nhận v1 và giữ parser `scope` cũ trong một phiên bản để chuyển tiếp.
- **Thêm test** validate payload do **hàm builder thật** của core-api tạo ra theo JSON schema, không chỉ validate fixture.
- **core-api từ chối `type='card'`** cho tới khi worker hỗ trợ.

---

## 7. Chi tiết từng bước

### 7.1 S0: Chuẩn hoá request

- Đọc `targets[]`: mỗi phần tử mang `lo_id`, `lo_code`, `bloom_level` kiểu **INT**. Giữ INT xuyên suốt; `_bloom_level()` chấp nhận thêm chuỗi số (sửa D4).
- `count_per_lo` ≤ 10 (theo contract). Tổng số câu = `len(targets) × count_per_lo`.
- **Ước tính ngân sách trước khi chạy** = tổng số câu × `tokens_per_item_estimate` (§8), cộng chi phí trích KU nếu chưa có cache. Vượt `max_tokens_per_request` → `FAILED` ngay với lý do rõ ràng. Khi có cơ chế quota, kiểm quota ở cùng chỗ này.
- Các LO được xử lý tuần tự trong một job; kết quả từng LO được lưu ngay sau khi xong LO đó (lỗi ở LO sau không làm mất LO trước).

### 7.2 S1: LO mapper lai

**Chạy khi nào:**
1. Cuối `RunPipelineUseCase`, sau khi tài liệu `INDEXED` và tài liệu thuộc khoá học đã có đề cương.
2. Sau khi ingest hoặc cập nhật đề cương: map lại mọi tài liệu của khoá học.
3. Script backfill một lần cho dữ liệu hiện có.

Mapper **thay thế** toàn bộ mapping của tài liệu (xoá rồi chèn trong một transaction), khác với upsert `GREATEST` hiện tại vốn không bao giờ hạ được confidence.

**Tín hiệu cho mỗi cặp (LO ℓ, chunk x):**
- **h(ℓ, x) ∈ {0, 1}, khớp chương**:
  - regex mở rộng `(?i)(chương|chapter|bài|lecture|module|phần|unit|tuần|week)\s*(\d+)` hoặc heading bắt đầu bằng số, so với số chương của LO;
  - **hoặc** Jaccard token giữa `heading_path` và `chapters.title` (đã chuẩn hoá) ≥ 0.5.
- **s(ℓ, x), tương đồng ngữ nghĩa**: cosine giữa vector chunk (lấy từ Qdrant) và `q_ℓ = embed(statement_vi + " / " + statement_en + " — " + tiêu đề chương)`. Lấy top 50 mỗi LO qua Qdrant (filter `course_id`, loại `content_type = toc`).
- **ŝ**: min–max của s trong tập ứng viên của ℓ (hợp của nhóm có h = 1 và top 50 theo s), để không phụ thuộc thang cosine tuyệt đối của BGE-m3.

**Điểm và lựa chọn:**
```python
score(ℓ, x) = W_H * h(ℓ, x) + W_S * ŝ(ℓ, x)          # khởi đầu W_H = 0.35, W_S = 0.65
giữ x nếu nằm trong top LO_POOL_SIZE (30) theo score VÀ s(ℓ, x) ≥ floor_course
floor_course = phân vị 50 của mọi cosine top-50 trong khoá học (tự thích nghi với từng khoá)
confidence = round(min(score, 1.0), 2)                # vừa kiểu NUMERIC(3,2)
```

- **Nhiều LO cùng chương:** mapping là nhiều–nhiều. ŝ phân biệt được L.O.4.1 với L.O.4.2, điều mapper hiện tại không làm được.
- **Hiệu chỉnh trọng số:** gán nhãn tay 20 LO × top 30 chunk (đúng/sai), chọn `W_H`, `W_S` và cách tính floor để tối đa F1 (§11.4).
- **Chi phí:** chỉ embed câu phát biểu LO (vài chục câu mỗi khoá học), không gọi LLM. Một bước LLM phân xử các cặp sát ngưỡng là tuỳ chọn, mặc định tắt.

### 7.3 S2a: Trích đơn vị kiến thức (KU)

**Vì sao cần KU:** chunk quá thô để lập kế hoạch. Một chunk 400 token có thể chứa 3–6 ý, và hai câu hỏi hỏi cùng một ý là trùng dù từ ngữ khác nhau. KU là đơn vị để **đo độ phủ, chống trùng và ghép với mức Bloom**.

- **Đầu vào:** các chunk trong kho của LO, xếp theo `score`; lấy 12 chunk đầu khi cần. Gộp **tối đa 3 chunk mỗi lần gọi** (~1500 token đầu vào).
- **Đầu ra mỗi chunk:** 2–6 KU `{type, statement, evidence_quote, key_terms}`.
- **Kiểm tra tất định:** `evidence_quote` phải là chuỗi con của chunk sau khi chuẩn hoá NFC và khoảng trắng. Sai thì **bỏ KU** (không sửa).
- **Cache:** key = `(chunk_id, content_hash, prompt_version)`, lưu trong Qdrant `knowledge_units`. KU chỉ được trích **lười**, tức là lần đầu có người yêu cầu quiz cho LO đó, không trích lúc ingest, để không tốn token cho nội dung không ai hỏi tới. Lần sau dùng lại.
- **Loại bỏ:** chunk TOC và chunk < 30 token (dùng `content_type`/`token_count` của chunker v2 khi có).

### 7.4 S2b: Chọn KU theo MMR

```python
def select_kus(pool: list[KU], q_lo, covered: list[KU], slots: list[SlotSpec], cfg) -> list[KU]:
    """Mỗi slot một KU: liên quan tới LO, khác các KU đã chọn và đã có câu hỏi, hợp mức Bloom."""
    chosen, per_chunk = [], Counter()
    avoid = [k.embedding for k in covered]        # KU đã có câu hỏi (status chưa ARCHIVED/xoá)
    for spec in slots:                            # slot có Bloom cao xếp trước (ít KU phù hợp hơn)
        cands = [k for k in pool
                 if k not in chosen
                 and per_chunk[k.chunk_id] < cfg.max_ku_per_chunk            # ≤ 2 KU mỗi chunk
                 and k.type in BLOOM_KU_COMPAT[spec.bloom]] or relax(pool)   # hết thì nới lỏng + gắn cờ
        best = max(cands, key=lambda k:
                   cfg.mmr_lambda * cos(k.embedding, q_lo)
                   - (1 - cfg.mmr_lambda) * max_cos(k.embedding, avoid + [c.embedding for c in chosen]))
        chosen.append(best); per_chunk[best.chunk_id] += 1
    return chosen
```

- `mmr_lambda = 0.7`: ưu tiên liên quan, nhưng phạt mạnh các KU gần với KU đã có câu.
- Chọn thêm `ceil(N/2)` KU **dự phòng** cho bước sinh bù (S7).
- **Tất định:** hoà điểm thì phân xử bằng `ku_id`.

### 7.5 S3: Blueprint

**Phân bổ Bloom** (không bao giờ vượt mức L của LO; theo nguyên tắc căn chỉnh — constructive alignment):

| style | mức L | L−1 | L−2 |
|---|---|---|---|
| `quiz` (ôn tập, formative) | 60% | 30% | 10% |
| `midterm` * | 70% | 30% | 0% |
| `final` * | 100% | 0% | 0% |

\* cần contract v2 (§13). Phần của mức < 1 được dồn lên mức hợp lệ gần nhất. Làm tròn theo phương pháp **phần dư lớn nhất** (largest remainder). Nếu L = 6 thì hạ xuống 5 và gắn cờ `bloom_capped`, vì mức Sáng tạo không đo được bằng trắc nghiệm chấm tự động; người duyệt nên bổ sung đánh giá mở.

**Phân bổ độ khó** (mục tiêu, được hiệu chỉnh lại bằng dữ liệu làm bài ở S9):

| style | easy | medium | hard |
|---|---|---|---|
| `quiz` | 40% | 40% | 20% |
| `midterm` | 25% | 50% | 25% |
| `final` | 20% | 40% | 40% |

Làm tròn cũng theo phần dư lớn nhất; hoà thì ưu tiên easy → medium → hard. Độ khó được hiện thực chủ yếu qua **độ gần của distractor** với đáp án (S5) và độ phức tạp của stem (S4).

**Loại câu:** giai đoạn 1 chỉ `MCQ_SINGLE`. Giai đoạn 3 thêm `TRUE_FALSE` (≤ 20% số câu, chỉ mức 1–2) và `MCQ_MULTI` (mức 3–4) sau khi core-api chuẩn hoá thứ tự mảng khi chấm.

**Vị trí đáp án đúng:**
```python
def key_positions(n: int, seed: bytes) -> list[int]:
    base = ([0, 1, 2, 3] * ceil(n / 4))[:n]       # mỗi vị trí ≈ n/4
    rng = random.Random(seed)                      # seed = uuid5(request_id, lo_id).bytes
    while True:
        rng.shuffle(base)
        if not has_run(base, length=3):            # không để 3 câu liên tiếp cùng vị trí
            return base
```

### 7.6 S4: Sinh câu (LLM)

**Một lần gọi cho mỗi slot**, không gộp nhiều câu: cách ly lỗi, sửa và sinh bù từng câu dễ hơn, và chỉ đưa đúng bằng chứng của câu đó vào prompt.

Prompt gồm:
1. LO (mã, phát biểu VI/EN).
2. **Hướng dẫn cho mức Bloom mục tiêu**: định nghĩa, động từ cho phép, 2 mẫu stem, lỗi hay gặp (Phụ lục B).
3. KU (`statement`) và toàn văn chunk chứa nó (bằng chứng).
4. Mô tả độ khó mục tiêu.
5. Luật viết câu:
   - stem là câu hỏi hoàn chỉnh, tự đứng được, không viết "theo đoạn văn trên/tài liệu";
   - tránh phủ định; nếu buộc phải dùng thì viết hoa "KHÔNG";
   - các phương án đồng nhất về dạng và độ dài;
   - cấm "tất cả đều đúng/sai", "không có đáp án nào";
   - viết cùng ngôn ngữ với tài liệu nguồn.
6. Schema đầu ra:

```json
{
  "stem": "…",
  "key": "…",
  "distractor_candidates": [
    {"text": "…", "misconception": "hiểu lầm mà phương án này nhắm tới", "why_wrong": "…"}
  ],
  "rationale": "vì sao key đúng, dựa trên bằng chứng",
  "evidence_quote": "trích NGUYÊN VĂN từ tài liệu, ≤ 300 ký tự",
  "bloom_claimed": 2
}
```

- Đúng **6** ứng viên distractor, mỗi cái nhắm một hiểu lầm có thật. Đây là nguồn để S5 chọn và để thay thế không cần LLM ở S7.
- `temperature = 0.6` cho generator (cần đa dạng); dùng `generate_structured_payload` hiện có (parse lỗi thì nhờ LLM sửa JSON một lần).

### 7.7 S5: Chọn distractor (tất định)

```python
BANNED = re.compile(r"(?i)(tất cả|cả \w+ (phương án|đáp án)|không (có )?(phương án|đáp án) nào|"
                    r"all of the above|none of the above|both [ab] and)")
BANDS = {"easy": (0.35, 0.75), "medium": (0.50, 0.85), "hard": (0.65, 0.92)}   # cosine với key, cần hiệu chỉnh

def select_distractors(key: str, cands, difficulty: str, emb, cfg):
    k = norm(key)                                     # NFC, lower, gộp khoảng trắng, bỏ dấu câu cuối
    pool = []
    for c in cands:
        t = norm(c.text)
        if not t or t == k or t in k or k in t:       # trùng / chứa nhau với key
            continue
        if BANNED.search(c.text):
            continue
        sim = cos(emb(c.text), emb(key))
        if sim >= cfg.distractor_dup_sim:             # 0.93: nhiều khả năng đồng nghĩa với key → 2 đáp án đúng
            continue
        pool.append((c, sim))
    lo, hi = BANDS[difficulty]
    pool.sort(key=lambda p: (band_distance(p[1], lo, hi), -p[1]))   # trong dải trước, rồi gần key hơn
    chosen = []
    for c, sim in pool:                               # đa dạng: hai distractor không gần trùng nhau
        if all(cos(emb(c.text), emb(d.text)) < cfg.distractor_pairwise_max for d in chosen):  # 0.90
            chosen.append(c)
        if len(chosen) == 3:
            break
    if len(chosen) < 3:
        return None                                   # → S7: xin thêm ứng viên (1 lần) hoặc bỏ câu
    return fix_length_cue(key, chosen, pool)          # key không được dài nổi bật
```

**Chống gợi ý độ dài:** nếu `len(key) > 1.3 × trung bình độ dài 3 distractor`, thử thay distractor ngắn nhất bằng ứng viên dài hơn còn lại trong pool. Không được thì gắn cờ `length_cue` để S7 sửa.

**Vì sao dùng dải tương đồng:** distractor quá xa đáp án (cosine thấp) thì hiển nhiên sai, câu thành dễ vô nghĩa. Quá gần (≥ 0.93) thì có nguy cơ cũng đúng. Dải theo độ khó biến "độ khó" từ một nhãn LLM tự gán thành một **tham số điều khiển được**.

### 7.8 S6: Kiểm tra

**S6a: 10 luật tất định (không tốn token, chạy trước judge):**

| # | Luật | Khi vi phạm |
|---|---|---|
| R1 | JSON hợp lệ theo schema | sửa JSON (một lần, đã có sẵn) |
| R2 | `evidence_quote` là chuỗi con nguyên văn của chunk bằng chứng (sau NFC + chuẩn hoá khoảng trắng) | sửa một lần, không được thì bỏ |
| R3 | 4 phương án khác nhau sau chuẩn hoá | thay distractor |
| R4 | Không có phương án cấm (`BANNED`) | thay distractor |
| R5 | Không gợi ý độ dài (như §7.7) | thay distractor, rồi mới đến sửa |
| R6 | Stem không chứa nguyên văn key (lộ đáp án) | sửa |
| R7 | Stem không phụ thuộc ngữ cảnh: không khớp `(?i)(đoạn (văn|trích) (trên|sau)|theo tài liệu|in the (passage|text) above)` | sửa |
| R8 | Phủ định trong stem phải được đánh dấu ("KHÔNG") | sửa |
| R9 | Không trùng: cosine(stem + key, mọi câu cùng LO trong `quiz_item_index` và trong lô hiện tại) < `dup_sim` (0.92) | bỏ, chuyển sang KU dự phòng |
| R10 | Độ dài: stem ≤ 400 ký tự, mỗi phương án ≤ 200; ngôn ngữ khớp tài liệu nguồn | sửa |

**S6b: judge (model khác, temperature 0), hai lần gọi:**

1. **Giải (J-solve):** judge nhận chunk bằng chứng, stem và 4 phương án **đã xáo theo một thứ tự khác** với thứ tự cuối cùng (tránh thiên vị vị trí), **không thấy đáp án**. Yêu cầu: chọn phương án đúng nhất **chỉ dựa trên tài liệu**, hoặc trả `AMBIGUOUS` (có hơn một phương án đúng) hay `NOT_IN_SOURCE`.
   - Chọn đúng key → sang J-rubric.
   - Ngược lại → sửa theo lý do judge đưa ra.
2. **Chấm rubric (J-rubric)**, chỉ chạy khi J-solve đúng, lần này được thấy đáp án. Trả JSON:
   `bloom_assessed` (1–6, kèm động từ minh chứng), `lo_alignment` (1–5), `distractor_verdicts[]` (mỗi distractor: `wrong` / `also_correct` / `unclear`), `issues[]` (gợi ý, phụ thuộc ngữ cảnh, ngữ pháp không khớp stem…).

**Luật chấp nhận:**

| Tình huống | Hành động |
|---|---|
| J-solve ≠ key, hoặc `AMBIGUOUS` / `NOT_IN_SOURCE` | sửa một lần theo lý do; vẫn trượt → **bỏ** |
| Một distractor bị đánh `also_correct` | **thay bằng ứng viên còn lại** (không gọi LLM), chạy lại J-solve; hết ứng viên → sửa |
| `bloom_assessed` < `bloom_target` | sửa một lần; vẫn thấp → với `quiz`: giữ, **lưu `bloom_level = bloom_assessed`**, gắn cờ `bloom_below_target`; với `midterm`/`final`: bỏ |
| `bloom_assessed` > mức của LO | bỏ (hỏi vượt LO) |
| `lo_alignment` ≤ 2 | bỏ |
| `issues` không rỗng | sửa một lần; vẫn còn → giữ, gắn cờ để người duyệt thấy |
| Judge lỗi (gọi hoặc parse hỏng) | thử lại một lần; vẫn lỗi → giữ câu với cờ `unverified` (**không** coi là qua) |

**Vì sao "giải trước, chấm sau":** khi đã thấy đáp án, model có xu hướng hợp lý hoá đáp án đó. Bắt judge tự giải trước thì phát hiện được câu có hai đáp án đúng hoặc đáp án sai. **Vì sao model khác:** giảm lỗi tương quan khi model tự chấm bài mình. Nếu chỉ cấu hình được một model thì vẫn chạy, nhưng log cảnh báo và gắn cờ `same_model_judge`.

### 7.9 S7: Sửa và sinh bù

```python
def generate_for_lo(lo, blueprint, spares, cfg, budget) -> list[ItemDraft]:
    accepted, queue = [], deque(blueprint.slots)
    attempts, limit = 0, blueprint.count * cfg.max_attempts_factor        # mặc định ×2
    while len(accepted) < blueprint.count and attempts < limit and budget.ok():
        slot = queue.popleft() if queue else blueprint.extra_slot(spares.pop()) if spares else None
        if slot is None:
            break
        attempts += 1
        item = run_slot(slot, cfg, budget)            # S4 → S5 → S6, tối đa cfg.max_repairs_per_item (1) lần sửa
        if item.accepted:
            accepted.append(item)
    return accepted
```

- **Sửa có mục tiêu:** prompt sửa chỉ chứa câu cũ, lý do cụ thể (từ luật R hoặc từ judge) và bằng chứng. Không sinh lại từ đầu.
- **Slot dự phòng** kế thừa Bloom/độ khó/vị trí của slot bị bỏ, nên phân bổ của blueprint vẫn được giữ.
- **Kết quả một phần:** lưu các câu được chấp nhận; request `SUCCEEDED` với `generated_count` < yêu cầu và `last_error = "partial: k/N — <lý do chính>"`.

### 7.10 S8: Lắp ráp và lưu

- **Thứ tự phương án:** key đặt ở `slot.key_position`; 3 distractor xếp ngẫu nhiên với seed = `slot_id`.
- **`correct_answer`** = text của key (khớp với cách core-api chấm).
- **`bloom_level`** = `bloom_assessed` của judge, kiểu INT (sửa D4).
- **`explanation`** = rationale + `"\n\nNguồn: “{evidence_quote}” ({heading_path}, tr. {page})"`.
- **`source_chunk_ids`** = chunk của KU (và chunk khác nếu judge dùng tới).
- **`quiz_id`** = `uuid5(NS, f"{request_id}:{lo_id}:{slot_index}")`. Câu lệnh SQL hiện tại đã có `ON CONFLICT (quiz_id) DO UPDATE`; thêm điều kiện `WHERE quiz_items.status = 'GENERATED_DRAFT'` để retry không ghi đè câu đã được duyệt (sửa O3).
- **Sau khi lưu:** upsert vector vào `quiz_item_index` để dùng cho kiểm tra trùng (R9) ở các lần sau.
- **Ghi usage** cho **mọi** lần gọi LLM: `status ∈ {'OK', 'ERROR', 'RATE_LIMITED'}` (viết hoa, sửa O2), kèm `prompt_tokens`, `completion_tokens`, `cost_usd` theo bảng giá cấu hình. `ILLMClient.generate` cần trả thêm `usage` (thêm `generate_with_usage()` để không phá chỗ khác).

### 7.11 S9: Vòng phản hồi

**Phân tích câu hỏi theo CTT** (chạy hằng đêm; chỉ tính **lần làm đầu tiên** của mỗi người học; cần ≥ `min_attempts` = 30):

| Chỉ số | Công thức | Cờ |
|---|---|---|
| Độ khó p | số lần đúng / số lần làm | `TOO_EASY` nếu p > 0.95; `TOO_HARD` nếu p < 0.20 (có thể sai đáp án) |
| Độ phân biệt r_pb | tương quan point-biserial giữa điểm câu (0/1) và năng lực người học (tỉ lệ đúng trên các câu **khác** của khoá học, cần ≥ 10 câu) | `LOW_DISC` nếu r < 0.10; `NEGATIVE_DISC` nếu r < 0 → ưu tiên duyệt lại |
| Hiệu quả distractor | tỉ lệ chọn từng phương án (từ `chosen_answer`); so nhóm 27% cao với 27% thấp | `NONFUNCTIONAL_DISTRACTOR` nếu < 5%; `MISKEY_SUSPECT` nếu nhóm cao chọn một distractor nhiều hơn chọn key |

Đây là các ngưỡng kinh nghiệm phổ biến của lý thuyết trắc nghiệm cổ điển, dùng làm giá trị khởi đầu.

- **Lưu:** bảng `quiz_item_stats(quiz_id, n, p_value, r_pb, option_shares JSONB, flags TEXT[], computed_at)`. Job chạy ở core-api (sở hữu DB) hoặc SQL view; chốt ở giai đoạn 3.
- **Hành động:** chỉ gắn cờ và xếp ưu tiên trong màn hình duyệt. **Không tự gỡ câu**; người quyết định.
- **Hiệu chỉnh độ khó:** so `difficulty_target` với độ khó thực (easy: p ≥ 0.8, medium: 0.5–0.8, hard: < 0.5) để chỉnh các dải ở §7.7.

**Tín hiệu từ người duyệt:**
- Tỉ lệ **duyệt không sửa**, tỉ lệ sửa, độ lớn chỉnh sửa (từ `review_audit_logs.raw_changes`), lý do reject. Tất cả nhóm theo `generation_meta.prompt_version` → **chỉ số chính** để so sánh phiên bản prompt.
- Giai đoạn 3: nút "Sinh lại" khi reject gửi request một slot kèm `replace_quiz_id` và lý do; lý do đi thẳng vào prompt sửa (sửa O4).

### 7.12 Đường enrichment

**Khuyến nghị: bỏ sinh quiz khỏi enrichment, chỉ giữ lesson card.** Lý do:
- quiz ở đường này không nhắm LO (LO được chọn theo chunk đầu tiên của section);
- không có kiểm tra;
- tốn token cho mọi tài liệu mới dù không ai cần;
- giảng viên đã có luồng yêu cầu quiz rõ ràng qua content generation.

Nếu chưa bỏ, tối thiểu phải:
1. Lỗi ở một section thì bỏ qua section đó và tiếp tục (sửa O1).
2. Không soft-delete bản nháp cũ nếu lần chèn mới ra 0 dòng.
3. Log số dòng thực sự được chèn.

---

## 8. Ngân sách và chi phí

Ước tính token cho **một câu được chấp nhận** (tiếng Việt khoảng 3.8 ký tự/token, theo số đo ở tài liệu chunk):

| Lần gọi | Đầu vào | Đầu ra | Ghi chú |
|---|---|---|---|
| S4 sinh câu | ~1800 | ~600 | hướng dẫn + Bloom ~1000, chunk ~450, LO/KU ~150 |
| S6 J-solve | ~1200 | ~100 | |
| S6 J-rubric | ~1600 | ~250 | chỉ khi J-solve đúng |
| S7 sửa (~30% số câu) | ~1500 | ~500 | trung bình ~0.3 lần mỗi câu |
| **Tổng / câu** | **~5000** | **~1100** | chưa tính trích KU (một lần mỗi chunk, có cache) |

So với hiện tại: với N = 5, cả lô tốn khoảng 10–12k token (≈ 2k/câu). **v2 ≈ 2.5–3 lần mỗi câu.** Đây là ước tính; con số thật sẽ có ngay khi O2 được sửa. Với model hạng flash thì mức này nhỏ, nhưng vẫn cần trần:

- `max_llm_calls_per_item` = 5 (sinh 1 + judge 2 + sửa 1 + dự phòng 1).
- `max_tokens_per_request` = mặc định 150k (≈ 20 câu × 6k + trích KU); vượt thì dừng sinh bù và trả kết quả một phần.

---

## 9. Cấu hình

Thêm namespace `quizgen` vào `WorkerSettings` (env theo quy ước nested `__`).

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `QUIZGEN__STRATEGY` | `v1` | `v1` \| `v2`: feature flag |
| `QUIZGEN__GENERATOR_MODEL` | = `LLM__MODEL` | model sinh câu |
| `QUIZGEN__GENERATOR_TEMPERATURE` | 0.6 | |
| `QUIZGEN__JUDGE_PROVIDER` / `QUIZGEN__JUDGE_MODEL` | (bắt buộc với v2) | khuyến nghị khác họ model với generator |
| `QUIZGEN__JUDGE_TEMPERATURE` | 0 | |
| `QUIZGEN__MAX_REPAIRS_PER_ITEM` | 1 | |
| `QUIZGEN__MAX_ATTEMPTS_FACTOR` | 2 | số slot tối đa = N × hệ số |
| `QUIZGEN__MAX_LLM_CALLS_PER_ITEM` | 5 | |
| `QUIZGEN__MAX_TOKENS_PER_REQUEST` | 150000 | |
| `QUIZGEN__LO_POOL_SIZE` | 30 | số chunk tối đa mỗi LO |
| `QUIZGEN__MAPPER_W_HEADING` / `_W_SEMANTIC` | 0.35 / 0.65 | hiệu chỉnh theo §11.4 |
| `QUIZGEN__KU_CHUNKS_PER_CALL` | 3 | |
| `QUIZGEN__MAX_KU_PER_CHUNK` | 2 | trong một lần chọn |
| `QUIZGEN__MMR_LAMBDA` | 0.7 | |
| `QUIZGEN__DUP_SIM` | 0.92 | ngưỡng trùng câu (R9) |
| `QUIZGEN__DISTRACTOR_DUP_SIM` | 0.93 | distractor gần key quá → loại |
| `QUIZGEN__DISTRACTOR_PAIRWISE_MAX` | 0.90 | |
| `QUIZGEN__DISTRACTOR_BANDS` | xem §7.7 | JSON |
| `QUIZGEN__ENABLED_TYPES` | `MCQ_SINGLE` | |
| `QUIZGEN__BLOOM_ALLOCATION` / `__DIFFICULTY_MIX` | xem §7.5 | JSON theo style |
| `QUIZGEN__STATS_MIN_ATTEMPTS` | 30 | |

Mọi ngưỡng tương đồng (0.92, 0.93, các dải) là **giá trị khởi đầu**, phải hiệu chỉnh trên dữ liệu thật với BGE-m3 trước khi bật v2 mặc định.

---

## 10. Thay đổi ngoài worker

**packages-ai**
- `HybridLoMapper` + nối vào cuối pipeline + script backfill (§7.2).
- `_bloom_level()` chấp nhận chuỗi số.
- `ILLMClient.generate_with_usage()`.
- Repository usage: chuẩn hoá `status` sang chữ hoa ở một chỗ duy nhất.

**core-api**
- Builder payload theo contract v1 (giải target thành `targets[]`); test validate theo schema.
- Từ chối `type='card'` cho tới khi được hỗ trợ.
- Màn hình duyệt: hiện `generation_meta.evidence`, cờ và thống kê câu hỏi (giai đoạn 2–3).
- Chuẩn hoá thứ tự mảng trong `canonical()` trước khi bật `MCQ_MULTI`.
- Migration: `quiz_items.generation_meta`, `quiz_items.difficulty`; sau đó `quiz_item_stats`.

**mcp-service**: API không đổi; chất lượng tự tăng nhờ mapping mới.

**contracts**: soạn v2 (thêm `style: midterm|final`, `difficulty_mix`, `replace_quiz_id`) khi cần (§13).

---

## 11. Kiểm thử và đánh giá

### 11.1 Unit test (phần tất định chiếm phần lớn logic)

`bloom.py` (bảng tương thích), `planner.py` (MMR tất định, phân bổ phần dư lớn nhất, `key_positions` cân bằng và không có chuỗi 3), `distractors.py` (từng luật loại; dải; đa dạng; chống gợi ý độ dài), `validators.py` (R1–R10 với ca dương và ca âm), `assembler.py` (`quiz_id` ổn định, thứ tự phương án theo seed), `item_stats.py` (p, r_pb, tỉ lệ chọn phương án trên dữ liệu tay), `hybrid_lo_mapper.py` (regex mở rộng, min–max, floor).

### 11.2 Regression (mỗi lỗi ở §1.2 có một test)

- D1: sau khi tài liệu được index cho khoá học có đề cương → `chunk_lo_mappings` có dòng.
- D4: LO có `bloom_level = 4` (INT) → câu lưu `bloom_level = 4` (hoặc mức judge đánh giá), không phải 2.
- V2: câu bị judge loại sau khi hết lượt sửa → không được lưu.
- G3: 40 câu → mỗi vị trí đáp án chiếm từ 20% đến 30%.
- G6: LLM giả trả thiếu câu → có sinh bù; hết ngân sách → `generated_count` báo đúng.
- O2: một lần ghi usage → dòng hợp lệ với CHECK, token > 0.
- O3: chạy lại cùng request → không có `quiz_id` mới.
- O1 (nếu còn giữ quiz trong enrichment): một section lỗi → các section khác vẫn được lưu.

### 11.3 Test luồng với LLM giả

LLM giả trả kịch bản cố định cho từng vai trò (generator, judge, repair), kiểm các nhánh:
- chấp nhận ngay;
- thay distractor không cần LLM;
- sửa một lần rồi đạt;
- sửa rồi vẫn trượt → sinh bù từ KU dự phòng;
- judge lỗi → cờ `unverified`;
- vượt ngân sách → kết quả một phần.

### 11.4 Đánh giá offline

- **Bộ dữ liệu:** 3–5 khoá học thật, 30–50 LO, 4 câu mỗi LO, cho cả v1 và v2 (≈ 300–400 câu).
- **Chấm mù bởi 2 người** (giảng viên/trợ giảng), thang 1–5 cho: đúng/sai, một đáp án đúng duy nhất, bám LO, đúng Bloom, distractor hợp lý, rõ ràng. Đo độ đồng thuận giữa hai người (Cohen's κ).
- **Hiệu chỉnh judge:** so phán quyết của judge với người chấm trên 100 câu. Nếu đồng thuận thấp thì chỉnh rubric/model trước khi tin judge.
- **Hiệu chỉnh mapper:** 20 LO × top 30 chunk được gán nhãn → chọn trọng số, floor theo F1.
- **Chỉ số tự động:** tỉ lệ qua từng luật; tỉ lệ trùng; độ phủ KU (số KU có câu / số KU trong kho); phân bố vị trí đáp án; token trên mỗi câu được chấp nhận; độ trễ.
- **Tiêu chí bật v2 mặc định:**
  - lỗi đúng/sai do người chấm phát hiện ≤ 2%;
  - điểm "distractor hợp lý" và "đúng Bloom" cao hơn v1 có ý nghĩa;
  - 0 câu thiếu trích dẫn hợp lệ;
  - vị trí đáp án lớn nhất ≤ 35%;
  - token/câu nằm trong ngân sách.

### 11.5 Chỉ số online và truy vấn xác minh hiện trạng

- **Chỉ số chính:** tỉ lệ duyệt không sửa theo `prompt_version`. Kèm theo: tỉ lệ reject và lý do, thời gian duyệt mỗi câu, các cờ ở S9.
- **Truy vấn kiểm tra hiện trạng** (chạy được ngay trên DB hiện tại):

```sql
-- D1: có mapping nào không?
SELECT count(*) FROM chunk_lo_mappings;

-- D4: phân bố bloom_level của các câu đã sinh (kỳ vọng hiện tại: gần như toàn 2)
SELECT bloom_level, count(*) FROM quiz_items WHERE deleted_at IS NULL GROUP BY 1 ORDER BY 1;

-- G3: phân bố vị trí đáp án đúng
SELECT o.idx - 1 AS key_position, count(*)
FROM quiz_items q,
     jsonb_array_elements_text(q.options) WITH ORDINALITY AS o(val, idx)
WHERE q.type = 'MCQ_SINGLE' AND q.deleted_at IS NULL AND to_jsonb(o.val) = q.correct_answer
GROUP BY 1 ORDER BY 1;

-- O2: có dòng usage nào của quiz không?
SELECT use_case, status, count(*) FROM llm_usage_logs GROUP BY 1, 2;
```

---

## 12. Kế hoạch triển khai

**Giai đoạn 0: sửa nền, không cần v2 — ĐÃ LÀM (2026-09-24)**
- [ ] Chạy các truy vấn §11.5 để chốt hiện trạng. **Chưa làm**: cần DB dev có dữ liệu thật; các mục dưới được kiểm chứng trên Postgres 18 dựng tạm.
- [x] Nối `MapChunksToLosUseCase` vào cuối `RunPipelineUseCase` + backfill (D1). `run_pipeline.py::_map_chunks_to_los_best_effort` chạy sau khi index xong, lấy `course_id` từ `get_document_context`; hỏng thì cảnh báo chứ không huỷ lượt. Backfill: `packages-ai/scripts/backfill_chunk_lo_mappings.py`. Kiểm chứng end-to-end trên Postgres thật ở `tests/integration/test_chunk_lo_mapping.py`.
- [x] Mở rộng regex chương (một phần D2). Nhận "Chương/Chuong/Chapter/Bài/Lecture/Tuần/Buổi/Unit"; "3.6 Bước 4" vẫn không bị coi là chương. Phần còn lại của D2 (map theo embedding) thuộc giai đoạn 1.
- [x] Sửa `bloom_level` (D4): quy đổi gom về `domain/bloom.py`, nhận cả `3`, `"3"`, `"analyze"`, `"Phân tích"`; không còn mặc định âm thầm về 2. Use case giữ tách bạch tên (cho prompt) và số (cho cột).
- [x] Usage `status` + token (O2): `status` viết hoa đúng CHECK; `ILLMClient.generate_with_usage` trả `LLMUsage`, cả Gemini lẫn `ai_runtime` đều đã nối; lần gọi sửa JSON cũng được tính.
- [x] Không lưu câu còn bị verifier loại sau khi hết lượt (V2). `_verify_and_refine` trả `(giữ, loại)`; loại hết thì request báo lỗi thay vì lưu câu đã biết là sai.
- [x] Xáo đáp án với vị trí cân bằng (G3) qua `application/services/answer_layout.py`, tất định theo `quiz_id`. `quiz_id` tất định `uuid5(namespace, lo_id|question)` và `ON CONFLICT … WHERE quiz_items.status = 'GENERATED_DRAFT'` (O3) nên retry không ghi đè câu đã duyệt.
- [x] Enrichment: bỏ qua section lỗi thay vì dừng cả tài liệu (O1). Mọi section đều hỏng thì mới dừng, để không ghi đè nội dung đang có bằng rỗng.
- [x] Test regression: `worker/tests/unit/test_quizgen_phase0.py` (20), bổ sung trong `test_run_pipeline.py` (D1) và `test_run_enrichment.py` (O1), `packages-ai/tests/integration/test_chunk_lo_mapping.py` (5).

**Ghi chú khi triển khai giai đoạn 0**

- `chunk_lo_mappings` có thêm `source` và `provenance`; cạnh do mapper sinh ra là `inferred`, và cạnh giảng viên đã xác nhận (`confirmed`) không bị hạ cấp khi chạy lại pipeline.
- Quan hệ chương ↔ LO nay đọc từ bảng `chapter_los` chứ không suy từ số đầu của mã LO, nên D2 "mọi LO cùng chương nhận toàn bộ chunk của chương" chỉ còn đúng với các LO mà đề cương thật sự gắn vào chương đó.
- Bloom mặc định "understand" vẫn còn, nhưng chỉ khi LO không có Bloom **và** request không chỉ định; trường hợp đó được ghi log riêng (`bloom_defaulted`) thay vì im lặng.

**Giai đoạn 1: v2 sau flag**
- [ ] Contract v1 end-to-end (core-api builder + worker parser + test schema).
- [ ] `HybridLoMapper` + hiệu chỉnh.
- [ ] Trích KU + Qdrant `knowledge_units`; planner (MMR + blueprint).
- [ ] Generator, distractor selector, validator, judge (client thứ hai), vòng sửa/sinh bù, ngân sách.
- [ ] `quiz_item_index` cho chống trùng.
- [ ] Unit test và test luồng với LLM giả.

**Giai đoạn 2: đánh giá và chuyển đổi**
- [ ] Đánh giá offline §11.4.
- [ ] Migration `generation_meta`, `difficulty`; màn hình duyệt hiện trích dẫn và cờ.
- [ ] Bật `QUIZGEN__STRATEGY=v2`; quyết định về quiz trong enrichment (§7.12).

**Giai đoạn 3: vòng phản hồi và mở rộng**
- [ ] `quiz_item_stats` + job hằng đêm + cờ trong màn hình duyệt.
- [ ] Nút "Sinh lại" khi reject.
- [ ] `TRUE_FALSE`, `MCQ_MULTI` (sau khi sửa `canonical()`); cân nhắc `FILL_BLANK` với cách so khớp mềm.
- [ ] Contract v2 cho `midterm`/`final`.

---

## 13. Rủi ro và câu hỏi mở

| # | Vấn đề | Đề xuất |
|---|---|---|
| R1 | Chi phí tăng ~2.5–3 lần mỗi câu | trần ngân sách; trích KU lười và có cache; đo thật sau khi sửa O2 rồi mới chốt |
| R2 | Judge khác model nhưng vẫn có lỗi tương quan | hiệu chỉnh với người chấm (§11.4); người duyệt vẫn là cổng cuối |
| R3 | Các ngưỡng cosine phụ thuộc model embedding | hiệu chỉnh trên BGE-m3; đổi model embedding thì phải hiệu chỉnh lại |
| R4 | Đổi mapping làm đổi kết quả của ai-tutor và mcp-service (cùng dùng `chunk_lo_mappings`) | coi như một thay đổi hành vi; chạy eval retrieval của tài liệu chunk song song |
| R5 | Trích KU lười làm lần sinh đầu tiên cho một LO chậm hơn | chấp nhận (job bất đồng bộ); có thể trích trước cho LO được yêu cầu nhiều |
| Q1 | Bỏ quiz khỏi enrichment? | khuyến nghị **bỏ** (§7.12); cần giảng viên xác nhận |
| Q2 | Contract v2 cho `midterm`/`final`, `difficulty_mix` | chỉ làm khi có nhu cầu thật; v1 đủ cho quiz ôn tập |
| Q3 | Bloom 5–6 với trắc nghiệm | giới hạn ở 5 dạng "chọn phương án tốt nhất"; mức 6 gắn cờ để giảng viên dùng đánh giá mở |
| Q4 | Kiểm tra "closed-book" (judge trả lời không có tài liệu) để phát hiện câu hỏi kiến thức phổ thông | tuỳ chọn ở giai đoạn 3; tốn thêm một lần gọi mỗi câu |
| Q5 | Chọn câu thích ứng theo người học | cần `quiz_item_stats` đủ dày trước; ngoài phạm vi tài liệu này |

---

## Phụ lục A: Ví dụ end-to-end

**Request:** khoá "Cơ sở dữ liệu", `targets = [{lo_code: "L.O.2.1", bloom_level: 2}]`, `count_per_lo = 4`, `style = quiz`.
L.O.2.1: *"Giải thích được các khái niệm siêu khoá, khoá, khoá chính và khoá ngoại trong mô hình quan hệ."*

Đây là ví dụ minh hoạ để làm rõ luồng xử lý; nội dung và điểm số là giả định, không phải output chạy thật.

**S1: kho nội dung.** Mapper lai chọn 18 chunk: 11 chunk thuộc "Chương 2" (h = 1) và 7 chunk có ŝ cao nằm ở phần bài tập cuối tài liệu. Mapper cũ sẽ bỏ sót 7 chunk này, và gán **cùng** 11 chunk kia cho cả L.O.2.2 (đại số quan hệ).

**S2: KU** (trích từ 12 chunk đầu, 4 lần gọi, lưu cache):

| KU | Loại | Mệnh đề |
|---|---|---|
| KU1 | definition | Siêu khoá là tập thuộc tính mà giá trị của nó xác định duy nhất mỗi bộ |
| KU2 | definition | Khoá là siêu khoá tối tiểu: bỏ bất kỳ thuộc tính nào thì không còn là siêu khoá |
| KU3 | comparison | Khoá chính là một khoá dự tuyển được chọn; các khoá dự tuyển khác vẫn là khoá |
| KU4 | definition | Khoá ngoại tham chiếu tới khoá chính của quan hệ khác *(đã có câu hỏi → nằm trong `covered`)* |
| KU5 | example | SINHVIEN(MSSV, CCCD, HoTen): MSSV và CCCD đều là khoá dự tuyển |
| KU6 | property | Thuộc tính của khoá chính không được nhận giá trị NULL |

**S3: blueprint** (N = 4, L = 2, style quiz):
- Bloom: 60% ở mức 2, 40% ở mức 1 (phần của mức 0 dồn lên mức 1) → theo phần dư lớn nhất: **2 câu mức 2, 2 câu mức 1**.
- Độ khó 40/40/20 → **2 easy, 1 medium, 1 hard**.
- Vị trí đáp án: hoán vị cân bằng `[2, 0, 3, 1]`.

| Slot | Bloom | Độ khó | Vị trí key | KU (MMR, lọc theo loại) |
|---|---|---|---|---|
| s1 | 2 | medium | 2 | KU3 (comparison) |
| s2 | 2 | easy | 0 | KU5 (example) |
| s3 | 1 | easy | 3 | KU2 (definition) |
| s4 | 1 | hard | 1 | KU1 (definition) |
| dự phòng | — | — | — | KU6 |

**S4–S6 với s1:**
- **Stem:** "Điểm khác nhau giữa khoá chính và các khoá dự tuyển khác của một quan hệ là gì?"
- **Key:** "Khoá chính là khoá dự tuyển được chọn làm định danh chính cho các bộ"
- **Ứng viên distractor:**
  - (a) "Khoá chính được phép chứa NULL, khoá dự tuyển thì không": đảo ngược luật NULL
  - (b) "Khoá dự tuyển luôn gồm nhiều thuộc tính, khoá chính chỉ một": nhầm về số thuộc tính
  - (c) "Một quan hệ có thể có nhiều khoá chính nhưng chỉ một khoá dự tuyển": đảo ngược bản số
  - (d) "Khoá chính là siêu khoá không cần tối tiểu": nhầm với siêu khoá
  - (e) "Hai khái niệm này hoàn toàn giống nhau"
  - (f) "Tất cả các phương án trên đều đúng"
- **S5:** (f) bị loại vì cấm; (e) có cosine 0.38, dưới dải medium (0.50–0.85), bị xếp sau. Chọn (a), (c), (d): đều trong dải, đôi một không gần trùng, độ dài tương đương key → qua R5.
- **S6:** R1–R10 qua. J-solve (thứ tự đã xáo khác) chọn đúng key. J-rubric: `bloom_assessed = 2` (so sánh/giải thích), `lo_alignment = 5`, 3 distractor đều `wrong` → **chấp nhận**.

**s4 (định nghĩa siêu khoá, độ khó hard):** dải hard (0.65–0.92) chọn ra các distractor rất gần key. Trong đó:
- "Tập thuộc tính tối tiểu xác định duy nhất mỗi bộ" là định nghĩa của *khoá*, sai với siêu khoá: một distractor tốt.
- "Tập thuộc tính xác định duy nhất mỗi bộ trong mọi trạng thái hợp lệ" thực chất là một cách phát biểu khác của định nghĩa siêu khoá.

J-solve vẫn chọn đúng key, nhưng J-rubric đánh phương án thứ hai là `also_correct`. → **Thay bằng ứng viên còn lại**, không gọi LLM → J-solve lại → chấp nhận.

**S8:** 4 câu được chấp nhận. `quiz_id` = uuid5 theo slot; key nằm ở các vị trí 2, 0, 3, 1; `bloom_level` = 2, 2, 1, 1; `generation_meta` chứa trích dẫn của từng câu.

**Chi phí:** 4 lần gọi trích KU (lần đầu, có cache) + 4 × 3 lần gọi (sinh + 2 judge) + 1 lần J-solve lại = **17 lần gọi**. Lần yêu cầu sau cho cùng LO không tốn 4 lần trích KU, và MMR sẽ tránh KU1, KU2, KU3, KU5 vì đã có câu.

---

## Phụ lục B: Bảng Bloom dùng trong prompt và planner

Theo thang Bloom sửa đổi (Anderson & Krathwohl, 2001).

| Mức | Tên | Người học làm được | Động từ (VI) | Mẫu stem | Loại KU phù hợp | Loại câu |
|---|---|---|---|---|---|---|
| 1 | Nhớ | nhận biết, nhắc lại | nêu, liệt kê, nhận biết, định nghĩa | "X là gì?"; "Thuật ngữ nào mô tả …?" | definition, fact, property | MCQ_SINGLE, TRUE_FALSE |
| 2 | Hiểu | giải thích, phân loại, so sánh, lấy ví dụ | giải thích, phân biệt, so sánh, phân loại, tóm tắt | "Điểm khác nhau giữa X và Y là gì?"; "Ví dụ nào minh hoạ đúng X?"; "Vì sao …?" | definition, comparison, example, cause_effect, principle | MCQ_SINGLE, TRUE_FALSE |
| 3 | Vận dụng | áp dụng quy trình vào tình huống mới | tính, áp dụng, thực hiện, sử dụng | "Cho R(A, B, C) và …, kết quả của … là?"; "Trong tình huống …, cần dùng …?" | procedure, formula, principle, example | MCQ_SINGLE, MCQ_MULTI |
| 4 | Phân tích | chia nhỏ, tìm quan hệ, chẩn đoán | phân tích, xác định nguyên nhân, phát hiện lỗi | "Lược đồ sau vi phạm dạng chuẩn nào, vì sao?"; "Câu SQL sau sai ở đâu?" | procedure, principle, comparison, cause_effect | MCQ_SINGLE (có tình huống), MCQ_MULTI |
| 5 | Đánh giá | phán đoán theo tiêu chí | đánh giá, chọn phương án tốt nhất, biện minh | "Thiết kế nào phù hợp nhất với yêu cầu … và vì sao?" | principle, comparison | MCQ_SINGLE dạng "tốt nhất" (giới hạn) |
| 6 | Sáng tạo | tạo ra sản phẩm mới | thiết kế, xây dựng, đề xuất | — | — | không phù hợp chấm tự động → hạ về 5 + cờ `bloom_capped` |

`BLOOM_KU_COMPAT` trong `bloom.py` chính là cột "Loại KU phù hợp".

---

## Phụ lục C: Truy vết lỗi → cách v2 xử lý

| Lỗi | Xử lý ở |
|---|---|
| D1 không có mapping | §7.2 (trigger + backfill); giai đoạn 0 |
| D2 mapper chỉ theo chương | §7.2 mapper lai |
| D3 lệch contract | §6.3 |
| D4 `bloom_level = 2` | §7.1, §7.10 |
| C1 thứ tự context tuỳ ý | §7.2 điểm liên tục + §7.4 MMR |
| C2 chỉ LO đầu tiên | §6.3 `targets[]`, §7.1 |
| C3 không phủ, trùng | §7.3 KU, §7.4 MMR, §7.8 R9 |
| G1 Bloom chỉ là con số | §7.5 blueprint, §7.6 hướng dẫn theo mức, §7.8 J-rubric, Phụ lục B |
| G2 distractor | §7.6 (6 ứng viên + misconception), §7.7 |
| G3 không xáo | §7.5 `key_positions`, §7.10 |
| G4 chỉ MCQ_SINGLE | §7.5 (giai đoạn 3) |
| G5 mất difficulty | §6.2 cột `difficulty`, §7.11 hiệu chỉnh |
| G6 thiếu câu | §7.9 sinh bù |
| V1 tự chấm | §7.8 judge khác model |
| V2 lưu câu bị loại | §7.8 luật chấp nhận, §4 nguyên tắc 3 |
| V3 thấy đáp án trước | §7.8 J-solve |
| O1 enrichment mất hết | §7.12 |
| O2 usage không được ghi | §7.10, §8 |
| O3 trùng khi retry | §7.10 `quiz_id` uuid5 + điều kiện ON CONFLICT |
| O4 reject không có vòng lại | §7.11 |
| O5 không dùng dữ liệu làm bài | §7.11 |
