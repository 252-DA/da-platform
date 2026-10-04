# Viewer tài liệu + chat: bàn giao cho hai nhánh song song

Mục tiêu bản này: hai người làm được song song mà không chờ nhau. Phần nối chung
(đọc file, đọc chunk theo trang, thu hẹp RAG theo tài liệu) **đã vá sẵn**; hai
track bên dưới chỉ gặp nhau ở một hợp đồng nhỏ.

## Đã có sẵn, dùng ngay

### 1. Bytes của tài liệu

`GET /api/documents/<document_id>/file?sid=<session>` (route của web).

Trình duyệt **không** gọi MinIO trực tiếp — MinIO nằm trong mạng nội bộ. Route
xin URL đọc hạn 5 phút từ core-api, fetch ở phía server rồi stream lại, đúng
chiều ngược của route upload đang chạy. Header `Range` được chuyển tiếp nguyên
vẹn nên PDF.js tải từng phần được.

Dưới nó: `GetDocumentFileUrl` (gRPC) → `DocumentService.getDocumentFileUrl` →
`DocumentStorageService.createPresignedDownloadUrl`. Tài liệu còn `UPLOADING`
thì trả 400.

### 2. Nội dung theo trang

`GET /api/documents/<document_id>/chunks?page=<N>` — bỏ `page` thì trả cả tài
liệu, theo `sort_order`.

Đây là đường cho câu hỏi "giải thích trang này": tra cứu chính xác theo
`(document_id, page_number)` trong Postgres, **không đụng Qdrant**. Qdrant chỉ
dùng cho câu hỏi nối tiếp.

gRPC: `GetDocumentChunks { documentId, page? }`. `page` phải là số nguyên ≥ 1.

### 3. RAG thu hẹp trong tài liệu đang mở

MCP tool `search_course_chunks` giờ nhận `document_ids: list[str]`. Các tầng
dưới (`SearchRequest` → `SearchFilter` → Qdrant filter) vốn đã hỗ trợ, chỉ thiếu
tham số ở tool. Bỏ trống = tìm cả khoá học.

Sửa ở cả `mcp-service/` (bản đang chạy) và `packages-ai/` (bản gốc) để hai bên
không lệch nhau.

## Track A — Viewer

Phạm vi: route viewer trong LTI tool hiện có (web :3001), PDF.js, thanh điều
hướng trang, và **phát ra số trang đang xem**.

- Dùng (1) cho bytes, (2) cho text của trang nếu cần hiển thị/ chọn đoạn.
- **Chỉ làm PDF trước.** PPTX phải convert sang PDF lúc ingest (LibreOffice
  headless trong worker) — chưa ai làm, xem "Việc chưa có chủ" bên dưới.
- **DOCX nằm ngoài phạm vi**: `docx_parser.py` đặt `page_count=0`, chunk không có
  `page_number`, nên "trang đang mở" không có nghĩa.
- Không cần đợi Track B: chat có thể là một panel rỗng cho tới khi B xong.

## Track B — Chat neo theo tài liệu

Phạm vi: đường lấy ngữ cảnh theo `(document_id, page_number)` cho ai-tutor.

Trạng thái hiện tại, đọc kỹ trước khi thiết kế:

- `TutorRequest.lo_code` **bắt buộc** (`ai-tutor/src/ai_tutor/models.py`).
- Adapter chỉ gọi đúng một tool: `retrieve_quiz_context`
  (`ai-tutor/src/ai_tutor/adapters/learning_context.py`), tool này resolve LO →
  `list_chunks_for_lo(lo_id)`.
- Hệ quả: **tài liệu chưa có `chunk_lo_mappings` thì tutor không với tới được**,
  dù đã index xong. Nới `lo_code` thành optional là chưa đủ.

Đề xuất: thêm một đường ngữ cảnh riêng nhận `document_id` + `page_number`, lấy
chunk của trang làm ngữ cảnh chính (qua (2) hoặc `IMetadataStore.list_chunks`),
rồi dùng `search_course_chunks(document_ids=[...])` cho câu hỏi nối tiếp.
`TutorCitation` đã có sẵn `document_id` + `page_number` nên viewer nhảy tới
trang nguồn được ngay, không cần đổi model.

## Hợp đồng giữa hai track

Chỉ có một thứ: **viewer gửi gì khi hỏi**.

```jsonc
{
  "document_id": "uuid",
  "page_number": 7,        // trang đang mở; null nếu tài liệu không có trang
  "message": "giải thích slide này",
  "history": []
}
```

Chốt cái này trước rồi hai bên tự làm. A mock response, B mock request.

## Việc chưa có chủ, cần chốt

1. **PPTX → PDF lúc ingest.** Không có nó thì viewer chỉ mở được PDF. Ai làm?
2. **Grading.** Schema **chưa có bảng annotation/highlight/comment nào**. AGS thì
   đã có đủ (`core-api/src/ags/`, đang chạy cho quiz), nên phần thiếu là mô hình
   annotation + luồng chấm trên tài liệu — cỡ ngang cả phần viewer. Vào v1 hay v2?
3. **Tài liệu chưa map LO thì chat xử lý sao?** Chặn chat, hay trả lời thuần
   theo tài liệu? (xem Track B)
4. **Slide toàn hình.** `docling_do_picture_description=False`; chunk của slide
   chỉ có diagram gần như rỗng. Hai hướng: bật VLM lúc ingest (chậm, sai là hỏng
   vĩnh viễn trong index), hoặc gửi ảnh trang kèm câu hỏi (viewer đã có sẵn ảnh).
5. **Filter theo page trong Qdrant.** `_build_filter` chưa có điều kiện
   `page_number` dù payload có lưu. Chỉ cần khi muốn "tìm quanh trang này" —
   chưa chặn gì, làm sau.

Không cần đường read-by-document ở vector store: Postgres đã giữ `content`.

## Nhánh và trạng thái

`core-api` và `web` là submodule, đang ở `dev`; `packages-ai`, `ai-tutor`,
`worker` ở `feat/model-routing`. `mcp-service` **không phải submodule** — nó nằm
ngay trong meta-repo.

Các thay đổi trên **chưa commit**: nằm ở working tree của `core-api`, `web`,
`packages-ai` (submodule) và của meta-repo (`mcp-service/`,
`contracts/proto/core_api.proto`, file này).

Chạy lại kiểm tra:

```sh
cd core-api && npx jest                       # 180 passed
cd packages-ai && .venv/bin/python -m pytest tests/unit -q
cd web && npx tsc --noEmit
```
