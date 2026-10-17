# Diagram phục vụ phát triển DA Platform

[Mở bộ Archify mới nhất](../.archify/index.html) · [Tải bộ HTML offline](../.archify/architecture-development-20261017-150028/architecture-development.zip).

Bản ngày **17/10/2026** đối chiếu source ở root `0dcba7642caf` và revision riêng của từng submodule. Có **54 diagram thuộc 8 loại**, ERD bao phủ **43 bảng, 430 cột và 64 FK**; danh mục **50 RPC và 30 Web route handlers**. Đây là bản mô tả code và cấu hình trong repo; database đang chạy chưa được introspect.

| Cần phát triển phần nào | Diagram |
|---|---|
| Kiến trúc, module, ownership và contracts | 01–07, 51–52 |
| Schema và quan hệ dữ liệu | 08–17; [từ điển dữ liệu](../.archify/architecture-development-20261017-150028/schema.html) |
| LTI, upload, generation và làm bài | 18–25 |
| Asset Processor: setup, notice, tải file, chấm và report | 26–29, 42 |
| AI Tutor độc lập | 30 |
| Curriculum, kiểm chứng quiz và duyệt nội dung | 31–33, 43–44 |
| Ingestion, retrieval và model routing | 34–37 |
| Outbox, grading và các trạng thái nền | 38–41, 53–54 |
| Triển khai, observability và CI | 45–47 |
| Canvas sync, enrichment và projection/delete | 48–50 |

Mỗi hình có HTML tương tác, `candidate.json`, Mermaid và receipt kiểm tra. Trang tra cứu hỗ trợ tìm theo chức năng, lọc loại diagram, mở riêng và xuất hình từ Viewer. Các nhãn và ghi chú bằng tiếng Việt; UI Viewer của Archify fallback tiếng Anh.

Các tài liệu đi kèm:

- [API và contracts](../.archify/architecture-development-20261017-150028/interfaces.html): protobuf RPC, handler target, Web routes và phạm vi các contract JSON.
- [Triển khai và queue ownership](../.archify/architecture-development-20261017-150028/operations.html): Compose, ports/profiles, producer/consumer và lệnh kiểm tra CI hiện có.
- [Thay đổi và giới hạn](../.archify/architecture-development-20261017-150028/changes.html): các khác biệt với bộ ngày 04/10, tính năng chạy riêng và thiết kế chưa nối vào runtime.
- [Source và kiểm tra](../.archify/architecture-development-20261017-150028/evidence.html): 271 range trong 75 file, pin theo đúng repo; kết quả các gate của từng hình.
- [ERD Mermaid toàn schema](../.archify/architecture-development-20261017-150028/full-schema.mmd): đủ 43 bảng / 64 FK, bổ sung cho các hình chia nhóm.

Các thay đổi đáng chú ý: tự luận ngắn chấm theo `grading_input` snapshot; AI lỗi chuyển `NEEDS_REVIEW` và giữ `AWAITING_GRADE`; có luồng chấm tay/chấm lại; bài luận dạng file đi qua Asset Processor và Asset Report; worker đọc model binding theo task với TTL 30 giây. AI Tutor hiện là service riêng. Tài liệu learning-agent đang sửa trong `docs/` chưa được coi là runtime hiện hành.

Tất cả diagram đã qua các gate tự động và kiểm tra trên Chrome. Một số hình tiêu biểu được chụp và đọc bằng mắt; mức kiểm tra được ghi riêng trong evidence. Không có waterfall hiệu năng vì chưa có trace đo thực tế.

## Tạo lại bộ này

Các recipe và candidate nằm trong thư mục output:

```bash
python3 .archify/architecture-development-20261017-150028/build.py
python3 .archify/architecture-development-20261017-150028/finalize.py
python3 .archify/architecture-development-20261017-150028/package.py
```

`finalize.py` dùng Archify CLI đã cài trên máy, cần chỉnh `CLI` khi chuyển môi trường. `package.py` cần PyYAML để đọc Compose. `build.py` tạo lại các candidate từ recipe và schema; chỉnh recipe nếu muốn giữ thay đổi sau lần build kế tiếp. Giữ revision nguồn trong `repositories.json` và xem `source-audit.json` khi đối chiếu.

`.archify/` là output local đang được `.gitignore` bỏ qua trong repo. Dùng ZIP để chia sẻ HTML, candidates, receipts và recipe. Bộ ngày 04/10 vẫn được giữ trong thư mục cũ; `.archify/index.html` trỏ tới bản ngày 17/10.
