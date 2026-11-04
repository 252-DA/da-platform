# Rà soát khả năng demo và bảo vệ — 03/11/2026

Phạm vi theo trao đổi: sinh quiz, tóm tắt, AI sinh video từ tài liệu, và xử lý/tóm tắt video có sẵn. Chưa có ngày bảo vệ nên báo cáo này xác định thứ tự ưu tiên, chưa cam kết thời gian hoàn thành.

Đã đọc code, chạy kiểm thử sẵn có, kiểm tra container và readiness, đọc số liệu tổng hợp từ database và Redis đang chạy. Database được truy vấn trong transaction `READ ONLY`; không tạo nội dung bằng model, retry job, sửa cấu hình hay thay đổi dữ liệu. Chưa thao tác đầy đủ từ tài khoản giảng viên/học viên trên trình duyệt, chưa gọi STT/render thật và chưa đánh giá chất lượng đầu ra bằng chuyên gia. Kiểm thử qua không đồng nghĩa toàn bộ sản phẩm sẵn sàng bảo vệ.

## 1. Kết luận theo chức năng bắt buộc

| Chức năng | Bằng chứng hiện có | Phần phải hoàn thành hoặc xác nhận |
| --- | --- | --- |
| Sinh quiz | Database có 34 request `SUCCEEDED`, đều có `generated_count > 0`; 7 request `FAILED`. Có 76 câu chưa xóa: 25 `PUBLISHED`, 6 `APPROVED`, 38 `GENERATED_DRAFT`, 7 `CHANGES_REQUESTED`. | Chạy lại một kịch bản hoàn chỉnh: chọn tài liệu/LO → sinh → kiểm tra → duyệt → tạo đề → học viên làm → lưu kết quả. Đánh giá chất lượng câu bằng người có chuyên môn. |
| Tóm tắt dưới dạng lesson card | Đã có use case sinh, kiểm chứng, lưu, duyệt và xuất bản; có trang đọc cho học viên. Database hiện có **0 lesson card**; chưa có request loại `card`. Hàng đợi `document_enrichment` có **10 job failed, 0 completed**. | Khôi phục đường sinh tóm tắt; cung cấp đường gọi rõ ràng từ giao diện; tạo, duyệt và đọc được một bộ card thật. Nếu yêu cầu là tóm tắt toàn bộ tài liệu thì cần chốt đầu ra đó riêng với card theo ý/LO. |
| AI sinh video | Đã có metadata, lưu kịch bản và lệnh phát event yêu cầu sinh/render. | Nút sinh AI đang bị khóa; chưa tìm thấy consumer cho queue video trong source/compose đã kiểm tra. Cần nối giao diện, worker sinh kịch bản, renderer và kết quả phát được. |
| Xử lý video có sẵn | Có service tạo URL upload/phát video MinIO và các bảng video/transcript/segment. Có bản thử tìm caption YouTube độc lập. | Giao diện chọn file chưa gọi upload; chưa tìm thấy pipeline STT → segment → tóm tắt/index cho file upload. Bản thử YouTube chưa thay thế được luồng này. |

Database hiện có 3 micro-content nháp: 2 chọn nguồn AI, 1 chọn upload; cả 3 đều `video_status=NONE`. Các bảng `videos`, `video_segments`, `transcript_segments` đều chưa có dữ liệu. Đây là trạng thái của database được kết nối trong lần kiểm tra, không đại diện cho các môi trường khác.

## 2. Những chỗ chặn demo

### A. Tóm tắt: đã có nền nhưng chưa có đầu ra sử dụng được

- [Use case sinh card](../worker/worker/use_cases/generate_lesson_cards.py:203) đã có sinh từ nguồn, kiểm chứng/sửa và lưu; [worker sinh nội dung](../worker/worker/runners/content_generation_worker.py:188) xử lý được `type=card`.
- [API web tạo yêu cầu](../web/src/app/api/content-generations/route.ts:144) hiện tạo `type=quiz`. Trong các caller web đã kiểm tra, chưa tìm thấy đường yêu cầu sinh card chủ động từ giao diện. Enrichment tự động là đường khác, nhưng đang có 10 job lỗi.
- Đọc 10 job enrichment lỗi: 6 job báo tất cả section sinh lỗi, 4 job báo `job stalled more than allowable limit`. Chưa xác định được lỗi gốc ở từng lời gọi model; không được suy ra rằng tất cả đều do API key hoặc chất lượng prompt.
- [Duyệt card](../core-api/src/review/review.service.ts:58), [xuất bản lesson](../core-api/src/lesson/lesson.service.ts:83), [trang học viên đọc card](../web/src/app/learn/lessons/[id]/page.tsx:45) đã tồn tại. Việc cần làm là nối và chứng minh luồng này bằng dữ liệu thật, không xây lại từ đầu.

Điều kiện hoàn thành: chọn tài liệu/LO ở giao diện, tạo được bộ tóm tắt bám nguồn, thấy trạng thái thành công/lỗi, giảng viên sửa/duyệt/xuất bản, học viên đọc được. Có mẫu đối chiếu với tài liệu gốc.

### B. AI sinh video: thiếu thành phần thực thi

- [Nút sinh kịch bản](../web/src/app/manage/micro-content/[id]/edit/video-panel.tsx:123) đang `disabled`.
- [Yêu cầu sinh kịch bản](../core-api/src/micro-content/micro-content.service.ts:411) và [yêu cầu render](../core-api/src/micro-content/micro-content.service.ts:523) mới tạo outbox event. [Outbox](../core-api/src/outbox/outbox.service.ts:137) chuyển sang queue `micro_content_video`.
- Trong source, danh sách worker và compose đã kiểm tra, chưa có consumer nhận `MICRO_CONTENT_SCRIPT_REQUESTED` / `MICRO_CONTENT_RENDER_REQUESTED`; queue đó cũng chưa có job hoàn tất.
- Chưa tìm thấy tích hợp TTS/renderer tạo file video trong luồng ứng dụng hiện tại. API nhận yêu cầu thành công chưa chứng minh sinh được MP4.

Phạm vi tối thiểu đề xuất: từ nội dung đã duyệt, tạo kịch bản một số cảnh ngắn, giảng viên xem/sửa, render video có hình và lời thuyết minh, lưu file và phát được. Nếu yêu cầu cho phép video dạng slide thuyết minh thì chốt dạng này trước; chưa mở rộng sang hoạt hình hoặc avatar.

### C. Video đầu vào: thiếu upload hoàn chỉnh và pipeline xử lý

- [Ô chọn file](../web/src/app/manage/micro-content/[id]/edit/video-panel.tsx:102) chưa có handler gửi file; chưa có các route BFF upload/confirm/video URL tương ứng trong thư mục API micro-content đã kiểm tra.
- [Core video service](../core-api/src/micro-content/micro-content-video.service.ts:17) đã có presigned upload/download, nhưng lưu và phát file là một bước riêng với nhận dạng lời nói và tóm tắt.
- Chưa tìm thấy triển khai STT cho file đầu vào, tạo transcript có timestamp rồi đưa sang luồng tóm tắt/index. Database cũng chưa có transcript/segment để kiểm chứng.
- [Video MCP pilot](../video-mcp/README.md:1) hiện tìm YouTube, lấy caption và chọn đoạn nhúng; [tài liệu pilot](youtube-video-pilot.md:13) ghi rõ phần tích hợp, lưu và publish còn là bước tiếp theo. Không nên trình bày bản thử này như tính năng xử lý file video đã hoàn tất.
- Chưa tìm thấy màn học viên phát micro-content video và gọi API tiến độ/nộp bài trong cây route hiện tại. Đây là phần cần nối nếu demo video gắn bài tập.

Điều kiện hoàn thành: upload một video ngắn thật → nhận transcript có timestamp → chia đoạn → tạo bản tóm tắt bám transcript → mở video đúng đoạn. Thêm index/tìm kiếm nếu nằm trong tiêu chí đã thống nhất với giảng viên.

## 3. Các rủi ro bổ sung cần chốt

1. **Chấm tự luận trong micro-content video bị lệch payload.** [Producer](../core-api/src/micro-content/micro-content-attempt.service.ts:250) gửi `answer_ids`, nhưng [consumer hiện tại](../worker/worker/runners/answer_grading_worker.py:51) yêu cầu `essay_attempt_ids` và `attempt_ids`. Đã gọi parser trực tiếp bằng cấu trúc producer và xác nhận bị từ chối: `essay_attempt_ids must be a list of ids`. Nếu demo có bài tự luận trong micro-content thì phải sửa luồng này; đây là luồng riêng với quiz thông thường.
2. **Các hàm placeholder cũ không phải bằng chứng toàn bộ micro-content còn giả.** gRPC [đã nối sang MicroContentAttemptService](../core-api/src/grpc/grpc-server.service.ts:258) có nghiệp vụ thật. Không nên đếm các hàm cũ trong `MicroContentService` như lỗi chạy hiện tại.
3. **CI chưa đồng bộ phiên bản dependency.** `check_materialize_pins.py` thất bại ở 3 cặp pin: `ai-tutor/ai-sdk`, `worker/ai-sdk`, `worker/core-chunking`. Cần chốt commit/submodule/pin và kiểm tra từ checkout sạch trước khi bàn giao/demo trên máy khác.
4. **Chương đánh giá chưa trình bày kết quả thực nghiệm.** [Chương 6](../report/lvtn_en/chapters/c6_danh_gia_he_thong.tex:7) hiện ghi là khung đánh giá dự kiến. Repo đã có [111 câu đo retrieval](../packages-ai/eval/README.md:1), nhưng README ghi do một người gán là Claude, chưa có người thứ hai đối chiếu. Cần kiểm tra lại với người có chuyên môn và đưa số liệu đo thật vào báo cáo; không kết luận rằng đã có ground truth độc lập.

## 4. Kết quả kiểm tra đã chạy

| Kiểm tra | Kết quả |
| --- | --- |
| Core API Jest | 30 suites, 303 test qua |
| Core API TypeScript | Qua |
| Web TypeScript | Qua |
| Web LTI/deep-link script | Qua |
| Worker unit tests | 235 test duy nhất qua sau khi chạy lại health tests ngoài sandbox |
| Packages AI unit tests | 407 qua, 1 bỏ qua |
| AI tutor tests | 60 test duy nhất qua sau khi chạy lại test HTTP ngoài sandbox |
| Content schema consistency | Qua: 5 loại câu hỏi và lesson card |
| Model catalog consistency | Qua |
| Materialize dependency pins | Không qua: 3 cặp pin lệch |
| Container/readiness | Các container ứng dụng chính đang chạy; 5 worker trả HTTP 200 ở `/ready` |

Các lỗi mở cổng localhost ban đầu trong Python tests là giới hạn sandbox; đã chạy lại phần bị ảnh hưởng và qua. Không ghi nhận chúng như lỗi sản phẩm. Readiness không chứng minh model/provider đang sinh được nội dung thành công.

## 5. Thứ tự triển khai đề xuất

1. **Giữ luồng quiz hiện có ổn định.** Chạy một kịch bản demo xuyên suốt, lưu bằng chứng và sửa lỗi trực tiếp trên kịch bản đó.
2. **Chốt tóm tắt bằng dữ liệu thật.** Điều tra lỗi enrichment hoặc nối đường `type=card` có sẵn; thêm điều khiển giao diện và kiểm chứng duyệt/xuất bản/đọc.
3. **Hoàn tất nền video dùng chung.** Upload thật, lưu metadata, trạng thái xử lý/lỗi, lấy URL và player. Hai nhánh video đều cần phần này.
4. **Làm hai nhánh video tối thiểu.** Video đầu vào: STT/timestamp/tóm tắt. Video đầu ra: kịch bản/duyệt/render/lưu/phát. Mỗi nhánh phải có ít nhất một mẫu chạy thật trước khi mở rộng.
5. **Chốt bằng chứng bảo vệ.** Một bộ tài liệu cố định, một video đầu vào, một video AI đầu ra, bộ quiz đã rà soát và bản tóm tắt đã duyệt. Ghi model/config, thời gian chạy, lỗi, chất lượng mẫu và các giới hạn; diễn tập lại từ phiên mới.
6. **Tích hợp Opencast sau khi có video chạy được**, trừ khi đó là điều kiện bắt buộc của giảng viên. Opencast chưa được tích hợp trong code đã kiểm tra; nối kho quản lý video không tự hoàn thành STT, sinh kịch bản hoặc render còn thiếu ở ứng dụng.

Chưa đủ dữ kiện để hứa kịp hạn: chưa có ngày bảo vệ và định nghĩa mức hoàn thành video được chấp nhận. Tuy nhiên, phần thiếu hiện đã xác định được theo từng luồng; không cần coi mọi tính năng trong tài liệu thiết kế là việc phải xây thêm cùng lúc.
