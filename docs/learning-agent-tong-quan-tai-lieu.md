# Tổng quan tài liệu: Learning Agent cho luyện tập thích ứng

**Đề tài:** Hệ thống LMS tự động tạo Micro-Content & Quiz bằng Generative AI (DA Platform)
**Ngày:** 14/10/2026
**Mục đích:** gom các nghiên cứu liên quan để thiết kế Learning Agent dựa trên bằng chứng. Thiết kế dùng tài liệu này nằm ở [bao-cao-thiet-ke-learning-agent.md](bao-cao-thiet-ke-learning-agent.md).

---

## Cách tìm và kiểm tra

- **Nguồn:** kỷ yếu EDM, AIED, ITS, LAK, L@S, UMAP, EC-TEL; tạp chí IJAIED, UMUAI, JEDM, IEEE TLT, Review of Educational Research, Psychological Bulletin, Psychological Science, PNAS; arXiv cho các bài 2024–2026.
- **Từ khoá:** knowledge tracing, mastery learning criteria, instructional sequencing, adaptive practice, spaced repetition, testing effect, feedback, open learner model, simulated learners, LLM agents for education, personalized question generation, item exposure control.
- **Kiểm tra:** mỗi bài đã được tra lại tác giả, năm, nơi đăng và DOI hoặc đường dẫn, trừ bốn sách và báo cáo kinh điển ghi theo trích dẫn chuẩn: Bloom (1968), Leitner (1972), Anderson & Krathwohl (2001), Russell & Norvig (2021). Cột "nội dung chính" lấy từ tóm tắt và trang công bố. Trước khi đưa một con số vào báo cáo chính thức, cần đối chiếu lại với toàn văn.
- **[preprint]** đánh dấu bản arXiv chưa qua bình duyệt. Các bài này chỉ dùng để chỉ hướng nghiên cứu mới, không dùng làm căn cứ chính.

Tổng cộng 91 tài liệu, chia 10 nhóm. Mỗi nhóm gồm: câu hỏi thiết kế mà nhóm trả lời, bằng chứng chính, hệ quả cho thiết kế, và bảng tài liệu. Danh mục đầy đủ ở cuối.

---

## 1. Agent và vòng lặp của hệ thống dạy học thông minh

**Câu hỏi:** "Agent" trong đồ án nghĩa là gì, và nó làm phần việc nào của một hệ thống dạy học?

**Bằng chứng chính**
- Định nghĩa kinh điển: agent là hệ thống tự hoạt động, quan sát môi trường và hành động để đạt mục tiêu. Định nghĩa này không đòi hỏi phải dùng LLM hay nhiều agent.
- VanLehn (2006) mô tả hệ thống dạy học thông minh (ITS) bằng hai vòng lặp. **Vòng ngoài** chọn bài tập tiếp theo. **Vòng trong** hỗ trợ từng bước trong một bài: phản hồi, gợi ý, cập nhật đánh giá về người học.
- ITS có hiệu quả thật. VanLehn (2011) tổng hợp: ITS hỗ trợ theo từng bước đạt hiệu ứng khoảng 0.76 so với không có gia sư, gần bằng gia sư người (khoảng 0.79). Kulik & Fletcher (2016) tổng hợp 50 đánh giá có đối chứng: trung vị cao hơn dạy thường 0.66 độ lệch chuẩn; hiệu ứng nhỏ hơn khi đo bằng bài kiểm tra chuẩn hoá.

**Hệ quả cho thiết kế**
- Learning Agent của đồ án là **vòng ngoài**: quan sát kết quả làm bài, cập nhật mô hình người học, chọn hoạt động tiếp theo.
- Tính "agent" nằm ở chỗ hành động thay đổi theo trạng thái của từng người học. Nó không nằm ở việc có gọi LLM hay không.

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Wooldridge & Jennings (1995) | Agent: tự chủ, phản ứng với môi trường, chủ động theo mục tiêu | Định nghĩa agent trong đồ án |
| Russell & Norvig (2021) | Agent dựa trên mô hình và dựa trên mục tiêu | Như trên |
| VanLehn (2006) | Vòng ngoài chọn bài, vòng trong hỗ trợ từng bước | Xác định phạm vi: Agent là vòng ngoài |
| VanLehn (2011) | ITS theo bước ≈ 0.76, gia sư người ≈ 0.79 | Lý do kỳ vọng vào hướng thích ứng |
| Kulik & Fletcher (2016) | 50 đánh giá, trung vị +0.66 SD; nhỏ hơn với bài kiểm tra chuẩn hoá | Như trên; lưu ý cách đo |
| Bloom (1984) | Gia sư một kèm một hơn lớp học thường khoảng 2 SD ("2 sigma") | Bối cảnh của mastery learning và ITS |

---

## 2. Mô hình người học (knowledge tracing)

**Câu hỏi:** Ước lượng mức thành thạo bằng mô hình nào, khi hệ thống chưa có dữ liệu để huấn luyện?

**Các họ mô hình**
- **BKT** (Corbett & Anderson, 1995): giữ xác suất người học đã nắm một kỹ năng, cập nhật sau mỗi câu trả lời bằng 4 tham số: biết trước, học được sau một lần làm, đoán đúng, biết mà vẫn sai.
- **Mở rộng BKT:** xác suất đoán và trượt theo ngữ cảnh (Baker et al., 2008); theo độ khó của câu, KT-IDEM (Pardos & Heffernan, 2011); tham số riêng cho từng người học (Yudelson et al., 2013); quan hệ tiên quyết giữa các kỹ năng bằng mạng Bayes động (Käser et al., 2014, 2017).
- **Mô hình logistic:** AFM (Cen et al., 2006) và PFA (Pavlik et al., 2009) dự đoán từ số lần làm, số lần đúng và sai. Elo (Pelánek, 2016; Pelánek et al., 2017) cập nhật đồng thời năng lực người học và độ khó câu, chạy trực tuyến mà không cần huấn luyện trước.
- **Học sâu:** DKT dùng mạng hồi quy (Piech et al., 2015).
- **LLM làm mô hình người học:** Neshaei et al. (2024), Hooshyar et al. (2025).

**Bằng chứng so sánh**
- Gervet et al. (2020), 9 bộ dữ liệu: hồi quy logistic tốt nhất với dữ liệu cỡ vừa; DKT tốt nhất với dữ liệu lớn; BKT kém hơn cả hai về độ chính xác dự đoán.
- Khajah et al. (2016): BKT thêm vài mở rộng thì gần bằng DKT; ưu thế của DKT không đến từ biểu diễn mới mà nó học được.
- Neshaei et al. (2024): LLM được tinh chỉnh chỉ ngang BKT, chưa bằng mô hình tốt nhất. Hooshyar et al. (2025) [preprint]: DKT đạt AUC 0.83, hơn LLM ở mọi cấu hình; LLM cập nhật mức thành thạo không nhất quán, có lần sai chiều.
- Ước lượng tham số BKT từ ít dữ liệu không ổn định: nhiều bộ tham số khác nhau giải thích cùng một dữ liệu (Beck & Chang, 2007). Doroudi & Brunskill (2017) phân tích lại vấn đề này.
- Cá nhân hoá tốc độ học có ích hơn cá nhân hoá mức biết trước (Yudelson et al., 2013).
- Thứ bậc của thang Bloom không chặt. Bản sửa đổi của thang Bloom nới lỏng giả định thứ bậc tích luỹ (Anderson & Krathwohl, 2001; Krathwohl, 2002). Lalwani & Agrawal (2018) dùng DKT trên khoảng 42 triệu lượt làm bài: dữ liệu ủng hộ thứ tự từ đơn giản đến phức tạp, nhưng các mức chồng lấn nhau, kể cả các mức không kề nhau.

**Hệ quả cho thiết kế**
- Hệ thống chưa có dữ liệu để huấn luyện DKT hay ước lượng tham số. Dùng **BKT với tham số cố định**, có xác suất đoán theo loại câu (ý tưởng của KT-IDEM, đơn giản hoá theo loại câu thay vì từng câu).
- Độ chính xác dự đoán không phải mục tiêu chính (xem nhóm 3). Tách "mô hình" khỏi "tiêu chí thành thạo" để thay và so sánh được.
- Khi đủ dữ liệu: ước lượng tham số bằng pyBKT (Badrinath et al., 2021), thử thêm Elo hoặc PFA.
- Không dùng LLM làm mô hình người học.
- Quan hệ giữa các mức Bloom là **giả định cần kiểm tra**, không phải sự thật có sẵn.

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Corbett & Anderson (1995) | Mô hình BKT gốc | Mô hình người học chính |
| Baker et al. (2008) | Đoán và trượt theo ngữ cảnh | Lý do để G phụ thuộc câu |
| Pardos & Heffernan (2011) | KT-IDEM: tham số theo độ khó câu | G theo loại câu |
| Yudelson et al. (2013) | Cá nhân hoá tốc độ học có ích hơn mức biết trước | Hướng mở rộng; thiết kế người học mô phỏng |
| Beck & Chang (2007) | Tham số BKT khó xác định duy nhất từ dữ liệu | Lý do dùng tham số cố định khi ít dữ liệu |
| Doroudi & Brunskill (2017) | Phân tích lại vấn đề xác định tham số của BKT | Như trên |
| Cen et al. (2006) | LFA và mô hình AFM | Mô hình sinh dữ liệu khác BKT trong mô phỏng |
| Pavlik et al. (2009) | PFA: đếm đúng và sai riêng | Phương án thay thế khi có dữ liệu |
| Pelánek (2016) | Elo trong hệ thống giáo dục thích ứng | Phương án thay thế; ước lượng độ khó câu |
| Pelánek et al. (2017) | Elo cho luyện tập dữ kiện thích ứng | Như trên |
| Piech et al. (2015) | DKT | Lý do không dùng: cần nhiều dữ liệu |
| Khajah et al. (2016) | BKT mở rộng ≈ DKT | BKT vẫn là lựa chọn hợp lý |
| Gervet et al. (2020) | So sánh trên 9 bộ dữ liệu theo cỡ dữ liệu | Như trên; chọn mô hình theo cỡ dữ liệu |
| Pelánek (2017) | Tổng quan BKT, mô hình logistic và các hướng khác | Bức tranh chung khi chọn mô hình |
| Abdelrahman et al. (2023) | Tổng quan KT từ cổ điển đến học sâu | Như trên |
| Liu et al. (2021) | Tổng quan KT: mô hình, biến thể, ứng dụng | Như trên |
| Badrinath et al. (2021) | Thư viện pyBKT | Công cụ ước lượng tham số về sau |
| Käser et al. (2014) | Mạng Bayes mô hình hoá cấu trúc kỹ năng | Quan hệ giữa các mức Bloom |
| Käser et al. (2017) | Mạng Bayes động, quan hệ tiên quyết giữa kỹ năng | Như trên, cách làm đầy đủ |
| Krathwohl (2002) | Thang Bloom sửa đổi; nới lỏng thứ bậc chặt | Giả định về thứ bậc mức Bloom |
| Lalwani & Agrawal (2018) | Dữ liệu ủng hộ thứ bậc Bloom nới lỏng, các mức chồng lấn | Như trên |
| Neshaei et al. (2024) | LLM tinh chỉnh ≈ BKT | Không dùng LLM làm mô hình người học |
| Hooshyar et al. (2025) [preprint] | DKT hơn LLM; LLM cập nhật mức thạo không nhất quán | Như trên |

---

## 3. Tiêu chí thành thạo: khi nào dừng luyện một kỹ năng

**Câu hỏi:** Ngưỡng nào để kết luận sinh viên đã nắm, và cần so sánh với tiêu chí đơn giản nào?

**Bằng chứng chính**
- Mastery learning (Bloom, 1968): mỗi người học luyện đến khi đạt mới sang phần sau. Kulik et al. (1990), 108 đánh giá có đối chứng: hiệu quả ở đại học, trung học và cuối tiểu học; người học yếu được lợi nhiều nhất; đổi lại tốn thêm thời gian.
- **Ngưỡng P(L) ≥ 0.95** của BKT là quy ước. Fancsali et al. (2013) phân tích hiệu năng tốt nhất và tệ nhất của cách đánh giá này. Zhang et al. (2025): người đạt ≥ 0.98 học bài sau tốt hơn người dừng ở 0.95. Kết quả này là tương quan, chưa chứng minh nhân quả.
- **N câu đúng liên tiếp (N-CCR):** ASSISTments dùng 3 câu đúng liên tiếp trong Skill Builder (Heffernan & Heffernan, 2014). Kelly et al. (2015): N-CCR dự đoán câu tiếp theo tốt hơn KT; 3 câu có vẻ đủ; nhưng khi đo bằng câu chuyển giao thì N lớn hơn tốt hơn. Niu et al. (2026): mô hình thích ứng ra quyết định nhất quán hơn "3 câu liên tiếp", nhất là ở giai đoạn đầu; kết quả của luật liên tiếp dao động theo kỹ năng, mẫu câu và việc dùng gợi ý.
- Pelánek & Řihák (2017, 2018): **dữ liệu dùng để quyết định và vị trí ngưỡng quan trọng hơn mô hình**; trung bình trượt mũ (EMA) đơn giản cũng làm được. Pelánek (2018): tiêu chí tốt cần tách "mức hiểu" khỏi "độ chắc chắn của ước lượng".
- Rollinson & Brunskill (2015): hai mô hình dự đoán tốt như nhau có thể cho số câu luyện rất khác nhau. Vì vậy cần đánh giá mô hình qua **chính sách nó sinh ra**, không chỉ qua độ chính xác dự đoán. Käser et al. (2016) phát triển chính sách "khi nào dừng" dùng được với nhiều loại mô hình.
- **Giậm chân tại chỗ (wheel-spinning)** (Beck & Gong, 2013): người học không đạt 3 câu đúng liên tiếp trong 10 lần đầu. Khoảng hai phần ba người học đạt thành thạo trong 10 lần; với phần còn lại, thêm câu gần như không giúp, cần cách can thiệp khác.
- **Công bằng** (Doroudi & Brunskill, 2019): KT công bằng hơn luyện đều số câu cho mọi người. Tuy vậy, khi mô hình không khớp với người học (dùng chung tham số, giả định sai về cách học), người học chậm bị thiệt. Cả BKT và N-CCR đều có điểm yếu này.

**Hệ quả cho thiết kế**
- Ngoài BKT, đánh giá phải có **ít nhất hai tiêu chí đối chứng**: N-CCR (3 câu đúng liên tiếp) và EMA.
- Ngưỡng là tham số cấu hình; báo cáo kết quả ở cả 0.95 và 0.98.
- Thêm **số quan sát tối thiểu** trước khi công nhận thành thạo, để xử lý độ không chắc khi mới có ít dữ liệu (theo hướng của Pelánek, 2018).
- Thêm luật giậm chân tại chỗ: 10 lần chưa đạt thì đổi hành động (xem lại nguồn, báo giảng viên), không giao thêm câu.
- **Điểm riêng của hệ thống:** ngân hàng câu có 5 loại với xác suất đoán rất khác nhau, từ 0.5 (đúng/sai) đến gần 0 (tự luận). N-CCR và EMA không tính đến việc đoán. Đây là khác biệt cần đo bằng mô phỏng.
- Đo công bằng theo nhóm người học nhanh và chậm.

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Bloom (1968) | Mastery learning | Nền của tiêu chí thành thạo |
| Kulik et al. (1990) | Meta-analysis 108 đánh giá mastery learning | Lợi ích và chi phí thời gian |
| Fancsali et al. (2013) | Hiệu năng tốt nhất/tệ nhất của đánh giá thành thạo bằng BKT | Giới hạn của ngưỡng BKT |
| Zhang et al. (2025) | Ngưỡng 0.98 liên quan kết quả bài sau tốt hơn | Phân tích độ nhạy của ngưỡng |
| Heffernan & Heffernan (2014) | Hệ sinh thái ASSISTments; Skill Builder | Nguồn của tiêu chí 3 câu liên tiếp |
| Kelly et al. (2015) | KT so với N câu đúng liên tiếp | Đối chứng N-CCR |
| Niu et al. (2026) | Mô hình thích ứng nhất quán hơn "3 câu liên tiếp" | Như trên |
| Pelánek & Řihák (2017) | Thực nghiệm các tiêu chí thành thạo; EMA dùng được | Đối chứng EMA; ngưỡng quan trọng hơn mô hình |
| Pelánek & Řihák (2018) | Phân tích và thiết kế tiêu chí thành thạo | Như trên |
| Pelánek (2018) | Tách độ chắc chắn khỏi mức hiểu | Số quan sát tối thiểu |
| Rollinson & Brunskill (2015) | Mô hình dự đoán tốt như nhau, chính sách khác nhau | Đánh giá theo chính sách |
| Käser et al. (2016) | Chính sách "khi nào dừng" dùng chung cho nhiều mô hình | Như trên |
| Beck & Gong (2013) | Wheel-spinning: 10 lần chưa đạt | Luật báo giảng viên |
| Doroudi & Brunskill (2019) | Công bằng của KT; người học chậm bị thiệt khi mô hình sai | Chỉ số công bằng |

---

## 4. Chọn hoạt động tiếp theo

**Câu hỏi:** Nên chọn hoạt động bằng luật, bằng bandit hay học tăng cường, hay bằng LLM?

**Bằng chứng chính**
- Doroudi et al. (2019) tổng quan học tăng cường (RL) cho việc sắp xếp hoạt động học từ thập niên 1960: kết quả lẫn lộn; nhiều chính sách RL không hơn đối chứng hợp lý.
- **Bandit:** Clement et al. (2015) đề xuất ZPDES, cần ít tri thức về môn học; thử với 400 học sinh. Girard et al. (2026) học chính sách từ log có sẵn bằng bandit ngữ cảnh offline với mô hình Rasch.
- **POMDP:** Rafferty et al. (2016) dạy nhanh hơn với bài học khái niệm, nhưng cần mô hình người học đúng.
- **Thích ứng hơn cố định:** Mettler et al. (2016): lịch luyện thích ứng theo độ chính xác và thời gian trả lời cho kết quả nhớ tốt hơn lịch cố định. Nhóm đối chứng "yoked", dùng đúng khoảng cách của người khác, cho thấy lợi ích đến từ việc thích ứng theo từng người và từng câu.
- **Luyện tập thích ứng cho dữ kiện:** Papoušek et al. (2014) chia hệ thống thành 3 phần: ước lượng mức biết trước, ước lượng mức hiện tại, chọn câu.
- **Luyện thừa (overpractice):** Noh et al. (2026) mô phỏng chiến lược tự chọn bài của người học (AFM sinh câu trả lời, BKT theo dõi, ngưỡng 0.95): chiến lược "né rủi ro" luyện thừa nhiều nhất; ràng buộc của hệ thống sửa được chiến lược kém mà không ảnh hưởng chiến lược tốt. Xia et al. (2025): bỏ qua các bước đã thạo giảm luyện thừa tới một phần ba trong mô phỏng.
- **Chia quyền chọn:** Corbalan et al. (2008): hệ thống thu hẹp lựa chọn theo kết quả, người học chọn trong đó. Cách này giữ được hiệu quả và tăng mức tham gia.
- **Xen kẽ nội dung:** Brunmair & Richter (2019), 59 nghiên cứu: học xen kẽ có lợi trung bình g = 0.42, mức lợi phụ thuộc độ tương tự giữa các nhóm nội dung.

**Hệ quả cho thiết kế**
- Không đủ dữ liệu cho RL hay bandit offline. Dùng **planner theo luật**, mỗi luật có căn cứ, tách riêng để thay được.
- Hiển thị một đề xuất kèm 1–2 lựa chọn khác, trong giới hạn hệ thống đặt.
- **Luyện thừa** là một chỉ số đánh giá chính.
- Xen câu ôn đơn vị cũ vào khi luyện đơn vị mới.

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Doroudi et al. (2019) | Tổng quan RL cho sắp xếp hoạt động học | Lý do chọn luật thay vì RL |
| Clement et al. (2015) | Bandit ZPDES, 400 học sinh | Hướng mở rộng |
| Girard et al. (2026) | Bandit ngữ cảnh offline học từ log | Hướng mở rộng khi có log |
| Rafferty et al. (2016) | POMDP dạy nhanh hơn | Như trên |
| Mettler et al. (2016) | Lịch thích ứng hơn lịch cố định | Đối chứng thứ tự cố định |
| Papoušek et al. (2014) | Ba phần của hệ luyện tập thích ứng | Kiến trúc mô hình người học và planner |
| Noh et al. (2026) | Mô phỏng chiến lược chọn bài, luyện thừa, ràng buộc hệ thống | Chỉ số luyện thừa; giới hạn cho lựa chọn của sinh viên |
| Xia et al. (2025) | Bỏ bước đã thạo, giảm luyện thừa 1/3 | Như trên |
| Corbalan et al. (2008) | Chia quyền chọn bài giữa hệ thống và người học | Hiển thị đề xuất kèm lựa chọn |
| Brunmair & Richter (2019) | Meta-analysis học xen kẽ | Xen câu ôn |

---

## 5. Luyện tập bằng kiểm tra và lặp lại ngắt quãng

**Câu hỏi:** Hoạt động nào nên là hoạt động chính, và khi nào cho ôn lại?

**Bằng chứng chính**
- **Hiệu ứng kiểm tra:** làm bài kiểm tra giúp nhớ lâu hơn đọc lại (Roediger & Karpicke, 2006; Karpicke & Roediger, 2008). Rowland (2014) và Adesope et al. (2017, 118 bài báo, 272 hiệu ứng) xác nhận bằng meta-analysis. Dunlosky et al. (2013) xếp luyện bằng kiểm tra và luyện ngắt quãng vào nhóm kỹ thuật hiệu quả cao.
- **Ngắt quãng:** Cepeda et al. (2006), 317 thí nghiệm: khoảng cách ôn tối ưu tăng theo thời gian cần nhớ.
- **Lịch ôn:**
  - Hộp Leitner (Leitner, 1972): thẻ lên hộp khi đúng, về hộp đầu khi sai. Đơn giản, dễ giải thích.
  - HLR của Duolingo (Settles & Meeder, 2016) học "chu kỳ bán rã" của trí nhớ từ dữ liệu, giảm sai số dự đoán hơn 45% so với các mốc so sánh.
  - Tabibian et al. (2019) tối ưu lịch ôn bằng điều khiển tối ưu. Ye et al. (2022) đề xuất SSP-MMC, nền của bộ lập lịch FSRS.
  - Lindsey et al. (2014), lớp tiếng Tây Ban Nha lớp 8, 179 học sinh, một học kỳ: ôn cá nhân hoá giúp nhớ hơn 16.5% so với học dồn và hơn 10% so với ôn đều cho mọi người.
  - Mettler et al. (2016) không thấy khoảng cách tăng dần tốt hơn khoảng cách đều; lợi ích đến từ việc thích ứng.

**Hệ quả cho thiết kế**
- Hoạt động chính của Agent là **làm câu hỏi**. Đọc lại chỉ là bước phụ sau khi sai.
- Có lịch ôn. Giai đoạn đầu dùng Leitner vì đơn giản và giải thích được. Tài liệu cho thấy lịch thích ứng theo từng người (HLR, FSRS) tốt hơn, nên để chỗ thay khi có dữ liệu.

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Roediger & Karpicke (2006) | Làm bài kiểm tra nhớ lâu hơn đọc lại | Làm câu hỏi là hoạt động chính |
| Karpicke & Roediger (2008) | Tầm quan trọng của việc nhớ lại | Như trên |
| Rowland (2014) | Meta-analysis hiệu ứng kiểm tra | Như trên |
| Adesope et al. (2017) | Meta-analysis luyện tập bằng kiểm tra | Như trên |
| Dunlosky et al. (2013) | Đánh giá 10 kỹ thuật học | Như trên; lịch ôn |
| Cepeda et al. (2006) | Meta-analysis luyện ngắt quãng | Khoảng cách ôn |
| Leitner (1972) | Hộp thẻ Leitner | Lịch ôn giai đoạn đầu |
| Settles & Meeder (2016) | HLR, Duolingo | Lịch ôn thích ứng về sau |
| Tabibian et al. (2019) | Tối ưu lịch ôn | Như trên |
| Ye et al. (2022) | SSP-MMC, nền của FSRS | Như trên |
| Lindsey et al. (2014) | Ôn cá nhân hoá trong lớp học thật | Bằng chứng lịch ôn cá nhân hoá có ích |

---

## 6. Phản hồi, chẩn đoán và mô hình người học mở

**Câu hỏi:** Sau khi sinh viên sai, nói gì với họ? Có nên cho họ xem mô hình của mình không?

**Bằng chứng chính**
- Phản hồi là yếu tố mạnh nhưng có thể có lợi hoặc có hại. Phản hồi tốt chỉ rõ khoảng cách giữa hiện tại và mục tiêu, và việc cần làm tiếp (Hattie & Timperley, 2007; Shute, 2008).
- Van der Kleij et al. (2015), 40 nghiên cứu, 70 hiệu ứng trong môi trường học trên máy: phản hồi có giải thích (0.49) hơn cho đáp án đúng (0.32), và hơn hẳn chỉ báo đúng/sai (0.05).
- **Đơn vị kiến thức (KC):** khung KLI (Koedinger et al., 2012) coi KC là đơn vị để mô hình hoá việc học. Moore et al. (2024) dùng GPT-4 sinh và gắn KC cho câu trắc nghiệm, chuyên gia đánh giá kết quả.
- Phương án nhiễu được thiết kế theo hiểu lầm thường gặp cho phép chẩn đoán từ lựa chọn sai (Gierl et al., 2017).
- **Mô hình người học mở:** cho người học xem mô hình về chính họ (Bull & Kay, 2016). Conati et al. (2021): giải thích vì sao hệ thống đưa gợi ý làm sinh viên tin hơn, thấy gợi ý hữu ích hơn và muốn dùng lại. Khalid et al. (2025): 12 giáo viên đánh giá mô hình giải thích được là dễ dùng và đáng tin hơn, dù số câu cần để đạt thành thạo gần như không đổi.

**Hệ quả cho thiết kế**
- Lưu kết quả từng ý rubric của câu tự luận. Khi sinh viên hụt một ý, phản hồi nêu đúng ý đó và trỏ về trang tài liệu nguồn.
- Lý do đề xuất viết theo mẫu, đọc được, không cần LLM.
- Trang cho sinh viên và giảng viên xem mức thành thạo theo LO.
- Gắn đơn vị kiến thức lúc sinh câu (LLM đề xuất, giảng viên xác nhận) là bước mở rộng.

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Hattie & Timperley (2007) | Mô hình phản hồi: đang ở đâu, cần đến đâu, làm gì tiếp | Cách viết lý do đề xuất |
| Shute (2008) | Tổng quan phản hồi hình thành | Như trên |
| Van der Kleij et al. (2015) | Phản hồi có giải thích hiệu quả nhất | Dùng nhận xét theo ý rubric |
| Koedinger et al. (2012) | Khung KLI, đơn vị kiến thức | Đơn vị theo dõi |
| Moore et al. (2024) | GPT-4 sinh và gắn KC cho câu trắc nghiệm | Gắn đơn vị kiến thức lúc sinh câu |
| Gierl et al. (2017) | Tổng quan về phương án nhiễu | Chẩn đoán từ lựa chọn sai |
| Bull & Kay (2016) | Khung SMILI☺ cho mô hình người học mở | Trang mức thành thạo |
| Conati et al. (2021) | Giải thích gợi ý làm tăng tin tưởng | Hiển thị lý do |
| Khalid et al. (2025) | Mô hình giải thích được và quyết định của giáo viên | Trang giảng viên |

---

## 7. Đánh giá chính sách bằng người học mô phỏng

**Câu hỏi:** Chưa có nhiều sinh viên thật, đánh giá Agent thế nào cho đáng tin?

**Bằng chứng chính**
- **Ma trận đánh giá vững** (Doroudi et al., 2017): chạy mỗi chính sách trên nhiều mô hình người học khác nhau. Một chính sách chỉ đáng tin khi nó tốt trên mọi mô hình, không chỉ trên mô hình nó dùng để ra quyết định.
- Käser & Alexandron (2024), tổng quan người học mô phỏng 2010–2019: gần một nửa nghiên cứu không kiểm chứng mô hình mô phỏng; mô hình thường chỉ mô tả vài khía cạnh của việc học. Các tác giả đề xuất một phép thử kiểu Turing.
- Noh et al. (2026) dùng AFM sinh câu trả lời và BKT để theo dõi, tức mô hình sinh dữ liệu khác mô hình ra quyết định.
- **LLM làm người học ảo:**
  - Lu & Wang (2024), "Generative Students": tạo hồ sơ theo KC (đã nắm, nhầm, chưa rõ); câu trả lời của sinh viên ảo tương quan mạnh với sinh viên thật.
  - Gao et al. (2025), Agent4Edu: mô phỏng người học bằng agent LLM có hồ sơ, bộ nhớ và hành động.
  - Yuan et al. (2026) [preprint] cảnh báo "nghịch lý năng lực": LLM quá giỏi nên khó đóng vai người chỉ biết một phần, sinh ra lỗi không giống người thật.

**Hệ quả cho thiết kế**
- Thực nghiệm chính dùng **người học mô phỏng bằng mô hình thống kê**: BKT cá nhân hoá, AFM, có quên. Mô hình sinh dữ liệu phải khác mô hình planner dùng.
- Không dùng LLM làm người học ảo trong thực nghiệm chính.
- Ghi rõ giới hạn: mô phỏng chỉ chứng minh chính sách đúng **dưới giả định của mô hình**. Nếu kịp, chạy thử nghiệm nhỏ với người thật.

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Doroudi et al. (2017) | Ma trận đánh giá vững | Thiết kế thực nghiệm chính |
| Käser & Alexandron (2024) | Tổng quan người học mô phỏng; nhiều mô hình không được kiểm chứng | Giới hạn và cách kiểm chứng mô phỏng |
| Noh et al. (2026) | Mô hình sinh dữ liệu khác mô hình theo dõi | Như trên |
| Lu & Wang (2024) | Sinh viên ảo bằng LLM theo hồ sơ KC | Hướng thử thêm |
| Gao et al. (2025) | Agent4Edu | Như trên |
| Yuan et al. (2026) [preprint] | Nghịch lý năng lực của sinh viên ảo bằng LLM | Lý do không dùng LLM trong thực nghiệm chính |

---

## 8. LLM trong agent giáo dục

**Câu hỏi:** LLM nên nằm ở đâu trong Agent?

**Bằng chứng chính**
- Kambhampati et al. (2024): LLM tự nó không lập kế hoạch và không tự kiểm chứng đáng tin. Các tác giả đề xuất khung **LLM-Modulo**: LLM đề xuất, bộ kiểm tra bên ngoài quyết định.
- **Tổng quan:** Wang et al. (2024) về LLM cho giáo dục. Chu et al. (2025) về LLM agent cho giáo dục: các thành phần bộ nhớ, công cụ, lập kế hoạch; mô hình người học là trạng thái, điều chỉnh dạy học là hành động.
- **Hệ thống gần đây:**
  - GenMentor (Wang et al., 2025): nhiều agent LLM, đi từ mục tiêu → kỹ năng → lộ trình → nội dung.
  - IntelliCode (David & Ghosh, 2025) [preprint]: trạng thái người học tập trung, có phiên bản, chỉ một nơi được ghi; 6 agent chuyên biệt.
  - ALIGNAgent (Tokoli et al., 2026) [preprint]: agent GPT-4o ước lượng mức thạo theo chủ đề và gợi ý tài liệu, thử trên 2 môn khoa học máy tính.
- **Rủi ro và lợi ích:**
  - Bastani et al. (2025), khoảng 1.000 học sinh: dùng GPT tự do làm điểm luyện tập tăng, nhưng khi bỏ AI thì điểm thi thấp hơn nhóm không dùng 17%. Phiên bản có rào chắn sư phạm tránh được phần lớn thiệt hại.
  - Kestin et al. (2025): gia sư AI được thiết kế theo nguyên tắc sư phạm giúp sinh viên vật lý học được nhiều hơn trong ít thời gian hơn so với lớp học tích cực.

**Hệ quả cho thiết kế**
- Quyết định (mức thành thạo, hành động tiếp theo) do code. LLM chỉ làm ở những chỗ có kiểm soát: chấm tự luận theo ý, viết câu hỏi nhắm chỗ hụt.
- Biến thể "LLM chọn hành động trong tập hợp lệ do code tính" là thực nghiệm đối chứng theo đúng khung LLM-Modulo.
- Agent không giải bài hộ sinh viên. Nó chỉ chọn việc để sinh viên tự làm, nên tránh được rủi ro "dựa dẫm" mà Bastani et al. (2025) mô tả.

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Kambhampati et al. (2024) | LLM-Modulo: LLM đề xuất, bộ kiểm tra quyết định | Thiết kế biến thể LLM chọn hành động |
| Wang et al. (2024) | Tổng quan LLM cho giáo dục | Bối cảnh |
| Chu et al. (2025) | Tổng quan LLM agent cho giáo dục | Bối cảnh; so sánh kiến trúc |
| Wang et al. (2025) | GenMentor | Hệ thống liên quan |
| David & Ghosh (2025) [preprint] | IntelliCode | Hệ thống liên quan; trạng thái tập trung |
| Tokoli et al. (2026) [preprint] | ALIGNAgent | Hệ thống liên quan; LLM ước lượng mức thạo |
| Bastani et al. (2025) | AI không rào chắn làm hại việc học | Agent không làm hộ bài |
| Kestin et al. (2025) | Gia sư AI theo sư phạm hơn lớp học tích cực | Bối cảnh |

---

## 9. Sinh câu hỏi theo trạng thái người học

**Câu hỏi:** Khi ngân hàng hết câu phù hợp, có nên để LLM sinh câu mới nhắm vào chỗ sinh viên hụt?

**Bằng chứng chính**
- Kurdi et al. (2020), tổng quan 93 bài về sinh câu hỏi tự động: kiểm soát độ khó và phản hồi ít được nghiên cứu.
- Scaria et al. (2024): LLM sinh được câu theo mức Bloom nếu prompt tốt, nhưng chất lượng khác nhiều giữa các model; đánh giá tự động kém hơn chuyên gia.
- Gao et al. (2026) [preprint], KT4EQG: dùng KT chọn khái niệm cần luyện, rồi LLM sinh câu cho khái niệm đó. Một nhận xét độc lập lưu ý rằng cách đánh giá có nguy cơ tự xác nhận, vì cùng một mô hình KT vừa chọn khái niệm vừa chấm hiệu quả.

**Hệ quả cho thiết kế**
- Sinh câu nhắm chỗ hụt là phần mở rộng, không phải lõi.
- Câu sinh ra đi qua pipeline kiểm tra hiện có và hàng đợi duyệt của giảng viên.
- Khi đánh giá phần này, không dùng chính mô hình đã chọn khái niệm để chấm kết quả.

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Kurdi et al. (2020) | Tổng quan sinh câu hỏi tự động | Bối cảnh |
| Scaria et al. (2024) | Sinh câu theo mức Bloom bằng LLM | Điều kiện về mức Bloom |
| Gao et al. (2026) [preprint] | KT chọn khái niệm, LLM sinh câu | Thiết kế và rủi ro đánh giá của hành động sinh câu |

---

## 10. Tách câu luyện tập khỏi câu thi

**Câu hỏi:** Agent lấy câu từ ngân hàng chung có làm lộ đề kiểm tra không?

**Bằng chứng chính:** kiểm tra thích ứng trên máy có cả một hướng nghiên cứu về kiểm soát mức lộ câu, để câu không bị dùng quá nhiều và không lộ trước khi thi (Georgiadou et al., 2007, tổng quan 1983–2005).

**Hệ quả cho thiết kế:** câu nằm trong đề có chế độ Kiểm tra không được đưa vào kho luyện của Agent. Khi giảng viên soạn đề Kiểm tra, hệ thống cho biết câu nào đã dùng trong luyện tập.

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Georgiadou et al. (2007) | Tổng quan kiểm soát mức lộ câu | Lọc kho luyện |

---

## 11. Truy vết: quyết định thiết kế và căn cứ

| Quyết định trong thiết kế | Căn cứ |
|---|---|
| Agent là vòng ngoài của ITS; tính agent nằm ở việc chọn hành động theo trạng thái | Wooldridge & Jennings (1995); VanLehn (2006) |
| BKT tham số cố định, xác suất đoán theo loại câu | Corbett & Anderson (1995); Pardos & Heffernan (2011); Beck & Chang (2007) |
| Không dùng DKT, không dùng LLM làm mô hình người học | Gervet et al. (2020); Khajah et al. (2016); Neshaei et al. (2024); Hooshyar et al. (2025) |
| So sánh BKT với 3 câu liên tiếp và EMA | Kelly et al. (2015); Pelánek & Řihák (2017); Niu et al. (2026) |
| Ngưỡng 0.95, phân tích thêm 0.98; số quan sát tối thiểu | Corbett & Anderson (1995); Zhang et al. (2025); Pelánek (2018) |
| Báo giảng viên sau 10 lần chưa đạt | Beck & Gong (2013) |
| Thứ bậc mức Bloom là giả định có thể bật/tắt | Krathwohl (2002); Lalwani & Agrawal (2018); Käser et al. (2017) |
| Planner theo luật thay vì RL | Doroudi et al. (2019) |
| Đề xuất kèm lựa chọn, trong giới hạn hệ thống | Corbalan et al. (2008); Noh et al. (2026) |
| Làm câu hỏi là hoạt động chính | Roediger & Karpicke (2006); Adesope et al. (2017); Dunlosky et al. (2013) |
| Lịch ôn Leitner, để chỗ thay bằng lịch thích ứng | Leitner (1972); Cepeda et al. (2006); Lindsey et al. (2014); Settles & Meeder (2016) |
| Phản hồi theo ý rubric, trỏ về nguồn | Van der Kleij et al. (2015); Hattie & Timperley (2007) |
| Hiện mức thành thạo và lý do đề xuất | Bull & Kay (2016); Conati et al. (2021) |
| Đánh giá trên nhiều mô hình người học; mô hình sinh khác mô hình planner | Doroudi et al. (2017); Käser & Alexandron (2024); Noh et al. (2026) |
| Chỉ số luyện thừa và công bằng | Noh et al. (2026); Xia et al. (2025); Doroudi & Brunskill (2019) |
| LLM chọn hành động chỉ trong tập hợp lệ | Kambhampati et al. (2024) |
| Agent không làm hộ bài | Bastani et al. (2025) |
| Lọc câu thuộc đề Kiểm tra khỏi kho luyện | Georgiadou et al. (2007) |

---

## 12. Khoảng trống đồ án nhắm tới

1. **Ngân hàng nhiều loại câu.** Các so sánh tiêu chí thành thạo trước đây chủ yếu dùng dữ liệu một loại bài, như toán trên ASSISTments. Ngân hàng của hệ thống có 5 loại câu với xác suất đoán từ 0.5 đến gần 0. Đồ án đo xem việc tính xác suất đoán theo loại câu ảnh hưởng thế nào đến tỉ lệ "thạo giả".
2. **Quan sát từ chấm tự luận bằng LLM.** Kết quả đạt hay chưa của từng ý rubric, do LLM phán, được dùng làm đầu vào cho mô hình người học và cho phản hồi.
3. **LLM bị ràng buộc ở vòng ngoài.** So sánh planner theo luật với LLM chọn hành động trong tập hợp lệ (LLM-Modulo), đo cả chất lượng quyết định lẫn chi phí.
4. **Bối cảnh triển khai.** Hệ thống chạy trong LMS thật (Canvas, qua LTI 1.3), với môn học bằng tiếng Việt.

---

## Danh mục tài liệu

- Abdelrahman, G., Wang, Q., & Nunes, B. P. (2023). Knowledge tracing: A survey. *ACM Computing Surveys*, 55(11), 1–37. https://doi.org/10.1145/3569576
- Adesope, O. O., Trevisan, D. A., & Sundararajan, N. (2017). Rethinking the use of tests: A meta-analysis of practice testing. *Review of Educational Research*, 87(3), 659–701. https://doi.org/10.3102/0034654316689306
- Anderson, L. W., & Krathwohl, D. R. (Eds.). (2001). *A taxonomy for learning, teaching, and assessing: A revision of Bloom's taxonomy of educational objectives*. Longman.
- Badrinath, A., Wang, F., & Pardos, Z. (2021). pyBKT: An accessible Python library of Bayesian knowledge tracing models. In *Proceedings of EDM 2021* (pp. 468–474). https://arxiv.org/abs/2105.00385
- Baker, R. S. J. d., Corbett, A. T., & Aleven, V. (2008). More accurate student modeling through contextual estimation of slip and guess probabilities in Bayesian knowledge tracing. In *ITS 2008*, LNCS 5091 (pp. 406–415). https://doi.org/10.1007/978-3-540-69132-7_44
- Bastani, H., et al. (2025). Generative AI without guardrails can harm learning: Evidence from high school mathematics. *PNAS*, 122(26), e2422633122. https://doi.org/10.1073/pnas.2422633122
- Beck, J. E., & Chang, K.-m. (2007). Identifiability: A fundamental problem of student modeling. In *User Modeling 2007*, LNCS 4511 (pp. 137–146). Springer.
- Beck, J. E., & Gong, Y. (2013). Wheel-spinning: Students who fail to master a skill. In *AIED 2013*, LNCS 7926 (pp. 431–440). Springer.
- Bloom, B. S. (1968). Learning for mastery. *Evaluation Comment*, 1(2).
- Bloom, B. S. (1984). The 2 sigma problem: The search for methods of group instruction as effective as one-to-one tutoring. *Educational Researcher*, 13(6), 4–16. https://doi.org/10.3102/0013189X013006004
- Brunmair, M., & Richter, T. (2019). Similarity matters: A meta-analysis of interleaved learning and its moderators. *Psychological Bulletin*, 145(11), 1029–1052. https://doi.org/10.1037/bul0000209
- Bull, S., & Kay, J. (2016). SMILI☺: A framework for interfaces to learning data in open learner models, learning analytics and related fields. *International Journal of Artificial Intelligence in Education*, 26(1), 293–331.
- Cen, H., Koedinger, K., & Junker, B. (2006). Learning factors analysis – A general method for cognitive model evaluation and improvement. In *ITS 2006* (pp. 164–175). Springer.
- Cepeda, N. J., Pashler, H., Vul, E., Wixted, J. T., & Rohrer, D. (2006). Distributed practice in verbal recall tasks: A review and quantitative synthesis. *Psychological Bulletin*, 132(3), 354–380. https://doi.org/10.1037/0033-2909.132.3.354
- Chu, Z., Wang, S., Xie, J., Zhu, T., Yan, Y., Ye, J., Zhong, A., Hu, X., Liang, J., Yu, P. S., & Wen, Q. (2025). LLM agents for education: Advances and applications. In *Findings of EMNLP 2025* (pp. 13782–13810). https://aclanthology.org/2025.findings-emnlp.743/
- Clement, B., Roy, D., Oudeyer, P.-Y., & Lopes, M. (2015). Multi-armed bandits for intelligent tutoring systems. *Journal of Educational Data Mining*, 7(2), 20–48. https://jedm.educationaldatamining.org/index.php/JEDM/article/view/111
- Conati, C., Barral, O., Putnam, V., & Rieger, L. (2021). Toward personalized XAI: A case study in intelligent tutoring systems. *Artificial Intelligence*, 298, 103503. https://doi.org/10.1016/j.artint.2021.103503
- Corbalan, G., Kester, L., & van Merriënboer, J. J. G. (2008). Selecting learning tasks: Effects of adaptation and shared control on learning efficiency and task involvement. *Contemporary Educational Psychology*, 33(4), 733–756.
- Corbett, A. T., & Anderson, J. R. (1995). Knowledge tracing: Modeling the acquisition of procedural knowledge. *User Modeling and User-Adapted Interaction*, 4(4), 253–278. https://doi.org/10.1007/BF01099821 (số tạp chí ghi tháng 12/1994; thường được trích là 1995)
- David, J., & Ghosh, S. (2025). IntelliCode: A multi-agent LLM tutoring system with centralized learner modeling [Preprint]. arXiv:2512.18669.
- Doroudi, S., Aleven, V., & Brunskill, E. (2017). Robust evaluation matrix: Towards a more principled offline exploration of instructional policies. In *L@S '17* (pp. 3–12). https://doi.org/10.1145/3051457.3051463
- Doroudi, S., Aleven, V., & Brunskill, E. (2019). Where's the reward? A review of reinforcement learning for instructional sequencing. *International Journal of Artificial Intelligence in Education*, 29(4), 568–620. https://doi.org/10.1007/s40593-019-00187-x
- Doroudi, S., & Brunskill, E. (2017). The misidentified identifiability problem of Bayesian knowledge tracing. In *Proceedings of EDM 2017*.
- Doroudi, S., & Brunskill, E. (2019). Fairer but not fair enough: On the equitability of knowledge tracing. In *LAK '19* (pp. 335–339). https://doi.org/10.1145/3303772.3303838
- Dunlosky, J., Rawson, K. A., Marsh, E. J., Nathan, M. J., & Willingham, D. T. (2013). Improving students' learning with effective learning techniques: Promising directions from cognitive and educational psychology. *Psychological Science in the Public Interest*, 14(1), 4–58. https://doi.org/10.1177/1529100612453266
- Fancsali, S. E., Nixon, T., & Ritter, S. (2013). Optimal and worst-case performance of mastery learning assessment with Bayesian knowledge tracing. In *Proceedings of EDM 2013* (pp. 35–42).
- Gao, W., et al. (2025). Agent4Edu: Generating learner response data by generative agents for intelligent education systems. In *AAAI 2025*, 39(22). https://doi.org/10.1609/aaai.v39i22.34565
- Gao, X., Wu, Q., Ding, L., Liao, Q. V., Qian, K., Xu, Y., Chang, S., & Zhang, Y. (2026). KT4EQG: Personalized exercise question generation via knowledge tracing [Preprint]. arXiv:2605.23933.
- Georgiadou, E., Triantafillou, E., & Economides, A. A. (2007). A review of item exposure control strategies for computerized adaptive testing developed from 1983 to 2005. *Journal of Technology, Learning, and Assessment*, 5(8). https://www.ejournals.bc.edu/index.php/jtla/article/view/1647
- Gervet, T., Koedinger, K., Schneider, J., & Mitchell, T. (2020). When is deep learning the best approach to knowledge tracing? *Journal of Educational Data Mining*, 12(3), 31–54. https://doi.org/10.5281/zenodo.4143614
- Gierl, M. J., Bulut, O., Guo, Q., & Zhang, X. (2017). Developing, analyzing, and using distractors for multiple-choice tests in education: A comprehensive review. *Review of Educational Research*, 87(6), 1082–1116. https://doi.org/10.3102/0034654317726529
- Girard, S., Minn, S., Bouzeghoub, A., & Vie, J.-J. (2026). Counterfactual learning of new adaptive instructional policies using logged data. In *ECML-PKDD 2026*. arXiv:2606.23015.
- Hattie, J., & Timperley, H. (2007). The power of feedback. *Review of Educational Research*, 77(1), 81–112. https://doi.org/10.3102/003465430298487
- Heffernan, N. T., & Heffernan, C. L. (2014). The ASSISTments ecosystem: Building a platform that brings scientists and teachers together for minimally invasive research on human learning and teaching. *International Journal of Artificial Intelligence in Education*, 24(4), 470–497. https://doi.org/10.1007/s40593-014-0024-x
- Hooshyar, D., Yang, Y., Šíř, G., Kärkkäinen, T., Hämäläinen, R., Cukurova, M., & Azevedo, R. (2025). Problems with large language models for learner modelling: Why LLMs alone fall short for responsible tutoring in K–12 education [Preprint]. arXiv:2512.23036.
- Kambhampati, S., et al. (2024). Position: LLMs can't plan, but can help planning in LLM-Modulo frameworks. In *ICML 2024*, PMLR 235, 22895–22907. https://proceedings.mlr.press/v235/kambhampati24a.html
- Karpicke, J. D., & Roediger, H. L. (2008). The critical importance of retrieval for learning. *Science*, 319(5865), 966–968. https://doi.org/10.1126/science.1152408
- Käser, T., & Alexandron, G. (2024). Simulated learners in educational technology: A systematic literature review and a Turing-like test. *International Journal of Artificial Intelligence in Education*, 34(2), 545–585. https://doi.org/10.1007/s40593-023-00337-2
- Käser, T., Klingler, S., & Gross, M. (2016). When to stop? Towards universal instructional policies. In *LAK '16* (pp. 289–298). ACM.
- Käser, T., Klingler, S., Schwing, A. G., & Gross, M. (2014). Beyond knowledge tracing: Modeling skill topologies with Bayesian networks. In *ITS 2014* (pp. 188–198). Springer.
- Käser, T., Klingler, S., Schwing, A. G., & Gross, M. (2017). Dynamic Bayesian networks for student modeling. *IEEE Transactions on Learning Technologies*, 10(4), 450–462.
- Kelly, K., Wang, Y., Thompson, T., & Heffernan, N. (2015). Defining mastery: Knowledge tracing versus N-consecutive correct responses. In *Proceedings of EDM 2015* (pp. 630–631). https://www.educationaldatamining.org/EDM2015/proceedings/poster630-631.pdf
- Kestin, G., Miller, K., Klales, A., Milbourne, T., & Ponti, G. (2025). AI tutoring outperforms in-class active learning. *Scientific Reports*, 15, 17458. https://doi.org/10.1038/s41598-025-97652-6
- Khajah, M., Lindsey, R. V., & Mozer, M. C. (2016). How deep is knowledge tracing? In *Proceedings of EDM 2016*. https://arxiv.org/abs/1604.02416
- Khalid, A., Deriyeva, A., & Paassen, B. (2025). Does interpretability of knowledge tracing models support teacher decision making? AIED 2025 Workshop on Epistemics and Decision-Making in AI-Supported Education. arXiv:2511.02718.
- Koedinger, K. R., Corbett, A. T., & Perfetti, C. (2012). The Knowledge-Learning-Instruction framework: Bridging the science-practice chasm to enhance robust student learning. *Cognitive Science*, 36(5), 757–798.
- Krathwohl, D. R. (2002). A revision of Bloom's taxonomy: An overview. *Theory Into Practice*, 41(4), 212–218. https://doi.org/10.1207/s15430421tip4104_2
- Kulik, C.-L. C., Kulik, J. A., & Bangert-Drowns, R. L. (1990). Effectiveness of mastery learning programs: A meta-analysis. *Review of Educational Research*, 60(2), 265–299. https://doi.org/10.3102/00346543060002265
- Kulik, J. A., & Fletcher, J. D. (2016). Effectiveness of intelligent tutoring systems: A meta-analytic review. *Review of Educational Research*, 86(1), 42–78. https://doi.org/10.3102/0034654315581420
- Kurdi, G., Leo, J., Parsia, B., Sattler, U., & Al-Emari, S. (2020). A systematic review of automatic question generation for educational purposes. *International Journal of Artificial Intelligence in Education*, 30, 121–204. https://doi.org/10.1007/s40593-019-00186-y
- Lalwani, A., & Agrawal, S. (2018). Validating revised Bloom's taxonomy using deep knowledge tracing. In *AIED 2018*. https://doi.org/10.1007/978-3-319-93843-1_17
- Leitner, S. (1972). *So lernt man lernen*. Herder.
- Lindsey, R. V., Shroyer, J. D., Pashler, H., & Mozer, M. C. (2014). Improving students' long-term knowledge retention through personalized review. *Psychological Science*, 25(3), 639–647. https://doi.org/10.1177/0956797613504302
- Liu, Q., Shen, S., Huang, Z., Chen, E., & Zheng, Y. (2021). A survey of knowledge tracing: Models, variants, and applications [Preprint; bản tạp chí đăng ở IEEE Transactions on Learning Technologies, 2024]. arXiv:2105.15106.
- Lu, X., & Wang, X. (2024). Generative students: Using LLM-simulated student profiles to support question item evaluation. In *L@S '24*. https://doi.org/10.1145/3657604.3662031
- Mettler, E., Massey, C. M., & Kellman, P. J. (2016). A comparison of adaptive and fixed schedules of practice. *Journal of Experimental Psychology: General*, 145(7), 897–917. https://doi.org/10.1037/xge0000170
- Moore, S., Schmucker, R., Mitchell, T., & Stamper, J. (2024). Automated generation and tagging of knowledge components from multiple-choice questions. In *L@S '24* (pp. 122–133). https://doi.org/10.1145/3657604.3662030
- Neshaei, S. P., Davis, R. L., Hazimeh, A., Lazarevski, B., Dillenbourg, P., & Käser, T. (2024). Towards modeling learner performance with large language models. In *Proceedings of EDM 2024* (poster). https://arxiv.org/abs/2403.14661
- Niu, C., Bradley, K. D., Waltman, B. F., & Ma, B. (2026). Beyond "three-in-a-row": Toward fairer adaptive mastery decisions in AI-supported formative assessment. In *Proceedings of AIME-Con 2026: Full Papers* (pp. 673–680). NCME. https://aclanthology.org/2026.aimecon-main.76/
- Noh, H., Chowdhary, A., Ooge, J., Aleven, V., & Borchers, C. (2026). Simulating learners' task-selection strategies and system constraints in mastery learning. In *Proceedings of EDM 2026* (short paper). https://educationaldatamining.org/edm2026/proceedings/2026.EDM.short-papers.242/index.html
- Papoušek, J., Pelánek, R., & Stanislav, V. (2014). Adaptive practice of facts in domains with varied prior knowledge. In *Proceedings of EDM 2014* (pp. 6–13).
- Pardos, Z. A., & Heffernan, N. T. (2011). KT-IDEM: Introducing item difficulty to the knowledge tracing model. In *UMAP 2011* (pp. 243–254). Springer.
- Pavlik, P. I., Cen, H., & Koedinger, K. R. (2009). Performance factors analysis – A new alternative to knowledge tracing. In *AIED 2009* (pp. 531–538). IOS Press.
- Pelánek, R. (2016). Applications of the Elo rating system in adaptive educational systems. *Computers & Education*. https://doi.org/10.1016/j.compedu.2016.03.017
- Pelánek, R. (2017). Bayesian knowledge tracing, logistic models, and beyond: An overview of learner modeling techniques. *User Modeling and User-Adapted Interaction*, 27(3–5), 313–350. https://doi.org/10.1007/s11257-017-9193-2
- Pelánek, R. (2018). Conceptual issues in mastery criteria: Differentiating uncertainty and degrees of knowledge. In *AIED 2018* (pp. 450–461). https://doi.org/10.1007/978-3-319-93843-1_33
- Pelánek, R., Papoušek, J., Řihák, J., Stanislav, V., & Nižnan, J. (2017). Elo-based learner modeling for the adaptive practice of facts. *User Modeling and User-Adapted Interaction*. https://doi.org/10.1007/s11257-016-9185-7
- Pelánek, R., & Řihák, J. (2017). Experimental analysis of mastery learning criteria. In *UMAP '17* (pp. 156–163). https://doi.org/10.1145/3079628.3079667
- Pelánek, R., & Řihák, J. (2018). Analysis and design of mastery learning criteria. *New Review of Hypermedia and Multimedia*, 24(3).
- Piech, C., Bassen, J., Huang, J., Ganguli, S., Sahami, M., Guibas, L. J., & Sohl-Dickstein, J. (2015). Deep knowledge tracing. In *Advances in Neural Information Processing Systems 28* (pp. 505–513).
- Rafferty, A. N., Brunskill, E., Griffiths, T. L., & Shafto, P. (2016). Faster teaching via POMDP planning. *Cognitive Science*, 40(6), 1290–1332.
- Roediger, H. L., & Karpicke, J. D. (2006). Test-enhanced learning: Taking memory tests improves long-term retention. *Psychological Science*, 17(3), 249–255. https://doi.org/10.1111/j.1467-9280.2006.01693.x
- Rollinson, J., & Brunskill, E. (2015). From predictive models to instructional policies. In *Proceedings of EDM 2015* (pp. 179–186).
- Rowland, C. A. (2014). The effect of testing versus restudy on retention: A meta-analytic review of the testing effect. *Psychological Bulletin*, 140(6), 1432–1463. https://doi.org/10.1037/a0037559
- Russell, S., & Norvig, P. (2021). *Artificial intelligence: A modern approach* (4th ed.). Pearson.
- Scaria, N., Chenna, S. D., & Subramani, D. (2024). Automated educational question generation at different Bloom's skill levels using large language models: Strategies and evaluation. In *AIED 2024* (pp. 165–179). https://doi.org/10.1007/978-3-031-64299-9_12
- Settles, B., & Meeder, B. (2016). A trainable spaced repetition model for language learning. In *ACL 2016* (pp. 1848–1858). https://doi.org/10.18653/v1/P16-1174
- Shute, V. J. (2008). Focus on formative feedback. *Review of Educational Research*, 78(1), 153–189. https://doi.org/10.3102/0034654307313795
- Tabibian, B., Upadhyay, U., De, A., Zarezade, A., Schölkopf, B., & Gomez-Rodriguez, M. (2019). Enhancing human learning via spaced repetition optimization. *PNAS*, 116(10), 3988–3993. https://doi.org/10.1073/pnas.1815156116
- Tokoli, B., Jaimes, L., & Dina, A. S. (2026). ALIGNAgent: Adaptive learner intelligence for gap identification and next-step guidance [Preprint]. arXiv:2601.15551.
- Van der Kleij, F. M., Feskens, R. C. W., & Eggen, T. J. H. M. (2015). Effects of feedback in a computer-based learning environment on students' learning outcomes: A meta-analysis. *Review of Educational Research*, 85(4), 475–511. https://doi.org/10.3102/0034654314564881
- VanLehn, K. (2006). The behavior of tutoring systems. *International Journal of Artificial Intelligence in Education*, 16(3), 227–265.
- VanLehn, K. (2011). The relative effectiveness of human tutoring, intelligent tutoring systems, and other tutoring systems. *Educational Psychologist*, 46(4), 197–221. https://doi.org/10.1080/00461520.2011.611369
- Wang, S., Xu, T., Li, H., Zhang, C., Liang, J., Tang, J., Yu, P. S., & Wen, Q. (2024). Large language models for education: A survey and outlook [Preprint]. arXiv:2403.18105.
- Wang, T., Zhan, Y., Lian, J., Hu, Z., Yuan, N. J., Zhang, Q., Xie, X., & Xiong, H. (2025). LLM-powered multi-agent framework for goal-oriented learning in intelligent tutoring system. In *WWW 2025 (Industry Track)*. arXiv:2501.15749.
- Wooldridge, M., & Jennings, N. R. (1995). Intelligent agents: Theory and practice. *The Knowledge Engineering Review*, 10(2), 115–152. https://doi.org/10.1017/S0269888900008122
- Xia, M., Schmucker, R., Borchers, C., & Aleven, V. (2025). Optimizing mastery learning by fast-forwarding over-practice steps. In *EC-TEL 2025*. arXiv:2506.17577.
- Ye, J., Su, J., & Cao, Y. (2022). A stochastic shortest path algorithm for optimizing spaced repetition scheduling. In *KDD '22* (pp. 4381–4390).
- Yuan, Z., Xiao, Y., Li, M., Xuan, W., Tong, R., Diab, M., & Mitchell, T. (2026). Towards valid student simulation with large language models [Preprint]. arXiv:2601.05473.
- Yudelson, M. V., Koedinger, K. R., & Gordon, G. J. (2013). Individualized Bayesian knowledge tracing models. In *AIED 2013* (pp. 171–180). https://doi.org/10.1007/978-3-642-39112-5_18
- Zhang, J., Vanacore, K., Baker, R. S., Ch, N., Mills, C., & Henkel, O. (2025). How much mastery is enough mastery? The relationship between mastery in a lesson and the performance on the subsequent lesson. In *Proceedings of EDM 2025* (short paper). https://educationaldatamining.org/EDM2025/proceedings/2025.EDM.short-papers.4/index.html
