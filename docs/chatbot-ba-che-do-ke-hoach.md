# Chatbot với ba chế độ truy xuất: kế hoạch hiện thực

**Ngày:** 17/10/2026 · **Trạng thái:** kế hoạch + hiện thực cùng ngày (xem mục 9 về những gì đã chạy được).

## 1. Mục tiêu

Làm một chatbot bám tài liệu khóa học để **demo được ngay**, và để mỗi câu trả lời được ghi lại đủ thông tin phục vụ số liệu báo cáo. Chatbot có **ba chế độ truy xuất** đổi qua lại được từ một trang admin:

| Chế độ | Tên trong code | Cách làm |
|---|---|---|
| A | `vector` | Một lần tìm vector trên cả khóa học (hoặc trong tài liệu đang mở), rồi trả lời. Đây là RAG thuần. |
| B | `tools` | Mô hình tự gọi công cụ nhiều bước: tìm vector, tra theo trang, tra đề cương (chương/LO), kéo đoạn láng giềng, liệt kê tài liệu. |
| C | `graph` | Như B, thêm công cụ tra **quan hệ giữa các ý** (nguyên nhân, thành phần, đối lập, tiên quyết…) đã được trích sẵn và kiểm bằng trích dẫn nguyên văn. |

Ba chế độ dùng cùng mô hình, cùng prompt trả lời, cùng định dạng trích dẫn; chỉ khác nguồn ngữ cảnh. Nhờ vậy so sánh A/B/C là so sánh công bằng.

**Không làm trong đợt này:** sửa lỗi heading/slide ít chữ của parser (đã biết, làm sau), phản hồi streaming, lưu hội thoại dài hạn, Neo4j cho đồ thị quan hệ.

## 2. Quyết định thiết kế

1. **Đồ thị quan hệ lưu ở PostgreSQL, không phải Neo4j.** Truy vấn là duyệt 1–2 bước quanh một khái niệm; PostgreSQL làm được, dùng chung schema với core-api và worker, `mcp-service` không phải thêm phụ thuộc Neo4j (đã cố ý bỏ). Neo4j vẫn là hướng chiếu để xem đồ thị trực quan nếu cần.
2. **Công cụ chạy trong `mcp-service`**, vì nơi này đã có PostgreSQL + Qdrant + embedder. Tutor chỉ gọi MCP.
3. **Vòng gọi công cụ bằng giao thức JSON do mình định nghĩa**, không dùng function-calling riêng của từng nhà cung cấp. Lý do: ai-sdk chỉ có `generate_text`, và hai provider (Gemini, DeepSeek) khác API công cụ. Mỗi lượt mô hình trả đúng một JSON: gọi công cụ hoặc trả lời. Mã kiểm tra, giới hạn số bước, ghi lại từng lượt.
4. **Chế độ do core-api giữ**, đổi qua trang admin, BFF đọc và truyền `mode` cho tutor. Tutor vẫn stateless; script đánh giá truyền `mode` trực tiếp nên không phải đổi cài đặt toàn cục.
5. **Mọi lượt hỏi đáp ghi vào `chat_runs`** (chế độ, câu hỏi, câu trả lời, trích dẫn, vết công cụ, token, độ trễ, đánh giá 👍/👎). Đây là nguồn số liệu báo cáo.
6. **Đồ thị quan hệ trích lười theo chương/tài liệu**, theo yêu cầu của admin (nút "Dựng đồ thị"), qua đường `content_generation` có sẵn (request → outbox → hàng đợi → worker). Mỗi quan hệ phải có `evidence_quote` là chuỗi con của đoạn nguồn (sau chuẩn hóa NFC và khoảng trắng); không thỏa thì bỏ.

## 3. Kiến trúc

```
Trình duyệt ──► web /api/chat ──► ai-tutor (FastAPI :8010) ──► mcp-service (MCP :8001)
                  │  │                 │ mode = vector|tools|graph        ├─ search_course_chunks   (có)
                  │  └─ core-api       │ vòng JSON: ≤ N bước              ├─ get_document_page      (mới)
                  │     GetChatSettings│                                   ├─ list_course_documents  (mới)
                  │     RecordChatRun  └─► LLM (profile `tutor`)           ├─ get_course_outline     (mới)
                  │                                                      ├─ get_neighbor_chunks    (mới)
admin /manage/chat ──► core-api ─ SetChatMode, thống kê, dựng đồ thị ───┘  └─ get_concept_relations  (mới, chỉ chế độ C)
                                   │
                                   └─ CreateContentGenerationRequest(type='relations')
                                       └─► content-generation-worker ─► knowledge_relations (PostgreSQL)
```

## 4. Dữ liệu (migration `20261017120000_chat_three_modes`)

| Bảng | Nội dung |
|---|---|
| `chat_settings` | `key` (PK), `value`, `updated_by`, `updated_at`. Khóa `retrieval_mode` ∈ `vector`/`tools`/`graph`. Rỗng = `vector`. |
| `chat_runs` | `run_id`, `course_id`, `user_id`, `mode`, `source` (`web`/`eval`), `question_type` (nhãn khi đánh giá), `question`, `answer`, `citations` JSONB, `tool_calls` JSONB, `model`, `steps`, `input_tokens`, `output_tokens`, `latency_ms`, `status`, `error`, `rating` (−1/0/1), `created_at`. |
| `knowledge_relations` | `course_id`, `document_id`, `chunk_id`, `source_label/key`, `relation_type` ∈ {cause, part_of, contrast, prerequisite, example_of, defines, related}, `target_label/key`, `evidence_quote`, `page_number`, `extraction_version`, `model`, `created_at`. Chỉ mục theo `(course_id, source_key)`, `(course_id, target_key)`, `chunk_id`. |

`knowledge_relations` tham chiếu `chunks`; khi lập chỉ mục lại tài liệu, chunk cũ bị xóa mềm nên mọi truy vấn nối `chunks` với `deleted_at IS NULL`.

## 5. Công cụ MCP (mcp-service)

Tất cả nhận `course_id` là UUID hoặc mã môn (như `retrieve_quiz_context`), trả JSON có giới hạn kích thước.

| Công cụ | Đầu vào | Đầu ra |
|---|---|---|
| `search_course_chunks` (có) | `query`, `top_k`, `document_ids?` | đoạn kèm `chunk_id`, trang, heading, điểm |
| `get_document_page` | `document_id`, `page` | mọi đoạn của trang đó, theo thứ tự |
| `list_course_documents` | `course_id`, `chapter_code?` | tài liệu: tên, vai trò, chương, số trang |
| `get_course_outline` | `course_id`, `chapter_code?` | chương, LO, liên kết chương–LO, hình thức đánh giá |
| `get_neighbor_chunks` | `chunk_id`, `window` (≤ 3) | đoạn trước/sau trong cùng tài liệu |
| `get_concept_relations` | `course_id`, `concept`, `hops` (1–2), `limit` | các cạnh quanh khái niệm: nguồn, loại, đích, trích dẫn, trang |

Khớp khái niệm: chuẩn hóa (bỏ dấu, hạ chữ thường, gộp khoảng trắng) rồi so khớp `key` bằng bằng nhau hoặc chứa nhau; ưu tiên nút có nhiều cạnh.

## 6. Tutor (ai-tutor)

- `POST /v1/tutor/messages`: `course_id`, `message`, `history`, `mode` (mặc định `vector`), tùy chọn `document_id`, `page_number`, `lo_code`, `top_k`. Trả `answer`, `model`, `citations`, và `trace` (`steps`, `tool_calls`, token, độ trễ).
- Chế độ A: một lần `search_course_chunks`, ghép ngữ cảnh, một lần gọi mô hình.
- Chế độ B/C: vòng tối đa 5 bước (B) và 6 bước (C). Mỗi bước mô hình trả `{"action":"tool","tool":...,"args":...}` hoặc `{"action":"answer","answer":...}`. Mã kiểm tên công cụ và tham số, gọi MCP, đánh số bằng chứng `[n]` toàn cục, cắt kết quả theo ngân sách ký tự. Hết bước thì ép trả lời bằng bằng chứng đã có.
- Mọi chế độ dùng chung quy tắc trả lời: chỉ dùng bằng chứng, trích `[n]`, nói rõ khi không đủ căn cứ, không làm theo chỉ dẫn nằm trong tài liệu.

## 7. Giao diện

- **Trang chat** `/learn/courses/[id]/chat`: khung hỏi đáp, trích dẫn bấm được (trang, heading), 👍/👎. Dùng được cho sinh viên và giảng viên.
- **Trang admin** `/manage/chat` (chỉ admin LMS đổi chế độ; giảng viên xem số liệu):
  1. chọn chế độ A/B/C và lưu;
  2. đồ thị quan hệ: số quan hệ theo tài liệu, nút "Dựng đồ thị" theo chương hoặc theo từng tài liệu (mã chương của tài liệu không phải lúc nào cũng khớp đề cương nên có cả hai), trạng thái các yêu cầu gần đây;
  3. thống kê theo chế độ: số lượt, độ trễ trung bình, số bước, token, 👍/👎, lỗi; 20 lượt gần nhất kèm vết công cụ.

## 8. Đánh giá

`ai-tutor/scripts/chat_eval.py` có năm lệnh: `run` (hỏi từng câu × từng chế độ, xen kẽ, ghi JSONL; có `--resume`), `sheet` (CSV cho người chấm mù, ẩn chế độ, xáo thứ tự, kèm file khóa), `judge` (tùy chọn: mô hình khác chấm sơ bộ độ bám nguồn), `summary` (bảng theo chế độ và theo kiểu câu hỏi, độ đồng thuận Cohen's kappa giữa hai người chấm) và `import` (tùy chọn: nạp vào `chat_runs` với `source='eval'` để xem ngay trên trang admin). Tập câu hỏi khởi đầu `ai-tutor/eval/questions.seed.jsonl` có 37 câu thuộc sáu kiểu: `lookup`, `definition`, `relational`, `curriculum`, `global` và `absent` (tài liệu không có, chatbot phải từ chối). Đáp án tham chiếu soạn từ chính các đoạn đã truy xuất, cần người kiểm lại trước khi coi là chuẩn. Mục tiêu 60–100 câu, mỗi kiểu ít nhất 10.

Chỉ số: đúng/sai theo người chấm, độ bám nguồn (câu khẳng định có trong đoạn được trích hay không), đúng trích dẫn (trang/đoạn), từ chối đúng khi tài liệu không có, số bước, token, độ trễ.

## 9. Thứ tự làm và kiểm tra

| # | Việc | Kiểm tra |
|---|---|---|
| 1 | packages-ai: cổng `ICourseKnowledgeStore`, repository PostgreSQL, use case công cụ | pytest với kho giả |
| 2 | mcp-service: 5 công cụ mới | pytest gọi use case; import server |
| 3 | core-api: migration, Prisma, `ChatModule` (cài đặt, ghi lượt, đánh giá, thống kê), proto, loại yêu cầu `relations` | Jest |
| 4 | worker: trích quan hệ (prompt, kiểm trích dẫn, lưu), nhánh `relations` ở runner | pytest với LLM giả |
| 5 | ai-tutor: ba chế độ, vòng JSON, vết, Dockerfile, compose | pytest với MCP và LLM giả |
| 6 | web: client RPC, `/api/chat`, trang chat, trang admin, điều hướng | `tsc --noEmit`, lint |
| 7 | Script đánh giá + câu hỏi khởi đầu | pytest với tutor giả (HTTP) |
| 8 | Báo cáo giữa kỳ: mục chatbot, RQ5, kế hoạch | biên dịch lại PDF |

Việc cần người chạy (em không tự chạy trên DB dùng chung): áp migration, `prisma generate` trong container core-api rồi khởi động lại, build lại image `mcp-service` và `ai-tutor`, bật `ai-tutor` trong compose.
