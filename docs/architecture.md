# Diagram phục vụ phát triển DA Platform

[Mở bộ Archify mới nhất](../.archify/index.html) · [Tải bộ HTML offline](../.archify/architecture-development-20261019-171859/architecture-development.zip) · [Kết quả kiểm tra code](../.archify/architecture-development-20261019-171859/review.html).

Bản ngày **19/10/2026** có **62 diagram thuộc 8 loại**, ERD bao phủ **52 bảng, 529 cột và 82 FK**; danh mục **75 RPC và 38 Web route handlers**. Source được pin theo root `96ce40ac651e` và HEAD riêng của từng submodule đang checkout. Chưa introspect database hoặc chạy full-stack E2E.

Working tree trước tác vụ đã thay đổi `ai-tutor`, `core-api`, `web`, `report` và `contracts/proto/core_api.proto`. Ba RPC hội thoại mới có trong proto local nhưng chưa commit ở meta-repo: proto tại root revision chỉ có 72 RPC, trong khi proto working tree và Core/Web đang khớp 75 RPC. Các source range trong diagram được đối chiếu với committed bytes của đúng repo; inventory proto local được ghi riêng trong [RPC provenance](../.archify/architecture-development-20261019-171859/rpc-provenance.json).

| Cần phát triển phần nào | Diagram |
|---|---|
| Kiến trúc, module, ownership và contracts | 01–07, 51–52 |
| Schema và quan hệ dữ liệu | 08–17, 55–56; [từ điển dữ liệu](../.archify/architecture-development-20261019-171859/schema.html) |
| LTI, upload, generation và làm bài | 18–25 |
| Asset Processor: setup, notice, tải file, chấm và report | 26–29, 42 |
| AI Tutor: vector, tools và graph | 30, 57–59, 62 |
| Curriculum, kiểm chứng quiz và duyệt nội dung | 31–33, 43–44 |
| Ingestion, retrieval và model routing | 34–37 |
| Outbox, grading và các trạng thái nền | 38–41, 53–54 |
| Triển khai, observability và CI | 45–47 |
| Canvas sync, enrichment và projection/delete | 48–50 |
| Micro-content: video, quyền xuất bản, progress và chấm | 55, 60–61 |

Web đã gọi Tutor qua HTTP/SSE; Core lưu hội thoại, lượt hỏi đáp, rating và cấu hình retrieval mode. Chế độ graph của chatbot đọc `knowledge_relations` trong PostgreSQL, khác luồng projection heading/concept ở Neo4j. Worker đã có extraction kiểm quote nguyên văn và generation theo batch tối đa 60 scopes.

Micro-content có CRUD, video và attempt RPC ở Core; UI video vẫn là phần khung, chưa nối upload/AI. Queue script/render chưa có consumer; payload chấm tự luận micro-content chưa khớp parser của worker. Sơ đồ 60–61 ghi rõ các giới hạn này. AGS đã có recovery `POSTING` quá 2 phút lúc startup; Asset Report dùng lease 2 phút; outbox reclaim `PROCESSING` dựa trên `occurred_at` quá 10 phút.

Các tài liệu đi kèm:

- [API và contracts](../.archify/architecture-development-20261019-171859/interfaces.html): RPC, handler target, Web routes, MCP tools và phạm vi proto chưa commit.
- [Triển khai và queue ownership](../.archify/architecture-development-20261019-171859/operations.html): Compose, ports/profiles và producer/consumer.
- [Thay đổi và giới hạn](../.archify/architecture-development-20261019-171859/changes.html): khác biệt với bộ ngày 17/10.
- [Kiểm tra code](../.archify/architecture-development-20261019-171859/review.html): 5 phát hiện kèm source và revision; đã chạy 7 suites / 72 unit tests, kiểm gRPC, content schema và model catalog. Kiểm tra CI pins thất bại ở 3 dependency.
- [Source và kiểm tra hình](../.archify/architecture-development-20261019-171859/evidence.html): 319 range trong 88 file, receipts của 62 diagram và ảnh tiêu biểu.
- [ERD Mermaid toàn schema](../.archify/architecture-development-20261019-171859/full-schema.mmd): đủ 52 bảng / 82 FK.

Mỗi diagram có HTML tương tác, `candidate.json`, Mermaid và receipt. Cả 62 hình đã qua các gate tự động và kiểm tra trên Chrome; 4 hình tiêu biểu được kiểm bằng mắt ở light/dark. Nhãn và ghi chú bằng tiếng Việt; UI Viewer fallback tiếng Anh. Không có số liệu timing hoặc waterfall hiệu năng đo thực tế.

## Tạo lại bộ này

Recipe, candidate và revision nguồn nằm trong thư mục output:

```bash
python3 .archify/architecture-development-20261019-171859/build.py
python3 .archify/architecture-development-20261019-171859/review.py
python3 .archify/architecture-development-20261019-171859/finalize.py
python3 .archify/architecture-development-20261019-171859/package.py
```

`build.py` dùng `refresh.py` để cập nhật các source range và nội dung đã đối chiếu. `finalize.py` cần Chrome và Archify CLI; sửa `CLI` khi chuyển máy. `package.py` cần PyYAML. `review.py` lưu các kết quả kiểm tra của lần review này; chạy lại các lệnh trong `code-review.json` nếu source thay đổi. Muốn đối chiếu đúng snapshot cũ, dùng revision trong `repositories.json`, không chỉ gitlink root.

`.archify/` là output local đang được `.gitignore` bỏ qua; dùng ZIP để chia sẻ. Các bộ 04/10 và 17/10 được giữ nguyên; `.archify/index.html` trỏ tới bản ngày 19/10.
