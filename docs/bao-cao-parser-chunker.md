# Cơ chế hoạt động và thiết kế: parser và chunker

Phạm vi: `packages-ai/src/document_chunk/adapters/parsers/` và `.../adapters/chunkers/structural/`.

---

## Gợi ý bố cục slide

| Slide | Nội dung | Mục |
|---|---|---|
| 1 | Hai bước trong pipeline, hợp đồng dữ liệu | §1 |
| 2 | Các kiểu dữ liệu đi qua hệ thống | §2 |
| 3 | Parser: chọn backend theo từng trang | §3.1 |
| 4 | PdfParser: bốn lượt duyệt | §3.2 |
| 5 | Đo và phân loại một trang | §3.3 |
| 6 | Thuật toán tìm rãnh cột | §3.4 |
| 7 | Routing, ghép trang, sổ trạng thái | §3.5 |
| 8 | Ngân sách xử lý | §3.6 |
| 9 | Chunker: đường đi tổng thể | §4.1 |
| 10 | Dựng cây section | §4.2 |
| 11 | Cắt block thành unit theo loại | §4.3 |
| 12 | Pack: chia cân bằng trong một node | §4.4 |
| 13 | Consolidate: luật LCP | §4.5 |
| 14 | Emit: render, overlap, ID tất định | §4.6 |
| 15 | Đếm token hai tầng | §4.7 |
| 16 | Ba nguyên tắc thiết kế xuyên suốt | §5 |

---

## 1. Hai bước và hợp đồng dữ liệu giữa chúng

```
file (PDF/DOCX/PPTX/MD)
      │
      ▼
  IParser.parse(path) -> Result[ParsedDocument, Exception]
      │        ParsedDocument = document + list[Section] + page_count + metadata
      ▼
  IChunker.chunk(parsed) -> Result[list[Chunk], Exception]
      │        Chunk = content + embedding_input + ChunkMetadata
      ▼
  embed (BGE-m3, trần 1024 token) → Qdrant + Postgres + Neo4j
```

Ba quy ước của lớp này:

- **Port / adapter.** `IParser` và `IChunker` là interface trong `domain/ports`; mỗi công nghệ (PyMuPDF, Docling, python-docx, python-pptx) là một adapter thay thế được, domain không biết thư viện nào đang chạy.
- **`Result[T, Exception]` thay cho ngoại lệ.** Parser và chunker không ném lỗi ra ngoài; mọi thất bại là `Err` có kiểu, buộc nơi gọi phải xử lý.
- **Parser không làm phẳng tài liệu thành Markdown.** Nó giữ `Section` có `element_type` (heading / paragraph / table / list / code / image / slide), cấp heading, số trang. Chunker nhờ đó biết đang cắt loại nội dung gì.

---

## 2. Các kiểu dữ liệu

**Tầng parser** (`domain/entities/document.py`):

| Kiểu | Nội dung |
|---|---|
| `Document` | metadata file: id, tên, loại, kích thước, mime |
| `Section` | `content`, `element_type`, `heading`, `heading_level`, `page_number`, `images`, `metadata` (có `source`: parser + trang + block + bbox) |
| `ParsedDocument` | `document`, `sections`, `page_count`, `images`, `language`, `metadata` (có `page_report`, `coverage`) |

**Tầng chunker** (`structural/model.py`) — các kiểu nội bộ, nhỏ dần:

| Kiểu | Vai trò |
|---|---|
| `Node` | một mục trong cây chương mục: `path` (tuple heading từ gốc), `level`, `ordinal`, `blocks` |
| `Block` | một khối nội dung thuộc node: `text`, `kind` (`text`/`table`/`list`/`code`/`image`/`toc`), `page`, `images`, `source` (chỉ số section gốc) |
| `Unit` | đơn vị nguyên tử không chia nhỏ hơn nữa: câu, hàng bảng, item, dòng code; mang `joiner`, `header` (header bảng), `glue_next` |
| `Run` | một dãy unit liên tiếp cùng một node, kèm `starts_node` |
| `Draft` | chunk nháp: `path` + danh sách `Run` + `part_index`/`part_count` |
| `Chunk` | kết quả cuối: `content`, `embedding_input`, `content_hash`, `images`, `ChunkMetadata` |

Chuỗi biến đổi: `Section → Block → Unit → Draft → Chunk`. Mỗi bước chỉ làm một việc, và mỗi kiểu giữ con trỏ ngược về nguồn (`Unit.block.source`, `Block.page`) để metadata cuối cùng dựng lại được.

---

## 3. Parser

### 3.1 Chọn backend theo từng trang (`AdaptivePdfParser`)

Hai backend với chi phí rất khác nhau:

| Backend | Chi phí | Đọc được |
|---|---|---|
| PyMuPDF (`PdfParser`) | mili-giây/trang | text layer, vị trí, font |
| Docling (`DoclingPdfParser`) | nạp model OCR + layout | trang scan, bảng có cấu trúc, nhiều cột |

Luồng điều phối:

```
PdfParser.parse(path)            # luôn chạy trước, rẻ
      │
      ├─ Err  ─────────────────► Docling cho cả file (không có đánh giá để route)
      │
      └─ Ok + page_report
             │
             ├─ không trang nào cần fallback ─────────► trả kết quả PyMuPDF
             │
             ├─ tỉ lệ trang cần fallback ≥ ngưỡng ────► Docling một lần cho cả file
             │
             └─ còn lại ──► gom trang thành các KHOẢNG liên tiếp
                            → Docling.parse_pages(first, last) cho từng khoảng
                            → ghép vào kết quả PyMuPDF theo số trang
```

Quyết định được đưa ra **ở mức trang**, không ở mức file. Docling giữ số trang tuyệt đối khi convert theo khoảng, nên kết quả ghép lại đúng vị trí.

### 3.2 `PdfParser`: bốn lượt duyệt

```
Lượt 1  mỗi trang → danh sách DÒNG
        get_text("dict") → block → line → nối các span của dòng
        giữ: text, cỡ chữ và độ đậm của span chiếm nhiều ký tự nhất,
             bbox, chỉ số block, cờ "nằm trong lề" (7% trên/dưới trang)

Lượt 2  bỏ header/footer chạy lặp
        chuẩn hoá dòng lề (mọi chữ số → '#'), đếm số trang xuất hiện,
        xuất hiện ở ≥ 30% số trang (tối thiểu 3) → bỏ

Lượt 3  mỗi trang → ĐO và PHÂN LOẠI  (+ trích ảnh nếu được bật)

Lượt 4  ngưỡng heading + dựng Section theo thứ tự trang
```

Thứ tự này có chủ đích: **bỏ header lặp trước khi đo**, nếu không một trang scan có số trang stamp sẵn sẽ được tính là "trang có text".

Ngưỡng heading ở lượt 4 tính từ phân phối cỡ chữ của cả tài liệu: `body` = median, `gap` = (max − body)/3, rồi `h3 = body + 0.8·gap`, `h2 = body + 1.5·gap`, `h1 = body + 2.2·gap`; ngoài ra dòng in đậm lớn hơn body cũng là h3. Mỗi `Section` sinh ra mang `metadata["source"]` = parser + trang + chỉ số block + bbox hợp của các dòng, để đối chiếu ngược lên PDF gốc.

### 3.3 Đo và phân loại một trang

Bốn số đo cho mỗi trang:

| Số đo | Cách lấy | Chỉ tính khi |
|---|---|---|
| Số ký tự | tổng độ dài các dòng **không nằm trong lề** | luôn |
| Độ phủ ảnh | tổng diện tích bbox ảnh ∩ trang, chia diện tích trang, chặn ở 1.0 | luôn |
| Số nét vẽ vector | `page.get_drawings()` | trang thiếu text và độ phủ ảnh thấp (tránh chi phí thừa) |
| Nhiều cột / số bảng | rãnh cột (§3.4) và `find_tables()` | trang đủ text (trang scan không cần) |

Luật phân loại — **thứ tự kiểm tra là một phần của thiết kế**:

```
nếu số ký tự ≥ ngưỡng:
        nhiều cột hoặc có bảng  → complex_layout     (có dữ liệu, thứ tự đọc chưa chắc)
        ngược lại               → text
ngược lại (ít hoặc không có chữ):
        độ phủ ảnh ≥ ngưỡng     → needs_ocr          (trang scan)
        có ảnh hoặc có nét vẽ   → needs_ocr          (trang vector, không có text layer)
        còn vài ký tự           → text               (trang thưa chữ, ví dụ trang bìa chương)
        không gì cả             → empty              (trang trắng thật, không phải lỗi)
```

Nhánh ảnh được xét **trước** nhánh "còn vài ký tự", vì trang scan thường vẫn có vài ký tự lọt ra từ watermark hoặc số trang.

### 3.4 Thuật toán tìm rãnh cột

Mục tiêu hẹp: trả lời "trang này có nhiều hơn một cột hay không", không dựng lại thứ tự đọc.

```
với mỗi vị trí x lấy mẫu trong dải giữa trang (20%–80% bề rộng):
    chia các dòng thành: nằm hẳn bên trái, nằm hẳn bên phải, cắt qua x
    nhận x là rãnh khi đồng thời:
        số dòng cắt qua  ≤ 5% tổng số dòng          (tiêu đề chạy ngang hai cột được bỏ qua)
        mỗi bên          ≥ 25% tổng số dòng và ≥ 3 dòng
        hai bên phủ chung theo trục dọc ≥ 50%       (tránh nhầm header trái + footer phải)
```

Điều kiện thứ ba là điều kiện chống nhận nhầm quan trọng nhất: hai khối văn bản ở hai góc chéo nhau của trang thỏa hai điều kiện đầu nhưng không phải hai cột.

Bảng được phát hiện qua đường kẻ (`find_tables` của PyMuPDF), nên bảng dàn bằng khoảng trắng không bị gắn cờ — giới hạn có ý thức: thà bỏ sót còn hơn route nhầm hàng loạt trang sang backend đắt.

### 3.5 Routing, ghép trang và sổ trạng thái

**Gom khoảng.** Danh sách trang cần fallback được gom thành các khoảng liên tiếp; nếu số khoảng vượt hạn mức thì nối các khoảng có khoảng cách nhỏ nhất lại với nhau — OCR thừa vài trang rẻ hơn gọi backend hàng chục lần.

**Ghép.** Kết quả mỗi lần chạy Docling được nhóm theo số trang, rồi dựng lại danh sách section bằng cách duyệt trang 1..n: trang nào có bản Docling thì dùng bản đó, không thì giữ bản PyMuPDF. Section rỗng của Docling bị bỏ qua, để không thay nội dung đã đọc được bằng nội dung trống.

**Sổ trạng thái.** Mỗi trang có một dòng trong `page_report` với ba trường độc lập:

| Trường | Nghĩa |
|---|---|
| `status` | kết luận của bước đo (`text` / `complex_layout` / `needs_ocr` / `empty`) |
| `attempts` | các backend **đã chạy xong** trên trang đó |
| `parsed_by` | backend đang giữ nội dung của trang (`None` = chưa đọc được) |

Ba trường này đủ để phân biệt ba kết cục mà bản cũ gộp chung thành "thành công":

| Kết cục | Dấu hiệu | Hành vi |
|---|---|---|
| chưa ai đọc | `parsed_by = None`, chỉ có một `attempts` | **Err** nêu rõ số trang |
| đã OCR, không có chữ | `parsed_by = None`, `attempts` có backend OCR | Ok + ghi nhận + cảnh báo |
| có text, layout chưa chuẩn | `status = complex_layout`, chưa qua layout backend | Ok + ghi nhận + cảnh báo |

Chi tiết quan trọng: **backend chạy lỗi không được ghi vào `attempts`** — nếu ghi, một lỗi hạ tầng sẽ bị báo cáo thành "trang không có chữ".

Tổng hợp mức tài liệu nằm trong `coverage`: `status` (`complete`/`partial`), số trang đã giải quyết, danh sách trang theo từng kết cục, và khoảng trang bị bỏ do hạn mức.

### 3.6 Ngân sách xử lý

Một đối tượng `_Budget` sống theo vòng đời một lần parse, kiểm tra tại các điểm cố định:

| Hạn mức | Kiểm tại |
|---|---|
| dung lượng file | trước khi mở file |
| thời gian | biên mỗi trang, ở cả lượt 1 và lượt 3 |
| số trang | khi tính phạm vi duyệt; cũng áp cho Docling |
| bytes ảnh | mỗi lần trích một ảnh; hết ngân sách thì dừng trích, **không** dừng parse |

Vượt hạn mức trả về `ParseBudgetExceededError` có trường `limit` — tách bạch với lỗi file hỏng, vì cách xử lý khác nhau: file hỏng thì bỏ, vượt hạn mức thì nới hạn mức hoặc tách file.

---

## 4. Chunker `StructuralChunker`

### 4.1 Đường đi tổng thể

```
ParsedDocument
      │
 build_nodes()    chuẩn hoá + dựng cây Node + lọc mục lục + gom block theo node
      │  list[Node], mỗi Node có blocks
      ▼
 segment()        mỗi Block → list[Unit] theo loại nội dung
      │
      ▼
 pack()           các Unit TRONG MỘT node → các Draft (chia cân bằng, trần cứng)
      │
      ▼
 consolidate()    gộp Draft nhỏ với hàng xóm theo luật LCP
      │
      ▼
 emit (trong chunk())   render content, breadcrumb, overlap, ID tất định, metadata, kiểm tra cuối
      ▼
 list[Chunk]
```

Bất biến kiến trúc: **`pack` chỉ làm việc bên trong một node**, nên chunk không thể vô tình vượt ranh giới chương mục. Việc vượt ranh giới chỉ xảy ra ở `consolidate`, qua **một luật duy nhất**, và luật đó được kiểm lại ở bước emit.

### 4.2 `build_nodes`: dựng cây và lọc mục lục

- **Chuẩn hoá**: `\r\n` → `\n`, Unicode NFC; văn xuôi PDF được nối lại từ bị ngắt bởi dấu gạch nối cuối dòng (`ky-\nthuat` → `kythuat`), rồi gom khoảng trắng trong từng đoạn.
- **Cây bằng heading stack**: gặp heading cấp `L` thì pop stack tới khi đỉnh có cấp < `L`, tạo `Node` với `path` = path của cha + tiêu đề. Heading trùng tiêu đề và trùng cấp với một tổ tiên đang mở thì không tạo node mới (tránh cây giả khi tiêu đề lặp giữa các trang).
- **Chốt chặn heading cho PDF**: cỡ chữ lớn chưa chắc là heading, nên một dòng bị loại khỏi vai trò heading nếu dài hơn 200 ký tự, hơn 25 từ, hoặc kết thúc bằng `.`/`;`/`,` và dài hơn 8 từ.
- **Nhận dạng loại block khi parser không nói rõ**: dòng thứ hai là dòng phân cách `---|---` → bảng; ≥ 60% số dòng khớp mẫu bullet/số thứ tự → danh sách.
- **Mục lục** được nhận bằng máy trạng thái chạy dọc tài liệu, kết hợp bốn tín hiệu: tiêu đề khớp ("Mục lục", "Table of Contents", "Danh mục hình"…), style `TOC n` của Word, ≥ 40% số dòng kết thúc bằng chuỗi dấu chấm dẫn + số trang, ≥ 50% số dòng kết thúc bằng tab/khoảng trắng + số. Trạng thái "đang trong mục lục" **chỉ được kích hoạt** bởi tiêu đề, hoặc bởi tín hiệu cấu trúc nằm trong 20% đầu tài liệu — nhờ vậy danh sách "Mục tiêu học tập" giữa bài không bị nhận nhầm.
- **Block chỉ có ảnh** được gắn vào block text gần nhất trong cùng node (ưu tiên block trước nó), không đứng thành chunk riêng.

### 4.3 `segment`: cắt block thành unit theo loại

Block vừa trần thì là **một unit nguyên khối** — không chia sớm. Chỉ khi vượt trần mới cắt, và cắt theo đơn vị tự nhiên của từng loại:

| Loại | Đơn vị unit | Joiner | Ghi chú |
|---|---|---|---|
| Văn xuôi | câu | `" "` | tách câu có xử lý viết tắt tiếng Việt (`v.v.`, `TS.`, `PGS.`) và số mục (`2.1.`) |
| Bảng | hàng | `"\n"` | mỗi hàng mang theo `header` của bảng |
| Danh sách | item (dòng khớp mẫu bullet + các dòng nối tiếp) | `""` | |
| Code | dòng | `""` | giữ nguyên thụt đầu dòng |

Dưới cùng là `split_bounded`: cắt theo cửa sổ ký tự bằng tìm kiếm nhị phân trên số token, luôn lùi về ranh giới khoảng trắng gần nhất, và **giữ đủ mọi ký tự**. Đây là mức cắt cuối cùng nên vòng lặp chia luôn dừng.

Hai chi tiết nhỏ có chủ đích:
- Unit kết thúc bằng `:` hoặc khớp mẫu caption (`Bảng 2.1:`, `Hình 3.4.`) được đánh `glue_next` để không bị bỏ lại một mình ở cuối chunk.
- Header bảng quá lớn (không thể lặp lại mà vẫn dưới trần) thì bảng được cắt thô theo dòng, header giữ đúng một lần — trần cứng thắng tính thẩm mỹ.

### 4.4 `pack`: chia cân bằng bên trong một node

```
total = số token của cả node
nếu total ≤ max:  per = max          → cả node là MỘT chunk, kể cả khi lớn hơn target
ngược lại:        n = ceil(total / target);  per = total / n
```

Chia cân bằng thay vì greedy: node 1100 token với greedy ra `512 / 512 / 76`; với `per ≈ 367` ra `367 / 367 / 366`.

Điểm cắt được chọn theo ba luật, xét lần lượt cho từng unit:

1. **Trần cứng** — thêm unit vào mà vượt `max_tokens` thì cắt. Luật này luôn thắng, kể cả `glue_next`.
2. **Cắt mềm** — đã đạt `per` và đang ở **ranh giới tự nhiên** (sang block nguồn khác, hoặc unit nối bằng `"\n"`), hoặc đã vượt `per × oversize_tolerance`.
3. **Cách ly mục lục** — block mục lục không bao giờ nằm chung chunk với nội dung thường.

Cuối cùng, nếu phần đuôi nhỏ hơn `min_tokens` và gộp ngược vào phần trước vẫn dưới trần thì gộp. Một unit đơn lẻ mà vẫn vượt trần là lỗi lập trình → `raise` (fail closed, không cắt âm thầm).

### 4.5 `consolidate`: luật LCP

Chỉ draft **nhỏ hơn `min_tokens`** mới đi tìm bạn để gộp. Ứng viên được xét theo thứ tự:

1. draft **kế sau**, nếu nó là node nguyên vẹn (`part_count == 1`)
2. draft **liền trước**, nếu nó là node nguyên vẹn
3. draft kế sau nếu nó là **phần đầu của node con** của draft hiện tại (mẫu "lời dẫn của chương + mục con đầu tiên")

Ưu tiên tiến trước vì lời dẫn ngắn giới thiệu cái đi sau nó. Ưu tiên node nguyên vẹn vì gộp vào một phần của node đã bị chia sẽ kéo path của riêng phần đó lên tổ tiên chung, trong khi các phần còn lại vẫn giữ path cũ.

Một lần gộp bị từ chối nếu:

| Điều kiện từ chối | Lý do |
|---|---|
| có block mục lục | mục lục luôn đứng riêng |
| LCP rỗng mà hai bên có path (khi không bật `merge_across_top_level`) | cấm gộp xuyên chương |
| `len(LCP) < min(len path) − 1` | chỉ cho tổng quát hoá **một cấp**, không kéo chunk lên gốc |
| kết quả vượt `target_tokens` | không nhét draft nhỏ vào chunk đã lớn |

Sau mỗi lần gộp, thuật toán lùi lại một vị trí và xét tiếp — mỗi lần gộp giảm số draft nên quá trình dừng.

### 4.6 `emit`: dựng chunk cuối

**Kiểm tra bất biến trước tiên**: `draft.path` phải đúng bằng LCP của path các run trong nó, sai thì `raise`.

**Render `content`**: với mỗi run, nếu path của run sâu hơn path của chunk thì chèn **tiêu đề con inline** (`"2.1 > 2.1.1"`) làm một dòng riêng; header bảng được chèn **một lần cho mỗi bảng** trước hàng đầu tiên của bảng đó trong chunk này (nhận diện theo `block.source`, không theo nội dung header, vì hai bảng có thể trùng header).

**`embedding_input`** được dựng theo bậc thang, mỗi bậc kiểm lại bằng số token chính xác:

```
breadcrumb + overlap + content
        │ vượt trần → bỏ overlap
breadcrumb + content
        │ vượt trần → bỏ breadcrumb
content
        │ vẫn vượt → raise (fail closed)
```

`breadcrumb` là đường dẫn chương mục (`"Chương 2 > 2.1 Khái niệm"`) bị cắt theo ngân sách token riêng bằng tìm kiếm nhị phân.

**Overlap** chỉ được thêm khi: chunk không phải phần đầu của node, chỉ có một run, cùng node với chunk trước, và hai đầu tiếp giáp đều là văn xuôi. Nó lấy **câu trọn vẹn** từ cuối chunk trước cho tới khi hết ngân sách. Overlap **chỉ nằm trong `embedding_input`**, không nằm trong `content`: nhờ vậy nối `content` của các phần lại đúng bằng nguyên văn section, hai chunk cạnh nhau cùng được trả về thì LLM không đọc câu lặp, mà embedding vẫn thấy ngữ cảnh trước — vốn là lý do overlap tồn tại.

**ID tất định**: `uuid5(namespace, [document_id, phiên bản chunker, chunk_index, heading_path, md5(content)])`. Cùng đầu vào → cùng ID, nên chạy lại pipeline không sinh bản sao mồ côi trong Qdrant; sửa heading mà giữ nguyên nội dung vẫn tạo ID mới vì path nằm trong khóa. `section_id` tính từ `[document_id, path, ordinal của node tổ tiên]`.

**Metadata**: `heading_path`, `heading_level`, `section_id`, `page_start`/`page_end` (min/max trang của các unit), `content_type` (loại block duy nhất, hoặc `"mixed"`), `token_count`, `part_index`/`part_count` — được **tính lại ở bước cuối** theo nhóm chunk thực tế cùng `section_id`, vì `consolidate` có thể đã hút phần đầu của node con sang chunk khác.

### 4.7 Đếm token hai tầng

Chunker đo bằng **đúng tokenizer của embedder** (BGE-m3), chỉ nạp `tokenizer.json` (~17 MB), không nạp model. Tokenizer bị tắt truncation/padding đã lưu sẵn trong file, nếu không phép đếm sẽ bị chính giới hạn đó che mất.

| Tầng | Ở đâu | Cách đếm |
|---|---|---|
| Nhanh | `pack` | đếm trên chuỗi đã render, có cache LRU |
| Chính xác | `emit` | đếm lại toàn bộ `content` và `embedding_input`, kể cả token của dấu phân cách |

Không có nhánh ước lượng kiểu `len/2`: thiếu tokenizer thật thì **báo lỗi cấu hình**. Lúc khởi động, hệ thống còn kiểm tra tokenizer của chunker trùng model của embedder và `embed_max_tokens` bằng `max_length` của embedder — sai lệch cấu hình bị chặn trước khi chạy, không để lộ ra thành chunk bị cắt âm thầm.

---

## 5. Ba nguyên tắc thiết kế xuyên suốt

**1. Đo bằng đơn vị của nơi tiêu thụ.** Embedder tính bằng token thì chunker đếm bằng token, không đếm ký tự. Người đọc tra cứu theo trang thì parser báo cáo theo trang, không báo cáo theo file.

**2. Quyết định ở đơn vị nhỏ nhất còn giữ đủ ngữ cảnh.** Parser quyết định theo *trang* (đơn vị mà một backend có thể xử lý độc lập); chunker đóng gói theo *node* (đơn vị mà ranh giới ngữ nghĩa còn đúng). Việc vượt ra khỏi đơn vị đó luôn đi qua đúng một luật được kiểm chứng.

**3. Fail closed.** Chunk vượt trần token, `heading_path` không phải LCP, thiếu tokenizer, trang chưa backend nào đọc — tất cả đều dừng và báo có tên, thay vì cắt bớt hoặc trả về "thành công" một phần. Mỗi trường hợp ngoại lệ có cờ cấu hình riêng để nới khi cần, nhưng mặc định là chặt.

---

## 6. Cấu hình

Chunker (`CHUNKER__`):

| Biến | Mặc định | Vai trò |
|---|---|---|
| `STRATEGY` | `heading` | `heading` \| `structural` |
| `TARGET_TOKENS` | 400 | kích thước nhắm tới khi chia cân bằng |
| `MAX_TOKENS` | 512 | trần cứng của `content` |
| `MIN_TOKENS` | 64 | dưới ngưỡng này mới xét gộp |
| `OVERLAP_TOKENS` | 48 | ngân sách overlap, chỉ vào `embedding_input` |
| `HEADER_MAX_TOKENS` | 64 | ngân sách breadcrumb |
| `EMBED_MAX_TOKENS` | 1024 | phải bằng `EMBEDDER__MAX_LENGTH` |
| `OVERSIZE_TOLERANCE` | 1.15 | mức vượt `per` được phép trước khi cắt ngoài ranh giới tự nhiên |
| `TOKENIZER_PATH` | (trống) | `tokenizer.json` bake sẵn trong image |
| `INDEX_TOC` | `false` | giữ mục lục (luôn ở chunk riêng) |
| `MERGE_ACROSS_TOP_LEVEL` | `false` | cho phép gộp xuyên chương |

Parser PDF (`PARSER_`):

| Biến | Mặc định | Vai trò |
|---|---|---|
| `PDF_MIN_PAGE_CHARS` | 40 | ngưỡng "trang thiếu text" |
| `PDF_SCAN_IMAGE_COVERAGE` | 0.5 | độ phủ ảnh để kết luận trang scan |
| `PDF_DETECT_TABLES` | `true` | bật phát hiện bảng |
| `PDF_PAGE_FALLBACK_ENABLED` | `true` | bật OCR/layout cho trang thiếu |
| `PDF_FULL_FALLBACK_PAGE_RATIO` | 0.5 | tỉ lệ trang khiến hệ thống chạy cả file |
| `PDF_MAX_FALLBACK_RANGES` | 8 | số lần gọi backend layout tối đa |
| `PDF_STRICT_MISSING_TEXT` | `true` | còn trang chưa ai đọc → Err |
| `PDF_MAX_FILE_BYTES` | 256 MB | ngân sách dung lượng |
| `PDF_TIMEOUT_SECONDS` | 600 | ngân sách thời gian |
| `PDF_EXTRACT_IMAGES` | `false` | trích bytes ảnh |
| `PDF_MAX_IMAGE_BYTES` | 64 MB | trần bytes ảnh |
