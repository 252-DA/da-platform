# Sinh quiz từ menu module Canvas

Trong Canvas: **Modules → ⋮ của một chương → Sinh quiz bằng DA**. Hộp thoại nhận module hiện tại, khớp tên module với chương trong đề cương, và hiển thị LO cùng slide của chương. Nếu tên module không khớp, giảng viên chọn chương trong hộp thoại.

1. Chọn LO, số câu (1–10 mỗi lượt) và mức Bloom.
2. Sinh câu hỏi, xem đáp án và giải thích, sửa nếu cần, rồi bấm **Duyệt và chọn**.
3. Đặt tên bài tập và bấm **Thêm … câu vào …**. Có thể dùng lại một quiz đã lưu.
4. Canvas tạo bài tập External Tool trong đúng module, thang điểm 100. Bài tập mới ở trạng thái **chưa xuất bản** theo mặc định của Canvas; giảng viên xuất bản khi sẵn sàng.
5. Sinh viên mở bài từ Canvas, làm quiz DA trong iframe và nộp bài. DA lưu từng câu theo LO/Bloom; poller AGS gửi điểm về đúng cột Canvas. Nếu Canvas tạm lỗi, bài nộp vẫn được giữ và thử gửi lại. Sinh viên được làm lại; mỗi lần gửi, DA gửi **điểm cao nhất** của sinh viên trên bài tập đó (Canvas chỉ giữ điểm gửi sau cùng, nên gửi lượt mới nhất sẽ kéo điểm xuống).
6. Khi bài tập chưa publish, Canvas trả 422 `This assignment is still unpublished`. DA không coi đó là lỗi: điểm giữ `PENDING` và thử lại mỗi `AGS_UNPUBLISHED_RETRY_MS` (mặc định 2 phút), không tính vào `AGS_MAX_RETRIES`, tới khi giảng viên publish.
7. Giảng viên mở bài tập từ Canvas thấy trang kết quả: đáp án và giải thích, tỉ lệ đúng theo câu/LO (theo lượt gần nhất của mỗi sinh viên), từng sinh viên với số lượt, điểm cao nhất và trạng thái sổ điểm Canvas (đã ghi / đang gửi / chờ publish / lỗi). Sinh viên mở lại bài thấy các lượt đã nộp và điểm cao nhất.

## Soạn đề theo ma trận (trang riêng)

`/manage/quizzes/new` (mục **Soạn đề** trong thanh giảng viên, hoặc link **Soạn đề nâng cao ↗** trong hộp thoại module) dành cho đề nhiều chương như giữa kỳ, cuối kỳ:

1. Chọn một hay nhiều chương. LO của các chương đó thành các dòng của ma trận.
2. Chọn tài liệu nguồn. Slide đã xử lý của các chương đã chọn được tick sẵn; tài liệu tham khảo chỉ làm ngữ cảnh bổ sung, nên phải có ít nhất một slide.
3. Điền ma trận đề: số câu cho mỗi LO ở mỗi mức Bloom (tối đa 20 câu mỗi ô, 60 ô và 100 câu mỗi lần sinh). Có điền nhanh theo mỗi LO, hoặc theo mức Bloom ghi trong đề cương.
4. Mỗi ô khác 0 là một yêu cầu sinh (`scope.origin = quiz_builder`, `source_document_ids` do giảng viên chọn). Core-api kiểm tra LO thuộc khóa và tài liệu thuộc khóa, đã có chunk.
5. Duyệt câu (Giữ / Bỏ / Sửa), đối chiếu số câu đã chọn với từng ô ma trận, đặt tên và cài đặt Luyện tập hoặc Kiểm tra rồi lưu.

Đề lưu vào `quiz_sets` với `chapter_ids` (mọi chương), `chapter_id` chỉ có khi đề đúng một chương, và `blueprint` (ma trận cùng tài liệu nguồn). Hộp thoại module liệt kê mọi đề của khóa trong **Dùng lại quiz đã tạo** (đề của chương đang mở lên đầu). Đề nhiều chương vì vậy thêm được vào module bất kỳ, ví dụ module "Kiểm tra giữa kỳ".

## Luyện tập và Kiểm tra

Khi thêm vào module, giảng viên chọn loại bài ở footer hộp thoại. Cả hai đều vào Canvas dưới dạng **Bài tập** (External Tool) có cột điểm — LTI không tạo được Bài kiểm tra Classic của Canvas, và luật làm bài nằm ở DA nên dùng lại được cho Moodle.

| | Luyện tập | Kiểm tra |
|---|---|---|
| Số lần làm | Không giới hạn | 1–20 hoặc không giới hạn (mặc định 1) |
| Thời gian | Không giới hạn | Tuỳ chọn, server tính từ lúc bấm Bắt đầu |
| Đề | Trả về khi mở trang | Chỉ trả về khi bắt đầu một lượt; tuỳ chọn xáo câu và phương án theo từng lượt |
| Câu bỏ trống | Phải trả lời đủ | Được nộp, tính sai; hết giờ tự nộp |
| Đáp án, giải thích | Ngay khi nộp | Sau khi đóng bài (giờ đóng, hoặc hạn nộp nếu không đặt giờ đóng) |
| Canvas | Thang điểm tuỳ chọn | Thêm hạn nộp và khung giờ: `submission.endDateTime` → `due_at`, `available.startDateTime/endDateTime` → `unlock_at/lock_at` |

Một lượt kiểm tra là một dòng `quiz_set_sessions` (thứ tự câu đã xáo, `expires_at` = min(bắt đầu + thời gian, giờ đóng)). Bấm Bắt đầu là đã dùng lượt, kể cả khi hết giờ mà chưa nộp. Nộp chỉ được nhận khi phiên còn mở và chưa quá `expires_at` + 60 giây; phiên bị khoá trong cùng transaction với việc ghi bài nên bấm nộp hai lần chỉ một lần được nhận. Bài đóng đúng hạn nộp khi không đặt giờ đóng — nếu nhận nộp muộn sau khi đã mở đáp án, sinh viên còn lượt có thể xem đáp án rồi làm lại.

## Điều kiện dữ liệu

- Đề cương đã được đồng bộ, chương có liên kết LO.
- Slide đã xử lý thành các đoạn nội dung, có vai trò `lecture`, được gắn đúng `chapter_code`, và có ánh xạ đoạn nội dung với LO.
- Canvas REST token trong core-api đọc được module của khóa học.
- Web và core-api dùng cùng client ID/khóa LTI; JWKS công khai truy cập được từ Canvas. Trong iframe HTTPS dùng cookie `SameSite=None; Secure`.

Yêu cầu sinh từ module được backend giới hạn bằng `source_document_ids` của chương. Worker lọc nguồn theo tài liệu này trước khi tạo prompt, không dùng truy xuất MCP không có bộ lọc tài liệu. UUID do PostgreSQL trả về được chuẩn hóa về chuỗi khi so sánh với ID trong job.

## Lưu trữ và LTI

`quiz_sets` lưu bản chụp các câu đã duyệt. Sửa câu gốc sau đó không đổi đề hoặc đáp án của quiz đã đưa vào Canvas. `quiz_attempts.submission_id` nhóm tất cả câu của một lượt nộp, tránh gửi điểm cho nửa bài khi hàng đợi chia batch và tránh lấy trung bình các lần làm lại.

Launch `LtiDeepLinkingRequest` phải qua xác minh chữ ký, state, nonce, vai trò và khóa học. Canvas hiện tại đặt `context_module_id` trong JWT `data` của return URL; DA chỉ đọc sau khi xác thực token LTI bên ngoài và giữ nguyên URL khi trả về. Phiên chọn được giữ trong Redis, gắn với giảng viên/khóa học và hết hạn sau 30 phút.

Response ký RS256 trả một `ltiResourceLink` kèm `lineItem` và custom claims `target_kind=quiz_set`, `target_id`. Khi mở bài tập, session lấy đích và resource link từ claims có chữ ký. Learner không nhận đáp án/giải thích trước khi nộp; server chấm theo bản chụp và kiểm tra resource link thuộc đúng quiz/khóa học.

## Cập nhật một môi trường đang chạy

Áp dụng migration DA `20260927150000_canvas_quiz_sets`, `20260927151000_ags_posting_status`, `20260927180000_quiz_set_exam_mode` và `20260927200000_quiz_set_blueprint`, chạy `prisma generate`, rồi nạp mã web/core-api/content-generation-worker. Migration thứ hai bổ sung trạng thái `POSTING` vào ràng buộc DB để poller AGS nhận bài được. Không cần build lại hoặc tạo lại container Canvas.

Đăng ký menu bằng script có thể chạy lại, giữ nguyên client/deployment hiện tại. Luôn truyền URL thực tế của môi trường:

```sh
docker exec -i \
  -e DA_LTI_TOOL_URL=https://app.canxphung.dev \
  -e DA_LTI_JWKS_URL=https://app.canxphung.dev/.well-known/jwks.json \
  canvas-lms-web-1 bundle exec rails runner - < scripts/setup_canvas_lti.rb
```

Sau cập nhật, tải lại trang Modules để Canvas lấy menu mới. Không dùng `docker compose down`, xóa volume hoặc rebuild Canvas cho thay đổi này.

## Kiểm tra hồi quy

- Web: `pnpm test:lti`; kiểm tra claim, module token, return origin, chữ ký response, line item và biểu mẫu trả về.
- Core: Jest `quiz-set.service.spec.ts` (gồm `results`, chế độ Kiểm tra, đề nhiều chương), `content-generation.service.spec.ts` (tài liệu nguồn tự chọn), `quiz-set-exam.spec.ts` (cài đặt, khung giờ, mở đáp án, xáo trộn), `ags-publisher.service.spec.ts` (điểm cao nhất, chờ publish), `ags-client.service.spec.ts` (422 unpublished), `content-generation.service.spec.ts`, `lesson.service.spec.ts`.
- Worker: pytest `test_module_quiz_sources.py`, `test_generate_curriculum_quiz.py`, `test_content_generation_worker.py`.
- Khi kiểm tra TypeScript bên cạnh `nest start --watch`, dùng `tsc --noEmit --incremental false` để tránh làm sai bộ nhớ biên dịch tăng dần của tiến trình đang chạy.

Kiểm tra tích hợp cần có launch ký bằng Canvas thật, kiểm tra chương/LO/nguồn trong hộp thoại, sinh một câu thật, xác thực response bằng Canvas, kiểm tra assignment/module/line item và điểm Test Student. Chỉ xóa các bản ghi kiểm thử đã tạo, giữ nguyên dữ liệu và container đang dùng.

### Xác nhận trên môi trường hiện tại (27/09/2026)

- Bộ dựng menu Canvas trả đúng `module_menu_modal`, tên **Sinh quiz bằng DA**, kiểu `LtiDeepLinkingRequest` và kích thước hộp thoại 1100 × 800.
- Launch ký bằng khóa Canvas thật đi qua login/launch DA; Chương 1 nhận đúng 2 LO và slide `Ch1_Big Data Intro.pdf`.
- Chrome render hộp thoại, sinh câu hỏi thật có nguồn; không có lỗi JavaScript.
- Response từ DA được validator gốc Canvas xác thực. Action Deep Linking gốc tạo assignment đúng module 1 và line item thang 100.
- Test Student mở đúng snapshot; trước nộp không có đáp án/giải thích trong dữ liệu trang. Score service Canvas ghi nhận 100, rồi nhận 0 khi làm lại; DA đánh dấu cả hai lượt `POSTED`.
- Nộp từ origin khác/sai resource link bị chặn 403; thiếu câu trả lời bị chặn 400.
- 27 kiểm thử backend, 25 kiểm thử worker, kiểm tra chữ ký Deep Linking, TypeScript và ESLint đều qua.
- Các container Canvas web/jobs/PostgreSQL/Redis giữ nguyên ID, image và thời điểm chạy; RCE vẫn dùng container đã sửa trước đó.
