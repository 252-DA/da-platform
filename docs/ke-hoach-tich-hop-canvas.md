# Kế hoạch cải tiến tích hợp DA ↔ Canvas

Viết ngày 12/11/2026, dựa trên rà soát code (`web/src/app/lti`, `core-api/src/{lti,ags,canvas,document,essay-processor}`), log core-api và dev DB, đối chiếu với source Canvas local (build 04/08/2026, `~/lms/canvas-lms`). Phần "Hướng sâu hơn" ở cuối là ý tưởng, chưa chốt.

## 1. Hiện trạng

Phần LTI (launch, AGS, Deep Linking, Asset Processor) làm khá kỹ: có nonce/state, cache JWKS, hàng đợi điểm bền, chờ publish, kiểm tra origin của return URL và PNS. Số liệu dev DB ngày 11/11:

| Thứ | Số |
|---|---|
| Khóa Canvas | 3 |
| Tài liệu, tất cả từ Canvas, đã index | 10 |
| Lượt làm quiz đã đẩy điểm về Canvas | 60/60 |
| Người học từng mở DA | 2 |
| Lần sync tài liệu thành công gần nhất | 29/10 |

Chỗ yếu nằm ở mô hình tích hợp và đường REST API:

**Tích hợp nông, Canvas chỉ là khung nhúng**
- Mọi thứ DA tạo ra (quiz, bài học, micro-content, chat, chương/LO) đều chạy trong iframe. Canvas chỉ giữ một External Tool assignment và một con số điểm. AGS không gửi phần mở rộng submission nên SpeedGrader không có gì để mở. Không có xuất QTI.
- Sync chỉ đọc item kiểu `File` trong Modules (`canvas-document-sync.service.ts`, `collectEntries`). Pages, Assignments, Discussions, Announcements vô hình với chatbot và sinh quiz.
- Không có NRPS: DA chỉ biết người đã từng bấm vào tool. Danh sách sinh viên dựng từ lượt làm bài.
- Hai cấu trúc song song (chapters/LOs của DA, Modules của Canvas) chỉ nối bằng regex tên module/tên file (`canvas-placement.ts`, độ tin cậy 0.7–0.8). Canvas Outcomes không dùng.
- Đăng ký tool không khai custom field nào (`scripts/setup_canvas_lti.rb`): không có `$Canvas.course.id`, `$Canvas.user.id`, `$Canvas.module.id`, `$Canvas.assignment.*`. Phải tra khóa qua `lti_context_id:`, deep link phải giải mã JWT `data` của Canvas, bảng user chỉ có LTI `sub`.

**Đường REST API hỏng đều đặn**
- Một token admin (`CANVAS_API_TOKEN`), site admin nên bị cờ `site_admin_access_token_expiration` giới hạn 1 tuần. Log ghi 401 "Expired access token" từ 22:00 ngày 04/11, ít nhất lần thứ ba từ đầu tháng 10. Kéo theo sync tài liệu, import đề cương, danh sách module trong hộp thoại sinh quiz.
- Hỏng âm thầm: không lưu kết quả lần sync cuối, chỉ in log. Sweep 15 phút vẫn chạy và fail (ngày 11/11 là 502 vì container canvas-lms-web đã exit 4 ngày).
- core-api gọi `https://canvas.canxphung.dev` qua tunnel Cloudflare dù Canvas chạy cùng máy; mỗi lần sync là N+1 request.
- Không có chiều đẩy từ Canvas (không Live Events/webhook).

**Lớp LTI, lệch nhỏ**
- Hai đăng ký tool cho một app (Canvas chỉ cho một `course_navigation` mỗi tool).
- `ags_score_maximum` chốt lúc deep link, không đọc lại line item; giảng viên sửa điểm/hạn/số lần làm trên Canvas thì DA không biết. Scope `lineitem`, `result.readonly` đăng ký nhưng không dùng.
- Session 30 phút cứng (`web/src/lib/session.ts`), không gia hạn; thi dài hơn 30 phút mất phiên.
- Map role bằng regex (`launch/route.ts`, `mapRoles`): TA Canvas gửi kèm `membership#Instructor` nên luôn thành instructor; mọi URI role chứa "membership" nên khớp `Member`, role lạ rơi thành learner.
- Deep link chỉ chạy từ menu ⋮ của module (bắt buộc `context_module_id`).

## 2. Nguyên tắc

1. Canvas là nguồn sự thật về người, lớp và bài tập. DA là nguồn sự thật về nội dung AI sinh ra. Mỗi trường dữ liệu chỉ có một chủ.
2. Thứ gì DA làm ra mà giảng viên cần chấm hay thống kê thì phải nhìn thấy được trong Canvas, không chỉ là một con số.
3. Mỗi đường nối Canvas khi hỏng phải hiện lên UI, không nằm trong log.

## 3. Lộ trình

> **Tiến độ 12/11/2026:** bước 0 và 1 đã viết xong (Sonnet làm, chưa commit). Bước 0 đã kiểm chứng trên dev. Bước 1: test xanh, NRPS đọc được lớp thật từ container, chủ dự án đã áp toàn bộ 7 migration treo (kể cả 6 cái từ 7/11) lúc 16:19 ngày 12/11 và generate lại client trong container; sweep ngay sau đó ghi dòng `roster` success cho cả hai khóa; tool chính và tool chat đã đăng ký lại với custom field + scope NRPS; cần một lần launch thật để kiểm chứng claim mới. Ghi chú kỹ thuật: NRPS phải gọi qua tên miền công khai (Canvas kiểm `aud` theo host), REST đi nội bộ qua `canvas.docker:3000`; client Prisma trong container đã mới, nên lớp SQL thô trong `core-api/src/roster/course-roster.repository.ts` và `canvas-sync-runs.service.ts` có thể đổi sang delegate Prisma khi tiện.


Mọi cơ chế dưới đây đã kiểm tra có trên Canvas local: biến `Canvas.course.id`, `Canvas.user.id`, `Canvas.module.id`, `Canvas.moduleItem.id`, `Canvas.assignment.{id,pointsPossible,dueAt.iso8601,unlockAt.iso8601,lockAt.iso8601,allowedAttempts,published}` (`lib/lti/variable_expander.rb`); NRPS (`names_and_roles_controller.rb`, scope `contextmembership.readonly`); phần mở rộng `https://canvas.instructure.com/lti/submission` trong AGS score (`scores_controller.rb`); line item có `startDateTime`/`endDateTime`.

| Bước | Việc | Công | Mở khóa gì |
|---|---|---|---|
| 0 | Ngừng hỏng hàng tuần | 1 ngày | Sync, đề cương, deep link chạy ổn |
| 1 | Custom field + NRPS | 3 ngày | DA biết cả lớp, không chỉ người đã bấm |
| 2 | Canvas làm chủ bài tập, SpeedGrader mở được bài | 3 ngày | Giảng viên ở lại Canvas khi chấm |
| 3 | Dọn LTI | 1 ngày | Thi dài không rớt phiên, role đúng |
| 4 | Đọc Pages, mô tả bài tập, Syllabus | 2 ngày | Chatbot và sinh quiz thấy đủ nội dung |
| 5 | Xuất quiz sang Canvas Quiz qua QTI | 5 ngày | Quiz native, thống kê câu hỏi của Canvas |

### Bước 0. Ngừng hỏng hàng tuần
- Tạo user dịch vụ riêng trên Canvas, cấp Account Admin ở root account nhưng không phải site admin, lấy token không hạn. Cờ `site_admin_access_token_expiration` chỉ chạm token của site admin. Ghi quy trình vào `docs/canvas_lti_setup.md`.
- Thêm bảng `canvas_sync_runs` (course_id, trigger, started_at, finished_at, status, summary jsonb, error). `CanvasSyncProcessor` ghi mỗi lần chạy. Trang quản lý tài liệu hiện "Đồng bộ lần cuối" và lỗi gần nhất bằng tiếng người, kèm nút thử lại.
- Kiểm tra token mỗi ngày bằng `GET /api/v1/users/self`, kết quả hiện cùng chỗ; 401 báo đỏ ngay.
- core-api gọi Canvas qua `http://host.docker.internal:3000` thay vì vòng qua tunnel. Link tải file vẫn mang domain public nên đổi origin về nội bộ khi host trùng `LTI_PLATFORM_URL`. Cần thử vì Canvas có thể redirect sang kho S3 local.
- Kiểm chứng: tắt Canvas rồi bật lại, UI báo đúng. Token mới sống qua ngày thứ tám.

### Bước 1. Custom field + NRPS
- Khai `custom_fields` trong `scripts/setup_canvas_lti.rb` (và script chat): `canvas_course_id=$Canvas.course.id`, `canvas_user_id=$Canvas.user.id`, `canvas_module_id=$Canvas.module.id`, `canvas_module_item_id=$Canvas.moduleItem.id`, `canvas_assignment_id=$Canvas.assignment.id`, `assignment_points=$Canvas.assignment.pointsPossible`, `assignment_due=$Canvas.assignment.dueAt.iso8601`, `assignment_unlock=$Canvas.assignment.unlockAt.iso8601`, `assignment_lock=$Canvas.assignment.lockAt.iso8601`, `assignment_attempts=$Canvas.assignment.allowedAttempts`, `assignment_published=$Canvas.assignment.published`. Lưu id Canvas vào `lms_user_mappings.lms_platform_user_id` và `lms_course_ref.lms_platform_course_id`. Deep link lấy module từ custom claim, bỏ giải mã JWT `data`.
- Thêm scope `https://purl.imsglobal.org/spec/lti-nrps/scope/contextmembership.readonly`. Launch lưu `context_memberships_url` (claim `https://purl.imsglobal.org/spec/lti-nrps/claim/namesroleservice`) vào `lms_course_ref`. Viết `NrpsClientService` dùng lại `AgsTokenService`, phân trang qua header Link. Chạy khi giảng viên launch (cooldown như Canvas sync) và trong sweep 15 phút. Upsert `lms_user_mappings` + `course_memberships` với cột `source` và `status` (Active/Inactive).
- Trang kết quả quiz liệt kê cả lớp, có dòng "chưa làm". Learning agent có mẫu số thật.
- Kiểm chứng: thêm sinh viên mới vào Canvas, không mở DA, sau một vòng sync vẫn thấy trong danh sách.

### Bước 2. Canvas làm chủ bài tập, SpeedGrader mở được bài làm
- Mỗi launch có AGS: đọc các biến `assignment_*`, cập nhật `lti_line_items.score_maximum` và cài đặt của resource link (hạn, mở/đóng, số lần làm). Cài đặt bài kiểm tra trong DA chỉ còn thứ Canvas không có: thời gian làm, xáo đề, lúc mở đáp án. Deep link gửi `startDateTime`/`endDateTime` trong `lineItem` để Canvas tạo đúng hạn từ đầu.
- AGS score payload thêm `https://canvas.instructure.com/lti/submission` với `submission_type: basic_lti_launch`, `submission_data` là URL trang xem bài của lượt nộp, `submitted_at`. SpeedGrader sẽ launch DA vào đúng bài. Launch handler phải tôn trọng `target_link_uri` cho đường này và chỉ cho instructor/TA cùng khóa xem.
- Thêm `comment` ngắn vào điểm (số câu đúng, LO yếu nhất).
- Kiểm chứng: sửa điểm tối đa trên Canvas thành 10, DA đẩy 7.5/10. Mở SpeedGrader thấy bài làm của sinh viên.

### Bước 3. Dọn LTI
- `readLtiSession` gia hạn phiên trượt mỗi request. Phiên thi lấy TTL = thời gian làm + 10 phút nếu dài hơn 30 phút.
- `mapRoles` so khớp URI chính xác (`membership#Instructor`, `membership/Instructor#TeachingAssistant`, `membership#Learner`, …), xét TA trước Instructor, role lạ trả 403.
- Deep link chấp nhận không có module khi mở từ trang Assignment (đã có `canvas_assignment_id`).

### Bước 4. Đọc thêm Canvas
- Module item kiểu `Page`: `GET /api/v1/courses/:id/pages/:url`, đổi HTML sang Markdown, lưu `documents` với `source='canvas'`, `mime_type='text/markdown'`, thêm cột `lms_page_url`. Mô tả Assignment và Syllabus body làm tương tự. Pipeline đã nhận Markdown nên không đụng worker.
- Kiểm chứng: hỏi chatbot một điều chỉ có trong một Page.

### Bước 5. Xuất quiz sang Canvas Quiz qua QTI
- Thiết kế trong `docs/question-bank-design.md`, spike QTI 2.1 đã qua. Bộ đề đóng gói QTI, đẩy qua Content Migrations API (`migration_type=qti_converter`), lưu `canvas_quiz_id`. Giảng viên có hai lựa chọn: gắn bài DA vào module như hiện nay (luyện tập, thích nghi), hoặc xuất thành Canvas Quiz (kiểm tra chính thức, SpeedGrader và thống kê câu hỏi của Canvas).
- Đọc ngược kết quả qua Quiz Submissions API vào `quiz_attempts` với `source='canvas'`, để learning agent không mù khi sinh viên làm bên Canvas.
- Kiểm chứng: import đề 10 câu, làm bên Canvas, kết quả về DA.

## 4. Cố ý không làm

- OAuth2 theo từng giảng viên: khi còn một trường và một Canvas, user dịch vụ là đủ. Để lúc deploy thật.
- Live Events: cần SQS/Kinesis; poll 15 phút cộng sync lúc launch là đủ cho quy mô này.
- Canvas Outcomes: chỉ đáng làm sau bước 5, khi câu hỏi đã là Canvas Quiz để gắn outcome.
- New Quizzes và Moodle adapter: cái đầu không có trên Canvas local, cái sau chờ Canvas xong.

## 5. Rủi ro

- Tổng khoảng 15 ngày làm việc của một người. Bước 0–2 chạm LTI và schema, nên là của chủ dự án. Bước 4–5 giao được cho teammate.
- Redis/BullMQ dùng chung với teammates: sweep NRPS cũng phải tắt ở máy họ như Canvas sync hiện nay (`CANVAS_AUTO_SYNC_ENABLED=false`).
- Bước 2 đổi cách lưu cài đặt bài kiểm tra, phải migrate 5 resource link đang có trên dev.

## 6. Hướng sâu hơn (ý tưởng, chưa chốt)

Lộ trình trên làm hai hệ nói chuyện đúng, nhưng vẫn là hai hệ. Để chúng thành một trải nghiệm, hướng chung là **Canvas là giao diện, DA là bộ não**: DA xuất hiện đúng chỗ người dùng đang đứng trong Canvas, dùng cơ chế của Canvas để điều hướng người học, và nội dung DA sinh ra sống trong Canvas. Tất cả cơ chế dưới đây đã kiểm tra có trên Canvas local (`app/models/lti/resource_placement.rb`, `ui/shared/lti/jquery/subjects/*`), chỗ nào chưa chắc có ghi "cần thử".

### 6.1 Trợ giảng biết sinh viên đang đọc gì
- Canvas có postMessage `lti.getPageContent`: tool trong iframe gửi, Canvas trả HTML của phần nội dung chính trang hiện tại (các phần tử `data-lti-page-content="true"`: thân Page, mô tả Assignment) kèm `content_id`. Ngăn chat ở `top_navigation` dùng nó để trả lời đúng trang sinh viên đang mở, không phải cả khóa. Đây là lời giải cho hạn chế "ngăn chat không biết file/slide đang mở" (xem `canvas-local-viewer-ai-limits`). Không chạm được nội dung PDF đang preview.
- Placement `file_menu` và `wiki_page_menu` ("Hỏi Trợ giảng về file/trang này", "Sinh câu hỏi từ trang này"): mở DA với đúng tài liệu. Cần thử Canvas đưa id file vào claim nào trong id_token.
- Các postMessage khác làm DA "ngồi vừa" trong Canvas: `lti.frameResize` ở mọi trang (hiện chỉ dùng ở deep link) để hết hai thanh cuộn; `lti.put_data`/`lti.get_data` (platform storage) thay cookie bên thứ ba, hết phụ thuộc SameSite/Safari; `lti.showAlert` để báo "điểm đã về sổ" bằng thông báo của Canvas; `lti.getPageSettings` lấy locale, theme, high-contrast để DA đồng màu với Canvas.

### 6.2 Vòng lặp bổ trợ chạy bằng Mastery Paths của Canvas
- Bài DA đẩy điểm qua AGS tạo submission đã chấm; Mastery Paths (conditional release) của Canvas kích hoạt trên submission `graded` và `posted` (`conditional_release/override_handler.rb`), không thấy loại trừ bài External Tool. Cần thử một lần với bài DA.
- Khi đó: sinh viên làm bài DA → Canvas tự mở module/item bổ trợ theo khoảng điểm → item đó là một resource link DA "Ôn theo điểm yếu" tự chọn micro-content theo LO yếu ở phía server. Sinh viên đi hết vòng trong luồng Modules của Canvas; giảng viên cấu hình nhánh bằng UI Mastery Paths quen thuộc. Đây là cách Canvas-native cho hướng "bổ trợ sau kiểm tra" (`docs/bao-cao-thiet-ke-bo-tro-sau-kiem-tra.md`). Mastery Paths rẽ nhánh theo tổng điểm, phần cá nhân hóa theo LO nằm trong item DA.
- Canvas Outcomes làm từ vựng chung: mỗi chương một outcome group, mỗi LO một outcome, thang mastery theo Bloom (`outcome_groups_api_controller.rb`). Quiz xuất QTI gắn outcome được. Ghi mastery của DA vào Learning Mastery Gradebook không có API trực tiếp; đường khả dĩ là rubric gắn outcome + rubric assessment, cần spike.

### 6.3 Nội dung DA sinh ra sống trong Canvas, không trong iframe
- Placement `editor_button` (Deep Linking): trong RCE của bất kỳ Page/Assignment/Discussion, giảng viên bấm nút DA, chọn tóm tắt khái niệm, bộ flashcard hoặc 3 câu kiểm tra nhanh; DA trả content item `html` (sửa được ngay trong RCE) hoặc `iframe` (bài tương tác). Nội dung Canvas và nội dung DA nằm trên cùng một trang.
- DA viết Pages qua REST (`wiki_pages_api_controller.rb`) kèm module item: tóm tắt bài học, lesson cards (đang tạm dừng) trở thành Canvas Page, giảng viên sửa bằng RCE, Canvas giữ phiên bản, DA đọc lại qua bước 4. "Bài học của DA" = "Page của Canvas", bỏ được một UI đọc riêng.

### 6.4 Canvas hiện "bộ não" của DA
- `student_context_card`: giảng viên bấm tên sinh viên ở bất kỳ đâu trong Canvas, thẻ ngữ cảnh có nút DA mở tóm tắt mức nắm vững (BKT) của em đó. Canvas nối `student_id` vào URL launch (`StudentContextTray.tsx`); cần thử nó vào claim nào.
- `analytics_hub`: phân tích lớp của DA nằm trong khu Analytics của Canvas.
- Custom gradebook column (`custom_gradebook_columns_api_controller.rb`): cột "Mức nắm vững DA" (chữ, không phải điểm) ngay trong sổ điểm, learning agent cập nhật.
- Planner notes (`planner_notes_controller.rb`): lịch ôn Leitner của DA xuất hiện trong To-Do của sinh viên trên dashboard Canvas. Planner là theo user, phải dùng `as_user_id` của admin; hơi hack, chỉ dùng khi cần.

### 6.5 Sống qua course copy
- Canvas copy khóa học kéo theo resource link của DA, nhưng `target_id` trỏ về quiz set của khóa cũ nên `syncLaunch` ném "Quiz không thuộc khóa học Canvas hiện tại". Tích hợp sâu nghĩa là lần launch đầu trong khóa mới DA tự clone quiz set (cùng giảng viên) sang khóa mới, hoặc dùng placement `migration_selection` để DA tham gia bước Import Course Content. Đây là luồng Canvas phổ biến nhất mỗi học kỳ.

### Thứ tự gợi ý nếu làm
1. 6.1 trước: rẻ (2–3 ngày), đổi cảm giác ngay, giải đúng hạn chế đã ghi nhận.
2. 6.2 vì trùng hướng bổ trợ của luận văn và dùng máy móc sẵn có của Canvas.
3. 6.3 `editor_button`, rồi 6.5 khi chuẩn bị học kỳ mới.

## 7. UI/UX khi nằm trong Canvas (rà soát 12/11/2026)

Hiện trạng theo code `web/src`:
- Chữ và màu không cùng họ với Canvas: `globals.css` đặt body Arial/Helvetica, biến `--font-geist-sans` không bao giờ được gán; bảng màu slate/sky của Tailwind. Canvas dùng Lato Extended và màu thương hiệu của trường (mặc định xanh `#0374B5`). `@media (prefers-color-scheme: dark)` đảo nền sang đen trong khi Canvas web không có dark mode.
- Điều hướng kép: Canvas đã có global nav + course nav + tiêu đề khóa; DA vẽ lại header với mã môn, tên môn, mô tả và một hàng 9–10 nút (`components/instructor-nav.tsx`), nhãn lẫn Anh/Việt. Sinh viên mở một module item vẫn thấy header khóa học của DA.
- Chiều cao iframe: chỉ deep link gọi `lti.frameResize`; các trang khác cuộn trong iframe, hai thanh cuộn.
- Lỗi và chờ: launch lỗi trả JSON thô vào iframe (`lti/launch/route.ts`); hết phiên chỉ có dòng chữ "Phiên hết hạn. Vui lòng mở lại từ LMS." không có nút; không có `loading.tsx`/`error.tsx` nào, trang trắng trong lúc gọi core-api qua tunnel.
- Không đọc `launch_presentation` (locale, document_target), không dùng `lti.getPageSettings` (locale, time_zone, use_high_contrast, active_brand_config_json_url, window_width), không `lti.showAlert`, không `lti.showModuleNavigation`, không `requestFullWindowLaunch`.
- Chưa thử trên app Canvas Student (webview, không hỗ trợ postMessage). Chưa rà WCAG; trường đại học thường yêu cầu audit accessibility trước khi bật LTI tool.

Việc rẻ, làm trước (1–2 ngày):
1. Nạp Lato (hoặc đọc font từ brand variables), bỏ đảo dark mode, map màu từ `GET /api/v1/brand_variables` (không cần auth) sang CSS variables của DA; đọc `lti.getPageSettings` để lấy locale/time_zone/high-contrast.
2. `lti.frameResize` ở mọi trang (ResizeObserver trên `<main>`), `lti.showAlert` sau khi nộp bài/đồng bộ, `lti.showModuleNavigation` khi launch từ module item, `lti.screenReaderAlert` cho thông báo động.
3. Trang lỗi launch bằng HTML cùng giao diện, có mã lỗi copy được và nút mở lại từ Canvas; trang hết phiên có nút relaunch (`requestFullWindowLaunch` hoặc link về khóa trên Canvas từ `canvas_course_id`).
4. `loading.tsx` skeleton cho learn/manage; `error.tsx` thay trang trắng.

Việc lớn hơn (sau khi làm 6.1):
- Bỏ header khóa học khi launch từ module item (chỉ còn hoạt động), thu nhỏ điều hướng giảng viên thành một hàng tab; không đặt lại tên mục khi chưa hỏi.
- Đối chiếu với nguyên tắc IgniteAI của Instructure: "assist, not replace", "not a chatbot added to the side", "show exactly where AI is used", "seamless and familiar inside Canvas". Ngăn chat ở thanh trên hiện đúng là mẫu "chatbot bên cạnh"; 6.1 (`getPageContent`, `file_menu`, `editor_button`) kéo nó về trong luồng.
- Ngưỡng tham chiếu: New Quizzes và Canvas Studio đều là LTI tool của Instructure mà người dùng không nhận ra; Hypothesis trong SpeedGrader (ba cột: văn bản, chú thích của sinh viên, công cụ chấm) là mẫu cho trang xem bài làm ở bước 2.

Tham khảo:
- Instructure UI (InstUI), MIT, React: https://instructure.design (theme `canvas` và `canvas-high-contrast`). DA dùng Next.js + Tailwind nên hợp lý là lấy token (font, màu, bán kính, focus ring) chứ không đổi thư viện component. Gói cộng đồng cho LTI: https://www.npmjs.com/package/@oxctl/ui-lti
- Canvas postMessage: https://developerdocs.instructure.com/services/canvas/external-tools/lti/file.lti_window_post_message
- Brand variables API: https://developerdocs.instructure.com/services/canvas/resources/brand_configs
- Instructure về IgniteAI: https://www.instructure.com/en-au/resources/blog/introducing-igniteai-instructures-integrated-education-first-approach-ai
- Hypothesis trong SpeedGrader: https://web.hypothes.is/blog/hypothesis-annotation-in-canvas-now-with-speedgrader/ và https://web.hypothes.is/help/grading-student-annotations-in-canvas/
- 1EdTech về deep linking và trải nghiệm: https://www.1edtech.org/hed/iln/dle-considerations ; LTI Advantage Implementation Guide: https://standards.1edtech.org/lti/guides/implementation_guide/implementation-guide
- Mobile: https://community.canvaslms.com/t5/Canvas-Developers-Group/Developing-LTI-Tool-that-works-well-and-looks-good-in-Canvas/m-p/395578
