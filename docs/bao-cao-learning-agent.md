# Báo cáo đề xuất Learning Agent cho luyện tập thích ứng

**Đề tài:** Hệ thống LMS tự động tạo Micro-Content & Quiz bằng Generative AI (DA Platform)  
**Nội dung:** Tổng quan nghiên cứu, thiết kế hệ thống và kế hoạch đánh giá  
**Ngày:** 16/10/2026  
**Trạng thái:** Đề xuất thiết kế, chưa triển khai Learning Agent và chưa có kết quả thực nghiệm của thành phần này.  
**Mục đích báo cáo:** Xin ý kiến giảng viên hướng dẫn về hướng nghiên cứu, phạm vi thực hiện và phương pháp đánh giá trước khi triển khai.

## Tóm tắt

DA Platform đã có luồng sinh câu hỏi từ tài liệu theo chuẩn đầu ra học tập (Learning Outcome, LO), tổ chức đề luyện tập hoặc kiểm tra, chấm tự luận ngắn bằng mô hình ngôn ngữ lớn (LLM) và tích hợp Canvas qua LTI 1.3. Theo hiện trạng được mô tả trong tài liệu dự án, hệ thống chưa sử dụng lịch sử làm bài để quyết định hoạt động tiếp theo cho từng sinh viên. Kết quả chấm từng ý của rubric cũng chưa được lưu đầy đủ để phục vụ phản hồi và theo dõi tiến bộ.

Báo cáo đề xuất một Learning Agent thực hiện vòng lặp: **quan sát kết quả → cập nhật mô hình người học → chọn hoạt động → giải thích → ghi nhận phản hồi**. Agent đảm nhiệm vòng ngoài của hệ thống dạy học thông minh: chọn nội dung và hoạt động luyện tập. Phiên bản đầu theo dõi mức thành thạo theo LO bằng Bayesian Knowledge Tracing (BKT), dùng bộ quy tắc để chọn câu luyện, đề xuất xem lại nguồn, lên lịch ôn, chuyển LO hoặc đánh dấu cần giảng viên hỗ trợ.

Tổng quan nghiên cứu được tổ chức theo 10 nhóm vấn đề, kế thừa danh mục 91 tài liệu của quá trình khảo sát. Các nghiên cứu về knowledge tracing, tiêu chí thành thạo, luyện tập ngắt quãng và đánh giá chính sách là căn cứ cho thiết kế. Các ngưỡng và tham số cụ thể của đồ án là **giả định khởi đầu cần kiểm tra**, không được xem là giá trị tối ưu đã được chứng minh cho môn học này. Các hệ thống agent dùng LLM gần đây được dùng để đối chiếu phạm vi và xác định câu hỏi thực nghiệm.

Phần đánh giá dự kiến so sánh sáu chính sách trên ba mô hình người học mô phỏng, gồm đối chứng đề cố định, ba câu đúng liên tiếp và trung bình trượt mũ. Chỉ số chính là tỉ lệ công nhận thành thạo khi người học chưa nắm, số câu cần luyện, số câu luyện thừa và mức chênh lệch giữa nhóm học nhanh, học chậm. Độ tin cậy của chấm tự luận được đánh giá riêng vì kết quả chấm là đầu vào của mô hình người học. Thử nghiệm nhỏ với sinh viên thật được đề xuất để kiểm tra khả năng sử dụng, không dùng để khẳng định hiệu quả học tập trên diện rộng.

Phạm vi đề nghị là hoàn thành lưu dữ liệu, mô hình theo LO, planner theo luật, giao diện và đánh giá mô phỏng. Theo dõi theo mức Bloom, gắn đơn vị kiến thức nhỏ hơn LO và sinh câu hỏi nhắm chỗ hụt được đặt ở giai đoạn mở rộng.

## Mục lục

1. Bối cảnh và vấn đề cần giải quyết
2. Tổng quan nghiên cứu và căn cứ thiết kế
3. Công trình liên quan, câu hỏi nghiên cứu và đóng góp dự kiến
4. Mục tiêu và phạm vi thực hiện
5. Kiến trúc và dữ liệu
6. Mô hình người học và lịch ôn
7. Chính sách chọn hoạt động
8. Vai trò của LLM và kiểm soát chất lượng
9. Giao diện và tích hợp hệ thống
10. Kế hoạch đánh giá
11. Lộ trình và rủi ro
12. Nội dung xin ý kiến giảng viên hướng dẫn

Phụ lục A: Truy vết quyết định thiết kế về căn cứ nghiên cứu.  
Phụ lục B: Danh mục tài liệu khảo sát.

## 1. Bối cảnh và vấn đề cần giải quyết

### 1.1. Hiện trạng của DA Platform

Các chức năng nền được mô tả trong tài liệu dự án gồm:

- Sinh câu hỏi từ tài liệu môn học, có LO, mức Bloom yêu cầu và một trong năm loại câu: trắc nghiệm một đáp án, trắc nghiệm nhiều đáp án, đúng/sai, điền khuyết, tự luận ngắn. Câu hỏi được đưa vào hàng đợi để giảng viên duyệt.
- Gom câu thành đề Luyện tập hoặc Kiểm tra, mở trong Canvas qua LTI 1.3 và gửi điểm của các hoạt động được cấu hình tính điểm về Canvas.
- Chấm tự luận ngắn theo rubric: LLM xét từng ý đạt hoặc chưa đạt và đưa nhận xét; chương trình tổng hợp điểm.
- Tổ chức thẻ bài học theo LO và lưu liên kết tới đoạn tài liệu nguồn, có số trang khi dữ liệu nguồn hỗ trợ.

Learning Agent là thành phần đề xuất bổ sung trên nền này. Những chức năng và cấu trúc dữ liệu mô tả từ mục 5 trở đi là thiết kế dự kiến, trừ khi được ghi rõ là thành phần nền đang có.

### 1.2. Tình huống minh hoạ

Trong môn Dữ liệu lớn, một câu tự luận thuộc L.O.1.1 yêu cầu giải thích khái niệm dữ liệu lớn. Rubric có ba ý: (1) giới hạn của công nghệ cơ sở dữ liệu tiêu chuẩn; (2) quy mô, tính đa dạng và phức tạp; (3) mục đích trích xuất giá trị.

Sinh viên A nêu được ý (2), (3) nhưng thiếu ý (1). Sinh viên B nêu đủ cả ba ý. Nếu hệ thống chỉ lưu điểm tổng và tiếp tục giao cùng một đề, thông tin khác biệt giữa hai sinh viên chưa được dùng để điều chỉnh việc luyện tập.

Với thiết kế đề xuất, hệ thống lưu kết quả từng ý và chỉ rõ nội dung A cần xem lại. Câu tự luận của A được tính là **một quan sát chưa đạt** cho L.O.1.1; Agent có thể giao thêm câu cùng LO hoặc trỏ về nguồn khi A sai liên tiếp. B chỉ chuyển LO khi đáp ứng đủ tiêu chí thành thạo dựa trên lịch sử, không phải chỉ vì trả lời đúng một câu. Các câu ôn được lên lịch sau khi LO đạt ngưỡng.

### 1.3. Ba vấn đề chính

| Vấn đề | Biểu hiện | Hệ quả đối với thiết kế |
|---|---|---|
| Chưa thích ứng theo người học | Sinh viên nhận cùng tập câu dù lịch sử khác nhau | Cần mô hình trạng thái và cơ chế chọn hoạt động tiếp theo |
| Chưa tận dụng thông tin chẩn đoán | Kết quả từng ý rubric chưa được giữ đầy đủ | Cần lưu kết quả từng ý, phản hồi cụ thể và liên kết về nguồn |
| Chưa có vòng ôn và hỗ trợ khi bị kẹt | LO đã đạt chưa có lịch ôn; sinh viên sai nhiều chưa có cờ hỗ trợ | Cần lịch ôn, giới hạn luyện và đường chuyển cho giảng viên |

## 2. Tổng quan nghiên cứu và căn cứ thiết kế

### 2.1. Phạm vi khảo sát và cách sử dụng bằng chứng

Danh mục khảo sát gồm 91 tài liệu, được tổ chức theo 10 nhóm. Nguồn tìm kiếm của tài liệu nền gồm kỷ yếu EDM, AIED, ITS, LAK, L@S, UMAP, EC-TEL; các tạp chí IJAIED, UMUAI, JEDM, IEEE TLT và các tạp chí tâm lý học, giáo dục; cùng arXiv để theo dõi hướng nghiên cứu mới. Từ khoá gồm knowledge tracing, mastery learning criteria, instructional sequencing, adaptive practice, spaced repetition, feedback, open learner model, simulated learners, LLM agents for education, personalized question generation và item exposure control.

Tiêu chí sử dụng trong báo cáo là mức liên quan đến một quyết định thiết kế hoặc một câu hỏi đánh giá. Nghiên cứu nền tảng, khảo sát và công trình có thực nghiệm được ưu tiên làm căn cứ; bài mới dùng để đối chiếu hướng tiếp cận. Bản tổng hợp này là **tổng quan định hướng thiết kế**, chưa phải tổng quan hệ thống có quy trình tìm kiếm, sàng lọc và đánh giá chất lượng tái lập đầy đủ.

Phần khảo sát ban đầu chủ yếu dựa trên tóm tắt và trang công bố. Vì vậy, báo cáo không lặp lại các cỡ hiệu ứng hoặc mức cải thiện định lượng chưa được kiểm tra đầy đủ về điều kiện đo. Các con số trong phần thiết kế và kế hoạch đánh giá là cấu hình đề xuất hoặc ví dụ tính từ công thức, được ghi rõ theo từng mục. Ký hiệu **[preprint]** chỉ bản thảo chưa được xác nhận xuất bản qua bình duyệt trong danh mục đang dùng; chúng không là căn cứ duy nhất cho lựa chọn cốt lõi.

### 2.2. Nhóm 1 — Agent và hệ thống dạy học thông minh

Wooldridge và Jennings (1995), Russell và Norvig (2021) cung cấp nền tảng về agent quan sát môi trường và chọn hành động hướng tới mục tiêu. VanLehn (2006) phân biệt vòng ngoài chọn bài tập với vòng trong hỗ trợ các bước giải. Các tổng hợp của VanLehn (2011), Kulik và Fletcher (2016), cùng bối cảnh gia sư một kèm một của Bloom (1984), cho thấy hướng dạy học có hỗ trợ và thích ứng có cơ sở để nghiên cứu. Hiệu quả của các hệ thống đã khảo sát không được chuyển trực tiếp thành kỳ vọng định lượng cho DA Platform.

**Lựa chọn cho đồ án:** xây Agent ở vòng ngoài, duy trì trạng thái người học qua nhiều lượt và chọn hoạt động dựa trên trạng thái đó. Đây là agent dùng mô hình người học và chính sách theo luật; khả năng tự học chính sách từ dữ liệu chưa thuộc phiên bản đầu.

### 2.3. Nhóm 2 — Mô hình người học và knowledge tracing

BKT của Corbett và Anderson (1995) biểu diễn trạng thái nắm kiến thức bằng xác suất và cập nhật sau từng câu trả lời. Các mở rộng nghiên cứu xác suất đoán, trượt theo ngữ cảnh (Baker et al., 2008), tác động độ khó câu hỏi (Pardos & Heffernan, 2011), khác biệt giữa người học (Yudelson et al., 2013) và quan hệ giữa các kỹ năng (Käser et al., 2014, 2017). AFM, PFA và Elo cung cấp các phương án khác với mức phức tạp vừa phải (Cen et al., 2006; Pavlik et al., 2009; Pelánek, 2016; Pelánek et al., 2017).

So sánh của [Gervet et al. (2020)](https://jedm.educationaldatamining.org/index.php/JEDM/article/view/451) cho thấy lựa chọn mô hình phụ thuộc quy mô và đặc điểm dữ liệu; BKT không phải mô hình dự đoán tốt nhất trong so sánh đó. Khajah et al. (2016) phân tích ảnh hưởng của các mở rộng BKT khi so với DKT của Piech et al. (2015). Các tổng quan của Pelánek (2017), Liu et al. (2021), Abdelrahman et al. (2023) giúp đặt các lựa chọn này vào cùng bối cảnh.

**Lựa chọn cho đồ án:** dùng BKT tham số cố định làm điểm xuất phát vì chưa có tập tương tác đủ để hiệu chỉnh đáng tin cậy. Đây là lựa chọn về tính khả thi và khả năng kiểm tra, không phải kết luận BKT ưu việt hơn. Các vấn đề xác định tham số của Beck và Chang (2007), Doroudi và Brunskill (2017) đòi hỏi phân tích độ nhạy. Khi có dữ liệu, có thể ước lượng bằng pyBKT (Badrinath et al., 2021) và so sánh thêm Elo/PFA.

### 2.4. Nhóm 3 — Tiêu chí thành thạo và thời điểm dừng luyện

Mastery learning yêu cầu điều chỉnh lượng luyện theo việc đạt mục tiêu (Bloom, 1968; Kulik et al., 1990). Tuy nhiên, chọn mô hình và chọn ngưỡng công nhận thành thạo là hai quyết định khác nhau. Fancsali et al. (2013), Rollinson và Brunskill (2015), Käser et al. (2016) đặt vấn đề đánh giá tác động của quyết định dừng, thay vì chỉ độ chính xác dự đoán.

Ba câu đúng liên tiếp là một tiêu chí thực dụng, được nghiên cứu trong bối cảnh ASSISTments (Heffernan & Heffernan, 2014; Kelly et al., 2015). [Pelánek và Řihák (2017)](https://www.fi.muni.cz/~xpelanek/publications/mastery-detection.pdf) nhấn mạnh vai trò của dữ liệu quan sát và ngưỡng, đồng thời đề xuất EMA như một đối chứng đơn giản. Pelánek và Řihák (2018), Pelánek (2018), Zhang et al. (2025) và Niu et al. (2026) tiếp tục đặt vấn đề về tiêu chí và tính nhất quán của quyết định.

**Lựa chọn cho đồ án:** so sánh BKT với N-CCR và EMA; thử các ngưỡng BKT 0.95, 0.98 và số quan sát tối thiểu. Ngưỡng hỗ trợ sau nhiều lần chưa đạt được lấy cảm hứng từ wheel-spinning (Beck & Gong, 2013), nhưng là cờ cần xem xét, không phải chẩn đoán sinh viên không thể học. Đánh giá tách nhóm học nhanh/chậm theo vấn đề công bằng được Doroudi và Brunskill (2019) nêu.

### 2.5. Nhóm 4 — Chọn hoạt động tiếp theo

Các hướng chọn hoạt động gồm quy tắc, bandit, POMDP và học tăng cường. Clement et al. (2015), Rafferty et al. (2016), Girard et al. (2026) minh hoạ các phương án này. Tổng quan của Doroudi et al. (2019) cho thấy hiệu quả của học tăng cường trong sắp xếp hoạt động học cần được đánh giá với đối chứng phù hợp. Papoušek et al. (2014) tách bài toán ước lượng trạng thái khỏi chọn câu; Mettler et al. (2016) nghiên cứu lịch luyện thích ứng so với cố định.

Noh et al. (2026), Xia et al. (2025) xem xét luyện thừa và các ràng buộc hệ thống. Corbalan et al. (2008) nghiên cứu chia quyền chọn bài giữa hệ thống và người học; Brunmair và Richter (2019) tổng hợp bằng chứng về xen kẽ nội dung.

**Lựa chọn cho đồ án:** planner theo luật, có thứ tự ưu tiên và nhật ký giải thích. Sinh viên được chọn trong một tập hoạt động hợp lệ. Luyện thừa và việc bỏ qua đề xuất đều được đo; lợi ích của từng luật cần được kiểm chứng trong thực nghiệm.

### 2.6. Nhóm 5 — Luyện bằng kiểm tra và ôn ngắt quãng

Roediger và Karpicke (2006), Karpicke và Roediger (2008), Rowland (2014), Adesope et al. (2017), Dunlosky et al. (2013) là căn cứ cho luyện tập bằng truy hồi kiến thức. Cepeda et al. (2006) là căn cứ về phân bố luyện tập theo thời gian. Các hướng lập lịch gồm hộp Leitner (1972), HLR (Settles & Meeder, 2016), tối ưu lịch ôn (Tabibian et al., 2019; Ye et al., 2022) và ôn cá nhân hoá trong lớp học (Lindsey et al., 2014).

**Lựa chọn cho đồ án:** hoạt động chính là làm câu hỏi có phản hồi; xem lại nguồn là can thiệp hỗ trợ. Dùng lịch kiểu Leitner ở phiên bản đầu và để riêng giao diện bộ lập lịch. Bằng chứng về lợi ích của ôn phân bố không chứng minh lịch 1–3–7–14–30 ngày của đề xuất là tối ưu, hoặc HLR/FSRS chắc chắn tốt hơn trong bối cảnh này.

### 2.7. Nhóm 6 — Phản hồi, chẩn đoán và mô hình người học mở

Hattie và Timperley (2007), Shute (2008), Van der Kleij et al. (2015) là căn cứ cho phản hồi chỉ rõ nội dung thiếu và bước tiếp theo. Khung KLI (Koedinger et al., 2012) và nghiên cứu gắn đơn vị kiến thức của Moore et al. (2024) gợi ý cách theo dõi chi tiết hơn LO. Gierl et al. (2017) cung cấp cơ sở cho thiết kế phương án nhiễu gắn với hiểu lầm.

Bull và Kay (2016), Conati et al. (2021), Khalid et al. (2025) đặt vấn đề hiển thị và giải thích mô hình người học cho người sử dụng.

**Lựa chọn cho đồ án:** lưu từng ý rubric để phản hồi và dẫn về nguồn; hiển thị trạng thái theo LO kèm số quan sát. Theo dõi từng ý như một đơn vị kiến thức độc lập cần bước ánh xạ và kiểm chứng bổ sung, được để ở phần mở rộng. Độ đúng của chấm LLM cần được đo riêng trước khi sử dụng kết quả chấm làm bằng chứng thành thạo.

### 2.8. Nhóm 7 — Đánh giá bằng người học mô phỏng

[Doroudi et al. (2017)](https://files.eric.ed.gov/fulltext/ED577159.pdf) đề xuất Robust Evaluation Matrix để xem xét sự không khớp giữa mô hình dùng khi thiết kế chính sách và mô hình mô phỏng dùng khi đánh giá. Käser và Alexandron (2024) cho thấy việc kiểm chứng mô hình người học ảo là một vấn đề cần quan tâm. Noh et al. (2026) minh hoạ đánh giá chính sách khi mô hình sinh câu trả lời khác mô hình theo dõi.

Lu và Wang (2024), Gao et al. (2025) nghiên cứu người học ảo dùng LLM. Yuan et al. (2026) [preprint] đặt vấn đề về tính hợp lệ của việc dùng LLM mô phỏng năng lực và lỗi của sinh viên.

**Lựa chọn cho đồ án:** dùng nhiều bộ sinh dữ liệu thống kê; có trường hợp sai lệch tham số và khác họ mô hình. Kết quả chỉ có giá trị dưới các giả định đã công bố, cần đối chiếu với dữ liệu thật khi có điều kiện.

### 2.9. Nhóm 8 — Vai trò của LLM trong agent giáo dục

Wang et al. (2024), Chu et al. (2025) tổng quan việc dùng LLM trong giáo dục. GenMentor, IntelliCode và ALIGNAgent cho thấy các cách tích hợp hồ sơ người học, công cụ và đề xuất hoạt động; đối chiếu cụ thể ở mục 3. Neshaei et al. (2024), Hooshyar et al. (2025) [preprint] là cơ sở để đặt câu hỏi về độ tin cậy khi LLM trực tiếp theo dõi trạng thái người học, không đủ để kết luận mọi cách dùng LLM đều không phù hợp.

[Kambhampati et al. (2024)](https://proceedings.mlr.press/v235/kambhampati24a.html) đề xuất kết hợp LLM với bộ kiểm tra bên ngoài trong khung LLM-Modulo. Bastani et al. (2025) và Kestin et al. (2025) cho thấy tác động giáo dục phụ thuộc thiết kế và điều kiện thử nghiệm.

**Lựa chọn cho đồ án:** chương trình cập nhật BKT và chọn hành động trong phiên bản triển khai đầu. LLM chấm tự luận theo rubric; biến thể chọn hành động có bộ kiểm tra chỉ dùng trong mô phỏng. Thiết kế hướng tới giảm việc làm bài hộ; khả năng giảm phụ thuộc của người học vẫn cần bằng chứng thực nghiệm.

### 2.10. Nhóm 9 — Sinh câu hỏi theo trạng thái người học

Kurdi et al. (2020), Scaria et al. (2024) là cơ sở cho sinh câu hỏi giáo dục và kiểm tra yêu cầu nhận thức. [KT4EQG của Gao et al. (2026)](https://arxiv.org/abs/2605.23933) [preprint] dùng knowledge tracing để hướng dẫn chọn khái niệm rồi sinh câu cá nhân hoá.

**Lựa chọn cho đồ án:** sinh câu nhắm chỗ hụt là phần mở rộng, đi qua kiểm tra chất lượng và duyệt của giảng viên. Một yêu cầu do đồ án đặt ra là kết quả sinh câu phải được đánh giá bằng tiêu chí độc lập với mô hình chọn khái niệm; đây là nguyên tắc thiết kế đánh giá, không phải kết luận rằng công trình liên quan đã bị chứng minh sai.

### 2.11. Nhóm 10 — Tách ngân hàng luyện tập khỏi câu thi

Georgiadou et al. (2007) tổng quan kiểm soát mức lộ câu trong kiểm tra thích ứng. Vấn đề này có liên quan khi đề luyện và đề kiểm tra dùng chung ngân hàng.

**Lựa chọn cho đồ án:** loại câu đang thuộc đề Kiểm tra khỏi kho Agent; cảnh báo lịch sử sử dụng khi giảng viên soạn đề. Quy tắc này hỗ trợ hạn chế lộ câu, chưa giải quyết hoàn toàn câu diễn đạt lại hoặc trùng ý nghĩa.

## 3. Công trình liên quan, câu hỏi nghiên cứu và đóng góp dự kiến

### 3.1. Đối chiếu các hướng gần với đề xuất

| Công trình hoặc hệ thống | Trọng tâm được mô tả trong công trình | Liên hệ với đề xuất DA Platform |
|---|---|---|
| ASSISTments; Heffernan & Heffernan (2014), Kelly et al. (2015) | Nền tảng luyện tập và nghiên cứu tiêu chí ba câu đúng liên tiếp | Cung cấp đối chứng thực dụng để kiểm tra giá trị tăng thêm của BKT |
| Pelánek & Řihák (2017, 2018) | Phân tích tiêu chí thành thạo, ngưỡng và EMA | Cung cấp đối chứng đơn giản và yêu cầu phân tích độ nhạy |
| [GenMentor; Wang et al. (2025)](https://arxiv.org/abs/2501.15749) | Hệ nhiều agent LLM, ánh xạ mục tiêu sang kỹ năng, lập lộ trình và sinh nội dung | Đề xuất hiện tại tập trung vòng chọn luyện theo LO đã có trong một môn học |
| [IntelliCode; David & Ghosh (2025)](https://arxiv.org/abs/2512.18669) [preprint] | Trạng thái người học tập trung, có phiên bản, điều phối các agent hỗ trợ | Tham khảo tổ chức trạng thái và truy vết; phiên bản đầu dùng một planner theo luật |
| [ALIGNAgent; Tokoli et al. (2026)](https://arxiv.org/abs/2601.15551) [preprint] | Ước lượng năng lực chủ đề, phát hiện chỗ hụt và gợi ý tài nguyên bằng các agent | Cùng bài toán chẩn đoán và gợi ý; đồ án giữ bộ cập nhật BKT ở chương trình và đo nhiễu chấm tự luận |
| KT4EQG; Gao et al. (2026) [preprint] | Kết hợp knowledge tracing và sinh câu theo khái niệm | Tham khảo cho phần sinh câu mở rộng; lõi hiện tại ưu tiên ngân hàng đã duyệt |

Bảng đối chiếu mô tả phạm vi liên quan; không khẳng định các công trình trên thiếu những chức năng không được liệt kê. Tổng quan hiện tại chưa đủ để tuyên bố một thuật toán mới hoặc tính mới tuyệt đối của việc dùng nhiều loại câu.

### 3.2. Câu hỏi nghiên cứu

| Mã | Câu hỏi | Cách trả lời dự kiến |
|---|---|---|
| RQ1 | Planner đề xuất thay đổi số câu luyện, tỉ lệ thạo giả và luyện thừa như thế nào so với đề cố định, N-CCR và EMA? | So sánh chính sách, báo cáo đồng thời hiệu quả và sai số quyết định |
| RQ2 | Kết luận có ổn định khi cách học của sinh viên ảo khác giả định của planner không? | Ma trận chính sách × bộ sinh dữ liệu và phân tích nhóm học nhanh/chậm |
| RQ3 | Dùng G theo loại câu thay cho G chung ảnh hưởng thế nào trong ngân hàng trộn năm loại câu? | So sánh loại bỏ thành phần, đồng thời thay đổi G thật và cơ cấu loại câu |
| RQ4 | LLM chọn trong tập hành động hợp lệ mang lại thay đổi nào so với luật, với chi phí và độ trễ bao nhiêu? | So sánh trên cùng tập con sinh viên ảo |
| RQ5 | Chấm tự luận theo rubric phù hợp với giảng viên ở mức nào, và sai số chấm ảnh hưởng thế nào đến kết luận thành thạo? | Đối chiếu chấm trên bài thật và mô phỏng có nhiễu quan sát |
| RQ6 | Sinh viên có sử dụng đề xuất và hiểu được lý do không? | Thử nghiệm sử dụng nhỏ, nếu điều kiện cho phép |

Các câu hỏi được đặt theo hướng kiểm chứng. Kết quả không vượt đối chứng hoặc chỉ tốt trong một số điều kiện vẫn là kết quả cần báo cáo.

### 3.3. Đóng góp dự kiến

1. **Về hệ thống:** bổ sung vòng luyện tập thích ứng theo LO, có lịch ôn, giải thích và đường chuyển cho giảng viên, trên nền LMS hiện có.
2. **Về thực nghiệm:** đánh giá chính sách trên ngân hàng trộn loại câu, có khác biệt xác suất trả lời đúng khi chưa nắm, sai lệch mô hình và nhiễu chấm tự luận.
3. **Về dữ liệu:** giữ lại kết quả từng ý rubric và nhật ký quyết định để phục vụ phản hồi, kiểm tra và hiệu chỉnh về sau.
4. **Về đối chiếu vai trò LLM:** đo giá trị và chi phí của biến thể chọn hành động có ràng buộc so với planner luật.

Canvas, LTI 1.3 và môn học tiếng Việt là bối cảnh tích hợp và triển khai thử nghiệm dự kiến. Chúng giúp xác định phạm vi ứng dụng; tính mới nghiên cứu cần được lập luận bằng câu hỏi và kết quả thực nghiệm.

## 4. Mục tiêu và phạm vi thực hiện

### 4.1. Mục tiêu

| Mã | Mục tiêu | Đầu ra kiểm chứng được |
|---|---|---|
| M1 | Lưu và chuẩn hoá bằng chứng làm bài theo LO | Kết quả từng ý rubric, nguồn lượt làm, quan sát đúng/sai có quy tắc rõ ràng |
| M2 | Ước lượng mức thành thạo và chọn hoạt động tiếp theo | Module BKT, planner, nhật ký và các ví dụ tính kiểm tra được |
| M3 | Hỗ trợ ôn và phát hiện trường hợp cần can thiệp | Lịch ôn, trạng thái cần hỗ trợ, trang giảng viên |
| M4 | Đánh giá lợi ích, chi phí và giới hạn của lựa chọn thiết kế | Kết quả RQ1–RQ5, có đối chứng và phân tích độ nhạy |

### 4.2. Phạm vi cốt lõi và mở rộng

| Thành phần | Phạm vi cốt lõi | Phần mở rộng |
|---|---|---|
| Đơn vị theo dõi | LO đã có trong ngân hàng | LO × Bloom; đơn vị kiến thức nhỏ hơn LO |
| Mô hình người học | BKT cố định; N-CCR/EMA làm đối chứng | Hiệu chỉnh tham số, Elo/PFA, quan hệ tiên quyết |
| Chọn hoạt động | Planner luật; LLM chọn có kiểm tra trong mô phỏng | Chính sách học từ dữ liệu khi đủ dữ liệu |
| Câu hỏi | Ngân hàng đã duyệt, có kiểm tra nguồn và lịch sử gặp | Sinh câu nhắm ý hụt, gắn đơn vị kiến thức, kiểm tra Bloom |
| Ôn tập | Lịch kiểu Leitner cấu hình được | Bộ lập lịch cá nhân hoá, có dữ liệu hiệu chỉnh |
| Đánh giá | Mô phỏng; đánh giá chấm tự luận trên tập bài mẫu | Thử nghiệm sử dụng nhỏ; thực nghiệm học tập có đối chứng khi đủ điều kiện |

Hoạt động do Agent giao được dùng để luyện tập và không gửi điểm về sổ điểm Canvas. Đề Kiểm tra vẫn theo cấu hình giảng viên. Thành phần video, trình xem tài liệu và trợ giảng chat được tích hợp qua liên kết hoặc RPC, theo ranh giới công việc của nhóm.

## 5. Kiến trúc và dữ liệu

### 5.1. Vòng hoạt động của Agent

1. Sinh viên làm một câu; hệ thống ghi lượt làm và nguồn hoạt động.
2. Khi đã có kết quả chấm hợp lệ, module người học chuẩn hoá và cập nhật các quan sát của LO liên quan.
3. Module lập lịch cập nhật việc đạt ngưỡng và hạn ôn; planner tính tập hành động hợp lệ rồi chọn đề xuất chính.
4. Giao diện hiển thị đề xuất, lý do và tối đa hai lựa chọn khác.
5. Hệ thống ghi quyết định và việc sinh viên thực hiện, bỏ qua hoặc chọn phương án khác.

```text
Sinh viên trong Canvas → web /learn → nộp câu trả lời
                                      ↓
                             core-api lưu lượt làm
                                      ↓
                 tự luận: worker chấm và lưu từng ý rubric
                                      ↓
Web yêu cầu GetNextActivity → kho câu hợp lệ + mô hình người học
                                      ↓
                             lịch ôn + planner luật
                                      ↓
                        đề xuất + lý do + lựa chọn khác
                                      ↓
                    nhật ký quyết định và hoạt động sinh viên
```

Mô hình người học, kho luyện, lịch ôn và planner dự kiến nằm trong module `learning-agent` của `core-api`. LLM tiếp tục chạy qua `worker`. Web gọi `GetNextActivity` khi sinh viên mở trang kết quả hoặc trang luyện tập; bài đến hạn ôn được phát hiện tại lần truy cập, chưa cần dịch vụ gửi nhắc nền.

### 5.2. Nguyên tắc tái tính và truy vết

Mức nắm BKT được tính bằng hàm thuần từ lịch sử quan sát đã chuẩn hoá và bộ tham số có phiên bản. Kết quả lưu theo sinh viên × khoá học × LO là bộ nhớ đệm. Độ trễ tính lại cần được đo trên quy mô dữ liệu thử nghiệm.

Lịch ôn, số lần xem lại nguồn và trạng thái cần hỗ trợ còn phụ thuộc **sự kiện hoạt động**, không chỉ đáp án. Vì vậy, trạng thái Agent được tái dựng từ cả lịch sử làm bài, lịch sử sự kiện và cấu hình tương ứng. Mỗi quyết định lưu phiên bản chính sách, mô hình, cấu hình và mốc dữ liệu đã dùng để giải thích lại được sau này.

Làm mới trang không được tạo lại một lần xem nguồn, một lần báo giảng viên hoặc một lần chuyển hộp ôn. Các cập nhật này cần mã sự kiện duy nhất và cơ chế chống ghi trùng. Việc giảng viên chấm lại làm thay đổi bằng chứng cho các quyết định tiếp theo; nhật ký quyết định cũ được giữ nguyên để phản ánh thông tin có tại thời điểm ra quyết định.

### 5.3. Quy tắc tạo quan sát

| Quy tắc | Cách xử lý trong phạm vi đầu |
|---|---|
| Nguồn lượt làm | Đề luyện, đề kiểm tra đã có kết quả và hoạt động Agent đều có thể cung cấp quan sát; lưu nguồn để phân tích riêng |
| Lần gặp câu | Chỉ lần trả lời đầu đã có kết quả hợp lệ của một câu hoặc nhóm câu trùng được dùng cho BKT |
| Câu trùng | Gộp theo văn bản chuẩn hoá ở phiên bản đầu; ghi rõ cách này chưa phát hiện hết câu diễn đạt lại |
| Câu đang chờ chấm hoặc cần duyệt | Không cập nhật BKT; hiển thị trạng thái đang chờ và không suy ra kết quả sai |
| Chấm lại | Dùng kết quả cuối của giảng viên; tính lại quan sát theo thứ tự thời điểm làm bài và mã lượt làm |
| Trắc nghiệm, đúng/sai, điền khuyết | Dùng quy tắc chấm của hệ thống để tạo kết quả đúng hoặc sai cho toàn câu |
| Tự luận ngắn | Cả câu là một quan sát: đúng khi đạt mọi ý bắt buộc của rubric; còn lại là chưa đạt |
| Kết quả từng ý rubric | Lưu để phản hồi và đối chiếu chất lượng chấm; chưa coi các ý cùng câu là nhiều quan sát độc lập |
| Câu có nhiều LO | Phiên bản đầu cần một LO chính được xác nhận; câu chưa xác định LO chính chưa dùng để cập nhật nhiều trạng thái đồng thời |

Quy tắc tự luận đạt mọi ý là một lựa chọn nhị phân tương đối chặt. Điểm phần trăm vẫn được lưu riêng, không đồng nhất với kết luận nắm LO. RQ5 kiểm tra ảnh hưởng của sai số chấm; khả năng dùng điểm một phần hoặc từng đơn vị kiến thức là hướng phát triển tiếp theo.

### 5.4. Kho câu luyện tập

Câu được giao trong hoạt động học mới phải đã duyệt, thuộc LO đang mở, không thuộc đề Kiểm tra và sinh viên chưa gặp theo nhóm câu trùng. Với hoạt động ôn, ưu tiên câu chưa gặp; nếu không còn thì có thể dùng lại câu gặp lâu nhất, theo quy tắc ở mục 6.5.

Trước khi bật Agent, cần thống kê số câu đủ điều kiện theo LO × loại câu. Cấu hình ban đầu cảnh báo LO dưới sáu câu; mốc sáu là ngưỡng vận hành đề xuất, không bảo đảm ngân hàng đã đủ cho mọi người học. Khi soạn đề Kiểm tra, giảng viên xem được câu nào đã dùng trong luyện và số sinh viên đã gặp.

### 5.5. Các nhóm dữ liệu dự kiến

| Nhóm dữ liệu | Nội dung cần lưu |
|---|---|
| Lượt làm và kết quả chấm | Câu, nhóm câu trùng, LO, loại, nguồn, thời điểm, trạng thái chấm, điểm, từng ý rubric, phiên bản rubric/model/prompt và kết quả giảng viên chỉnh |
| Trạng thái người học | P(L), số quan sát, chuỗi sai, lượt luyện trong đợt hiện tại, trạng thái đạt/cần ôn/tạm dừng, phiên bản tham số |
| Lịch ôn | Hộp, lần ôn gần nhất, hạn ôn, kết quả ôn và mã sự kiện đã áp dụng |
| Cấu hình khoá học | LO được mở, ngưỡng thành thạo, số câu tối đa/ngày, giới hạn ôn và các quyền do giảng viên đặt |
| Nhật ký hoạt động | Quyết định, tập hành động hợp lệ, lý do, phiên bản chính sách, lựa chọn sinh viên, mở nguồn, cờ hỗ trợ và việc xử lý |

Thiết kế ban đầu dự kiến mở rộng `quiz_attempts`, thêm `learner_unit_state`, `agent_course_settings` và tái sử dụng `learning_events` theo tài liệu dự án. Tên cột và mức tái sử dụng được xác nhận khi triển khai migration, để khớp schema thực tế.

## 6. Mô hình người học và lịch ôn

### 6.1. Đơn vị theo dõi và giả định

Phiên bản đầu theo dõi một trạng thái cho mỗi sinh viên × khoá học × LO. Cách này tận dụng nhãn có sẵn nhưng giả định các câu cùng LO cung cấp bằng chứng cho một năng lực tương đối thống nhất. Một LO rộng hoặc chứa nhiều kỹ năng có thể vi phạm giả định này; cần đối chiếu với giảng viên và nêu giới hạn khi diễn giải kết quả.

Mức Bloom được yêu cầu lúc sinh câu chưa được xem là nhãn đã kiểm chứng. Anderson và Krathwohl (2001), Krathwohl (2002), Lalwani và Agrawal (2018) cũng không cho phép mặc định các mức nhận thức tạo thành một chuỗi tiên quyết chặt cho mọi nội dung. Vì vậy, mô hình LO × Bloom và mọi luật lan truyền giữa mức chỉ được thử sau khi có kiểm tra nhãn, có so sánh bật/tắt giả định.

### 6.2. Công thức BKT

Gọi p = P(L) là xác suất ước lượng sinh viên đã nắm LO trước quan sát. Bốn tham số gồm P(L₀), xác suất học được T, trượt S = P(sai | đã nắm) và G = P(đúng | chưa nắm). Với câu có G tương ứng, cập nhật hậu nghiệm:

$$
P(L \mid \text{đúng}) = \frac{p(1-S)}{p(1-S)+(1-p)G}
$$

$$
P(L \mid \text{sai}) = \frac{pS}{pS+(1-p)(1-G)}
$$

Sau đó thêm chuyển trạng thái học được:

$$
P(L_{\text{mới}}) = P(L \mid \text{quan sát}) + \bigl(1-P(L \mid \text{quan sát})\bigr)T
$$

Mô hình này kế thừa BKT, với G thay đổi theo loại câu. Dùng thuộc tính câu để thay đổi tham số được gợi ý từ các mở rộng theo ngữ cảnh và độ khó; cách gán G cố định theo năm loại của đồ án là một đơn giản hoá cần đánh giá.

### 6.3. Tham số khởi đầu

| Tham số | Giá trị đề xuất | Cách diễn giải |
|---|---|---|
| P(L₀) | 0.20 | Mức biết trước giả định cho LO mới |
| T | 0.15 | Xác suất chuyển sang đã nắm sau một cơ hội luyện |
| S | 0.10 | Xác suất sai dù đã nắm |
| G | Theo bảng dưới | Xác suất đúng khi chưa nắm, chưa được hiệu chỉnh từ dữ liệu |

| Loại câu | G khởi đầu | Giả định và giới hạn |
|---|---|---|
| Đúng/sai | 0.50 | Tương ứng đoán ngẫu nhiên giữa hai lựa chọn; chưa mô tả mọi trường hợp hiểu một phần |
| Trắc nghiệm một đáp án | 0.25 nếu có bốn phương án | Nếu số phương án khác, mốc đoán đều là 1/k; vẫn cần kiểm tra với dữ liệu thật |
| Trắc nghiệm nhiều đáp án | 0.10 | Giả định vận hành; còn phụ thuộc số phương án, luật chọn và cách tính đúng toàn bộ |
| Điền khuyết | 0.05 | Giả định vận hành; phụ thuộc dạng chỗ trống và đáp án được chấp nhận |
| Tự luận ngắn | 0.05 | Giả định vận hành; kết quả quan sát còn chịu ảnh hưởng của rubric và bộ chấm |

Trong BKT, G là xác suất **đúng khi chưa nắm**, không chỉ xác suất chọn ngẫu nhiên. Các giá trị 0.10 và 0.05 không được coi là hằng số đã xác lập trong nghiên cứu. Ngay cả 0.50 hoặc 1/k cũng chỉ là điểm khởi đầu theo giả định đoán đều. RQ3 phải có kịch bản G thật khác G planner; RQ5 tách thêm sai số do chấm.

### 6.4. Tiêu chí công nhận thành thạo

Một LO đạt tiêu chí của hệ thống khi đồng thời P(L) ≥ θ và số quan sát hợp lệ ≥ n_min. Cấu hình đầu là θ = 0.95, n_min = 3; phân tích thêm θ = 0.98 và n_min = 1. Ngưỡng ba quan sát là biện pháp vận hành thận trọng, chưa thay thế một phép đo độ bất định thống kê đầy đủ.

Với bộ tham số ở mục 6.3, số câu đúng liên tiếp để P(L) vượt ngưỡng được tính như sau:

| Loại câu | Vượt 0.95 | Vượt 0.98 | Được công nhận với θ = 0.95, n_min = 3 |
|---|---|---|---|
| Đúng/sai | 6 | 7 | 6 |
| Trắc nghiệm một đáp án, bốn phương án | 3 | 4 | 3 |
| Trắc nghiệm nhiều đáp án | 2 | 3 | 3 |
| Điền khuyết | 2 | 2 | 3 |
| Tự luận ngắn | 2 | 2 | 3 |

Đây là kết quả tính từ tham số giả định, không phải số câu đã đo trên sinh viên. Ví dụ, người đoán độc lập và đều có xác suất đúng ba câu đúng/sai liên tiếp là 12.5%, trong khi ba câu trắc nghiệm bốn phương án là khoảng 1.6%. Chênh lệch này giải thích câu hỏi nghiên cứu về loại câu; nó chưa chứng minh chính sách BKT đề xuất sẽ giảm thạo giả trong thực tế.

### 6.5. Lịch ôn và trạng thái cần ôn

BKT đang chọn chưa có chuyển trạng thái quên theo thời gian. Do đó, hệ thống duy trì thêm trạng thái đến hạn ôn; P(L) cao không đồng nghĩa kiến thức đã được xác nhận ở thời điểm hiện tại.

- Khi LO vừa đạt tiêu chí, ghi một sự kiện đạt và đưa vào hộp ôn đầu tiên.
- Khoảng cách đề xuất của năm hộp là 1, 3, 7, 14, 30 ngày; đây là cấu hình có thể đổi.
- Ôn đúng thì tăng tối đa một hộp; ôn sai thì về hộp đầu và chuyển sang trạng thái cần ôn hoặc xác nhận lại.
- Câu ôn chưa từng gặp tạo thêm quan sát BKT. Câu gặp lại cập nhật lịch ôn và nhật ký nhưng không tạo thêm bằng chứng độc lập cho BKT.
- Nếu câu gặp lại bị sai trong khi P(L) vẫn cao, giao diện vẫn hiện cần ôn; cần câu chưa gặp hoặc xem xét của giảng viên để xác nhận lại mức nắm.
- Tính ngày theo múi giờ `Asia/Ho_Chi_Minh`; áp dụng mỗi kết quả ôn một lần, có ghi thời điểm thực hiện.

Lịch ôn được tách khỏi module BKT để sau này thay bằng một mô hình trí nhớ phù hợp hơn. Kết quả ôn câu đã gặp và kết quả câu mới được báo cáo riêng nhằm hạn chế nhầm nhớ đáp án với nhớ kiến thức.

## 7. Chính sách chọn hoạt động

### 7.1. Trạng thái dùng để ra quyết định

Planner dùng LO đang xử lý, P(L), số quan sát hợp lệ, số câu sai liên tiếp, số lần xem lại nguồn đã được ghi nhận, các LO đến hạn và giới hạn ngày. LO đang xử lý là LO của hoạt động vừa có kết quả; khi chưa có hoạt động thì chọn LO chưa đạt, đang mở và không bị tạm dừng, theo thứ tự giảng viên cấu hình.

Cần phân biệt số quan sát tích luỹ với số lượt trong **đợt luyện hiện tại**. Số lượt của đợt được dùng phát hiện bị kẹt; đợt mới bắt đầu khi LO được mở lại để luyện hoặc giảng viên cho tiếp tục sau can thiệp. Một sinh viên từng đạt LO rồi quay lại ôn không bị gắn cờ chỉ vì trước đó đã làm nhiều câu.

Việc đề xuất mở nguồn chưa được xem là sinh viên đã đọc nguồn. Hệ thống ghi riêng đề xuất, mở nguồn và xác nhận tiếp tục; chỉ cập nhật bộ đếm can thiệp một lần khi có sự kiện thực hiện tương ứng. Hành vi mở nguồn cũng chưa chứng minh sinh viên đã hiểu nội dung.

### 7.2. Tập hành động

| Mã | Hành động | Điều kiện chính | Phạm vi |
|---|---|---|---|
| A0 | Kết thúc phiên hoặc nghỉ | Đạt giới hạn ngày, không còn việc hợp lệ hoặc sinh viên chọn nghỉ | Cốt lõi |
| A1 | Làm câu mới cùng LO | Còn câu hợp lệ chưa gặp | Cốt lõi |
| A2 | Chuyển mức Bloom | Có mô hình theo mức và đạt điều kiện chuyển | Mở rộng |
| A3 | Xem lại thẻ bài học hoặc tài liệu nguồn | Có nguồn phù hợp với LO hoặc câu vừa làm | Cốt lõi |
| A4 | Ôn LO đến hạn | Có LO cần ôn và có câu phù hợp | Cốt lõi |
| A5 | Chuyển LO | LO vừa đạt; có LO kế tiếp được mở và đủ điều kiện | Cốt lõi |
| A6 | Đánh dấu cần giảng viên hỗ trợ | Có dấu hiệu bị kẹt hoặc thiếu tài nguyên luyện | Cốt lõi |
| A7 | Yêu cầu sinh câu nhắm chỗ hụt | Được giảng viên bật, có hạn mức và đi qua duyệt | Mở rộng |

A6 tạo cờ trên trang giảng viên, gồm lý do và bằng chứng; không đồng nghĩa gửi tin nhắn hoặc tự quyết định sinh viên không đạt môn. Tách lý do **khó khăn học tập** và **thiếu câu phù hợp** để tránh gán thiếu tài nguyên thành yếu năng lực.

### 7.3. Thứ tự luật dự kiến

Trước khi chọn hành động, hệ thống cập nhật chuyển trạng thái đạt và lịch ôn đúng một lần. Planner sau đó xét các luật theo thứ tự; mọi ngưỡng dưới đây là cấu hình khởi đầu.

| Luật | Điều kiện | Đề xuất | Căn cứ và phần cần kiểm chứng |
|---|---|---|---|
| R0 | Đạt số câu tối đa trong ngày | A0 | Giới hạn tải do giảng viên đặt |
| R1 | Có LO đến hạn, chưa đạt hạn mức ôn ngày | A4; ưu tiên LO quá hạn lâu nhất | Nghiên cứu ôn ngắt quãng; hạn mức đầu là năm câu ôn/ngày |
| R2 | LO chưa đạt; ít nhất 10 quan sát trong đợt, hoặc đã xem lại nguồn hai lần và vẫn sai hai câu liên tiếp | A6; tạm dừng đợt và cho phép chọn LO khác đủ điều kiện | Lấy cảm hứng từ wheel-spinning; các mốc 10, 2 là giả định vận hành |
| R3 | LO chưa đạt và sai hai câu liên tiếp | A3; ghi sự kiện khi sinh viên thực hiện | Phản hồi gắn với nội dung và nguồn; cần đo tác dụng can thiệp |
| R4 | LO chưa đạt tiêu chí hoặc cần xác nhận lại | A1; thiếu câu thì A6 với lý do thiếu tài nguyên | Luyện truy hồi; A7 là nhánh mở rộng nếu được bật |
| R5 | Đạt điều kiện chuyển mức Bloom | A2 | Chỉ xét ở phần mở rộng |
| R6 | LO đang xử lý đã đạt; cần chọn nội dung tiếp theo | A5; hết LO thì A0 | Mastery learning; lịch ôn đã được ghi ở bước cập nhật trạng thái |

Nếu không có nguồn phù hợp cho A3, hệ thống bỏ qua nhánh xem nguồn và chọn hành động hợp lệ khác, đồng thời ghi tình trạng thiếu nguồn. Nếu LO đến hạn không có cả câu mới lẫn câu ôn dùng lại được, ghi cờ thiếu tài nguyên rồi xét LO khác; tránh lặp một đề xuất không thể thực hiện.

Sau một lần xem nguồn đã được ghi nhận, chuỗi sai cho đợt can thiệp được đặt lại để đánh giá các câu tiếp theo. Giới hạn ngày và quyền mở LO là ràng buộc chung cho mọi hành động. Tạm dừng một LO chỉ cho phép chuyển tới LO đáp ứng điều kiện của giảng viên, không tự suy ra rằng có thể bỏ qua quan hệ tiên quyết.

### 7.4. Chọn câu và chia quyền lựa chọn

Trong A1/A4, lọc điều kiện kho câu trước, rồi chọn ngẫu nhiên có seed khi mô phỏng. Ưu tiên đổi loại so với câu vừa làm nếu ngân hàng cho phép; không mở thêm câu tự luận cùng LO khi câu trước chưa có kết quả chấm. Với ôn, chỉ dùng lại câu cũ khi đã hết câu chưa gặp.

Chọn câu theo độ khó thực nghiệm cần dữ liệu hiệu chỉnh và được để ở giai đoạn sau. Các thay đổi cơ cấu loại câu do planner tạo ra phải được ghi lại, vì chúng có thể tác động tới số câu và độ khó của so sánh.

Sinh viên thấy một đề xuất chính, tối đa hai lựa chọn hợp lệ khác và khả năng nghỉ. Hệ thống ghi cả đề xuất lẫn hành động thực hiện. Mô phỏng chính giả định làm theo planner; một kịch bản bổ sung thay đổi xác suất làm theo. Thử nghiệm nhỏ đo hành vi thực tế để đối chiếu giả định này.

### 7.5. Ví dụ tính và quyết định

Bắt đầu từ P(L₀) = 0.20, dùng tham số mục 6.3, xét chuỗi sau của L.O.1.1:

| Lượt | Loại câu | Kết quả | P(L) sau cập nhật | Hành động minh hoạ |
|---|---|---|---|---|
| 1 | Trắc nghiệm một đáp án | Đúng | 0.553 | A1: cần thêm bằng chứng cho LO |
| 2 | Tự luận ngắn | Thiếu một ý rubric, cả câu chưa đạt | 0.248 | A1, kèm phản hồi đúng ý còn thiếu |
| 3 | Đúng/sai | Sai | 0.203 | A3 vì có hai câu chưa đạt liên tiếp |
| Sau lượt 3 | Xem nguồn | Sinh viên mở nguồn và tiếp tục | Không tự tăng P(L) | Ghi can thiệp; tiếp tục lấy bằng chứng từ câu trả lời |
| 4 | Trắc nghiệm một đáp án | Đúng | 0.556 | A1 |
| 5 | Điền khuyết | Đúng | 0.964 | Đạt θ = 0.95 và năm quan sát; lên lịch ôn, A5 |

Ví dụ chỉ minh hoạ cách chạy công thức và luật, không dùng để kết luận BKT tốt hơn ba câu đúng liên tiếp. Ở chuỗi này, N-CCR còn tiếp tục vì mới có hai câu đúng liên tiếp; việc BKT dừng sớm hơn có đúng hay không phải được đối chiếu với trạng thái thật trong mô phỏng hoặc bằng chứng độc lập.

## 8. Vai trò của LLM và kiểm soát chất lượng

### 8.1. Phân công giữa chương trình và LLM

| Công việc | Cơ chế đề xuất | Cách kiểm soát |
|---|---|---|
| Cập nhật mức nắm | Công thức BKT trong chương trình | Quan sát có quy tắc, tham số có phiên bản, ví dụ tính đối chiếu |
| Chọn hoạt động triển khai đầu | Planner luật | Ràng buộc hợp lệ, thứ tự ưu tiên, nhật ký |
| Chấm tự luận ngắn | Luồng LLM theo rubric của hệ thống | Lưu từng ý, kiểm tra cấu trúc, chuyển duyệt khi lỗi, đối chiếu giảng viên |
| Viết lý do đề xuất | Mẫu theo luật; trích phản hồi từng ý đã có | Lý do gắn đúng bằng chứng và LO, không tự suy ra thêm lỗi của sinh viên |
| Sinh câu nhắm ý hụt | LLM trong phần mở rộng | Kiểm tra chất lượng và giảng viên duyệt trước khi dùng |
| LLM chọn hoạt động | Chỉ trong thực nghiệm | Bộ lọc và kiểm tra bên ngoài; lỗi thì dùng luật |

Mục tiêu là giữ vòng quyết định kiểm tra và tái lập được. Tuy nhiên, khi quan sát tự luận do LLM chấm, mô hình người học vẫn gián tiếp phụ thuộc chất lượng LLM. Vì vậy, đánh giá bộ chấm và độ nhạy với nhiễu quan sát là một phần của phạm vi cốt lõi.

### 8.2. Chấm tự luận và xử lý kết quả không chắc chắn

Đầu ra chấm cần gắn từng kết luận với mã ý rubric và lưu model, prompt, phiên bản rubric. Chương trình kiểm tra đủ ý bắt buộc, giá trị đúng định dạng và tính nhất quán của điểm tổng. Bài làm được coi là dữ liệu đầu vào, tách khỏi chỉ dẫn của bộ chấm; việc đặt mốc phân cách là một lớp tổ chức đầu vào, chưa đủ để bảo đảm chấm đúng.

Kết quả lỗi, thiếu ý hoặc bị giảng viên đánh dấu cần xem xét đi vào trạng thái chờ duyệt, chưa cập nhật BKT. Kết luận tự báo của model về độ tự tin chưa được dùng làm bảo đảm chất lượng nếu chưa có hiệu chỉnh. Giảng viên có thể sửa kết quả; hệ thống tính lại trạng thái từ bằng chứng mới và giữ lịch sử phiên bản.

Thiết kế chỉ giao hoạt động để sinh viên tự làm và giới hạn lời giải lộ trong phản hồi luyện tập. [Bastani et al. (2025)](https://www.pnas.org/doi/10.1073/pnas.2422633122) cho thấy tác động của AI phụ thuộc các rào chắn sư phạm trong cấu hình tutor được thử nghiệm. Báo cáo coi giảm phụ thuộc là mục tiêu thiết kế, chưa khẳng định Agent này đã tránh được rủi ro đó.

### 8.3. Biến thể LLM chọn trong tập hợp lệ

1. Chương trình áp dụng ràng buộc bắt buộc, tính các cặp hành động × LO × tài nguyên hợp lệ. Khi đã đạt giới hạn ngày, tập chỉ còn hành động nghỉ.
2. LLM nhận tóm tắt trạng thái, vài lượt gần nhất, các hạn ôn và tập hợp lệ; không cần thông tin định danh sinh viên.
3. LLM trả cấu trúc gồm `action`, `lo_id`, mã tài nguyên nếu có và `reason`.
4. Chương trình kiểm tra cấu trúc và toàn bộ tham chiếu; lỗi, quá thời gian hoặc ngoài tập hợp lệ thì dùng planner luật.
5. Nhật ký ghi đề xuất ban đầu của LLM, kết quả kiểm tra, hành động thực thi, lựa chọn của luật, token, chi phí và độ trễ.

Đây là biến thể chọn hành động lấy cảm hứng từ LLM-Modulo, không được xem là triển khai đầy đủ mọi thành phần của khung này. Tính hợp lệ không chứng minh hiệu quả sư phạm; RQ4 cần đo kết quả học mô phỏng ngoài tỉ lệ chọn hợp lệ hoặc trùng luật. Sinh viên thật trong thử nghiệm đầu dùng planner luật.

## 9. Giao diện và tích hợp hệ thống

### 9.1. Giao diện sinh viên

- **Bước tiếp theo:** đặt tại trang kết quả và trang luyện tập; hiển thị LO, hoạt động, lý do, nút thực hiện và lựa chọn khác.
- **Trang luyện tập:** mỗi lần một câu, dùng lại bộ hiển thị và nhập đáp án hiện có cho năm loại câu; phân biệt đang chờ chấm với chưa đạt.
- **Mức nắm theo LO:** hiển thị mức ước lượng, số quan sát, trạng thái cần ôn và ngày ôn; tránh trình bày xác suất nắm như điểm môn học.

Ví dụ lý do: “Câu vừa rồi của bạn chưa nêu giới hạn của công nghệ cơ sở dữ liệu thông thường. Xem lại phần định nghĩa ở trang nguồn, rồi làm tiếp một câu về L.O.1.1.” Lý do phải được tạo từ kết quả thực có; không dùng câu “đang tiến bộ” nếu bằng chứng chỉ cho thấy cần luyện thêm.

### 9.2. Giao diện giảng viên

Giảng viên xem bảng sinh viên × LO, số quan sát và các trường hợp cần hỗ trợ; phân biệt cờ khó khăn học tập, thiếu câu và chờ duyệt kết quả. Trang cấu hình cho phép mở LO, đặt giới hạn câu/ngày, ngưỡng thành thạo, hạn mức ôn và quyền sinh câu mở rộng. Khi soạn đề Kiểm tra, hệ thống hiện lịch sử dùng câu trong luyện tập.

### 9.3. Các thay đổi dự kiến

| Thành phần | Thay đổi chính | Giai đoạn |
|---|---|---|
| `worker` và lưu kết quả chấm | Giữ từng ý rubric, trạng thái duyệt và phiên bản kết quả | 0 |
| Cơ sở dữ liệu | Mở rộng lượt làm; lưu trạng thái, cấu hình, lịch ôn và sự kiện | 0–2 |
| `core-api` | Module `learning-agent`; RPC dự kiến `GetNextActivity`, `GetLearnerSummary`, `GetCourseMastery`, `RecordAgentEvent`, `GetAgentSettings`, `UpdateAgentSettings` | 1–2 |
| Luồng nộp bài | Ghi nguồn hoạt động; không gửi điểm hoạt động Agent về Canvas | 1–2 |
| `contracts` | Hợp đồng RPC và kiểu dữ liệu quan sát, kết quả từng ý, quyết định; trường nhắm ý hụt chỉ ở mở rộng | 0–2; mở rộng |
| `web` | Các trang sinh viên, giảng viên và đường liên kết về nguồn | 1–2 |
| Bộ đánh giá | Gọi cùng module mô hình/planner dùng trong ứng dụng, lưu cấu hình và seed | 3 |

Nếu trình xem tài liệu hỗ trợ mở đúng trang, Agent dùng liên kết đó; nếu chưa hỗ trợ thì hiện tên tài liệu và số trang. Các tích hợp với chat hoặc video cần hợp đồng dữ liệu riêng, không là điều kiện để hoàn thành vòng luyện cốt lõi.

## 10. Kế hoạch đánh giá

### 10.1. Nguyên tắc

Đánh giá tách ba lớp: tính đúng của chương trình, chất lượng quan sát từ bộ chấm và hiệu quả của chính sách. Một chương trình cập nhật đúng công thức vẫn có thể cho chính sách không phù hợp nếu tham số, nhãn LO hoặc kết quả chấm không phản ánh người học.

Mỗi chính sách được đánh giá trên nhiều bộ sinh dữ liệu. Một cấu hình phù hợp với BKT chưa đủ để kết luận vững khi mô hình thực khác BKT. Báo cáo trình bày kết quả theo từng kịch bản và đánh đổi giữa luyện ít, thạo giả, luyện thừa; không mặc định tồn tại một chính sách tốt nhất trên mọi chỉ số.

### 10.2. Sáu chính sách so sánh

| Mã | Chính sách | Vai trò |
|---|---|---|
| P0 | Đề cố định: N câu mỗi LO theo thứ tự đã xác định | Mốc hiện trạng; chọn N trước khi đo trên tập đánh giá |
| P1 | N-CCR: dừng khi đúng ba câu liên tiếp | Đối chứng tiêu chí đơn giản |
| P2 | EMA: dừng khi trung bình trượt mũ vượt ngưỡng | Đối chứng có ghi nhớ lịch sử gần; hệ số/ngưỡng chọn trên tập hiệu chỉnh riêng |
| P3a | Chỉ BKT: luyện đến khi đạt ngưỡng và số quan sát tối thiểu | Tách ảnh hưởng của mô hình khỏi các luật hỗ trợ |
| P3 | Planner đầy đủ: BKT, xem nguồn, ôn và cờ hỗ trợ | Chính sách đề xuất |
| P4 | LLM chọn trong tập hợp lệ, cùng cơ chế BKT và lịch ôn | Đánh giá giá trị tăng thêm của cách chọn hành động |

Để tách tác động của tiêu chí dừng, P1, P2, P3a dùng cùng điều kiện kho và cơ chế chọn câu trong các so sánh chính. P3 so với P3a đo tác động của các luật bổ sung. So sánh P3/P4 dùng cùng các công cụ, chi phí hành động và ràng buộc bắt buộc.

Các chính sách cùng chịu một ngân sách câu, thời gian mô phỏng và điều kiện khả dụng của ngân hàng được công bố trước khi chạy. Quy tắc chuyển hỗ trợ sau 10 lượt là thành phần của chính sách có luật đó, không được coi là đã đạt. Không hiệu chỉnh tham số bằng kết quả của chính tập đánh giá cuối.

### 10.3. Ba mô hình sinh dữ liệu

| Mã | Bộ sinh dữ liệu | Định nghĩa đạt mục tiêu dùng để đối chiếu |
|---|---|---|
| S1 | BKT cá nhân hoá: tham số mỗi sinh viên ảo khác tham số planner; có nhóm học nhanh và chậm | Trạng thái ẩn đã nắm của bộ sinh dữ liệu |
| S2 | AFM: năng lực tăng theo cơ hội luyện, kết hợp xác suất đoán/trượt theo loại câu | Xác suất đúng chuẩn hoá sau khi tách đoán/trượt đạt ít nhất 0.90; đây là định nghĩa đánh giá được đặt trước |
| S3 | S1 có chuyển trạng thái quên theo thời gian và lịch truy cập | Trạng thái ẩn tại từng thời điểm; thêm bài kiểm tra trễ bằng câu mới |

S1 là kiểm tra sai lệch tham số trong cùng họ mô hình, S2 là kiểm tra khác họ, S3 kiểm tra vai trò lịch ôn khi có quên. Định nghĩa mục tiêu của S2 là quy ước của mô phỏng, không phải chân lý về thành thạo. Kết quả được so sánh trong từng hàng; không gộp các định nghĩa khác nhau thành một con số hiệu quả chung.

Các bộ sinh có thể biểu diễn xác suất trả lời đúng theo dạng G_thật + (1 − G_thật − S_thật) × q, trong đó q là trạng thái nắm hoặc mức năng lực chuẩn hoá của bộ sinh. Cần ràng buộc tham số để xác suất hợp lệ. Planner chỉ thấy kết quả quan sát, không được biết q hoặc tham số thật.

Ngân hàng ảo lấy số LO và cơ cấu loại câu từ một chương hoặc môn thử nghiệm đã thống kê. Bổ sung kịch bản ngân hàng mỏng, khoảng năm câu mỗi LO, và ngân hàng dày, ít nhất 15 câu mỗi LO; đây là các mức thử nghiệm dự kiến. Câu đã gặp, câu thiếu nguồn và tự luận đang chờ chấm được mô hình hoá theo cùng quy tắc của ứng dụng.

### 10.4. Chỉ số và cách xử lý trường hợp chưa đạt

| Chỉ số | Định nghĩa vận hành | RQ liên quan |
|---|---|---|
| Tỉ lệ hoàn thành | Tỉ lệ sinh viên ảo đạt mục tiêu trước khi hết ngân sách | RQ1, RQ2 |
| Số câu đến khi nắm | Số câu tới lần đạt mục tiêu ẩn; báo cáo kèm tỉ lệ chưa đạt | RQ1, RQ2 |
| Thạo giả | Số lần hệ thống công nhận đạt khi bộ sinh chưa đạt, chia tổng số lần công nhận | RQ1–RQ3, RQ5 |
| Luyện thừa | Số câu tiếp tục giao khi bộ sinh đã đạt tại thời điểm giao | RQ1, RQ2 |
| Gánh nặng hỗ trợ | Số lần xem nguồn, chuyển giảng viên, tạm dừng và thiếu câu; tách lý do | RQ1, RQ2 |
| Chất lượng cờ cần hỗ trợ | Precision/recall theo định nghĩa đối chiếu đã đặt cho từng bộ sinh | RQ2 |
| Ghi nhớ trễ | Kết quả bộ câu mới tại mốc định trước, dự kiến ngày 30 trong S3 | RQ1, RQ2 |
| Chênh lệch giữa nhóm | Chênh lệch hoàn thành, thạo giả, số câu và cờ hỗ trợ giữa nhóm nhanh/chậm | RQ2 |
| Hiệu quả biến thể LLM | Các chỉ số học ở trên, cộng lỗi hợp lệ trước fallback, mức trùng luật, chi phí và độ trễ | RQ4 |
| Chất lượng bộ chấm | Đồng thuận, precision/recall từng ý, sai lệch điểm và tác động lên công nhận đạt | RQ5 |

Không chỉ lấy trung bình trên sinh viên đã đạt rồi bỏ người chưa đạt. Trường hợp hết câu, hết ngân sách hoặc chuyển hỗ trợ phải được báo cáo riêng; nếu không có lần công nhận nào thì thạo giả được ghi là không xác định, không gán bằng 0. Với S3 có quên, đo trạng thái tại thời điểm quyết định thay vì coi một lần đạt là đã đạt mãi mãi.

Số câu ít hơn chưa chắc giảm tổng thời gian nếu planner thêm nhiều lần đọc nguồn. Vì chưa có số đo thời gian thật, mô phỏng báo cáo số lần từng hành động và phân tích thêm các giả định chi phí; thử nghiệm sử dụng nhỏ thu thời gian quan sát được. Cờ sau 10 lần là tín hiệu cần hỗ trợ, không là nhãn chắc chắn về năng lực của sinh viên thật.

### 10.5. Phân tích độ nhạy và cách chạy

Các trục phân tích gồm:

- θ = 0.95/0.98; số quan sát tối thiểu 1/3; thay đổi P(L₀), T và S theo các khoảng được công bố trong cấu hình chạy.
- G chung so với G theo loại; thay đổi cơ cấu năm loại câu, G thật và mức biết một phần để tránh mô phỏng chỉ thuận lợi cho giả định planner.
- Ngân hàng mỏng/dày, câu trùng, giới hạn lượt trong đợt và xác suất sinh viên làm theo đề xuất.
- Tác dụng của xem nguồn: với bộ sinh BKT thử hệ số T × 1.0, × 1.5, × 2.0 và chặn trong miền xác suất hợp lệ; với AFM công bố cách quy đổi can thiệp sang cơ hội học. Mức ×1.0 kiểm tra trường hợp can thiệp không có lợi ích giả định.
- Nhiễu chấm: thêm đúng giả và sai giả ở các mức 0%, 5%, 10%, 20%; bổ sung mức ước lượng từ đối chiếu giảng viên nếu có. Tách hai loại lỗi và ưu tiên áp dụng cho câu tự luận.
- Lan truyền giữa mức Bloom bật/tắt chỉ ở giai đoạn mở rộng, chưa là điều kiện hoàn thành đánh giá cốt lõi.

Đề xuất chạy 1.000 sinh viên ảo mỗi ô và năm seed; các chính sách dùng chung hồ sơ và bộ tham số sinh viên cho so sánh theo cặp, nhưng lịch sử câu trả lời phát sinh theo hành động thực của từng chính sách. Lưu cấu hình, seed, phiên bản mã và kết quả từng lượt. Báo cáo khoảng tin cậy 95% cho chênh lệch, lấy mẫu lại theo sinh viên để giữ phụ thuộc giữa các lượt của cùng người.

P4 chạy trên tập con 100 sinh viên mỗi mô hình để giới hạn chi phí; P3 được chạy trên **đúng tập con đó** cho đối chiếu chính. Lưu model, phiên bản, prompt và thiết lập lấy mẫu của LLM; không coi kết quả một lần gọi là tất định.

### 10.6. Đối chiếu chấm tự luận với giảng viên

Đề xuất chuẩn bị 50–100 câu trả lời cho một tập câu tự luận có rubric được giảng viên xác nhận, bao gồm bài đúng, thiếu ý và cách diễn đạt khác nhau. Quy mô này là dự kiến để xin ý kiến thầy, chưa phải dữ liệu đã thu thập.

Quy trình dự kiến:

1. Tách mẫu dùng chỉnh rubric/prompt khỏi mẫu đánh giá cuối; giữ nguyên cấu hình trên mẫu cuối.
2. Giảng viên chấm từng ý độc lập với đầu ra LLM. Nếu có điều kiện, một phần bài được hai người chấm, sau đó trao đổi các trường hợp bất đồng để hình thành kết quả tham chiếu.
3. Đối chiếu từng ý và kết luận đạt cả câu: báo cáo đồng thuận, precision/recall của ý đạt, đúng giả/sai giả, sai lệch điểm và khoảng tin cậy. Không chỉ báo cáo tương quan điểm tổng.
4. Phân tích loại lỗi và kiểm tra lại các chuỗi quyết định thành thạo khi thay kết quả LLM bằng kết quả tham chiếu.
5. Đưa các mức nhiễu đo được vào RQ5; chốt tiêu chí chấp nhận cùng giảng viên trước khi mở rộng sử dụng.

Kết quả tham chiếu của giảng viên cũng có thể có bất đồng; báo cáo giữ lại mức bất đồng này. Nếu chưa có bài làm thật, có thể dùng bài viết thử để kiểm tra quy trình kỹ thuật, nhưng phải ghi rõ nguồn bài và chưa xem đó là xác nhận chất lượng trên sinh viên thật.

### 10.7. Kiểm chứng chương trình

| Thành phần | Tình huống cần xác nhận |
|---|---|
| BKT | Khớp công thức và các giá trị mục 6.4, 7.5; cùng lịch sử và phiên bản cho cùng trạng thái |
| Chuẩn hoá quan sát | Chờ chấm không thay mức nắm; câu lặp không thêm bằng chứng; chấm lại dùng đúng phiên bản |
| Tiêu chí đạt | Đủ xác suất nhưng thiếu số quan sát thì chưa công nhận |
| Planner | Mỗi luật có trường hợp kiểm tra, gồm khi nhiều luật cùng thoả và tài nguyên không còn |
| Sự kiện | Làm mới trang không đếm lại xem nguồn, cảnh báo hoặc chuyển hộp; mở lại đợt không dùng sai bộ đếm cũ |
| Kho luyện | Loại câu thi; gộp câu trùng; phân biệt câu mới với câu ôn dùng lại |
| LLM chọn hành động | Từ chối hành động hoặc tài nguyên ngoài tập hợp lệ; fallback và nhật ký đầy đủ |
| Tích hợp Canvas | Lượt Agent có nguồn riêng và không phát sinh cập nhật điểm về sổ điểm |

Đây là danh sách kiểm chứng khi triển khai, chưa phải các kiểm thử đã chạy hoặc đã đạt trong báo cáo thiết kế này.

### 10.8. Thử nghiệm sử dụng nhỏ và giới hạn kết luận

Nếu có điều kiện, mời 5–10 sinh viên dùng trong một chương, 1–2 tuần, theo hình thức tham gia được thống nhất với giảng viên. Thu tỉ lệ làm theo đề xuất, thời gian, tình huống bị kẹt, ý kiến về mức hữu ích và khả năng hiểu lý do; dùng dữ liệu ẩn danh khi phân tích.

Thử nghiệm này hỗ trợ kiểm tra hệ thống và giả định sử dụng. Quy mô, thời gian và cách chọn mẫu chưa đủ để kết luận nhân quả về hiệu quả học tập, công bằng giáo dục hoặc ghi nhớ 30 ngày. Mô phỏng nhiều kịch bản cũng không thay thế thực nghiệm có đối chứng với lớp thật. Nếu thầy yêu cầu kết luận về cải thiện kết quả học tập thực tế, cần thiết kế một nghiên cứu riêng, có phép đo độc lập và cỡ mẫu phù hợp.

## 11. Lộ trình và rủi ro

### 11.1. Lộ trình theo đầu ra

| Giai đoạn | Nội dung | Điều kiện hoàn thành |
|---|---|---|
| 0. Dữ liệu nền | Lưu từng ý rubric, nguồn lượt làm, phiên bản chấm; lọc câu thi và câu trùng; thống kê kho theo LO × loại; chuẩn bị tập đối chiếu chấm | Migration và luồng lưu được kiểm tra; có bảng ngân hàng và kế hoạch chấm tham chiếu |
| 1. Mô hình người học | Chuẩn hoá quan sát; BKT, N-CCR, EMA qua giao diện chung; trạng thái theo LO | Khớp ví dụ tính; xử lý chờ chấm/chấm lại/câu lặp; xem được mức nắm |
| 2. Planner và tích hợp | Luật, lịch ôn, nhật ký chống ghi trùng, các trang sinh viên/giảng viên và RPC | Chạy được một vòng từ làm bài đến đề xuất và ghi nhận lựa chọn; kiểm tra ranh giới điểm Canvas |
| 3. Đánh giá | Ma trận 6 × 3, đối chiếu bộ chấm, phân tích độ nhạy, biến thể LLM; thử nghiệm sử dụng nếu có điều kiện | Báo cáo RQ1–RQ5 và giới hạn; cấu hình, seed và kết quả có thể kiểm tra lại |
| 4. Mở rộng | Bloom, đơn vị kiến thức, sinh câu nhắm ý hụt, độ khó thực nghiệm hoặc bộ lập lịch mới | Chỉ triển khai phần có đủ điều kiện đầu vào và thời gian đánh giá |

Đề nghị chốt giai đoạn 0–3 là phạm vi đồ án. Giai đoạn 4 không là điều kiện để hoàn thành mục tiêu cốt lõi. Mốc lịch cụ thể cần ghép với lịch bảo vệ và phần việc của các thành viên; báo cáo này chưa cam kết ngày hoàn thành chưa được thống nhất.

### 11.2. Rủi ro chính

| Rủi ro | Ảnh hưởng | Hướng xử lý dự kiến |
|---|---|---|
| LO quá rộng hoặc gán sai | Một xác suất nắm không phản ánh đúng các kỹ năng | Rà nhãn với giảng viên; giới hạn diễn giải; tách đơn vị nhỏ khi đủ điều kiện |
| Bộ chấm tự luận sai | Bằng chứng đầu vào sai, dễ thành thạo giả hoặc luyện thừa | Chấm tham chiếu, lưu phiên bản, cho sửa và phân tích nhiễu |
| Tham số BKT chưa hiệu chỉnh | Kết luận phụ thuộc giả định | Phân tích độ nhạy và dùng bộ sinh khác; hiệu chỉnh khi đủ dữ liệu |
| Ngân hàng mỏng hoặc trùng ý | Hết câu, hoặc nhớ đáp án được xem là học được | Thống kê trước, sinh bù theo lô đã duyệt, báo thiếu câu; phân biệt ôn lại với quan sát mới |
| Mô phỏng không phản ánh người thật | Kết quả khó chuyển sang sử dụng thực tế | Công bố giả định, nhiều bộ sinh, đối chiếu bài thật và thử nghiệm sử dụng |
| Luật hỗ trợ gắn cờ quá sớm | Người học chậm bị dừng hoặc chuyển không phù hợp | Tách nhóm khi đánh giá, cấu hình mốc và cho giảng viên mở lại |
| Lịch ôn và điểm nắm không nhất quán | Hiện đã đạt dù bằng chứng cũ hoặc ôn sai | Trạng thái cần ôn riêng; xác nhận bằng câu mới; nhật ký sự kiện tái dựng được |
| Sinh viên không làm theo | Hiệu quả giả định của planner không xảy ra | Chia quyền lựa chọn, ghi hành vi thực hiện và phân tích độ nhạy |
| Câu thi đã xuất hiện trong luyện | Ảnh hưởng tính độc lập của kiểm tra | Lọc kho, chỉ báo khi soạn đề; ghi giới hạn của chống trùng văn bản |
| Chi phí hoặc độ trễ LLM | Vượt ngân sách thực nghiệm | P4 chạy tập con; lưu chi phí; fallback về luật |
| Mở rộng vượt thời gian | Thiếu đánh giá cho phần cốt lõi | Chốt theo giai đoạn và ưu tiên đầu ra giai đoạn 0–3 |

## 12. Nội dung xin ý kiến giảng viên hướng dẫn

| Vấn đề cần chốt | Đề xuất để thầy góp ý |
|---|---|
| Phạm vi đồ án | Hoàn thành giai đoạn 0–3; phần Bloom và sinh câu cá nhân hoá là mở rộng |
| Đơn vị theo dõi | Bắt đầu theo LO; chọn một chương có LO và ngân hàng đủ rõ để thử nghiệm |
| Định hướng đóng góp | Tập trung vòng luyện có giải thích và đánh giá quyết định trong ngân hàng nhiều loại câu, có nhiễu chấm |
| Mức đánh giá cần thiết | Mô phỏng và đối chiếu chấm là kết quả chính; thử nghiệm sử dụng nhỏ là bổ sung. Cần thầy xác nhận có yêu cầu thực nghiệm học tập với lớp thật hay không |
| Tập bài chấm tham chiếu | Thống nhất số bài, người chấm, rubric và tiêu chí chất lượng trước khi dùng kết quả LLM cho Agent |
| Cơ chế tính điểm | Hoạt động Agent chỉ để luyện, không gửi điểm về Canvas |
| Quyền duyệt câu mới | Câu sinh thêm phải qua giảng viên trước khi sinh viên dùng |
| Thử nghiệm với sinh viên | Thống nhất cách mời, đồng ý tham gia, phạm vi dữ liệu và thời gian phù hợp |
| Lịch thực hiện | Gắn các đầu ra từng giai đoạn với lịch bảo vệ thực tế |

Đề xuất cần được xem như một thiết kế có thể kiểm chứng: lý thuyết và nghiên cứu liên quan giải thích vì sao lựa chọn đáng thử; dữ liệu triển khai và thực nghiệm sẽ quyết định lựa chọn đó có phù hợp trong DA Platform hay không. Ở thời điểm báo cáo, chưa có căn cứ để khẳng định Agent giúp sinh viên học tốt hơn hoặc BKT/LLM vượt các đối chứng.

## Phụ lục A. Truy vết quyết định thiết kế

| Quyết định | Căn cứ liên quan | Phần do đồ án đề xuất và cần kiểm tra |
|---|---|---|
| Agent làm vòng ngoài của ITS | Wooldridge & Jennings (1995); VanLehn (2006) | Vòng sau mỗi kết quả và tập hành động trong DA Platform |
| BKT theo LO | Corbett & Anderson (1995); Pelánek (2017); Gervet et al. (2020) | Mức phù hợp của LO và khả năng sử dụng tham số cố định |
| G phụ thuộc loại câu | Baker et al. (2008); Pardos & Heffernan (2011) | Các giá trị ban đầu và ảnh hưởng của hiểu một phần |
| Tách mô hình khỏi tiêu chí dừng | Rollinson & Brunskill (2015); Käser et al. (2016) | Giao diện chung để thay BKT/N-CCR/EMA |
| Đối chứng N-CCR và EMA | Kelly et al. (2015); Pelánek & Řihák (2017, 2018) | Cấu hình đối chứng được hiệu chỉnh trên tập riêng |
| Ngưỡng và số quan sát tối thiểu | Fancsali et al. (2013); Pelánek (2018); Zhang et al. (2025) | θ = 0.95/0.98, n_min = 1/3; chưa là thước đo bất định đầy đủ |
| Can thiệp khi có dấu hiệu bị kẹt | Beck & Gong (2013); Doroudi & Brunskill (2019) | Mốc 10 lượt và hai lần xem nguồn; đánh giá riêng nhóm học chậm |
| Làm câu hỏi, ôn phân bố | Roediger & Karpicke (2006); Adesope et al. (2017); Cepeda et al. (2006) | Tần suất, hạn mức và khoảng cách ôn cụ thể |
| Lịch kiểu Leitner | Leitner (1972); Lindsey et al. (2014); Settles & Meeder (2016) | Lịch 1–3–7–14–30 ngày, chưa chứng minh tối ưu |
| Phản hồi theo ý và nguồn | Hattie & Timperley (2007); Shute (2008); Van der Kleij et al. (2015) | Cách ánh xạ rubric–nguồn và độ đúng của bộ chấm |
| Hiện mô hình, lý do và cho lựa chọn | Bull & Kay (2016); Conati et al. (2021); Corbalan et al. (2008) | Cách hiển thị, mức hiểu và hành vi dùng đề xuất |
| Đánh giá nhiều bộ sinh | Doroudi et al. (2017); Käser & Alexandron (2024) | S1/S2/S3, định nghĩa mục tiêu và các giả định chi phí |
| LLM chọn có kiểm tra | Kambhampati et al. (2024) | Giá trị tăng thêm so với luật trong cùng tập hành động |
| Thiết kế giảm làm bài hộ | Bastani et al. (2025) | Tác động trong hệ thống này chưa được xác nhận |
| Sinh câu cá nhân hoá ở mở rộng | Kurdi et al. (2020); Scaria et al. (2024); Gao et al. (2026) | Kiểm tra chất lượng độc lập và luồng duyệt |
| Lọc câu thi và theo dõi mức lộ | Georgiadou et al. (2007) | Quy tắc lọc cụ thể và giới hạn phát hiện câu trùng ý |

## Phụ lục B. Danh mục tài liệu khảo sát

Danh mục dưới đây giữ 91 nguồn của quá trình khảo sát, gồm tài liệu nền, công trình được phân tích trực tiếp và các hướng mở rộng. Việc có tên trong danh mục không đồng nghĩa mọi kết quả đã được tái kiểm chứng trên toàn văn. Phần thân báo cáo chỉ sử dụng các kết luận phù hợp với mức bằng chứng và nêu riêng các giả định của đồ án.

1. Abdelrahman, G., Wang, Q., & Nunes, B. P. (2023). Knowledge tracing: A survey. *ACM Computing Surveys*, 55(11), 1–37. [DOI](https://doi.org/10.1145/3569576)

2. Adesope, O. O., Trevisan, D. A., & Sundararajan, N. (2017). Rethinking the use of tests: A meta-analysis of practice testing. *Review of Educational Research*, 87(3), 659–701. [DOI](https://doi.org/10.3102/0034654316689306)

3. Anderson, L. W., & Krathwohl, D. R. (Eds.). (2001). *A taxonomy for learning, teaching, and assessing: A revision of Bloom's taxonomy of educational objectives*. Longman.

4. Badrinath, A., Wang, F., & Pardos, Z. (2021). pyBKT: An accessible Python library of Bayesian knowledge tracing models. In *Proceedings of EDM 2021* (pp. 468–474). [arXiv](https://arxiv.org/abs/2105.00385)

5. Baker, R. S. J. d., Corbett, A. T., & Aleven, V. (2008). More accurate student modeling through contextual estimation of slip and guess probabilities in Bayesian knowledge tracing. In *ITS 2008*, LNCS 5091 (pp. 406–415). [DOI](https://doi.org/10.1007/978-3-540-69132-7_44)

6. Bastani, H., et al. (2025). Generative AI without guardrails can harm learning: Evidence from high school mathematics. *PNAS*, 122(26), e2422633122. [DOI](https://doi.org/10.1073/pnas.2422633122)

7. Beck, J. E., & Chang, K.-m. (2007). Identifiability: A fundamental problem of student modeling. In *User Modeling 2007*, LNCS 4511 (pp. 137–146). Springer.

8. Beck, J. E., & Gong, Y. (2013). Wheel-spinning: Students who fail to master a skill. In *AIED 2013*, LNCS 7926 (pp. 431–440). Springer.

9. Bloom, B. S. (1968). Learning for mastery. *Evaluation Comment*, 1(2).

10. Bloom, B. S. (1984). The 2 sigma problem: The search for methods of group instruction as effective as one-to-one tutoring. *Educational Researcher*, 13(6), 4–16. [DOI](https://doi.org/10.3102/0013189X013006004)

11. Brunmair, M., & Richter, T. (2019). Similarity matters: A meta-analysis of interleaved learning and its moderators. *Psychological Bulletin*, 145(11), 1029–1052. [DOI](https://doi.org/10.1037/bul0000209)

12. Bull, S., & Kay, J. (2016). SMILI☺: A framework for interfaces to learning data in open learner models, learning analytics and related fields. *International Journal of Artificial Intelligence in Education*, 26(1), 293–331.

13. Cen, H., Koedinger, K., & Junker, B. (2006). Learning factors analysis – A general method for cognitive model evaluation and improvement. In *ITS 2006* (pp. 164–175). Springer.

14. Cepeda, N. J., Pashler, H., Vul, E., Wixted, J. T., & Rohrer, D. (2006). Distributed practice in verbal recall tasks: A review and quantitative synthesis. *Psychological Bulletin*, 132(3), 354–380. [DOI](https://doi.org/10.1037/0033-2909.132.3.354)

15. Chu, Z., Wang, S., Xie, J., Zhu, T., Yan, Y., Ye, J., Zhong, A., Hu, X., Liang, J., Yu, P. S., & Wen, Q. (2025). LLM agents for education: Advances and applications. In *Findings of EMNLP 2025* (pp. 13782–13810). [Trang công bố](https://aclanthology.org/2025.findings-emnlp.743/)

16. Clement, B., Roy, D., Oudeyer, P.-Y., & Lopes, M. (2015). Multi-armed bandits for intelligent tutoring systems. *Journal of Educational Data Mining*, 7(2), 20–48. [Trang công bố](https://jedm.educationaldatamining.org/index.php/JEDM/article/view/111)

17. Conati, C., Barral, O., Putnam, V., & Rieger, L. (2021). Toward personalized XAI: A case study in intelligent tutoring systems. *Artificial Intelligence*, 298, 103503. [DOI](https://doi.org/10.1016/j.artint.2021.103503)

18. Corbalan, G., Kester, L., & van Merriënboer, J. J. G. (2008). Selecting learning tasks: Effects of adaptation and shared control on learning efficiency and task involvement. *Contemporary Educational Psychology*, 33(4), 733–756.

19. Corbett, A. T., & Anderson, J. R. (1995). Knowledge tracing: Modeling the acquisition of procedural knowledge. *User Modeling and User-Adapted Interaction*, 4(4), 253–278. [DOI](https://doi.org/10.1007/BF01099821) (số tạp chí ghi tháng 12/1994; thường được trích là 1995)

20. David, J., & Ghosh, S. (2025). IntelliCode: A multi-agent LLM tutoring system with centralized learner modeling [Preprint]. [arXiv:2512.18669](https://arxiv.org/abs/2512.18669).

21. Doroudi, S., Aleven, V., & Brunskill, E. (2017). Robust evaluation matrix: Towards a more principled offline exploration of instructional policies. In *L@S '17* (pp. 3–12). [DOI](https://doi.org/10.1145/3051457.3051463)

22. Doroudi, S., Aleven, V., & Brunskill, E. (2019). Where's the reward? A review of reinforcement learning for instructional sequencing. *International Journal of Artificial Intelligence in Education*, 29(4), 568–620. [DOI](https://doi.org/10.1007/s40593-019-00187-x)

23. Doroudi, S., & Brunskill, E. (2017). The misidentified identifiability problem of Bayesian knowledge tracing. In *Proceedings of EDM 2017*.

24. Doroudi, S., & Brunskill, E. (2019). Fairer but not fair enough: On the equitability of knowledge tracing. In *LAK '19* (pp. 335–339). [DOI](https://doi.org/10.1145/3303772.3303838)

25. Dunlosky, J., Rawson, K. A., Marsh, E. J., Nathan, M. J., & Willingham, D. T. (2013). Improving students' learning with effective learning techniques: Promising directions from cognitive and educational psychology. *Psychological Science in the Public Interest*, 14(1), 4–58. [DOI](https://doi.org/10.1177/1529100612453266)

26. Fancsali, S. E., Nixon, T., & Ritter, S. (2013). Optimal and worst-case performance of mastery learning assessment with Bayesian knowledge tracing. In *Proceedings of EDM 2013* (pp. 35–42).

27. Gao, W., et al. (2025). Agent4Edu: Generating learner response data by generative agents for intelligent education systems. In *AAAI 2025*, 39(22). [DOI](https://doi.org/10.1609/aaai.v39i22.34565)

28. Gao, X., Wu, Q., Ding, L., Liao, Q. V., Qian, K., Xu, Y., Chang, S., & Zhang, Y. (2026). KT4EQG: Personalized exercise question generation via knowledge tracing [Preprint]. [arXiv:2605.23933](https://arxiv.org/abs/2605.23933).

29. Georgiadou, E., Triantafillou, E., & Economides, A. A. (2007). A review of item exposure control strategies for computerized adaptive testing developed from 1983 to 2005. *Journal of Technology, Learning, and Assessment*, 5(8). [Trang công bố](https://www.ejournals.bc.edu/index.php/jtla/article/view/1647)

30. Gervet, T., Koedinger, K., Schneider, J., & Mitchell, T. (2020). When is deep learning the best approach to knowledge tracing? *Journal of Educational Data Mining*, 12(3), 31–54. [DOI](https://doi.org/10.5281/zenodo.4143614)

31. Gierl, M. J., Bulut, O., Guo, Q., & Zhang, X. (2017). Developing, analyzing, and using distractors for multiple-choice tests in education: A comprehensive review. *Review of Educational Research*, 87(6), 1082–1116. [DOI](https://doi.org/10.3102/0034654317726529)

32. Girard, S., Minn, S., Bouzeghoub, A., & Vie, J.-J. (2026). Counterfactual learning of new adaptive instructional policies using logged data. In *ECML-PKDD 2026*. [arXiv:2606.23015](https://arxiv.org/abs/2606.23015).

33. Hattie, J., & Timperley, H. (2007). The power of feedback. *Review of Educational Research*, 77(1), 81–112. [DOI](https://doi.org/10.3102/003465430298487)

34. Heffernan, N. T., & Heffernan, C. L. (2014). The ASSISTments ecosystem: Building a platform that brings scientists and teachers together for minimally invasive research on human learning and teaching. *International Journal of Artificial Intelligence in Education*, 24(4), 470–497. [DOI](https://doi.org/10.1007/s40593-014-0024-x)

35. Hooshyar, D., Yang, Y., Šíř, G., Kärkkäinen, T., Hämäläinen, R., Cukurova, M., & Azevedo, R. (2025). Problems with large language models for learner modelling: Why LLMs alone fall short for responsible tutoring in K–12 education [Preprint]. [arXiv:2512.23036](https://arxiv.org/abs/2512.23036).

36. Kambhampati, S., et al. (2024). Position: LLMs can't plan, but can help planning in LLM-Modulo frameworks. In *ICML 2024*, PMLR 235, 22895–22907. [Trang công bố](https://proceedings.mlr.press/v235/kambhampati24a.html)

37. Karpicke, J. D., & Roediger, H. L. (2008). The critical importance of retrieval for learning. *Science*, 319(5865), 966–968. [DOI](https://doi.org/10.1126/science.1152408)

38. Käser, T., & Alexandron, G. (2024). Simulated learners in educational technology: A systematic literature review and a Turing-like test. *International Journal of Artificial Intelligence in Education*, 34(2), 545–585. [DOI](https://doi.org/10.1007/s40593-023-00337-2)

39. Käser, T., Klingler, S., & Gross, M. (2016). When to stop? Towards universal instructional policies. In *LAK '16* (pp. 289–298). ACM.

40. Käser, T., Klingler, S., Schwing, A. G., & Gross, M. (2014). Beyond knowledge tracing: Modeling skill topologies with Bayesian networks. In *ITS 2014* (pp. 188–198). Springer.

41. Käser, T., Klingler, S., Schwing, A. G., & Gross, M. (2017). Dynamic Bayesian networks for student modeling. *IEEE Transactions on Learning Technologies*, 10(4), 450–462.

42. Kelly, K., Wang, Y., Thompson, T., & Heffernan, N. (2015). Defining mastery: Knowledge tracing versus N-consecutive correct responses. In *Proceedings of EDM 2015* (pp. 630–631). [Trang công bố](https://www.educationaldatamining.org/EDM2015/proceedings/poster630-631.pdf)

43. Kestin, G., Miller, K., Klales, A., Milbourne, T., & Ponti, G. (2025). AI tutoring outperforms in-class active learning. *Scientific Reports*, 15, 17458. [DOI](https://doi.org/10.1038/s41598-025-97652-6)

44. Khajah, M., Lindsey, R. V., & Mozer, M. C. (2016). How deep is knowledge tracing? In *Proceedings of EDM 2016*. [arXiv](https://arxiv.org/abs/1604.02416)

45. Khalid, A., Deriyeva, A., & Paassen, B. (2025). Does interpretability of knowledge tracing models support teacher decision making? AIED 2025 Workshop on Epistemics and Decision-Making in AI-Supported Education. [arXiv:2511.02718](https://arxiv.org/abs/2511.02718).

46. Koedinger, K. R., Corbett, A. T., & Perfetti, C. (2012). The Knowledge-Learning-Instruction framework: Bridging the science-practice chasm to enhance robust student learning. *Cognitive Science*, 36(5), 757–798.

47. Krathwohl, D. R. (2002). A revision of Bloom's taxonomy: An overview. *Theory Into Practice*, 41(4), 212–218. [DOI](https://doi.org/10.1207/s15430421tip4104_2)

48. Kulik, C.-L. C., Kulik, J. A., & Bangert-Drowns, R. L. (1990). Effectiveness of mastery learning programs: A meta-analysis. *Review of Educational Research*, 60(2), 265–299. [DOI](https://doi.org/10.3102/00346543060002265)

49. Kulik, J. A., & Fletcher, J. D. (2016). Effectiveness of intelligent tutoring systems: A meta-analytic review. *Review of Educational Research*, 86(1), 42–78. [DOI](https://doi.org/10.3102/0034654315581420)

50. Kurdi, G., Leo, J., Parsia, B., Sattler, U., & Al-Emari, S. (2020). A systematic review of automatic question generation for educational purposes. *International Journal of Artificial Intelligence in Education*, 30, 121–204. [DOI](https://doi.org/10.1007/s40593-019-00186-y)

51. Lalwani, A., & Agrawal, S. (2018). Validating revised Bloom's taxonomy using deep knowledge tracing. In *AIED 2018*. [DOI](https://doi.org/10.1007/978-3-319-93843-1_17)

52. Leitner, S. (1972). *So lernt man lernen*. Herder.

53. Lindsey, R. V., Shroyer, J. D., Pashler, H., & Mozer, M. C. (2014). Improving students' long-term knowledge retention through personalized review. *Psychological Science*, 25(3), 639–647. [DOI](https://doi.org/10.1177/0956797613504302)

54. Liu, Q., Shen, S., Huang, Z., Chen, E., & Zheng, Y. (2021). A survey of knowledge tracing: Models, variants, and applications [Preprint; bản tạp chí đăng ở IEEE Transactions on Learning Technologies, 2024]. [arXiv:2105.15106](https://arxiv.org/abs/2105.15106).

55. Lu, X., & Wang, X. (2024). Generative students: Using LLM-simulated student profiles to support question item evaluation. In *L@S '24*. [DOI](https://doi.org/10.1145/3657604.3662031)

56. Mettler, E., Massey, C. M., & Kellman, P. J. (2016). A comparison of adaptive and fixed schedules of practice. *Journal of Experimental Psychology: General*, 145(7), 897–917. [DOI](https://doi.org/10.1037/xge0000170)

57. Moore, S., Schmucker, R., Mitchell, T., & Stamper, J. (2024). Automated generation and tagging of knowledge components from multiple-choice questions. In *L@S '24* (pp. 122–133). [DOI](https://doi.org/10.1145/3657604.3662030)

58. Neshaei, S. P., Davis, R. L., Hazimeh, A., Lazarevski, B., Dillenbourg, P., & Käser, T. (2024). Towards modeling learner performance with large language models. In *Proceedings of EDM 2024* (poster). [arXiv](https://arxiv.org/abs/2403.14661)

59. Niu, C., Bradley, K. D., Waltman, B. F., & Ma, B. (2026). Beyond "three-in-a-row": Toward fairer adaptive mastery decisions in AI-supported formative assessment. In *Proceedings of AIME-Con 2026: Full Papers* (pp. 673–680). NCME. [Trang công bố](https://aclanthology.org/2026.aimecon-main.76/)

60. Noh, H., Chowdhary, A., Ooge, J., Aleven, V., & Borchers, C. (2026). Simulating learners' task-selection strategies and system constraints in mastery learning. In *Proceedings of EDM 2026* (short paper). [Trang công bố](https://educationaldatamining.org/edm2026/proceedings/2026.EDM.short-papers.242/index.html)

61. Papoušek, J., Pelánek, R., & Stanislav, V. (2014). Adaptive practice of facts in domains with varied prior knowledge. In *Proceedings of EDM 2014* (pp. 6–13).

62. Pardos, Z. A., & Heffernan, N. T. (2011). KT-IDEM: Introducing item difficulty to the knowledge tracing model. In *UMAP 2011* (pp. 243–254). Springer.

63. Pavlik, P. I., Cen, H., & Koedinger, K. R. (2009). Performance factors analysis – A new alternative to knowledge tracing. In *AIED 2009* (pp. 531–538). IOS Press.

64. Pelánek, R. (2016). Applications of the Elo rating system in adaptive educational systems. *Computers & Education*. [DOI](https://doi.org/10.1016/j.compedu.2016.03.017)

65. Pelánek, R. (2017). Bayesian knowledge tracing, logistic models, and beyond: An overview of learner modeling techniques. *User Modeling and User-Adapted Interaction*, 27(3–5), 313–350. [DOI](https://doi.org/10.1007/s11257-017-9193-2)

66. Pelánek, R. (2018). Conceptual issues in mastery criteria: Differentiating uncertainty and degrees of knowledge. In *AIED 2018* (pp. 450–461). [DOI](https://doi.org/10.1007/978-3-319-93843-1_33)

67. Pelánek, R., Papoušek, J., Řihák, J., Stanislav, V., & Nižnan, J. (2017). Elo-based learner modeling for the adaptive practice of facts. *User Modeling and User-Adapted Interaction*. [DOI](https://doi.org/10.1007/s11257-016-9185-7)

68. Pelánek, R., & Řihák, J. (2017). Experimental analysis of mastery learning criteria. In *UMAP '17* (pp. 156–163). [DOI](https://doi.org/10.1145/3079628.3079667)

69. Pelánek, R., & Řihák, J. (2018). Analysis and design of mastery learning criteria. *New Review of Hypermedia and Multimedia*, 24(3).

70. Piech, C., Bassen, J., Huang, J., Ganguli, S., Sahami, M., Guibas, L. J., & Sohl-Dickstein, J. (2015). Deep knowledge tracing. In *Advances in Neural Information Processing Systems 28* (pp. 505–513).

71. Rafferty, A. N., Brunskill, E., Griffiths, T. L., & Shafto, P. (2016). Faster teaching via POMDP planning. *Cognitive Science*, 40(6), 1290–1332.

72. Roediger, H. L., & Karpicke, J. D. (2006). Test-enhanced learning: Taking memory tests improves long-term retention. *Psychological Science*, 17(3), 249–255. [DOI](https://doi.org/10.1111/j.1467-9280.2006.01693.x)

73. Rollinson, J., & Brunskill, E. (2015). From predictive models to instructional policies. In *Proceedings of EDM 2015* (pp. 179–186).

74. Rowland, C. A. (2014). The effect of testing versus restudy on retention: A meta-analytic review of the testing effect. *Psychological Bulletin*, 140(6), 1432–1463. [DOI](https://doi.org/10.1037/a0037559)

75. Russell, S., & Norvig, P. (2021). *Artificial intelligence: A modern approach* (4th ed.). Pearson.

76. Scaria, N., Chenna, S. D., & Subramani, D. (2024). Automated educational question generation at different Bloom's skill levels using large language models: Strategies and evaluation. In *AIED 2024* (pp. 165–179). [DOI](https://doi.org/10.1007/978-3-031-64299-9_12)

77. Settles, B., & Meeder, B. (2016). A trainable spaced repetition model for language learning. In *ACL 2016* (pp. 1848–1858). [DOI](https://doi.org/10.18653/v1/P16-1174)

78. Shute, V. J. (2008). Focus on formative feedback. *Review of Educational Research*, 78(1), 153–189. [DOI](https://doi.org/10.3102/0034654307313795)

79. Tabibian, B., Upadhyay, U., De, A., Zarezade, A., Schölkopf, B., & Gomez-Rodriguez, M. (2019). Enhancing human learning via spaced repetition optimization. *PNAS*, 116(10), 3988–3993. [DOI](https://doi.org/10.1073/pnas.1815156116)

80. Tokoli, B., Jaimes, L., & Dina, A. S. (2026). ALIGNAgent: Adaptive learner intelligence for gap identification and next-step guidance [Preprint]. [arXiv:2601.15551](https://arxiv.org/abs/2601.15551).

81. Van der Kleij, F. M., Feskens, R. C. W., & Eggen, T. J. H. M. (2015). Effects of feedback in a computer-based learning environment on students' learning outcomes: A meta-analysis. *Review of Educational Research*, 85(4), 475–511. [DOI](https://doi.org/10.3102/0034654314564881)

82. VanLehn, K. (2006). The behavior of tutoring systems. *International Journal of Artificial Intelligence in Education*, 16(3), 227–265.

83. VanLehn, K. (2011). The relative effectiveness of human tutoring, intelligent tutoring systems, and other tutoring systems. *Educational Psychologist*, 46(4), 197–221. [DOI](https://doi.org/10.1080/00461520.2011.611369)

84. Wang, S., Xu, T., Li, H., Zhang, C., Liang, J., Tang, J., Yu, P. S., & Wen, Q. (2024). Large language models for education: A survey and outlook [Preprint]. [arXiv:2403.18105](https://arxiv.org/abs/2403.18105).

85. Wang, T., Zhan, Y., Lian, J., Hu, Z., Yuan, N. J., Zhang, Q., Xie, X., & Xiong, H. (2025). LLM-powered multi-agent framework for goal-oriented learning in intelligent tutoring system. In *WWW 2025 (Industry Track)*. [arXiv:2501.15749](https://arxiv.org/abs/2501.15749).

86. Wooldridge, M., & Jennings, N. R. (1995). Intelligent agents: Theory and practice. *The Knowledge Engineering Review*, 10(2), 115–152. [DOI](https://doi.org/10.1017/S0269888900008122)

87. Xia, M., Schmucker, R., Borchers, C., & Aleven, V. (2025). Optimizing mastery learning by fast-forwarding over-practice steps. In *EC-TEL 2025*. [arXiv:2506.17577](https://arxiv.org/abs/2506.17577).

88. Ye, J., Su, J., & Cao, Y. (2022). A stochastic shortest path algorithm for optimizing spaced repetition scheduling. In *KDD '22* (pp. 4381–4390).

89. Yuan, Z., Xiao, Y., Li, M., Xuan, W., Tong, R., Diab, M., & Mitchell, T. (2026). Towards valid student simulation with large language models [Preprint]. [arXiv:2601.05473](https://arxiv.org/abs/2601.05473).

90. Yudelson, M. V., Koedinger, K. R., & Gordon, G. J. (2013). Individualized Bayesian knowledge tracing models. In *AIED 2013* (pp. 171–180). [DOI](https://doi.org/10.1007/978-3-642-39112-5_18)

91. Zhang, J., Vanacore, K., Baker, R. S., Ch, N., Mills, C., & Henkel, O. (2025). How much mastery is enough mastery? The relationship between mastery in a lesson and the performance on the subsequent lesson. In *Proceedings of EDM 2025* (short paper). [Trang công bố](https://educationaldatamining.org/EDM2025/proceedings/2025.EDM.short-papers.4/index.html)
