# Thiết kế lại thuật toán chunk — `StructuralChunker` (v2)

| | |
|---|---|
| Trạng thái | Đã triển khai sau flag `structural`; chưa chuyển mặc định / chưa eval retrieval có nhãn |
| Ngày | 2026-09-21 |
| Phạm vi | `packages-ai` (chunker, parser PDF/DOCX/Markdown, Qdrant adapter, `PipelineCore`), `worker`, `document-inspector`, `ai-tutor` |
| Thay thế | `adapters/chunkers/heading_chunker.py` + `adapters/chunkers/toc_detector.py` |

---

## Ghi chú triển khai — 2026-09-23

Code đã có trong `packages-ai/src/document_chunk/adapters/chunkers/structural/`, wiring worker và cả hai endpoint inspect. Parser PDF/Markdown/DOCX/PPTX, payload/filter Qdrant, soft-delete Postgres, cleanup vector, tutor breadcrumb và giới hạn quiz context đã cập nhật. Giữ `heading` làm mặc định.

Các điều chỉnh sau review so với đề xuất bên dưới:

- **Không dùng fallback `len/2`**: thiếu tokenizer thật thì báo lỗi cấu hình. Ước lượng không thể bảo đảm G1 với Unicode. Token counting tắt truncation/padding trong tokenizer và đếm lại chuỗi render đầy đủ, kể cả separator/header.
- **Header bảng tự nó quá lớn**: không thể vừa lặp nguyên header vừa giữ trần cứng. Nhánh này giữ toàn bộ text và chia theo ngân sách, không lặp header; header thông thường vẫn lặp theo từng bảng (định danh bằng source block, không bằng nội dung header).
- **ID gồm cả heading path** để đổi heading mà giữ nguyên body vẫn tạo ID mới. UUID ổn định trong retry cùng document ID, nội dung và cấu trúc.
- **Dọn vector sau transaction Postgres thành công**. Transaction upsert + soft-delete + outbox giữ nguyên citation cũ; lỗi metadata không xóa vector cũ. Đây chưa phải transaction xuyên hai database. Các lượt re-index cùng document cần được tuần tự hóa bởi caller/queue.
- **Fail closed khi vi phạm invariant**, không âm thầm cắt bỏ dữ liệu. Target/min là mục tiêu mềm; trần content/embed được kiểm tra chính xác.
- **Cấu trúc nội bộ** dùng danh sách node theo pre-order và stack tổ tiên, giữ source run khi gộp. Không hứa O(n) tuyệt đối cho consolidation dùng thao tác danh sách; đo trên corpus trước khi tối ưu tiếp.
- Không cắt tiêu đề metadata xuống 150 ký tự vì có thể mất phân biệt giữa các heading dài; chỉ giới hạn breadcrumb gửi embedder theo token.

Bật thử nghiệm:

```dotenv
CHUNKER__STRATEGY=structural
CHUNKER__TOKENIZER_PATH=/app/bge-m3-tokenizer.json
```

Worker và inspector Dockerfile bake tokenizer BGE-m3 snapshot `5617a9f61b028005a4858fdac845db406aefb181`. Local có thể trỏ `TOKENIZER_PATH` tới `tokenizer.json` đã tải. Tokenizer/model và `embed_max_tokens`/`embedder.max_length` được kiểm tra khi tạo chunker ở container; với embedder gRPC cần giữ config phía service đồng bộ.

Inspector nhận `chunker=structural` ở `/documents/inspect/chunking`, trả p50/p95/max token, số vượt trần/dưới min, số block TOC bị loại và số merge. Strategy cũ cũng được đo bằng tokenizer đó khi có sẵn.

### Đầu vào PDF: đánh giá theo từng trang (2026-09-23)

Chunker chỉ chia đúng phần text nhận được; độ đúng và độ đầy đủ của đầu vào PDF là bước riêng. Điểm yếu đã sửa: việc chọn parser dựa trên câu hỏi "PyMuPDF có đọc được text không?", nên PDF 100 trang có 10 trang scan vẫn trả về **parse thành công** và 10 trang đó mất im lặng.

- **`pdf_page_assessment.py` (mới)**: đo từng trang rồi gắn status — `text`, `complex_layout` (nhiều cột phát hiện bằng rãnh dọc, hoặc có bảng theo `find_tables`), `needs_ocr` (thiếu text layer nhưng có ảnh/vector), `empty` (trang trắng thật). Header/footer chạy lặp bị bỏ **trước** khi đo, nên trang scan có số trang stamp sẵn không bị tính là "có text".
- **`PdfParser`**: trả kèm `metadata["page_report"]` (một dòng mỗi trang) và `metadata["coverage"]`; mỗi `Section` giữ `metadata["source"]` = parser + số trang + block + bbox để đối chiếu lại trên PDF. Mặc định `enforce_coverage=True` → Err khi còn trang chưa đọc được.
- **`AdaptivePdfParser`**: route theo trang. Docling chỉ chạy trên các khoảng trang cần (`parse_pages`, số trang tuyệt đối), gộp lại theo thứ tự trang; vượt `pdf_full_fallback_page_ratio` thì chạy một lần cho cả file. Ba kết cục phân biệt rõ: `unprocessed_pages` (chưa ai đọc → Err theo `pdf_strict_missing_text`, mặc định bật), `no_text_pages` (đã OCR, không có chữ → ghi nhận), `degraded_pages` (có text, layout chưa qua layout backend → cảnh báo). Backend lỗi giữa đường **không** được tính là "đã xử lý".
- **Ngân sách theo tài liệu** (`concurrency=1` chỉ chặn số tài liệu song song): `pdf_max_file_bytes` 256 MB, `pdf_timeout_seconds` 600 s kiểm tra ở biên mỗi trang, `pdf_max_pages` cũng áp cho Docling, `pdf_extract_images` **tắt mặc định** (chưa có consumer cho bytes ảnh) với trần `pdf_max_image_bytes`. Vượt hạn mức → `ParseBudgetExceededError` nêu rõ hạn mức nào.
- **Wiring**: container của `packages-ai` trước đây dùng Docling cho mọi PDF; nay dùng `AdaptivePdfParser` như worker và inspector. Metric `pdf_pages_total{status,backend}`; `PipelineCore` log `pipeline.parse_partial_coverage` khi coverage không `complete`.

Giới hạn còn lại: bảng chỉ được phát hiện qua đường kẻ (bảng dàn bằng khoảng trắng không bị gắn cờ); phát hiện cột chỉ trả lời "nhiều hơn một cột hay không", việc dựng lại thứ tự đọc vẫn do layout backend làm; ngưỡng (`pdf_min_page_chars`, `pdf_scan_image_coverage`) chưa hiệu chỉnh trên corpus thật; đường Docling thật (có model) chưa chạy trong lượt này — unit test dùng stub converter.

`packages-ai/scripts/evaluate_chunking.py` tính Recall@5/MRR@10 từ JSONL chứa ranked hits của hai strategy và heading kỳ vọng (schema nằm trong docstring script). Không coi root path rỗng là hit tự động. **Chưa có bộ 60–100 câu hỏi gán nhãn để quyết định rollout; chưa re-index dữ liệu thật.** Docker build và integration với Postgres/Qdrant dịch vụ thật chưa chạy trong lượt triển khai này.

---

## 0. Tóm tắt

- **Giữ triết lý cũ** (chunk theo cấu trúc heading) nhưng xây lại trên ba nền mới: **đo bằng token của chính BGE-m3**, **xử lý trên cây section thay vì danh sách phẳng**, và **một tập bất biến có test**.
- **Trần cứng:** không chunk nào vượt 512 token nội dung, và `embedding_input` không bao giờ vượt 1024 token (giới hạn của embedder). Hiện tại một bảng 8197 ký tự thành **1 chunk 3212 token**, embedder cắt ở 1024 nên **~68% bảng không được embed** nhưng vẫn được lưu và trả về.
- **Bảng, danh sách, code là đơn vị có cấu trúc:** bảng cắt theo hàng và lặp header, danh sách cắt theo item, code cắt theo dòng. Không bao giờ cắt giữa hàng hay giữa từ.
- **Gộp section nhỏ theo luật LCP** (tiền tố chung dài nhất của `heading_path`): chunk gộp mang path của tổ tiên chung và giữ tiêu đề con inline trong nội dung. Luật này thay cho phép so sánh `heading_path[:-1]` đang gộp nhầm Chương 1 với Chương 2.
- **Mục lục mặc định không index.** Cờ `importance_score=0.1` hiện tại không được lưu ở tầng nào nên chưa bao giờ có tác dụng. TOC detector được siết lại để không nuốt nhầm danh sách "Mục tiêu học tập".
- **ID chunk tất định (`uuid5`)** để BullMQ retry không sinh point mồ côi trong Qdrant.
- **Target 400 token ≈ 1500 ký tự văn xuôi tiếng Việt** (đo thực tế, §3), nên độ mịn retrieval gần như giữ nguyên và không phải chỉnh lại `top_k`.
- **Ba sửa lỗi parser là điều kiện tiên quyết.** Quan trọng nhất: `PdfParser` đang **làm rơi mọi span < 10 ký tự**, tức là từ in đậm hoặc in nghiêng ngắn nằm giữa câu biến mất.
- **Triển khai sau feature flag** `CHUNKER__STRATEGY`, so sánh song song qua `document-inspector`, và chạy eval retrieval trước khi đổi mặc định.

---

## 1. Hiện trạng

### 1.1 Luồng hiện tại

```
worker (BullMQ) ─► RunPipelineUseCase ─► PipelineCore.run()
                                          ├─ parse    AdaptivePdfParser (PyMuPDF → Docling) / Docx / Pptx / Markdown
                                          ├─ chunk    HeadingChunker (max 1500 ký tự, min 100, overlap 200)
                                          ├─ embed    BGE-m3 (in-process hoặc embedding-service), max_length=1024
                                          ├─ upsert   Qdrant
                                          └─ persist  Postgres chunks + outbox HEADING_GRAPH_PROJECT → Neo4j
```

### 1.2 Lỗi đã tái hiện

Các lỗi dưới đây đã được **chạy thật** bằng `.venv` của `packages-ai`, với `ParsedDocument` và PDF dựng tay; không sửa code repo. P-d là kết luận từ đọc code, chưa chạy.

**Chunker và các tầng lưu trữ:**

| # | Vị trí | Lỗi | Bằng chứng | Hệ quả |
|---|---|---|---|---|
| C1 | `heading_chunker.py:127` | Mục lục ở đầu tài liệu mất nhãn TOC | detector trả `[0, 1]`, chunk ra `content_type=None` | TOC lẫn vào kết quả search như nội dung thường |
| C2 | `heading_chunker.py:332-335` | Gộp chunk nhỏ xuyên chương | chunk `path=('Chương 1',)` chứa nội dung Chương 2 | metadata sai; heading "Chương 2" biến mất khỏi index; LO mapper map sai chương |
| C3 | `heading_chunker.py:299-306` | Không có trần cứng | bảng 8197 ký tự → 1 chunk 3212 token | embedder cắt ở 1024 → ~68% bảng không được embed nhưng vẫn được lưu và trả về |
| C4 | `heading_chunker.py:303-304` | Overlap dính chữ, bắt đầu giữa câu | `"...khac nhau.Day la..."` | nhiễu embedding, text hiển thị lỗi |
| C5 | `qdrant_adapter.py:239-257`, `_pipeline_core.py:246-262` | `content_type`, `importance_score` không được lưu vào Qdrant, Postgres hay outbox | payload không có hai key này | cơ chế hạ điểm TOC chưa từng chạy end-to-end |
| C6 | `ai-tutor/.../service.py:47-50` | Prompt LLM chỉ có `chunk.content`, không có heading | `f"[{index}] {chunk.content}"` | LLM không biết đoạn trích thuộc mục nào |
| C7 | `heading_chunker.py:265`; outbox `attempts: 5` | ID `uuid4` mới mỗi lần chạy | worker `raise` khi pipeline lỗi → BullMQ retry | lỗi xảy ra sau bước upsert Qdrant (ví dụ lúc ghi Postgres) → retry sinh bộ point mới, bộ cũ mồ côi trong Qdrant |

**Parser (đầu vào của chunker):**

| # | Vị trí | Lỗi | Bằng chứng |
|---|---|---|---|
| P-a | `pdf_parser.py:141` | Lọc `len < 10` áp dụng cho **từng span**, trong khi PyMuPDF tách span mỗi khi đổi font | PDF "He quan tri **CSDL** la phan mem…" → parse ra `"He quan tri la phan mem…"`: mất "CSDL" |
| P-b | `pdf_parser.py:208` | Mọi span giữa hai heading nối bằng `" "` thành một section | mất ranh giới đoạn; nhánh tách `\n\n` của chunker không bao giờ chạy với PDF có text |
| P-c | `toc_detector.py:21`, `:76-97` | Hai tín hiệu yếu (nằm đầu tài liệu + nhiều dòng ngắn) đã đủ ngưỡng TOC | danh sách "Mục tiêu học tập" 5 dòng bị đánh dấu TOC |
| P-d | `markdown_parser.py:79-102` | Không theo dõi code fence; bảng và list đều thành `PARAGRAPH` | dòng `# comment` trong khối code Python bị hiểu là heading (đọc code, chưa chạy) |

### 1.3 Nguyên nhân gốc

1. **Đơn vị đo sai.** Chunker đo bằng ký tự trong khi giới hạn thật (embedder) tính bằng token; bảng dày token gấp ~1.7 lần văn xuôi. → C3
2. **Xử lý tuyến tính trên danh sách phẳng.** Quan hệ cha–con giữa các heading chỉ tồn tại trong một stack tạm; bước merge sau đó phải đoán lại quan hệ từ `heading_path[:-1]`. → C2
3. **Mọi thứ đều là text.** Bảng, list, code bị đối xử như văn xuôi. → C3
4. **Không có bất biến, không có test riêng.** `HeadingChunker` chỉ xuất hiện như baseline trong `test_llamaindex_chunkers.py`. → C1–C4 lọt CI
5. **Metadata không đi end-to-end.** Chunker sinh field mà không tầng nào lưu. → C5

---

## 2. Ràng buộc từ hệ thống (không được phá)

| Ràng buộc | Ai phụ thuộc | Hệ quả cho thiết kế |
|---|---|---|
| `heading_path` là đường dẫn phân cấp thật, đóng theo tiền tố | Neo4j dựng cây `Heading` với id `document_id:level:path[:level]` (`neo4j_graph_store.py:243-244`); LO mapper tách số chương từ path (`heuristic_lo_mapper.py:21-40`); enrichment nhóm chunk liên tiếp theo path (`run_enrichment.py:309`) | chunk gộp phải mang path của **tổ tiên chung**, không được mượn path của một phần |
| `chunk_index` liên tục `0..n-1` theo thứ tự đọc | Postgres `sort_order`, cạnh `NEXT` trong Neo4j | chỉ đánh số ở bước cuối, sau khi gộp |
| Bảng `chunks` do Prisma của core-api sở hữu, chỉ có `content, heading_path, page_number, sort_order, language` | `core-api/prisma/migrations/0_init/migration.sql:179` | field mới đi vào payload Qdrant (schemaless) trước; migration Postgres là bước tuỳ chọn |
| Embedder cắt ở 1024 token | `infrastructure/config.py:150`, `embedding-service/.../config.py:45` | trần cứng phải tính cả breadcrumb và overlap |
| Quiz context cắt mỗi chunk ở 1600 ký tự; sinh quiz tổng 6000 ký tự | `retrieve_quiz_context.py:58`, `generate_curriculum_quiz.py:116` | chunk 512 token (~1950 ký tự tiếng Việt) sẽ bị cắt → phải nâng giới hạn (§11.4) |
| `IChunker.chunk(ParsedDocument) -> Result[list[Chunk]]` | `PipelineCore`, inspector | giữ nguyên interface |
| Worker chạy CPU, batch embed đã phải hạ xuống 4 để tránh OOM | `infrastructure/config.py:147-149` | không nạp thêm model; chỉ nạp tokenizer (~17 MB) |
| `dcmh_extractor` đọc thẳng `ParsedDocument`, không đọc chunk | `dcmh_extractor.py:126-131` | bỏ TOC khỏi chunk không ảnh hưởng trích xuất đề cương |
| `source_chunk_ids` của nội dung sinh ra và `chunk_lo_mappings` tham chiếu `chunk_id` | `run_enrichment.py:113-114`, `migration.sql:194` | re-index phải **soft-delete** chunk cũ (không xoá cứng) và chạy lại mapping |

---

## 3. Số liệu đo

Tokenizer `BAAI/bge-m3` (`XLMRobertaTokenizerFast`). Corpus: các chương luận văn trong `report/lvtn` (tiếng Việt) và `report/lvtn_en` (tiếng Anh), lấy các đoạn ≥ 300 ký tự sau khi bỏ lệnh LaTeX.

| Loại văn bản | Số đoạn | Ký tự/token (median) | p10 | min | 1500 ký tự ≈ |
|---|---|---|---|---|---|
| Văn xuôi tiếng Việt | 347 | 3.82 | 3.26 | 2.46 | 425 token (max 499) |
| Văn xuôi tiếng Anh | 316 | 4.31 | 3.57 | 2.72 | 388 token (max 423) |
| Bảng markdown tiếng Việt | — | 2.23 | — | — | 674 token |

Tốc độ: tokenize 40081 ký tự mất ~30 ms trên máy dev, không đáng kể so với parse và embed.

**Kết luận:**
- Với văn xuôi, mức 1500 ký tự hiện tại thực ra hợp lý (~425 token). Vấn đề nằm ở **phần đuôi phân phối**: không có trần, và bảng/code dày token hơn nhiều.
- `target = 400 token` giữ nguyên độ mịn retrieval hiện tại. `max = 512` chừa gần một nửa ngân sách 1024 cho breadcrumb và overlap.

---

## 4. Mục tiêu và phạm vi

**Mục tiêu** (mỗi mục có test tương ứng ở §12):

| # | Mục tiêu |
|---|---|
| G1 | **Trần cứng**: `tokens(content) ≤ 512` và `tokens(embedding_input) ≤ 1024 − 2` với mọi chunk, trong mọi trường hợp đầu vào |
| G2 | **Không vượt ranh giới heading**, trừ khi gộp theo luật LCP, và khi đó path luôn đúng |
| G3 | **Hiểu cấu trúc**: bảng, list, code, caption được cắt theo đơn vị tự nhiên của chúng |
| G4 | **Không mất, không lặp nội dung** trong `content` (ngoại lệ có chủ đích: header bảng lặp lại, tiêu đề con inline) |
| G5 | **Tất định và idempotent**: cùng input → cùng chunk, cùng ID |
| G6 | **Metadata downstream cần thì phải được lưu** end-to-end |
| G7 | **Chi phí O(n)** theo số token, không thêm model |

**Không làm:**
- **Semantic chunking bằng embedding từng câu**: phải embed từng câu trên worker CPU, bỏ mất heading, không có trần cứng.
- **LLM chunking / contextual retrieval**: để sau (§14).
- **Hybrid search với sparse vector của BGE-m3**: ngoài phạm vi, nhưng thiết kế này không cản trở.
- **Viết lại parser**: chỉ sửa tối thiểu những gì chunker cần (§11.1).

---

## 5. Các phương án đã cân nhắc

| Phương án | Ưu | Nhược | Kết luận |
|---|---|---|---|
| A. Vá 4 bug trong `HeadingChunker` | nhanh (~50 dòng) | nguyên nhân gốc 1–3 còn nguyên | chỉ làm như hotfix nếu v2 cần hơn 2 tuần |
| B. LlamaIndex `SentenceSplitter` trong từng nhóm heading (đã có trong inspector) | ít code | không hiểu bảng/list; không gộp theo cây; mặc định đếm token bằng tiktoken chứ không phải tokenizer BGE-m3; kéo thêm llama-index vào worker | không |
| C. `SemanticSplitterNodeParser` | ranh giới theo chủ đề | embed từng câu trên CPU; bỏ heading; không có trần cứng (docstring của chính class đã ghi) | không |
| **D. `StructuralChunker` v2** (tài liệu này) | giải quyết cả 5 nguyên nhân gốc; kiểm soát hoàn toàn | nhiều code hơn (~800–1000 dòng + test) | **chọn** |

---

## 6. Tổng quan kiến trúc

### 6.1 Sáu pha

```
ParsedDocument.sections                (danh sách phẳng từ parser)
        │
  A. Normalize     NFC, khoảng trắng, placeholder ảnh, nhận dạng lại loại block (bảng/list/code)
        │
  B. Build tree    heading stack → cây SectionNode; lọc heading giả và heading lặp; đánh dấu TOC
        │
  C. Segment       mỗi block → các Unit nguyên tử theo loại (đoạn→câu→từ, hàng bảng, item, dòng code)
        │
  D. Pack          gom Unit trong CÙNG MỘT node → DraftChunk; chia cân bằng; trần cứng
        │
  E. Consolidate   gộp DraftChunk nhỏ với hàng xóm theo luật LCP; chèn tiêu đề con inline
        │
  F. Emit          đánh số, ID tất định, embedding_input (+ overlap), metadata, kiểm bất biến
        ▼
list[Chunk]
```

Ý tưởng cốt lõi: **pha D chỉ làm việc bên trong một node**, nên chunk không thể vượt ranh giới heading một cách vô tình. Việc vượt ranh giới chỉ xảy ra ở **pha E**, qua một luật duy nhất (LCP) được kiểm chứng.

### 6.2 Bố cục module

```
packages-ai/src/document_chunk/adapters/chunkers/structural/
├── __init__.py        StructuralChunker(IChunker): điều phối 6 pha
├── tokens.py          TokenCounter (tokenizer BGE-m3 + fallback)
├── normalize.py       Pha A
├── tree.py            Pha B: SectionNode, build_tree, heading guard
├── toc.py             TOC detector v2 (thay adapters/chunkers/toc_detector.py)
├── segment.py         Pha C: splitter theo loại + tách câu tiếng Việt
├── pack.py            Pha D
├── consolidate.py     Pha E
└── emit.py            Pha F + kiểm bất biến
```

Config thêm vào `ChunkerConfig` trong `infrastructure/config.py`, cùng namespace `chunker` (§10).

---

## 7. Mô hình dữ liệu

### 7.1 Kiểu nội bộ (private trong package `structural`)

```python
class BlockKind(str, Enum):
    PROSE = "text"
    LIST = "list"
    TABLE = "table"
    CODE = "code"
    CAPTION = "caption"   # chú thích ảnh/bảng: luôn dính vào block kề bên
    NOTES = "notes"       # speaker notes của PPTX
    TOC = "toc"


@dataclass(frozen=True)
class Block:
    """Một Section đã chuẩn hoá: kết quả pha A."""
    kind: BlockKind
    text: str
    page: int | None
    images: tuple[str, ...]
    source_index: int                 # vị trí Section gốc, dùng để debug và tính offset


@dataclass(frozen=True)
class Unit:
    """Đơn vị nguyên tử: pha D không được cắt nhỏ thêm."""
    kind: BlockKind
    text: str
    tokens: int
    page: int | None
    images: tuple[str, ...]
    joiner: str                       # "\n\n" giữa đoạn/block, "\n" giữa hàng/item/dòng code, " " giữa câu
    starts_block: bool                # unit đầu tiên của một block (ranh giới tốt để cắt)
    glue_next: bool = False           # không được cắt ngay sau unit này (câu dẫn "…sau:", caption bảng)
    table_header: str | None = None   # hàng bảng: header để lặp lại khi bảng bị chia


@dataclass
class SectionNode:
    title: str | None                 # None cho node gốc
    level: int                        # heading level thật (1–6); gốc = 0
    path: tuple[str, ...]             # tiêu đề từ gốc tới node này
    blocks: list[Block]               # nội dung trực tiếp, trước heading con đầu tiên
    children: list["SectionNode"]
    ordinal: int                      # thứ tự duyệt pre-order, dùng cho section_id


@dataclass
class Run:
    """Các unit liên tiếp có cùng path gốc bên trong một DraftChunk."""
    path: tuple[str, ...]
    units: list[Unit]
    starts_node: bool                 # run này mở đầu node của nó (cần tiêu đề inline khi bị gộp)


@dataclass
class DraftChunk:
    path: tuple[str, ...]             # sau pha E: LCP của mọi run.path
    level: int
    runs: list[Run]
    node_ordinal: int
    part_index: int                   # vị trí trong node bị chia (0-based)
    part_count: int
    is_toc: bool = False
```

### 7.2 `ChunkMetadata`

Mọi field mới đều optional, nên `Chunk` cũ và code đọc payload cũ vẫn chạy.

| Field | Hiện tại | v2 |
|---|---|---|
| `heading_path` | path tại lúc mở buffer | LCP của mọi nội dung trong chunk |
| `heading_level` | level của heading mở buffer | level thật của node cuối trong path (0 = gốc) |
| `page_number` | trang đầu tiên | `= page_start` (giữ để tương thích) |
| `page_start`, `page_end` | — | **mới** |
| `content_type` | chỉ `"toc"` | `text` / `list` / `table` / `code` / `mixed` / `toc` |
| `token_count` | không gán | số token của `content` (BGE-m3) |
| `char_count` | chỉ LlamaIndex chunker gán | luôn gán |
| `section_id` | không gán | `uuid5(document_id, "/".join(path) + ordinal)` của node |
| `part_index`, `part_count` | — | **mới**: vị trí khi một node bị chia thành nhiều phần |
| `chunker_version` | — | **mới**: `"structural-v2"` |
| `importance_score` | 0.1 cho TOC | bỏ dùng (TOC không index mặc định) |

### 7.3 Ba "góc nhìn" văn bản

| Trường | Dùng cho | Nội dung |
|---|---|---|
| `content` | hiển thị, Postgres, quiz, LO mapping, hash | thân chunk + tiêu đề con inline (nếu gộp) + header bảng (nếu là phần tiếp của bảng). **Không** có breadcrumb, **không** có overlap |
| `embedding_input` | chỉ để embed | `breadcrumb` + `overlap` (nếu có) + `content` |
| Prompt LLM (ai-tutor) | sinh câu trả lời | `"[i] (breadcrumb · tr. X)\n" + content`, sửa ở phía consumer (§11.4) |

Vì sao không nhét breadcrumb vào `content`: `content` được dùng cho hash, quiz, LO mapping và hiển thị; breadcrumb sẽ bị lặp ở mọi chunk. Cách đúng là consumer tự render breadcrumb từ `heading_path` (đã có sẵn trong payload và trong citation của ai-tutor).

### 7.4 Payload Qdrant

Thêm key: `content_type`, `token_count`, `page_start`, `page_end`, `section_id`, `part_index`, `part_count`, `chunker_version`.
Tạo thêm payload index `KEYWORD` cho `content_type` và `chunker_version`. `create_payload_index` chạy được trên collection đã tồn tại, nên không cần tạo lại collection.

Postgres **không đổi schema ở giai đoạn 1**: các cột hiện có đã đủ cho mọi consumer đang chạy.

---

## 8. Đếm token

```python
class TokenCounter:
    """Đếm token bằng đúng tokenizer của embedder. Chỉ nạp tokenizer.json, không nạp model."""

    def __init__(self, cfg: ChunkerConfig) -> None:
        # Dùng thư viện `tokenizers` (Rust); đã có trong worker qua transformers ← FlagEmbedding.
        # Nguồn: CHUNKER__TOKENIZER_PATH (bake sẵn vào image) → HF id CHUNKER__TOKENIZER → fallback.
        ...

    def count(self, text: str) -> int: ...              # add_special_tokens=False, có LRU cache
    def count_many(self, texts: list[str]) -> list[int]: ...   # encode_batch
```

**Tính cộng dồn.** SentencePiece gần như cộng được tại ranh giới khoảng trắng: `tok(a + " " + b) ≈ tok(a) + tok(b)`, sai lệch ±1. Pha D dùng tổng cộng dồn cộng chi phí joiner cho nhanh. **Pha F đếm lại chính xác** từng chunk; nếu vượt trần thì chia lại chunk đó. Vòng này chắc chắn dừng vì mức cắt thấp nhất (cắt theo từ) luôn tạo được mảnh ≤ trần.

**Fallback** khi không tải được tokenizer: `ceil(len(text) / 2.0)`. Ước lượng này dư so với mọi tỉ lệ đo được ở §3 (thấp nhất 2.23 với bảng), nên an toàn với tài liệu VI/EN. Văn bản CJK hoặc nhiều emoji có thể dưới 2 ký tự/token; khi đó embedder vẫn là lớp chặn cuối. Khi fallback thì log `chunker.tokenizer_fallback` và tăng metric.

**Kiểm tra lúc khởi động.** `CHUNKER__TOKENIZER` phải trùng model của embedder, và `max_tokens + header_max_tokens + overlap_tokens + 2 ≤ embed_max_tokens` (mặc định 512 + 64 + 48 + 2 = 626 ≤ 1024). Sai thì raise lỗi cấu hình ngay khi khởi động, không đợi tới lúc xử lý tài liệu.

---

## 9. Chi tiết thuật toán

### 9.1 Pha A: Normalize

| # | Quy tắc | Lý do |
|---|---|---|
| A1 | Unicode **NFC** cho mọi text | PDF có thể trả tiếng Việt dạng tổ hợp (NFD); LO mapper so khớp bằng `w in heading_lower`, và hash/dedupe đều phụ thuộc dạng chuẩn |
| A2 | `\r\n` → `\n`; gộp khoảng trắng liên tiếp trong văn xuôi; **giữ nguyên** xuống dòng trong bảng, list, code | giữ cấu trúc cho pha C |
| A3 | Nối gạch nối cuối dòng của PDF: `([a-zà-ỹ])-\n([a-zà-ỹ])` → `\1\2` | "infor-\nmation" |
| A4 | Section ảnh có nội dung là placeholder (`"[Image]"`, rỗng): **không tạo block text**, chuyển `images` sang block trước đó trong cùng node (không có thì sang block sau) | chuỗi `"[Image]"` của Docling hiện đang bị embed như nội dung |
| A5 | Nhận dạng lại loại block khi parser trả `PARAGRAPH`/`UNKNOWN` (xem dưới) | parser Markdown và PDF không đánh dấu bảng/list |
| A6 | Bỏ block nhiễu: `^\s*(\d+\|[ivxlcdm]+\|Trang \d+\|Page \d+( of \d+)?)\s*$` | số trang lọt vào nội dung |

Luật nhận dạng loại block (A5):
- **TABLE**: ≥ 2 dòng; dòng thứ hai khớp separator `^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$`; ≥ 80% số dòng chứa `|`.
- **LIST**: ≥ 2 dòng và ≥ 60% số dòng bắt đầu bằng `[-*•+▪–]\s`, `\d+[.)]\s` hoặc `[a-zđ][.)]\s`.
- **CODE**: `Section.element_type == CODE` (parser Markdown đã sửa ở §11.1 sẽ trả loại này cho code fence).
- **CAPTION**: đoạn ngắn (≤ 40 token) khớp `^(Bảng|Hình|Table|Figure|Biểu đồ)\s*\d+([.\-]\d+)*\s*[:.]`.

### 9.2 Pha B: Dựng cây section

```python
def build_tree(sections: list[Section], doc_type: DocumentType) -> SectionNode:
    root = SectionNode(title=None, level=0, path=(), blocks=[], children=[], ordinal=0)
    stack = [root]
    for i, sec in enumerate(sections):
        if is_real_heading(sec, doc_type):                                 # B1
            title = normalize_title(sec.heading or sec.content)            # B6
            if any(n.level == sec.heading_level and n.title == title for n in stack):
                continue                                                   # B2: running header
            while stack[-1].level >= sec.heading_level:                    # B3: tự xử lý nhảy cấp
                stack.pop()
            parent = stack[-1]
            node = SectionNode(title, sec.heading_level, parent.path + (title,), [], [], next_ordinal())
            parent.children.append(node)
            stack.append(node)
            body = heading_body(sec, title)                                # B5
            if body:
                node.blocks.append(to_block(body, sec, i))
        else:
            stack[-1].blocks.append(to_block(sec, i))                      # B4: trước heading đầu → gốc
    return root
```

| # | Quy tắc | Chi tiết |
|---|---|---|
| B1 | **Chặn heading giả** (chỉ áp dụng cho PDF, vì heading PDF là suy đoán từ font) | hạ thành đoạn văn nếu tiêu đề > 200 ký tự, hoặc > 25 từ, hoặc kết thúc bằng `.` `;` `,` và > 8 từ. DOCX và Markdown có heading tường minh nên tin tuyệt đối |
| B2 | **Heading lặp** | tiêu đề trùng với một node đang mở ở cùng level → bỏ. Đây gần như luôn là header chạy đầu trang, và nếu giữ lại sẽ tạo node anh em trùng path, khiến id Heading trong Neo4j đụng nhau |
| B3 | **Nhảy cấp** (H1 → H3) | xử lý tự nhiên bằng stack. Path có độ sâu 2 nhưng `level` giữ 3; Neo4j dùng `enumerate(path)` nên không bị ảnh hưởng |
| B4 | **Lời mở đầu** (nội dung trước heading đầu tiên) | gắn vào gốc, `path=()` |
| B5 | **Heading có thân** (heading DOCX kèm text trong cùng Section) | phần khác tiêu đề trở thành block đầu của node |
| B6 | **Chuẩn hoá tiêu đề** | NFC, gộp khoảng trắng, bỏ dấu `.` `:` ở cuối, cắt còn 150 ký tự |

### 9.3 TOC detector v2

Nguyên tắc: **tín hiệu yếu không bao giờ tự đủ để kết luận là TOC.**

| Loại | Tín hiệu |
|---|---|
| Mạnh | S1: tiêu đề hoặc dòng ngắn ≤ 60 ký tự chứa `mục lục`, `table of contents`, `contents`, `danh mục hình`, `danh mục bảng`, `list of figures`, `list of tables`. **Không** dùng `danh mục` đơn lẻ, vì nó khớp cả "Danh mục tài liệu tham khảo" và "Danh mục từ viết tắt" (glossary là nội dung có ích) |
| Mạnh | S2: ≥ 40% số dòng khớp dot-leader + số trang `\.{3,}\s*\d+\s*$` |
| Mạnh | S3: ≥ 50% số dòng kết thúc bằng tab hoặc ≥ 2 khoảng trắng rồi đến số trang |
| Mạnh | S4: DOCX style `TOC 1`…`TOC 9` (parser truyền qua `Section.metadata["style"]`, §11.1) |
| Yếu | W1: nằm trong 20% đầu tài liệu; W2: ≥ 70% dòng ngắn < 80 ký tự và ≥ 5 dòng |

Luật quyết định:
- **Mở** block TOC khi có ≥ 1 tín hiệu mạnh, và (S1 hoặc W1).
- **Tiếp tục** block chỉ khi block kế có S2, S3 hoặc S4 (tín hiệu cấu trúc theo dòng); S1 không đủ để tiếp tục.
- **Đóng** tại block đầu tiên không thoả luật tiếp tục.

Xử lý:
- `CHUNKER__INDEX_TOC=false` (mặc định): block TOC bị loại khỏi luồng chunk, số lượng được log và hiện trong thống kê của inspector.
- `true`: phát thành chunk riêng với `content_type="toc"`, **không bao giờ gộp** với nội dung khác, và search mặc định lọc bỏ (§11.3).

Với case P-c (danh sách mục tiêu học tập): không có từ khoá, không có dot-leader, không có số trang → không phải TOC ✓.

### 9.4 Pha C: Segment (block → unit)

Ngân sách của một unit là `max_tokens`; riêng hàng bảng là `max_tokens − tokens(header)`.

**Văn xuôi (PROSE):**
```
đoạn (tách "\n\n")        ≤ max ─► 1 unit, joiner "\n\n", starts_block=True cho đoạn đầu
  └─ > max ─► câu        ≤ max ─► unit, joiner " "
        └─ > max ─► cửa sổ từ: cắt tại khoảng trắng gần nhất sao cho ≤ max (mức cuối, luôn thành công)
```

**Tách câu tiếng Việt**: che (mask) các vùng được bảo vệ → tách → bỏ che.
- Điểm tách ứng viên: `[.!?…]` + dấu đóng tuỳ chọn `["')\]»]` + khoảng trắng.
- **Chỉ chấp nhận** khi ký tự có chữ tiếp theo là **chữ hoa hoặc chữ số** (dùng `str.isupper()` nên bao được `Đ`, `Ô`, `Ư`…).
- **Không tách** khi từ đứng trước dấu chấm nằm trong danh sách viết tắt: `v.v`, `TS`, `ThS`, `PGS`, `GS`, `TP`, `Tp`, `TT`, `ĐH`, `e.g`, `i.e`, `etc`, `vs`, `Fig`, `No`, `pp`, `tr`.
- **Không tách** số thập phân `\d\.\d`, số mục `\b\d+(\.\d+)+\.?` (ví dụ "Hình 2.3", "mục 1.2.") và dấu ba chấm giữa câu.

**Danh sách (LIST):**
- Các block LIST liên tiếp trong cùng node tạo thành một nhóm; mỗi item là một unit với joiner `"\n"`. Block LIST nhiều dòng được tách theo marker đầu dòng; dòng thụt lề không có marker thuộc về item trước.
- Item > max → tách tiếp như văn xuôi.
- **Luật dính:** unit văn xuôi ngay trước nhóm list mà kết thúc bằng `:` được gắn `glue_next=True`, để câu dẫn luôn đi cùng item đầu tiên.

**Bảng (TABLE):**
```python
rows = block.text.split("\n")
n_head = 2 if len(rows) > 1 and is_md_separator(rows[1]) else 1
header, body = "\n".join(rows[:n_head]), rows[n_head:]
if tokens(block.text) <= max_tokens:
    return [Unit(TABLE, block.text, ..., starts_block=True)]      # bảng vừa → nguyên khối
units = [Unit(TABLE, row, ..., joiner="\n", table_header=header) for row in body]
# hàng quá lớn (ô chứa đoạn văn dài) → cắt theo cửa sổ từ, mỗi mảnh vẫn mang table_header
```
- Caption đứng ngay trước bảng (A5) được gắn `glue_next=True`.
- Header không phải một unit riêng. Mỗi hàng mang `table_header`; trong **mọi** chunk chứa hàng của bảng bị chia (kể cả chunk đầu), header được chèn ngay trước hàng đầu tiên của bảng đó. Pha D tính chi phí header vào ngân sách (`cost_of`), pha F chèn vào text.

**Code (CODE):** tách theo dòng trống, rồi theo dòng; joiner `"\n"`; giữ nguyên khoảng trắng đầu dòng. Không tách câu.

**Caption đi kèm ảnh:** là unit PROSE với `glue_next=True`, nên không bao giờ đứng một mình ở cuối chunk.

### 9.5 Pha D: Pack (unit → draft chunk, bên trong một node)

```python
def pack(node: SectionNode, units: list[Unit], cfg) -> list[DraftChunk]:
    total = sum_tokens(units)                                    # đã gồm chi phí joiner
    if total <= cfg.max_tokens:
        return [draft(node, units, part_index=0, part_count=1)]  # vừa một chunk → không cắt

    n = ceil(total / cfg.target_tokens)
    per = total / n                                              # kích thước cân bằng mong muốn
    drafts, cur = [], Accumulator(node)

    for u in units:
        cost = cur.cost_of(u)       # u.tokens + joiner + header bảng nếu chunk mới bắt đầu giữa bảng
        if cur and cur.tokens + cost > cfg.max_tokens:           # 1) trần cứng: bắt buộc cắt
            drafts.append(cur.close()); cost = cur.cost_of(u)    #    (tính lại: có thể phải thêm header)
        elif cur and cur.tokens >= per and can_break(cur.last, u):              # 2) đủ cỡ + ranh giới tốt
            drafts.append(cur.close()); cost = cur.cost_of(u)
        elif cur and cur.tokens >= per * cfg.oversize_tolerance and not cur.last.glue_next:
            drafts.append(cur.close()); cost = cur.cost_of(u)    # 3) quá cỡ → cắt ở ranh giới bất kỳ
        cur.add(u, cost)
    drafts.append(cur.close())
    return number_parts(rebalance_tail(drafts, cfg))


def can_break(prev: Unit, nxt: Unit) -> bool:
    # ranh giới tốt: hết đoạn/khối ("\n\n", starts_block) hoặc giữa hàng bảng / item / dòng code ("\n").
    # Ranh giới câu (joiner " ") KHÔNG ở đây: chỉ được cắt khi vượt ngưỡng oversize_tolerance (luật 3).
    return not prev.glue_next and (nxt.starts_block or nxt.joiner in ("\n\n", "\n"))


def rebalance_tail(drafts, cfg):
    """Tránh phần đuôi quá nhỏ (hiếm xảy ra nhờ chia cân bằng, nhưng vẫn có thể)."""
    if len(drafts) >= 2 and drafts[-1].tokens < cfg.min_tokens:
        prev, last = drafts[-2], drafts[-1]
        if prev.tokens + last.tokens <= cfg.max_tokens:
            drafts[-2:] = [prev.merge(last)]
        else:
            # chuyển dần unit cuối của prev sang last, không phá glue_next
            while last.tokens < cfg.min_tokens and prev.can_give(cfg.min_tokens):
                last.prepend(prev.pop())
    return drafts
```

**Vì sao chia cân bằng:** greedy thuần cho node 1100 token sẽ ra `512 / 512 / 76`. Chia cân bằng với `n = ceil(1100/400) = 3` và `per ≈ 367` sẽ ra khoảng `367 / 367 / 366`, và ưu tiên cắt ở ranh giới đoạn. Node ≤ 512 token luôn giữ nguyên một chunk, kể cả khi lớn hơn target, để không băm một ý trọn vẹn 500 token thành hai nửa.

**Luật 1 luôn thắng `glue_next`**: trần cứng quan trọng hơn thẩm mỹ.

### 9.6 Overlap

Overlap chỉ đi vào **`embedding_input`**, không đi vào `content`.

```python
def overlap_for(prev: DraftChunk, cur: DraftChunk, cfg) -> str:
    if cur.part_index == 0 or prev.node_ordinal != cur.node_ordinal:
        return ""                               # chỉ giữa các phần của cùng một node
    if prev.last_unit.kind is not BlockKind.PROSE or cur.first_unit.kind is not BlockKind.PROSE:
        return ""                               # bảng đã có header lặp; list/code không overlap
    picked, budget = [], cfg.overlap_tokens
    for s in reversed(sentences(prev.tail_text)):
        t = tokens(s)
        if t > budget:
            break
        picked.insert(0, s)
        budget -= t
    return " ".join(picked)                     # rỗng nếu câu cuối đã dài hơn ngân sách → không cắt giữa câu
```

Vì sao overlap không nằm trong `content`:
1. Khi hai chunk kề nhau cùng được retrieve, LLM không phải đọc câu bị lặp.
2. `content` của các phần trong một node nối lại đúng bằng nguyên văn section (G4), nên `start_char`/`end_char` có nghĩa và mở rộng ngữ cảnh ở phía retrieval (lấy chunk `index ± 1`) dễ làm.
3. Embedding vẫn thấy ngữ cảnh phía trước, và đó mới là lý do tồn tại của overlap.

Đánh đổi: một chunk hiển thị riêng lẻ thiếu câu dẫn. Nếu eval (§12.4) cho thấy recall giảm thì chuyển overlap vào `content`; chỉ cần đổi một cờ.

### 9.7 Pha E: Consolidate (gộp draft nhỏ theo luật LCP)

Đầu vào: danh sách draft theo thứ tự pre-order của cây. Chỉ draft **nhỏ** (`tokens < min_tokens`) mới tìm bạn để gộp.

```python
def consolidate(drafts: list[DraftChunk], cfg) -> list[DraftChunk]:
    out = list(drafts)
    changed = True
    while changed:                    # mỗi lần gộp làm giảm số draft → chắc chắn dừng
        changed = False
        for i, d in enumerate(out):
            if d.tokens >= cfg.min_tokens or d.is_toc:
                continue
            j = pick_partner(out, i, cfg)
            if j is not None:
                a, b = sorted((i, j))
                out[a:b + 1] = [merge(out[a], out[b])]
                changed = True
                break
    return out


def can_merge(x: DraftChunk, y: DraftChunk, cfg) -> bool:
    if x.is_toc or y.is_toc:
        return False
    lcp = common_prefix(x.path, y.path)
    if not lcp and (x.path or y.path) and not cfg.merge_across_top_level:
        return False                  # không gộp xuyên chương (sửa C2)
    if len(lcp) < min(len(x.path), len(y.path)) - 1:
        return False                  # chỉ cho cha–con, anh–em, cháu–chú; không cho họ hàng xa
    return x.tokens + y.tokens + inline_heading_cost(x, y, lcp) <= cfg.target_tokens


def pick_partner(out, i, cfg) -> int | None:
    prev = i - 1 if i > 0 else None
    nxt = i + 1 if i + 1 < len(out) else None
    order = [
        (nxt,  nxt is not None and out[nxt].part_count == 1),     # 1. tiến vào node nguyên vẹn
        (prev, prev is not None and out[prev].part_count == 1),   # 2. lùi vào node nguyên vẹn
        (nxt,  nxt is not None and out[nxt].part_index == 0       # 3. lời dẫn của CHA tiến vào phần đầu
               and is_proper_prefix(out[i].path, out[nxt].path)), #    của node CON bị chia
    ]
    for j, ok in order:
        if ok and can_merge(out[i], out[j], cfg):
            return j
    return None                       # 4. đứng riêng: path đúng quan trọng hơn kích thước đẹp


def merge(x: DraftChunk, y: DraftChunk) -> DraftChunk:
    lcp = common_prefix(x.path, y.path)
    return DraftChunk(
        path=lcp,
        level=level_of(lcp),
        runs=x.runs + y.runs,         # mỗi run giữ path gốc → pha F chèn tiêu đề inline
        node_ordinal=ordinal_of(lcp),
        part_index=0, part_count=1,
    )
```

Vì sao chọn thứ tự ưu tiên này:
- **Tiến trước** vì mẫu phổ biến nhất là "lời dẫn ngắn của chương + mục con đầu tiên". Lời dẫn giới thiệu cái đi sau nó.
- **Ưu tiên node nguyên vẹn** vì gộp vào một phần của node bị chia sẽ kéo path của phần đó lên tổ tiên chung, làm phần đó mất độ chính xác trong khi các phần còn lại vẫn giữ path cũ.
- **Luật 3 chỉ dành cho lời dẫn của cha → con.** Trường hợp này path gộp (= path của cha) vẫn mô tả đúng nội dung. Với anh em (ví dụ "2.2" nhỏ đứng trước "2.3" bị chia), gộp sẽ làm thô path của phần đầu "2.3", nên draft nhỏ đứng riêng.
- **Giới hạn gộp là `target`, không phải `max`**, để draft nhỏ không bị nhét vào một chunk đã lớn.

**Bất biến duy nhất của pha này:** `chunk.heading_path == LCP(path của mọi run)`, và mọi run có path dài hơn LCP đều mở đầu bằng tiêu đề inline. Nhờ vậy:
- Neo4j gắn chunk vào đúng heading tổ tiên chung, và cây Heading không có node giả.
- LO mapper vẫn thấy số chương, vì gộp xuyên chương bị cấm.
- Enrichment nhóm theo path vẫn hợp lệ.

### 9.8 Pha F: Emit

1. **Đánh số** `chunk_index` = 0..n-1 theo thứ tự draft (pre-order).
2. **Dựng `content`:**
   ```python
   def render_content(d: DraftChunk) -> str:
       parts = []
       for run in d.runs:
           extra = run.path[len(d.path):]
           if extra and run.starts_node:
               parts.append(" > ".join(extra))                 # tiêu đề con inline, một dòng riêng
           parts.append(join_units(run.units))
       return "\n\n".join(parts)


   def join_units(units: list[Unit]) -> str:
       out, seen_tables = [], set()
       for u in units:
           if u.table_header and u.table_header not in seen_tables:   # hàng đầu tiên của bảng trong chunk này
               seen_tables.add(u.table_header)
               out.append(("\n\n" if out else "") + u.table_header + "\n" + u.text)
           else:
               out.append((u.joiner if out else "") + u.text)
       return "".join(out)
   ```
3. **Breadcrumb** = `" > ".join(path)` (giữ định dạng hiện tại để tương thích dữ liệu cũ). Nếu > `header_max_tokens` thì rút gọn thành `path[0] > … > path[-2] > path[-1]`; vẫn dài thì cắt mỗi tiêu đề còn 60 ký tự.
4. **`embedding_input`** = `breadcrumb` + `"\n\n"` + `overlap` + `"\n\n"` + `content` (bỏ các phần rỗng).
5. **ID tất định:**
   ```python
   CHUNK_NS = uuid.UUID("…")   # hằng số cố định trong code, không bao giờ đổi
   content_hash = hashlib.md5(content.encode()).hexdigest()    # giữ md5 để tương thích payload cũ
   chunk_id = uuid.uuid5(CHUNK_NS, f"{document_id}:{chunker_version}:{chunk_index}:{content_hash}")
   ```
   Retry cho ra đúng bộ ID cũ, nên upsert Qdrant ghi đè và Postgres `ON CONFLICT (chunk_id)` cập nhật (sửa C7). Nội dung thay đổi (ví dụ sau khi sửa parser) → ID mới, và bộ cũ được dọn theo §11.2.
6. **Metadata:**
   - `content_type`: tất cả unit cùng loại → loại đó; lẫn nhiều loại → `mixed`.
   - `page_start` / `page_end`: min và max trang của các unit.
   - `images`: hợp các ảnh của mọi unit, giữ thứ tự, bỏ trùng. Ảnh đi theo unit chứa nó, thay vì chỉ gắn vào chunk con đầu tiên như hiện tại.
7. **Kiểm bất biến ngay trong code** (không chỉ trong test): đếm lại token chính xác; kiểm path là tiền tố; kiểm chỉ số liên tục. Trong test/dev thì vi phạm → raise. Trong production thì log `chunker.invariant_violation{rule}`, tăng metric `CHUNK_INVARIANT_VIOLATIONS`, rồi sửa (chia lại chunk vượt trần).

### 9.9 PPTX

- **Node gốc có tiêu đề**: `core_properties.title`, hoặc tiêu đề slide đầu nếu đó là title slide. Nhờ vậy mọi slide có chung tổ tiên, luật LCP gộp được slide nhỏ mà không phải bật `merge_across_top_level`, và path mang tên bài (ví dụ "Bài 3: SQL") mà LO mapper có thể tận dụng.
- **Slide phân đoạn** (có tiêu đề, thân ≤ 12 token) → node level 1; các slide sau là level 2 cho tới slide phân đoạn tiếp theo. Deck không có slide phân đoạn thì mọi slide là level 1.
- **Slide tiếp nối** (tiêu đề trùng slide trước, hoặc kết thúc bằng `(tiếp)`, `(cont.)`, `continued`, `(2)`) → cùng node, nối blocks.
- **Blocks trong slide**: shape theo thứ tự đọc → PROSE/LIST (theo bullet level); shape bảng → TABLE; notes → block NOTES với tiền tố `"Ghi chú: "` khi `pptx_include_notes`.
- Sau đó slide đi qua đúng các pha C–F như tài liệu thường. Nhánh `_chunk_by_slides` riêng không còn cần.

### 9.10 Độ phức tạp

Mỗi pha duyệt tuyến tính số block/unit. Pha E lặp tới điểm bất động, nhưng mỗi lần gộp giảm số draft và mỗi vòng dừng ngay ở lần gộp đầu tiên, nên trường hợp xấu nhất là O(k²) với k = số draft nhỏ. Thực tế k nhỏ; nếu cần có thể viết lại thành một lượt duyệt tuyến tính. Chi phí tokenize ~30 ms / 40k ký tự (§3).

---

## 10. Cấu hình

Thêm vào `ChunkerConfig`. Env theo quy ước nested hiện có của `Settings` (`env_nested_delimiter="__"`), ví dụ `CHUNKER__TARGET_TOKENS`.

| Biến | Mặc định | Ý nghĩa / lý do |
|---|---|---|
| `CHUNKER__STRATEGY` | `heading` | `heading` \| `structural`: feature flag; chuyển sang `structural` sau khi eval đạt (§13) |
| `CHUNKER__TARGET_TOKENS` | 400 | ≈ 1500 ký tự tiếng Việt (§3), giữ độ mịn hiện tại |
| `CHUNKER__MAX_TOKENS` | 512 | trần cứng của `content` |
| `CHUNKER__MIN_TOKENS` | 64 | ≈ 240 ký tự tiếng Việt; draft dưới ngưỡng này mới xét gộp |
| `CHUNKER__OVERLAP_TOKENS` | 48 | ~12% target; chỉ đi vào `embedding_input` |
| `CHUNKER__HEADER_MAX_TOKENS` | 64 | ngân sách cho breadcrumb |
| `CHUNKER__EMBED_MAX_TOKENS` | 1024 | phải bằng `EMBEDDER__MAX_LENGTH`; kiểm lúc khởi động |
| `CHUNKER__OVERSIZE_TOLERANCE` | 1.15 | vượt `per × hệ số` thì được cắt ở ranh giới câu/hàng |
| `CHUNKER__TOKENIZER` | `BAAI/bge-m3` | phải cùng model với embedder |
| `CHUNKER__TOKENIZER_PATH` | (trống) | đường dẫn `tokenizer.json` bake sẵn trong image (khuyến nghị cho worker) |
| `CHUNKER__INDEX_TOC` | `false` | xem §9.3 |
| `CHUNKER__MERGE_ACROSS_TOP_LEVEL` | `false` | cho phép gộp draft nhỏ giữa các chương (không khuyến nghị) |

Các field cũ (`max_chunk_size`, `min_chunk_size`, `overlap_size`) giữ nguyên cho `HeadingChunker` cho tới khi gỡ bỏ ở giai đoạn 3.

---

## 11. Thay đổi ngoài chunker

### 11.1 Parser (điều kiện tiên quyết)

**PDF (`PdfParser`)**
- **P1: sửa lỗi mất chữ (P-a), ưu tiên cao nhất, làm được độc lập.** Đổi `_iter_spans` thành `_iter_lines`: text của dòng = nối các span; lọc độ dài theo **dòng**; font size và bold của dòng = của span chiếm nhiều ký tự nhất. Heading cũng xét theo dòng, nên một dòng chỉ có vài từ in đậm không còn bị hiểu là heading.
- **P2: giữ ranh giới đoạn (P-b).** Mỗi text block của PyMuPDF (≈ một đoạn) thành một `Section`; các dòng trong block nối bằng `" "`. Chunker nhờ vậy có đơn vị "đoạn" thật.
- **P3: bỏ header/footer chạy.** Dòng nằm trong 7% trên hoặc dưới của trang, có text chuẩn hoá (chữ số → `#`) lặp lại ở ≥ 30% số trang (tối thiểu 3 trang) → bỏ. `bbox` và kích thước trang đã có sẵn trong `get_text("dict")`.
- Gán `ParsedDocument.metadata["parser"] = "pymupdf"` (Docling đã gán `"docling"`) để chunker biết độ tin cậy của heading.

**DOCX (`DocxParser`)**
- Paragraph có style `TOC 1`…`TOC 9` → truyền `metadata["style"]` (tín hiệu S4 của TOC v2).
- Paragraph có `numPr` hoặc style `List …` → `ElementType.LIST`.
- Ô gộp: python-docx trả cùng một ô ở mọi vị trí lưới nó chiếm → bỏ ô trùng liên tiếp trong một hàng trước khi nối.

**Markdown (`MarkdownParser`)**
- Theo dõi code fence (ba backtick hoặc ba dấu ngã): nội dung bên trong → `ElementType.CODE`, **không** nhận dạng heading bên trong (sửa P-d).
- Bảng (các dòng `|` + separator) → `TABLE`; khối list → `LIST`.
- Bỏ YAML front matter ở đầu file.

**Docling**: không cần sửa; placeholder `"[Image]"` được pha A xử lý.

### 11.2 `PipelineCore`: idempotency và dọn chunk cũ

Sau khi upsert Qdrant **thành công**:
- **Qdrant**: xoá các point có `document_id = X` và `chunk_id ∉ new_ids` (filter `must` theo `document_id`, `must_not` `HasIdCondition(new_ids)`). Upsert trước rồi mới xoá, nên không có lúc nào tài liệu mất hết vector.
- **Postgres**: trong **cùng transaction** với `upsert_chunks_with_outbox`, soft-delete (`deleted_at = now()`) các dòng `chunks` của tài liệu không nằm trong `new_ids`. **Không xoá cứng**, vì `chunk_lo_mappings` và `source_chunk_ids` của nội dung đã sinh vẫn trỏ tới chúng.

### 11.3 Qdrant adapter

- `_chunk_to_payload` / `_payload_to_chunk`: thêm các key ở §7.4.
- `_ensure_collection`: thêm payload index cho `content_type` và `chunker_version`; gọi được cho collection đã tồn tại.
- `SearchFilter`: thêm `exclude_content_types`, mặc định `("toc",)`, dịch thành `must_not` trên `content_type`.

### 11.4 Consumer

- **ai-tutor** `_build_prompt`: render `[i] (Chương 2 > 2.1 Khái niệm · tr. 12)\n{content}` từ `heading_path` và `page_number`, vốn đã có trong context (sửa C6).
- **`retrieve_quiz_context`**: nâng `max_chunk_chars` từ 1600 lên 2600, hoặc tốt hơn là đổi sang giới hạn theo `token_count`. 512 token ≈ 1950 ký tự văn xuôi tiếng Việt và ≈ 2200 ký tự tiếng Anh (§3).
- **`generate_curriculum_quiz`**: `max_context_chars=6000` chứa được khoảng 3 chunk; giữ nguyên nhưng cân nhắc đổi sang token.

### 11.5 Wiring

- `worker/worker/container.py` `build_chunker()` và `packages-ai/.../container.py` `chunker`: chọn theo `CHUNKER__STRATEGY`.
- `document-inspector`: thêm `structural` vào `strategy: Literal[...]`, và thêm thống kê token p50/p95/max, số chunk vượt trần, số chunk < min, số block TOC bị loại, số lần gộp LCP. Đây là công cụ so sánh chính ở giai đoạn 1.
- Dockerfile của worker: bake `tokenizer.json` của BGE-m3 vào image và đặt `CHUNKER__TOKENIZER_PATH`.

---

## 12. Kiểm thử

### 12.1 Bất biến

Chạy trên mọi fixture và trên tài liệu sinh ngẫu nhiên có seed (cây heading ngẫu nhiên × độ dài ngẫu nhiên × loại block ngẫu nhiên). Không cần thêm dependency `hypothesis`.

| # | Bất biến | Cách kiểm |
|---|---|---|
| I1 | `tokens(content) ≤ max_tokens`; `tokens(embedding_input) ≤ embed_max − 2` | đếm lại bằng `TokenCounter` |
| I2 | Nối `content` theo `chunk_index`, bỏ tiêu đề inline và header bảng lặp, bằng text đã normalize của các block không phải TOC | so sánh chuỗi sau khi chuẩn hoá khoảng trắng |
| I3 | `heading_path` là tiền tố của path gốc của mọi run, và bằng LCP của chúng | kiểm trên draft trước khi emit |
| I4 | Không chunk nào chứa nội dung của hai node cấp 1 khác nhau (khi `merge_across_top_level=false`) | theo `path[0]` của các run |
| I5 | Mọi chunk chứa hàng của một bảng bị chia đều có header ngay trước hàng đầu tiên của bảng đó | kiểm theo từng bảng |
| I6 | Tất định: chạy hai lần → ID và `content` giống hệt | so sánh |
| I7 | `chunk_index` liên tục `0..n-1` | kiểm |
| I8 | Không chunk nào bắt đầu hoặc kết thúc giữa từ (trừ từ đơn lẻ dài hơn `max`) | kiểm ký tự biên |
| I9 | Không block TOC nào lọt vào chunk thường | kiểm `content_type` và nguồn |

### 12.2 Regression (mỗi lỗi ở §1.2 có một test)

- C1: mục lục ở đầu tài liệu → bị loại (hoặc có `content_type="toc"` khi `index_toc=true`).
- C2: `Chương 1` (thân 1 câu) + `Chương 2` → không gộp; path của từng chunk đúng.
- C3: bảng 200 hàng → mọi chunk ≤ 512 token, mỗi chunk có header.
- C4: đoạn 40 câu bị chia → không chunk nào dính chữ; overlap chỉ gồm câu trọn vẹn và chỉ nằm trong `embedding_input`.
- C7: chạy pipeline hai lần trên cùng input → cùng bộ ID; sau khi đổi nội dung, point cũ bị xoá khỏi Qdrant.
- P-a: PDF sinh bằng PyMuPDF có từ in đậm ngắn giữa câu → không mất chữ (dựng PDF ngay trong test, không commit file nhị phân).
- P-c: danh sách "Mục tiêu học tập" 5 dòng ở đầu tài liệu → không phải TOC.
- P-d: Markdown có khối code Python chứa `# comment` → không sinh heading.

### 12.3 Unit test theo pha

`test_structural_normalize.py`, `test_structural_tree.py`, `test_toc_v2.py`, `test_structural_segment.py` (đặc biệt là tách câu tiếng Việt với `v.v.`, `TS.`, `Hình 2.3`, số thập phân), `test_structural_pack.py`, `test_structural_consolidate.py`, `test_structural_emit.py`, `test_structural_invariants.py`, `test_token_counter.py` (gồm fallback), cùng test parser `test_pdf_parser_lines.py` và `test_markdown_parser_blocks.py`.

### 12.4 Eval retrieval (script offline, không chạy trong CI)

- **Corpus**: 5–10 tài liệu môn học thật (PDF, DOCX, PPTX) + luận văn trong `report/lvtn`.
- **Bộ câu hỏi**: 60–100 câu, mỗi câu gán nhãn **section kỳ vọng** (heading path), không gán chunk ID. Nhờ vậy cùng một bộ nhãn so được hai chunker khác nhau.
- **Tính trúng**: chunk được retrieve trúng nếu `heading_path` của nó bắt đầu bằng path kỳ vọng, hoặc path kỳ vọng bắt đầu bằng path của nó (trường hợp chunk gộp LCP).
- **Chỉ số**: Recall@5, MRR@10; thống kê kích thước (p50/p95/max token, % chunk < min, % vượt trần); số chunk mỗi tài liệu.
- **Tiêu chí chuyển mặc định**: Recall@5 và MRR@10 **không thấp hơn** `heading`; **0** chunk vượt trần; < 2% chunk < min.

---

## 13. Kế hoạch triển khai

**Giai đoạn 0: sửa độc lập, làm ngay (không phụ thuộc v2)**
- [ ] P1: `PdfParser` lọc theo dòng thay vì span (lỗi mất nội dung trên đường mặc định của worker).
- [ ] Parser Markdown: code fence.
- [ ] Test regression cho P-a, P-d.
- [ ] Nếu dự kiến v2 cần hơn 2 tuần: hotfix C2 và C3 trên `HeadingChunker`.

**Giai đoạn 1: implement sau flag**
- [ ] `TokenCounter` + bake tokenizer vào image worker.
- [ ] Pha A–F, TOC v2, PPTX.
- [ ] Toàn bộ test ở §12.1–12.3.
- [ ] Inspector: strategy `structural` + thống kê.
- [ ] Qdrant adapter: payload mới + index + `exclude_content_types`.
- [ ] Parser P2, P3; DOCX style/list.

**Giai đoạn 2: đánh giá và chuyển đổi**
- [ ] Eval §12.4; điều chỉnh `target`/`min`/overlap nếu cần.
- [ ] `PipelineCore`: dọn chunk cũ (§11.2).
- [ ] Consumer: ai-tutor prompt, `max_chunk_chars`.
- [ ] Đổi mặc định `CHUNKER__STRATEGY=structural`.
- [ ] **Re-index** tài liệu hiện có. Chunk ID đổi, nên với mỗi tài liệu:
  1. chạy lại pipeline (outbox `HEADING_GRAPH_PROJECT` tự chiếu lại Neo4j);
  2. chạy lại `map_chunks_to_los`;
  3. chạy lại enrichment.

  Chunk cũ được soft-delete nên citation và `source_chunk_ids` cũ vẫn tra được. Trong lúc chuyển đổi, collection chứa lẫn hai phiên bản; lọc theo `chunker_version` nếu cần.

**Giai đoạn 3: dọn dẹp**
- [ ] Migration Prisma (tuỳ chọn): `content_type`, `token_count`, `page_end`, `section_id` nếu core-api hoặc UI cần.
- [ ] Gỡ `HeadingChunker`, `toc_detector.py`, các field config dạng ký tự.

---

## 14. Rủi ro và câu hỏi mở

| # | Vấn đề | Đề xuất |
|---|---|---|
| R1 | Tokenizer không có trong môi trường offline | bake vào image; fallback `len/2.0` + metric cảnh báo |
| R2 | Overlap chỉ trong `embedding_input` là lựa chọn ít phổ biến | eval cả hai cách; đổi bằng một cờ |
| R3 | Không index TOC → mất khả năng trả lời "tài liệu có những chương nào?" | câu hỏi cấu trúc nên trả lời từ cây Heading trong Neo4j, không từ vector search |
| R4 | Gộp LCP làm path của mục con rất nhỏ thô hơn | chấp nhận: chỉ xảy ra với draft < 64 token, tiêu đề vẫn còn inline, và không bao giờ gộp xuyên chương |
| R5 | Target 400 có thể chưa tối ưu (256 cho kết quả sắc hơn?) | quyết định bằng eval §12.4, không đoán |
| R6 | Heuristic heading giả / header chạy của PDF có thể sai với layout lạ | các ngưỡng nằm trong config; inspector hiện rõ số heading bị hạ cấp |
| Q1 | Contextual retrieval (LLM sinh một câu ngữ cảnh cho mỗi chunk trước khi embed) | để sau; `embedding_input` đã có chỗ để chèn |
| Q2 | Hybrid dense + sparse (BGE-m3 hỗ trợ sẵn sparse) | để sau; không phụ thuộc chunker |
| Q3 | Small-to-big retrieval (retrieve chunk nhỏ, trả về cả section) | `section_id` + `part_index` ở §7.2 đã chuẩn bị sẵn |

---

## Phụ lục A: Ví dụ end-to-end

Cùng một tài liệu, số token đo bằng tokenizer BGE-m3. Cột "hiện tại" là kết quả **chạy thật** `HeadingChunker`; cột v2 là kết quả **suy ra từ thiết kế** (v2 chưa được implement).

**Đầu vào:**

```
H1  Chương 2: Mô hình quan hệ
P   lời dẫn chương                                          20
H2  2.1 Khái niệm
P   6 đoạn văn × 88                                        528
H2  2.2 Ràng buộc
P   "Có ba loại ràng buộc chính:"                            7
L   3 item × 11                                             33
H2  2.3 Ví dụ
P   "Bảng 2.1: Danh sách sinh viên"                          7
T   bảng 60 hàng: header 31 + hàng ~26.6                  1625
H1  Chương 3: Đại số quan hệ
P   lời dẫn chương                                          12
```

**v2, pha D (pack trong từng node):**

| Draft | Node | Token | Ghi chú |
|---|---|---|---|
| d0 | Chương 2 (lời dẫn) | 20 | nhỏ |
| d1, d2 | 2.1 | ~265 mỗi phần | 528 > 512 → n = 2, per = 264; cắt đúng sau đoạn thứ 3 |
| d3 | 2.2 | 40 | nhỏ; câu dẫn dính với item đầu (`glue_next`) |
| d4–d8 | 2.3 | 330 / 350 / 350 / 350 / 377 | ~1632 → n = 5, per ≈ 326; cắt giữa các hàng; mỗi phần có header 31 token; caption dính vào phần đầu |
| d9 | Chương 3 (lời dẫn) | 12 | nhỏ |

**v2, pha E (consolidate):**
- **d0**: d1 là phần của node bị chia (luật 1 ✗); không có draft trước (luật 2 ✗); luật 3: d0 là lời dẫn của cha, d1 là phần đầu của con, 20 + 265 + 4 (dòng inline "2.1 Khái niệm") = 289 ≤ 400 ✓. Kết quả **M0** có path `(Chương 2)`.
- **d3**: d4 và d2 đều không nguyên vẹn (luật 1, 2 ✗); d3 không phải cha của d4 (luật 3 ✗). → **đứng riêng** với path đúng `(Chương 2, 2.2 Ràng buộc)`. Một danh sách trọn vẹn 40 token là chunk tốt.
- **d9**: không có draft sau; d8 thuộc Chương 2 nên LCP = `()` → bị chặn. → **đứng riêng**.

**Đối chiếu đầu ra** (token của `embedding_input`):

| | `HeadingChunker` (chạy thật) | v2 (theo thiết kế) |
|---|---|---|
| Số chunk | 8 | 9 |
| Lời dẫn Chương 2 | chunk riêng 26 token | gộp với phần đầu 2.1 (M0, ~289 + breadcrumb) |
| Mục 2.1 | 363 / 150 / 100, chunk thứ hai bắt đầu giữa câu (`"có quan hệ với nhau. …"`) | ~265 / ~265, cắt tại ranh giới đoạn; overlap 2 câu trọn vẹn chỉ trong `embedding_input` |
| Mục 2.2 | 52 | ~40 + breadcrumb |
| Caption "Bảng 2.1" | chunk riêng 17 token, **và** lặp lại ở đầu chunk bảng qua overlap | nằm trong phần đầu của bảng, không lặp |
| Bảng | **1 chunk 1642 token → embedder bỏ ~38% phần đuôi** | 5 chunk 330–377 token, chunk nào cũng có header |
| Lời dẫn Chương 3 | 18 | 12 + breadcrumb (đứng riêng, không gộp xuyên chương) |
| Chunk vượt 1024 token | 1 | 0 |

## Phụ lục B: Truy vết lỗi → cách v2 xử lý

| Lỗi | Xử lý ở |
|---|---|
| C1 TOC mất nhãn | §9.3: TOC là thuộc tính của block, xử lý trước khi pack; mặc định loại khỏi index |
| C2 gộp xuyên chương | §9.7: luật LCP + chặn gộp xuyên cấp 1 + path tính lại |
| C3 không có trần | §8 đếm token thật, §9.4 cắt theo loại tới mức từ, §9.5 luật 1, §9.8 kiểm lại |
| C4 overlap dính chữ | §9.6: chỉ câu trọn vẹn, nối bằng `" "`, nằm ngoài `content` |
| C5 metadata không được lưu | §7.4, §11.3 |
| C6 LLM không thấy heading | §7.3, §11.4 |
| C7 point mồ côi khi retry | §9.8 ID `uuid5`, §11.2 dọn chunk cũ |
| P-a PDF mất chữ | §11.1 P1 |
| P-b PDF mất ranh giới đoạn | §11.1 P2 |
| P-c TOC nhận nhầm | §9.3 tín hiệu mạnh/yếu |
| P-d Markdown code fence | §11.1 Markdown |
