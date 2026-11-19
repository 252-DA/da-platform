# Chấm bài luận nộp file qua LTI Asset Processor

Sinh viên nộp bài luận (PDF, DOCX, TXT hoặc nhập chữ) vào một **Assignment gốc
của Canvas**. AI chấm theo rubric của giảng viên và đưa **điểm gợi ý kèm nhận
xét** vào SpeedGrader. Giảng viên quyết định điểm cuối. Hệ thống không ghi điểm
vào sổ điểm.

Cơ chế dùng là chuẩn 1EdTech LTI Asset Processor. Canvas gọi nó là
**Document Processor**, xem tài liệu `doc/api/document_processor.md` và
`doc/api/pns.md` trong mã nguồn Canvas. Quiz không dùng đường này: Canvas chỉ
gửi bài nộp file và bài nhập chữ của Assignment (`Submission#asset_processor_compatible?`),
và quiz cần ghi điểm thật qua AGS.

## Luồng

```
Giảng viên: Assignment (nộp file) → Add Document Processing App → DA
  Canvas ──LtiDeepLinkingRequest (ActivityAssetProcessor)──▶ web /lti/launch
  web /lti/asset-processor: nhập đề bài + rubric
  web ──CreateEssayProcessor──▶ core-api: PUT notice handler (PNS), lưu essay_processors
  web ──content item ltiAssetProcessor {custom.da_processor_id}──▶ Canvas

Sinh viên nộp bài
  Canvas ──POST {notices:[jwt]}──▶ web /api/lti/notices (xác minh chữ ký)
  web ──ReceiveAssetNotices──▶ core-api: essay_submissions RECEIVED
  core-api poller: báo cáo "Processing" → tải file (Asset Service) → MinIO
                   → QUEUED + outbox ESSAY_GRADING_REQUESTED
  worker (answer-grading-worker, hàng đợi essay_grading): đọc chữ → LLM chấm
                   từng tiêu chí → kẹp điểm, cộng → GRADED (hoặc FAILED)
  core-api poller: báo cáo "Processed" (điểm gợi ý + nhận xét) → REPORTED
                   hoặc báo cáo "Failed" để giảng viên chấm tay

Giảng viên/sinh viên bấm View report trong Canvas
  Canvas ──LtiReportReviewRequest──▶ web /lti/essay-report (chi tiết từng tiêu chí)
```

Worker không gọi LMS. Mọi lời gọi tới Canvas đi qua core-api bằng token LTI
Advantage của tool (cùng key với AGS), và chỉ được gọi tới địa chỉ thuộc
`LTI_PLATFORM_URL`.

## Thành phần

| Phần | File |
|---|---|
| Bảng | `core-api/prisma/migrations/20261014160000_essay_asset_processor`: `essay_processors`, `essay_submissions` |
| core-api | `src/essay-processor/`: service (gắn/sửa bộ chấm, nhận thông báo, xem báo cáo), `essay-report.publisher.ts` (tải file, gửi báo cáo), `lti-services.client.ts` (PNS, Asset Service, Asset Report Service) |
| web | `src/lib/lti-asset-processor*.ts`, `src/app/lti/asset-processor` (form), `src/app/api/lti/asset-processor`, `src/app/api/lti/notices`, `src/app/lti/essay-report` |
| worker | `use_cases/grade_essay_submission.py`, `services/essay_text.py`, `services/essay_submission_store.py`, `prompts/essay_grading.py`; runner `answer_grading_worker` |
| Contract | `contracts/integration-events/v1/essay-grading-requested.json` |
| Đăng ký tool | `scripts/setup_canvas_lti.rb`: scope `noticehandlers`, `asset.readonly`, `report` và placement `ActivityAssetProcessor` |

Model chấm là model của task **Kiểm chứng & chấm tự luận** trên trang
`/manage/models`; chi phí ghi `llm_usage_logs.use_case = 'essay_grading'`.

## Cài đặt

1. **Migration** (DB dùng chung, chỉ thêm bảng):
   ```bash
   docker exec -w /app da-platform-core-api-1 ./node_modules/.bin/prisma migrate deploy
   ```
2. **Cập nhật tool trên Canvas** để thêm scope và placement. Đây là cùng lệnh
   trong [canvas_lti_setup.md](canvas_lti_setup.md); script giữ nguyên client_id
   và deployment_id:
   ```bash
   docker exec -i \
     -e DA_LTI_TOOL_URL=https://app.canxphung.dev \
     -e DA_LTI_JWKS_URL=https://app.canxphung.dev/.well-known/jwks.json \
     canvas-lms-web-1 bundle exec rails runner - < scripts/setup_canvas_lti.rb
   ```
   Cờ `lti_asset_processor` và `lti_asset_processor_course` mặc định bật ở
   Canvas môi trường development. Canvas do Instructure host phải bật cờ
   "Document Processor" cho account.
3. Không cần restart: core-api chạy `--watch`, worker có `dev_reload`, web là
   Next dev.

## Cách dùng

1. Tạo Assignment, loại nộp **File Uploads** và/hoặc **Text Entry**.
2. Ở mục **Document Processors**, bấm **Add Document Processing App** rồi chọn
   *Chấm bài luận bằng AI (DA)*. Nhập đề bài, rubric (tối đa 8 tiêu chí; điểm
   tối đa của bài = tổng điểm) và chọn có cho sinh viên xem nhận xét không.
   Bấm **Gắn vào bài tập**, rồi **lưu Assignment**.
3. Sinh viên nộp bài như mọi Assignment khác. Sau khoảng một phút, SpeedGrader
   hiện báo cáo "Chấm bài AI (điểm gợi ý)", ví dụ `7.5/10`, kèm nhận xét từng
   tiêu chí. **View report** mở bảng chi tiết.
4. Muốn đổi rubric: trên trang sửa Assignment, bấm **Modify** ở bộ chấm. Bài
   nộp sau khi lưu sẽ chấm theo rubric mới.

## Giới hạn

- **Điểm chỉ là gợi ý.** Báo cáo không ghi vào sổ điểm Canvas.
- **PDF scan chỉ có ảnh** không đọc được chữ (không chạy OCR). Báo cáo về
  `UNSUPPORTED_ASSET_TYPE`, giảng viên chấm tay.
- Mỗi file tối đa 25 MB. AI đọc tối đa khoảng 60.000 ký tự đầu (khoảng 30 trang);
  bài dài hơn thì báo cáo có ghi chú.
- Nhiều file trong một lần nộp được chấm chung thành một kết quả, gắn vào từng file.
- **Canvas không gửi lại thông báo** khi web không nhận được (tunnel tắt, web
  lỗi). Trong SpeedGrader có nút **Resubmit All Files** cho bài chưa có báo cáo
  hoặc báo cáo lỗi.
- **Dùng chung DB, mỗi người một tool:** chỉ core-api có đúng `LTI_CLIENT_ID`
  của bộ chấm mới tải file và gửi báo cáo (`essay_processors.lti_client_id`).
  Worker của thành viên khác vẫn có thể nhận job chấm, vì Redis dùng chung;
  việc chấm không cần token nên vẫn đúng.

## Kiểm tra nhanh

Smoke test qua Canvas, web, core-api, Redis, MinIO và worker đang chạy, dùng
model chấm thật (có sử dụng API):

```bash
python3 scripts/test_essay_grading.py
# Giữ khóa học và bài nộp thử để xem trên Canvas:
python3 scripts/test_essay_grading.py --keep
```

Script tạo khóa học riêng, gắn rubric qua RPC `CreateEssayProcessor`, nộp
file TXT qua Canvas rồi đợi báo cáo về SpeedGrader; sau đó kiểm tra file ZIP
được báo `UNSUPPORTED_ASSET_TYPE`. Điểm từng tiêu chí phải hợp lệ, cộng đúng
tổng và khớp báo cáo Canvas; điểm chính thức của bài nộp phải còn trống.
Không kiểm tra một mức điểm cố định vì model có thể chấm khác nhau giữa các
lần chạy. Mặc định script dọn dữ liệu thử và khôi phục đăng ký nhận thông báo
ban đầu; `--keep` in URL khóa học để kiểm tra thủ công. Stack dùng tên container
development trong `docker-compose.yml` và cần tunnel Canvas/app hoạt động.

Canvas đứng sau proxy HTTPS có thể sinh URL `http` trong thông báo chạy nền.
Core-api nâng URL cùng host và cổng mặc định về HTTPS đã cấu hình trước khi
gửi token; host khác, cổng khác và URL có user/password đều bị từ chối.

```bash
# Bài nộp đã về chưa, đang ở bước nào
docker logs da-platform-core-api-1 2>&1 | grep EssayReport
docker logs da-platform-answer-grading-worker-1 2>&1 | grep grade_essay
```
