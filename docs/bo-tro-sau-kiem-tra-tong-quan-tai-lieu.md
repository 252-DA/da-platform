# Tổng quan tài liệu: chẩn đoán và bổ trợ sau bài kiểm tra

**Ngày:** 16/10/2026
**Đi kèm:** [bao-cao-thiet-ke-bo-tro-sau-kiem-tra.md](bao-cao-thiet-ke-bo-tro-sau-kiem-tra.md)
**Tài liệu nền:** [learning-agent-tong-quan-tai-lieu.md](learning-agent-tong-quan-tai-lieu.md) (91 tài liệu, cho phương án Learning Agent trước đó). Tài liệu này giữ lại phần còn dùng được và bổ sung các nhóm mới: chấm theo rubric bằng LLM, chất lượng câu do LLM sinh, cách đưa bổ trợ vào LMS, báo cáo cho giảng viên.

---

## Cách tìm và kiểm tra

- **Câu hỏi tìm:** bổ trợ sau bài kiểm tra có căn cứ không; nên làm theo khuôn nào; LLM chấm từng ý có đủ tin để chẩn đoán không; câu do LLM sinh có dùng được không; làm sao để sinh viên trong LMS thật sự làm bổ trợ; nên đánh giá thế nào.
- **Kiểm tra:** mỗi bài được tra lại tác giả, năm, nơi đăng và DOI hoặc đường dẫn. Phần lớn nội dung lấy từ tóm tắt và trang công bố. Trước khi đưa một con số vào báo cáo chính thức, cần đối chiếu với toàn văn.
- **[preprint]** đánh dấu bản chưa qua bình duyệt. Các bài này chỉ dùng để chỉ hướng, không làm căn cứ chính.
- Tổng cộng 42 tài liệu, chia 7 nhóm, cộng 4 trang hướng dẫn của Canvas.

---

## 1. Mastery learning trong lớp học và đánh giá hình thành

**Câu hỏi thiết kế:** bổ trợ sau kiểm tra có căn cứ không, và nên theo khuôn nào?

**Bằng chứng chính**
- Bloom (1968) đề xuất *Learning for Mastery*: dạy theo đơn vị, kiểm tra hình thành sau mỗi đơn vị, bổ trợ cho người chưa đạt, rồi kiểm tra lần hai.
- Guskey (2007) nhắc lại lập luận của Bloom: dạy mọi người cùng một cách, cùng một thời lượng thì kết quả phân tán rộng; mastery learning thu hẹp khoảng cách bằng cách giảm độ phân tán đó.
- Guskey (2010) mô tả vòng lặp trong lớp học thường:
    - bài kiểm tra hình thành thứ nhất cho biết mỗi người đã nắm gì, còn hụt gì, kèm hoạt động bổ trợ cụ thể;
    - bổ trợ khác với dạy lại: giảng lại y như cũ, chậm hơn, không được tính là bổ trợ;
    - bài kiểm tra thứ hai dùng câu khác nhưng cùng mục tiêu, cho biết bổ trợ có hiệu quả không;
    - cơ hội thứ hai tạo động lực cho người học;
    - mỗi đơn vị dài thêm khoảng 10–20% thời gian.
- Kulik et al. (1990), tổng hợp 108 đánh giá có đối chứng: mastery learning có hiệu quả ở đại học, trung học và cuối tiểu học; người học yếu được lợi nhiều nhất; đổi lại tốn thêm thời gian.
- Black & Wiliam (1998), tổng quan về đánh giá hình thành trong lớp: các cải tiến làm phản hồi thường xuyên tốt hơn cho kết quả học tập tăng đáng kể.

**Hệ quả cho thiết kế:** dùng đúng vòng bốn bước của Bloom, bám vào bài giảng viên đã giao: kiểm tra → chẩn đoán → bổ trợ → kiểm tra lại bằng câu khác. Bổ trợ không phải chiếu lại bài giảng.

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Bloom (1968) | Learning for Mastery | Khuôn vòng lặp |
| Guskey (2007) | Mastery learning giảm phân tán kết quả | Lý do bổ trợ theo từng người |
| Guskey (2010) | Bổ trợ ≠ dạy lại; kiểm tra lần hai bằng câu khác | Bộ bổ trợ, kiểm tra lại |
| Kulik et al. (1990) | Meta-analysis 108 đánh giá | Hiệu quả và chi phí thời gian |
| Black & Wiliam (1998) | Tổng quan đánh giá hình thành | Căn cứ chung |

---

## 2. Phản hồi và học từ lỗi

**Câu hỏi thiết kế:** bộ bổ trợ nên nói gì với sinh viên?

**Bằng chứng chính**
- Phản hồi tốt chỉ rõ khoảng cách giữa hiện tại và mục tiêu, và việc cần làm tiếp (Hattie & Timperley, 2007; Shute, 2008).
- Wisniewski et al. (2020), 435 nghiên cứu: hiệu ứng trung bình của phản hồi d = 0.48, rất khác nhau giữa các nghiên cứu; lượng thông tin trong phản hồi là yếu tố điều tiết lớn.
- Kluger & DeNisi (1996): hiệu ứng trung bình d = 0.41, nhưng hơn một phần ba số can thiệp phản hồi làm kết quả *giảm*. Hiệu quả giảm khi phản hồi kéo sự chú ý từ nhiệm vụ sang bản thân người học.
- Van der Kleij et al. (2015), môi trường học trên máy: phản hồi có giải thích (0.49) hơn cho đáp án đúng (0.32), và hơn hẳn chỉ báo đúng/sai (0.05).
- Butler & Roediger (2008): trắc nghiệm không có phản hồi có thể khiến người học nhớ nhầm phương án sai. Phản hồi, ngay hay muộn, làm tăng câu trả lời đúng và giảm lỗi mang theo từ bài trắc nghiệm.
- Metcalfe (2017): lỗi được theo sau bởi phản hồi sửa sai, có phân tích lập luận dẫn tới lỗi, giúp học tốt hơn; lỗi mắc với độ tự tin cao được sửa dễ hơn; nên để người học mắc và sửa lỗi ở tình huống ít rủi ro.

**Hệ quả cho thiết kế:** bổ trợ nói về *chỗ hụt cụ thể* (ý rubric, câu sai, lời giải thích), không nói về người học ("bạn yếu"). Sau bài trắc nghiệm, cho xem đáp án và lời giải thích.

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Hattie & Timperley (2007) | Mô hình phản hồi | Nội dung bổ trợ |
| Shute (2008) | Tổng quan phản hồi hình thành | Như trên |
| Wisniewski et al. (2020) | Meta-analysis, d = 0.48 | Như trên |
| Kluger & DeNisi (1996) | Hơn 1/3 can thiệp phản hồi gây hại | Không phản hồi về bản thân người học |
| Van der Kleij et al. (2015) | Phản hồi có giải thích mạnh nhất | Dùng nhận xét theo ý và lời giải thích |
| Butler & Roediger (2008) | Phản hồi sau trắc nghiệm | Mở đáp án trong bổ trợ |
| Metcalfe (2017) | Học từ lỗi | Bổ trợ xoay quanh lỗi đã mắc |

---

## 3. Luyện bằng kiểm tra và kiểm tra lại

**Câu hỏi thiết kế:** bổ trợ gồm câu luyện hay chỉ đọc lại? Có nên cho kiểm tra lại?

**Bằng chứng chính**
- Làm bài kiểm tra giúp nhớ lâu hơn đọc lại (Roediger & Karpicke, 2006). Rowland (2014) và Adesope et al. (2017) xác nhận bằng meta-analysis.
- Morphew et al. (2020), môn cơ học nhập môn: thay hai bài giữa kỳ bằng bảy bài kiểm tra ngắn trên máy, mỗi bài có một lần thi lại tuỳ chọn. Điểm bài cuối kỳ chung tăng khoảng 7 điểm phần trăm, số điểm A gần gấp đôi, số trượt giảm một nửa. Đây là so sánh giữa hai học kỳ trong một môn.

**Hệ quả cho thiết kế:** bộ bổ trợ có câu luyện, không chỉ có tài liệu đọc lại. Kiểm tra lại là một phần của vòng, dùng câu khác câu đã gặp.

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Roediger & Karpicke (2006) | Hiệu ứng kiểm tra | Câu luyện trong bổ trợ |
| Rowland (2014) | Meta-analysis hiệu ứng kiểm tra | Như trên |
| Adesope et al. (2017) | Meta-analysis luyện bằng kiểm tra | Như trên |
| Morphew et al. (2020) | Kiểm tra thường xuyên kèm thi lại | Kiểm tra lại, chính sách điểm |

---

## 4. LLM chấm tự luận theo rubric: có đủ tin để chẩn đoán không

**Câu hỏi thiết kế:** kết quả chấm từng ý của LLM có dùng được để quyết định bổ trợ không?

**Bằng chứng chính**
- Burrows et al. (2015), tổng quan hơn 80 bài về chấm tự động câu trả lời ngắn, trước thời LLM.
- Jiang & Bosch (2024): GPT-4 chấm bộ dữ liệu ASAP-SAS với rubric trong prompt, hệ số kappa có trọng số trung bình 0.677 trên 10 câu; kết quả khác nhau theo môn và phụ thuộc chất lượng rubric.
- Flodén (2025): ChatGPT-3.5 chấm 463 bài của ba đề thi thạc sĩ, so với giảng viên: đồng thuận yếu (kappa 0.139; kappa có trọng số 0.409).
- Deng et al. (2025) [preprint]: đồng thuận với chuyên gia giữ được khi nhãn là nhị phân (đạt/chưa đạt), giảm khi nhãn chia mịn hơn; bỏ các dự đoán có độ tin thấp làm phần còn lại chính xác hơn.
- Heinrich et al. (2025), thử nghiệm có đối chứng với gần 300 sinh viên trong bốn môn đại học: chấm có AI hỗ trợ có thể làm gần giống việc giảng viên làm trong lớp nhỏ.
- Basu et al. (2013): gom câu trả lời giống nhau thành cụm để giảng viên chấm và phản hồi một lần cho cả cụm, và nhìn ra hiểu lầm chung.
- Milani et al. (2025): sinh viên có thể cài lệnh ẩn vào bài làm (prompt injection) để được điểm cao hơn, và kiểu thao túng này có thể lọt qua sự giám sát của giảng viên.

**Hệ quả cho thiết kế:**
- Giữ cách chấm hiện tại: mỗi ý một nhãn đạt/chưa đạt, vì với nhãn nhị phân LLM khớp với người tốt hơn nhãn chia mịn.
- Đồng thuận thay đổi nhiều theo môn và rubric, nên phải đo trên dữ liệu của chính đồ án (RQ1), không lấy số của bài khác.
- Vì rubric chia thành các ý rời rạc, gộp chỗ hụt của cả lớp chỉ là đếm theo ý; không cần gom cụm như Basu et al. (2013).
- Chẩn đoán chỉ quyết định việc bổ trợ, rủi ro thấp hơn điểm số; nhưng nhận xét vẫn ghi rõ là do AI, và giảng viên sửa được.

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Burrows et al. (2015) | Tổng quan chấm câu trả lời ngắn | Bối cảnh |
| Jiang & Bosch (2024) | GPT-4, kappa có trọng số 0.677 | Mức đồng thuận tham khảo |
| Flodén (2025) | ChatGPT-3.5, đồng thuận yếu trên đề thi đại học | Lý do phải tự đo |
| Deng et al. (2025) [preprint] | Nhãn nhị phân khớp tốt hơn | Giữ chấm đạt/chưa đạt theo ý |
| Heinrich et al. (2025) | Thử nghiệm chấm có AI trong bốn môn | Bối cảnh đại học |
| Basu et al. (2013) | Gom câu trả lời để giảng viên xử lý theo nhóm | Gộp chỗ hụt của lớp |
| Milani et al. (2025) | Prompt injection trong bài làm | Kiểm soát rủi ro |

---

## 5. Câu do LLM sinh: chất lượng và cách kiểm tra

**Câu hỏi thiết kế:** có nên sinh câu bổ trợ bằng LLM, và kiểm soát thế nào?

**Bằng chứng chính**
- Kurdi et al. (2020), tổng quan 93 bài về sinh câu hỏi tự động: kiểm soát độ khó và phản hồi ít được nghiên cứu.
- Gierl, Lai & Turner (2012): sinh câu tự động từ mô hình nhận thức và mẫu câu do chuyên gia soạn. Gierl et al. (2017): tổng quan về thiết kế phương án nhiễu.
- Scaria et al. (2024): LLM sinh được câu theo mức Bloom nếu prompt tốt, nhưng chất lượng khác nhiều giữa các model.
- Bhandari et al. (2024): 207 người làm cả câu do ChatGPT sinh và câu trong một giáo trình mở; phân tích theo lý thuyết ứng đáp câu hỏi (IRT). Các bài trích sau mô tả kết quả là câu do LLM sinh có độ phân biệt nhỉnh hơn một chút.
- Isley et al. (2026): sinh câu theo vòng sinh – phê bình – sửa bằng LLM; thử thực địa với gần 1.700 sinh viên ở nhiều trường; theo IRT, câu do AI sinh tương đương câu do chuyên gia viết cho các kỳ thi chuẩn hoá.
- Pardos & Bhandari (2024), 274 người tham gia: gợi ý do ChatGPT viết tạo được tiến bộ so với nhóm không có gợi ý, không khác có ý nghĩa thống kê so với gợi ý của gia sư người. Nhưng 32% gợi ý ban đầu không qua kiểm tra chất lượng; sau khi dùng kỹ thuật tự nhất quán, tỉ lệ lỗi còn gần 0% ở đại số và 13% ở thống kê.
- An et al. (2025) [preprint], khoảng 60 sinh viên trong hai môn khoa học dữ liệu: tỉ lệ đúng 89% ở các tuần có câu luyện do LLM sinh, 73% ở tuần không có. Đây là so sánh giữa các tuần, không phân nhóm ngẫu nhiên.
- arXiv:2609.27063 (2026) [preprint]: nhãn độ khó do LLM gán gần như không tương quan với độ khó thực tế của sinh viên (ρ = 0.06); nhãn bám theo mức Bloom và độ dài câu. Nhóm tác giả khuyên kiểm tra độ khó bằng dữ liệu trả lời.
- Worden et al. (2026), thử nghiệm ngẫu nhiên quy mô lớn: phản hồi do LLM sinh cho câu sai giúp học sinh toán THCS có kiến thức nền thấp tiến bộ trong ngắn hạn.
- Haladyna & Rodriguez (2013): xây dựng và kiểm định câu hỏi, gồm phân tích câu sau khi dùng (độ khó, độ phân biệt, phương án nhiễu).

**Hệ quả cho thiết kế:**
- Câu do LLM sinh có thể đạt chất lượng đo lường tốt, nhưng tỉ lệ lỗi ban đầu đáng kể. Vì vậy câu bổ trợ đi qua bước kiểm tra tự động và giảng viên duyệt, không sinh riêng rồi đưa thẳng cho sinh viên.
- Không tin nhãn độ khó do LLM; đo độ khó và độ phân biệt từ lượt làm thật.
- Bằng chứng về câu sinh *nhắm vào đúng ý bị hụt* để bổ trợ còn mỏng; đây là phần đồ án đóng góp và đo (RQ2).

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Kurdi et al. (2020) | Tổng quan sinh câu hỏi tự động | Bối cảnh |
| Gierl, Lai & Turner (2012) | Sinh câu từ mô hình nhận thức và mẫu câu | Sinh câu theo chỗ hụt |
| Gierl et al. (2017) | Phương án nhiễu | Chẩn đoán từ phương án sai |
| Scaria et al. (2024) | Sinh câu theo mức Bloom | Giới hạn của nhãn Bloom |
| Bhandari et al. (2024) | Câu ChatGPT so với giáo trình, theo IRT | Câu sinh dùng được |
| Isley et al. (2026) | Thử thực địa ~1.700 sinh viên | Như trên |
| Pardos & Bhandari (2024) | 32% gợi ý lỗi trước khi kiểm tra | Bắt buộc kiểm tra và duyệt |
| An et al. (2025) [preprint] | Câu luyện do LLM sinh trong môn đại học | Bối cảnh lớp học |
| arXiv:2609.27063 [preprint] | Nhãn độ khó LLM không khớp thực tế | Thống kê câu sau khi dùng |
| Worden et al. (2026) | Phản hồi do LLM sinh cho câu sai | Bối cảnh |
| Haladyna & Rodriguez (2013) | Phân tích câu | Thống kê câu |

---

## 6. Đưa bổ trợ vào LMS: công cụ có sẵn và mức tham gia

**Câu hỏi thiết kế:** Canvas đã có gì, và làm sao để sinh viên thật sự làm bổ trợ?

**Bằng chứng chính**
- Canvas Outcomes tính mức thạo theo từng outcome bằng các cách như trung bình giảm dần (decaying average) hoặc "n Number of Times" (đạt từ 1 đến 5 lần) (Instructure, Canvas Guides).
- Canvas Mastery Paths mở nội dung khác nhau theo khoảng điểm của *một* bài đã chấm. Nội dung phải soạn sẵn; công cụ ngoài (external tool) không dùng làm nội dung có điều kiện được (Instructure, Canvas Guides).
- Hinkle (2023), thử nghiệm Mastery Paths trong môn sinh lý bệnh và dược lý điều dưỡng: sinh viên điểm thấp ở bài quiz sau buổi học được mở thêm tài liệu ôn và một bài quiz tiếp theo; điểm môn học tăng có ý nghĩa so với học kỳ trước. Đây là so sánh với khoá trước, không phải thử nghiệm ngẫu nhiên.
- Kibble (2007) nghiên cứu ảnh hưởng của điểm khuyến khích lên mức tham gia các bài quiz trực tuyến tự làm; các bài sau trích nghiên cứu này cho kết luận rằng gắn điểm làm tăng mức tham gia.
- Thomas et al. (2025) [preprint], 885 người học: người chủ động dùng phản hồi do LLM viết vốn đã giỏi hơn. Sau khi hiệu chỉnh theo xác suất chọn (propensity score), chỉ 2 trên 7 bài học cho thấy lợi ích có ý nghĩa (0.28 và 0.33 độ lệch chuẩn).
- Georgiadou et al. (2007), tổng quan kiểm soát mức lộ câu trong kiểm tra thích ứng: câu không được dùng quá nhiều và không được lộ trước khi thi.

**Hệ quả cho thiết kế:**
- Phần mới so với Canvas là chẩn đoán tới từng ý và tự sinh nội dung, không phải cách tính mức thạo.
- Bổ trợ là một bài tập trong Canvas, có hạn nộp và tuỳ chọn điểm hoàn thành, không chỉ là một khung trên trang kết quả.
- Khi đánh giá, không so người có làm với người không làm, vì người tự chọn làm vốn khác. Phải chia ngẫu nhiên.
- Kho câu bổ trợ loại câu từng nằm trong đề Kiểm tra; bổ trợ chỉ mở sau khi đáp án của đề đã được mở.

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Canvas Guides: Outcomes | Cách tính mức thạo có sẵn | So sánh với Canvas |
| Canvas Guides: Mastery Paths | Mở nội dung theo khoảng điểm | So sánh với Canvas |
| Hinkle (2023) | Mastery Paths: ôn + quiz tiếp theo | Bằng chứng gần nhất trong Canvas |
| Kibble (2007) | Điểm khuyến khích và mức tham gia | Điểm hoàn thành |
| Thomas et al. (2025) [preprint] | Thiên lệch tự chọn | Chia ngẫu nhiên khi đánh giá |
| Georgiadou et al. (2007) | Kiểm soát mức lộ câu | Lọc kho, thời điểm mở |

---

## 7. Báo cáo cho giảng viên và rủi ro của GenAI

**Câu hỏi thiết kế:** giảng viên cần thấy gì; LLM được làm đến đâu?

**Bằng chứng chính**
- Holstein et al. (2018): kính thực tế hỗn hợp cho giáo viên thấy phân tích thời gian thực từ hệ thống dạy học thông minh; thử nghiệm ba nhóm với 286 học sinh, 18 lớp, 8 giáo viên cho thấy học sinh học tốt hơn so với dạy như thường lệ và so với chỉ theo dõi không có phân tích.
- Molenaar & Knoop-van Campen (2019): giáo viên khác nhau nhiều trong cách biến thông tin trên bảng điều khiển thành hành động.
- Bull & Kay (2016): khung thiết kế giao diện cho mô hình người học mở, tức cho người học và giáo viên xem dữ liệu về việc học.
- Bastani et al. (2025), khoảng 1.000 học sinh: dùng GPT tự do làm điểm luyện tập tăng, nhưng khi bỏ AI thì điểm thi thấp hơn nhóm không dùng 17%; bản có ràng buộc giảm phần lớn tác hại đó.

**Hệ quả cho thiết kế:**
- Báo cáo lớp chỉ ra việc cụ thể: ý nào nhiều người hụt, ai cần hỗ trợ, câu nào cần xem lại, kèm nút sinh câu bổ trợ. Không chỉ là bảng số.
- LLM không làm bài hộ và không trò chuyện tự do với sinh viên trong bổ trợ; nó chấm theo ý và viết câu cho giảng viên duyệt.

| Tài liệu | Nội dung chính | Dùng cho |
|---|---|---|
| Holstein et al. (2018) | Phân tích cho giáo viên giúp học sinh học tốt hơn | Báo cáo lớp |
| Molenaar & Knoop-van Campen (2019) | Giáo viên dùng bảng điều khiển rất khác nhau | Báo cáo phải chỉ ra việc cần làm |
| Bull & Kay (2016) | Mô hình người học mở | Trạng thái LO cho sinh viên |
| Bastani et al. (2025) | AI không ràng buộc có thể hại việc học | Giới hạn vai trò của LLM |

---

## 8. Truy vết: quyết định thiết kế và căn cứ

| Quyết định | Căn cứ |
|---|---|
| Bám vào bài giảng viên đã giao, theo vòng kiểm tra → bổ trợ → kiểm tra lại | Bloom (1968); Guskey (2007, 2010); Kulik et al. (1990); Black & Wiliam (1998) |
| Chẩn đoán tới từng ý rubric, không chỉ điểm tổng | Van der Kleij et al. (2015); Wisniewski et al. (2020); Hattie & Timperley (2007) |
| Phản hồi nói về chỗ hụt, không nói về người học | Kluger & DeNisi (1996) |
| Mở đáp án và lời giải thích trong bổ trợ | Butler & Roediger (2008); Metcalfe (2017) |
| Bổ trợ có câu luyện, không chỉ đọc lại | Roediger & Karpicke (2006); Rowland (2014); Adesope et al. (2017) |
| Kiểm tra lại bằng câu khác, cùng LO | Guskey (2010); Morphew et al. (2020) |
| Giữ nhãn đạt/chưa đạt cho từng ý khi chấm | Deng et al. (2025); Jiang & Bosch (2024) |
| Tự đo đồng thuận AI – giảng viên trên dữ liệu của đồ án | Flodén (2025); Jiang & Bosch (2024) |
| Gộp chỗ hụt của lớp bằng cách đếm theo ý | Basu et al. (2013) |
| Câu sinh qua kiểm tra tự động và giảng viên duyệt | Pardos & Bhandari (2024); Bhandari et al. (2024); Isley et al. (2026) |
| Thống kê độ khó và độ phân biệt từ lượt làm thật | arXiv:2609.27063; Haladyna & Rodriguez (2013) |
| Bổ trợ là bài tập Canvas, tuỳ chọn điểm hoàn thành | Kibble (2007); Hinkle (2023) |
| Đánh giá bằng chia ngẫu nhiên, không so người tự chọn | Thomas et al. (2025); Hinkle (2023) |
| Loại câu đề Kiểm tra khỏi kho; mở bổ trợ sau khi mở đáp án | Georgiadou et al. (2007) |
| Báo cáo lớp chỉ ra việc cụ thể | Holstein et al. (2018); Molenaar & Knoop-van Campen (2019) |
| LLM không quyết định đạt/chưa đạt, không làm bài hộ | Bastani et al. (2025); Milani et al. (2025) |

---

## 9. Khoảng trống đồ án nhắm tới

1. **Câu sinh nhắm vào đúng ý bị hụt để bổ trợ.** Các thử nghiệm tìm được chủ yếu đo gợi ý hoặc phản hồi do LLM viết (Pardos & Bhandari, 2024; Worden et al., 2026), hoặc câu luyện chung (An et al., 2025). Chưa thấy đánh giá câu sinh từ một ý rubric cụ thể mà nhiều sinh viên cùng hụt.
2. **Bằng chứng về bổ trợ trong Canvas còn nhỏ.** Nghiên cứu Mastery Paths tìm được là thử nghiệm một môn, so với học kỳ trước (Hinkle, 2023).
3. **Chẩn đoán theo ý bằng LLM cho mục đích bổ trợ.** Các nghiên cứu đo đồng thuận khi chấm điểm; chưa thấy nghiên cứu đo đồng thuận ở mức từng ý khi kết quả dùng để quyết định bổ trợ.

---

## Danh mục tài liệu

- Adesope, O. O., Trevisan, D. A., & Sundararajan, N. (2017). Rethinking the use of tests: A meta-analysis of practice testing. *Review of Educational Research*, 87(3), 659–701. https://doi.org/10.3102/0034654316689306
- An, Y., Liu, J., Acharya, N., & Hashmi, R. (2025). Enhancing student learning with LLM-generated retrieval practice questions: An empirical study in data science courses [Preprint]. arXiv:2507.05629.
- Bastani, H., et al. (2025). Generative AI without guardrails can harm learning: Evidence from high school mathematics. *PNAS*, 122(26), e2422633122. https://doi.org/10.1073/pnas.2422633122
- Basu, S., Jacobs, C., & Vanderwende, L. (2013). Powergrading: A clustering approach to amplify human effort for short answer grading. *Transactions of the Association for Computational Linguistics*, 1, 391–402. https://doi.org/10.1162/tacl_a_00236
- Bhandari, S., Liu, Y., Kwak, Y., & Pardos, Z. A. (2024). Evaluating the psychometric properties of ChatGPT-generated questions. *Computers and Education: Artificial Intelligence*, 7, 100284. https://doi.org/10.1016/j.caeai.2024.100284
- Black, P., & Wiliam, D. (1998). Assessment and classroom learning. *Assessment in Education: Principles, Policy & Practice*, 5(1), 7–74. https://doi.org/10.1080/0969595980050102
- Bloom, B. S. (1968). Learning for mastery. *Evaluation Comment*, 1(2).
- Bull, S., & Kay, J. (2016). SMILI☺: A framework for interfaces to learning data in open learner models, learning analytics and related fields. *International Journal of Artificial Intelligence in Education*, 26(1), 293–331.
- Burrows, S., Gurevych, I., & Stein, B. (2015). The eras and trends of automatic short answer grading. *International Journal of Artificial Intelligence in Education*, 25(1), 60–117. https://doi.org/10.1007/s40593-014-0026-8
- Butler, A. C., & Roediger, H. L. (2008). Feedback enhances the positive effects and reduces the negative effects of multiple-choice testing. *Memory & Cognition*, 36(3), 604–616. https://doi.org/10.3758/MC.36.3.604
- Deng, H., Farber, C., Lee, J., & Tang, D. (2025). Rubric-conditioned LLM grading: Alignment, uncertainty, and robustness [Preprint]. arXiv:2601.08843.
- Flodén, J. (2025). Grading exams using large language models: A comparison between human and AI grading of exams in higher education using ChatGPT. *British Educational Research Journal*, 51(1), 201–224. https://doi.org/10.1002/berj.4069
- Georgiadou, E., Triantafillou, E., & Economides, A. A. (2007). A review of item exposure control strategies for computerized adaptive testing developed from 1983 to 2005. *Journal of Technology, Learning, and Assessment*, 5(8). https://www.ejournals.bc.edu/index.php/jtla/article/view/1647
- Gierl, M. J., Bulut, O., Guo, Q., & Zhang, X. (2017). Developing, analyzing, and using distractors for multiple-choice tests in education: A comprehensive review. *Review of Educational Research*, 87(6), 1082–1116. https://doi.org/10.3102/0034654317726529
- Gierl, M. J., Lai, H., & Turner, S. R. (2012). Using automatic item generation to create multiple-choice test items. *Medical Education*, 46(8), 757–765. https://doi.org/10.1111/j.1365-2923.2012.04289.x
- Guskey, T. R. (2007). Closing achievement gaps: Revisiting Benjamin S. Bloom's "Learning for Mastery". *Journal of Advanced Academics*, 19(1), 8–31. https://doi.org/10.4219/jaa-2007-704
- Guskey, T. R. (2010). Lessons of mastery learning. *Educational Leadership*, 68(2), 52–57. https://www.ascd.org/el/articles/lessons-of-mastery-learning
- Haladyna, T. M., & Rodriguez, M. C. (2013). *Developing and validating test items*. Routledge.
- Hattie, J., & Timperley, H. (2007). The power of feedback. *Review of Educational Research*, 77(1), 81–112. https://doi.org/10.3102/003465430298487
- Heinrich, T., Baily, S., Chen, K.-W., DeOliveira, J., Park, S., & Wang, N. C.-H. (2025). AI-assisted grading and personalized feedback in large political science classes: Results from randomized controlled trials. *PLOS ONE*, 20(8), e0328041. https://doi.org/10.1371/journal.pone.0328041
- Hinkle, J. F. (2023). Personalization and learning outcome in a nursing pathophysiology and pharmacology course: Canvas Mastery adoption pilot study. *SAGE Open Nursing*, 9. https://doi.org/10.1177/23779608231186030
- Holstein, K., McLaren, B. M., & Aleven, V. (2018). Student learning benefits of a mixed-reality teacher awareness tool in AI-enhanced classrooms. In *AIED 2018*, LNCS 10947 (pp. 154–168). Springer. https://doi.org/10.1007/978-3-319-93843-1_12
- Instructure. (n.d.). How do I add conditional content to a Mastery Path source item? *Canvas Guides*. https://community.canvaslms.com/docs/DOC-9936
- Instructure. (n.d.). How do I manage outcome mastery calculations in a course? *Canvas Guides* (bản sao trên trang hỗ trợ của SBCTC). https://support.corrections.sbctc.edu/m/127848/l/2006717-how-do-i-manage-outcome-mastery-calculations-in-a-course
- Instructure. (n.d.). What are Mastery Paths? *Canvas Guides*. https://community.canvaslms.com/t5/Canvas-Basics-Guide/What-is-MasteryPaths/ta-p/404483
- Instructure. (n.d.). What are Outcomes? *Canvas Guides*. https://community.canvaslms.com/t5/Canvas-Basics-Guide/What-are-Outcomes/ta-p/75
- Isley, C., Gilbert, J., Kassos, E., Kocher, M., Nie, A., Brunskill, E., Domingue, B., Hofman, J., Legewie, J., Svoronos, T., Tuminelli, C., & Goel, S. (2026). Assessing the quality of AI-generated exams: A large-scale field study. In *AAAI 2026*. https://doi.org/10.1609/aaai.v40i45.41205
- Jiang, L., & Bosch, N. (2024). Short answer scoring with GPT-4. In *L@S '24* (pp. 438–442). ACM. https://doi.org/10.1145/3657604.3664685
- Kibble, J. (2007). Use of unsupervised online quizzes as formative assessment in a medical physiology course: Effects of incentives on student participation and performance. *Advances in Physiology Education*, 31(3), 253–260. https://doi.org/10.1152/advan.00027.2007
- Kluger, A. N., & DeNisi, A. (1996). The effects of feedback interventions on performance: A historical review, a meta-analysis, and a preliminary feedback intervention theory. *Psychological Bulletin*, 119(2), 254–284. https://doi.org/10.1037/0033-2909.119.2.254
- Kulik, C.-L. C., Kulik, J. A., & Bangert-Drowns, R. L. (1990). Effectiveness of mastery learning programs: A meta-analysis. *Review of Educational Research*, 60(2), 265–299. https://doi.org/10.3102/00346543060002265
- Kurdi, G., Leo, J., Parsia, B., Sattler, U., & Al-Emari, S. (2020). A systematic review of automatic question generation for educational purposes. *International Journal of Artificial Intelligence in Education*, 30, 121–204. https://doi.org/10.1007/s40593-019-00186-y
- Metcalfe, J. (2017). Learning from errors. *Annual Review of Psychology*, 68, 465–489. https://doi.org/10.1146/annurev-psych-010416-044022
- Milani, A., Franzoni, V., Florindi, E., Omarbekova, A., Bekmanova, G., & Yergesh, B. (2025). When AI is fooled: Hidden risks in LLM-assisted grading. *Education Sciences*, 15(11), 1419. https://doi.org/10.3390/educsci15111419
- Molenaar, I., & Knoop-van Campen, C. A. N. (2019). How teachers make dashboard information actionable. *IEEE Transactions on Learning Technologies*, 12(3), 347–355. https://doi.org/10.1109/TLT.2018.2851585
- Morphew, J. W., Silva, M., Herman, G., & West, M. (2020). Frequent mastery testing with second-chance exams leads to enhanced student learning in undergraduate engineering. *Applied Cognitive Psychology*, 34(1), 168–181. https://doi.org/10.1002/acp.3605
- Pardos, Z. A., & Bhandari, S. (2024). ChatGPT-generated help produces learning gains equivalent to human tutor-authored help on mathematics skills. *PLOS ONE*, 19(5), e0304013. https://doi.org/10.1371/journal.pone.0304013
- Roediger, H. L., & Karpicke, J. D. (2006). Test-enhanced learning: Taking memory tests improves long-term retention. *Psychological Science*, 17(3), 249–255. https://doi.org/10.1111/j.1467-9280.2006.01693.x
- Rowland, C. A. (2014). The effect of testing versus restudy on retention: A meta-analytic review of the testing effect. *Psychological Bulletin*, 140(6), 1432–1463. https://doi.org/10.1037/a0037559
- Scaria, N., Chenna, S. D., & Subramani, D. (2024). Automated educational question generation at different Bloom's skill levels using large language models: Strategies and evaluation. In *AIED 2024* (pp. 165–179). https://doi.org/10.1007/978-3-031-64299-9_12
- Shute, V. J. (2008). Focus on formative feedback. *Review of Educational Research*, 78(1), 153–189. https://doi.org/10.3102/0034654307313795
- *Student use of LLMs and the limits of AI-generated question difficulty in data science courses* (2026) [Preprint]. arXiv:2609.27063. Chưa xác minh được danh sách tác giả.
- Thomas, D. R., Borchers, C., Bhushan, S., Gatz, E., Gupta, S., & Koedinger, K. R. (2025). LLM-generated feedback supports learning if learners choose to use it [Preprint]. arXiv:2506.17006.
- Van der Kleij, F. M., Feskens, R. C. W., & Eggen, T. J. H. M. (2015). Effects of feedback in a computer-based learning environment on students' learning outcomes: A meta-analysis. *Review of Educational Research*, 85(4), 475–511. https://doi.org/10.3102/0034654314564881
- Wisniewski, B., Zierer, K., & Hattie, J. (2020). The power of feedback revisited: A meta-analysis of educational feedback research. *Frontiers in Psychology*, 10, 3087. https://doi.org/10.3389/fpsyg.2019.03087
- Worden, E., Dang, L., Lim, W. C., Miller, S., Zhang, J., Haim, A., Sales, A., Gurung, A., & Heffernan, N. (2026). A large scale randomized control trial showing LLM generated feedback helps low-knowledge middle school math students with short-term learning. In *L@S '26*. ACM. https://doi.org/10.1145/3774398.3811594
