# Báo cáo thiết kế: Chẩn đoán và bổ trợ theo LO sau bài kiểm tra

**Đề tài:** Hệ thống LMS tự động tạo Micro-Content & Quiz bằng Generative AI (DA Platform)
**Ngày:** 16/10/2026
**Trạng thái:** thiết kế, chưa triển khai. Báo cáo này để xin ý kiến thầy trước khi làm.
**Tài liệu kèm:** [bo-tro-sau-kiem-tra-tong-quan-tai-lieu.md](bo-tro-sau-kiem-tra-tong-quan-tai-lieu.md) tổng hợp 42 tài liệu liên quan, có bảng truy vết từ quyết định thiết kế về căn cứ.
**Thay cho:** phương án Learning Agent tự lên lộ trình luyện tập ([bao-cao-thiet-ke-learning-agent.md](bao-cao-thiet-ke-learning-agent.md)). Lý do đổi ở mục 4.2.

---

## Tóm tắt

- **Vấn đề.** Hệ thống đã sinh được câu hỏi theo LO và chấm được tự luận ngắn theo từng ý của rubric. Nhưng sau một bài kiểm tra, sinh viên chỉ nhận điểm. Kết quả "hụt ý nào" bị bỏ đi, không có gì giúp sinh viên khắc phục đúng LO còn yếu, và giảng viên chỉ thấy điểm tổng.
- **Đề xuất.** Thêm vòng *kiểm tra → chẩn đoán → bổ trợ → kiểm tra lại* theo mô hình Learning for Mastery (Bloom, 1968; Guskey, 2010), bám vào bài mà giảng viên đã giao trên Canvas. Chấm xong, hệ thống xác định mỗi sinh viên chưa đạt LO nào và hụt ý nào. Với mỗi LO đó, sinh viên nhận một bộ bổ trợ ngắn: chỗ hụt và lời giải thích, chỗ cần đọc lại, vài câu luyện. Sau đó là một câu kiểm tra lại khác mọi câu đã gặp.
- **Vai trò của GenAI.** LLM chấm theo ý để chẩn đoán (đã có, chỉ cần lưu lại kết quả từng ý). LLM sinh câu bổ trợ nhắm vào những ý mà nhiều sinh viên trong lớp cùng hụt; câu sinh ra vào hàng đợi duyệt của giảng viên. Việc kết luận đạt hay chưa đạt và việc chọn câu do code làm.
- **Khác Canvas ở đâu.** Canvas Outcomes đã tính được mức thạo theo outcome, và Mastery Paths đã mở được nội dung theo khoảng điểm. Phần mới ở đây là chẩn đoán tới từng ý rubric, nội dung bổ trợ tự sinh từ chỗ hụt, và báo cáo cho giảng viên về những ý cả lớp hay hụt và những câu cần xem lại.
- **Đánh giá.** (1) Đồng thuận giữa AI và người chấm khi chấm từng ý. (2) Chất lượng câu bổ trợ sinh ra: tỉ lệ giảng viên duyệt, có nhắm đúng ý bị hụt không, độ khó và độ phân biệt thực tế. (3) Thử nghiệm nhỏ trong một lớp thật: các LO cần bổ trợ của mỗi sinh viên được chia ngẫu nhiên thành hai nhóm, so kết quả kiểm tra lại.
- **Phạm vi và thời gian:** giai đoạn 0–4, khoảng 7–8 tuần cho một người làm (mục 13).

---

## 1. Vấn đề

### 1.1 Hệ thống hiện có

- Giảng viên sinh câu hỏi từ tài liệu môn học, chọn LO, mức Bloom và một trong 5 loại câu: trắc nghiệm một đáp án, trắc nghiệm nhiều đáp án, đúng/sai, điền khuyết, tự luận ngắn. Câu sinh ra chờ giảng viên duyệt.
- Giảng viên gom câu thành đề, chế độ Luyện tập hoặc Kiểm tra, và thêm đề vào Canvas qua LTI 1.3 Deep Linking. Điểm gửi về sổ điểm Canvas.
- Với đề Kiểm tra, đáp án chỉ mở cho sinh viên sau khi đề đóng. Với đề Luyện tập, đáp án mở ngay sau khi nộp.
- Câu tự luận ngắn được LLM chấm theo rubric: LLM xét từng ý đạt hay chưa đạt, kèm nhận xét; code tính điểm từ số ý đạt.
- Mỗi câu có LO, lời giải thích và đoạn nguồn; mỗi đoạn nguồn biết số trang. Mỗi LO có các thẻ bài học.

### 1.2 Một ví dụ

Bài Kiểm tra chương 1 môn Dữ liệu lớn có ba câu thuộc L.O.1.1: một câu trắc nghiệm, một câu đúng/sai, và câu tự luận ngắn sau:

> **Câu:** Giải thích ngắn gọn khái niệm dữ liệu lớn dựa trên định nghĩa trong tài liệu.
> **Rubric:** (1) giới hạn của công nghệ CSDL tiêu chuẩn; (2) quy mô, đa dạng và phức tạp; (3) mục đích trích xuất giá trị.

Sinh viên A làm đúng câu trắc nghiệm, sai câu đúng/sai. Ở câu tự luận, A trả lời "Dữ liệu lớn là dữ liệu có quy mô lớn, đa dạng và phức tạp, cần phân tích để rút ra giá trị": đạt ý (2) và (3), chưa đạt ý (1). Sinh viên B đúng cả ba câu.

**Hiện nay**
- A thấy điểm, một nhận xét chung cho câu tự luận, và đáp án sau khi đề đóng. Kết luận "ý (1) chưa đạt" đã được LLM tính ra nhưng không được lưu.
- Không có gì hướng A quay lại phần định nghĩa, hay cho A cơ hội làm lại phần L.O.1.1.
- Giảng viên thấy điểm tổng của từng sinh viên. Muốn biết bao nhiêu người cùng hụt ý (1), giảng viên phải tự đọc từng bài.

**Khi có bổ trợ**
- Hệ thống lưu kết quả từng ý. L.O.1.1 của A đạt 56%, dưới ngưỡng 80%, nên A cần bổ trợ L.O.1.1. B đạt 100%, không phải làm gì thêm.
- Sau khi đề đóng, A mở bài "Bổ trợ sau Kiểm tra chương 1" trong Canvas và thấy:
    - nhận xét về ý (1) và lời giải thích của câu đúng/sai đã sai;
    - đường dẫn đến thẻ bài học của L.O.1.1 và trang tài liệu có định nghĩa;
    - hai câu luyện về L.O.1.1, có phản hồi ngay;
    - một câu kiểm tra lại về L.O.1.1, khác mọi câu A đã gặp.
- A làm đúng câu kiểm tra lại thì L.O.1.1 chuyển sang "đã khắc phục". Làm sai thì A vào danh sách "cần hỗ trợ" của giảng viên.
- Giảng viên thấy ý (1) là chỗ nhiều sinh viên cùng hụt nhất, bấm sinh câu bổ trợ cho ý đó, duyệt ba câu mới. Những sinh viên mở bổ trợ sau đó có thêm câu luyện nhắm đúng ý (1).

### 1.3 Ba khoảng trống

1. **Mất thông tin chẩn đoán.** Hệ thống biết sinh viên thiếu bao nhiêu điểm nhưng không giữ lại thiếu ý nào, sai LO nào.
2. **Không có bổ trợ sau kiểm tra.** Bài kiểm tra kết thúc ở điểm số. Không có vòng khắc phục và kiểm tra lại như mastery learning đề xuất.
3. **Giảng viên không thấy chỗ hụt chung.** Giảng viên không biết ý nào cả lớp hay hụt, ai cần hỗ trợ, và câu nào có vấn đề, kể cả câu do AI sinh.

---

## 2. Mục tiêu và phạm vi

**Mục tiêu**

| # | Mục tiêu | Đo bằng |
|---|---|---|
| M1 | Chẩn đoán mỗi sinh viên theo LO và theo ý rubric sau mỗi bài | Đồng thuận giữa AI và người chấm (RQ1) |
| M2 | Giao bộ bổ trợ và câu kiểm tra lại cho đúng LO chưa đạt | Thử nghiệm nhỏ: tỉ lệ đúng ở kiểm tra lại (RQ3) |
| M3 | Sinh câu bổ trợ nhắm vào chỗ hụt phổ biến của lớp, qua giảng viên duyệt | Tỉ lệ duyệt, mức nhắm đúng ý, thống kê câu (RQ2) |
| M4 | Báo cáo lớp cho giảng viên: LO × sinh viên, ý hay hụt, câu cần xem lại, ai cần hỗ trợ | Nhật ký sử dụng; phỏng vấn giảng viên (RQ4) |

**Không làm**
- Không đổi điểm của bài gốc. Bài bổ trợ có điểm riêng nếu giảng viên chọn (mục 7.3).
- Không lên lộ trình học dài hạn cho từng sinh viên, không lịch ôn. Đây là phương án đã cân nhắc và không chọn (mục 4.2).
- Không huấn luyện mô hình, vì không đủ dữ liệu.
- Không để LLM kết luận sinh viên đạt hay chưa đạt, và không để LLM viết phản hồi mới cho sinh viên mà không qua duyệt.
- Không sửa phần video, trình xem tài liệu và trợ giảng chat của các thành viên khác; chỉ nối với chúng qua đường dẫn.

---

## 3. Vòng bổ trợ

```text
[1] Bài gốc (Canvas, LTI) ─► chấm: code chấm câu chọn, LLM chấm tự luận theo từng ý
         │  khi chấm xong; với đề Kiểm tra: khi đáp án đã mở
         ▼
[2] Chẩn đoán (code): mỗi sinh viên × LO → đạt / chưa đạt, kèm chỗ hụt
         │
   ┌─────┴────────────────────────────┐
   ▼ sinh viên                        ▼ giảng viên
[3] Bộ bổ trợ cho mỗi LO chưa đạt     [5] Báo cáo lớp: chỗ hụt phổ biến,
    chỗ hụt · đọc lại · câu luyện         ai cần hỗ trợ, câu nên xem lại
   ▼                                  ▼
[4] Kiểm tra lại bằng câu khác        [6] Sinh câu cho chỗ hụt phổ biến (LLM)
    đúng → đã khắc phục                   → kiểm tra tự động → giảng viên duyệt
    sai  → cần hỗ trợ, vào [5]            → câu đã duyệt vào kho, dùng ở [3] và [4]
```

Vòng này là Learning for Mastery của Bloom đặt vào LMS:

| Bước của Learning for Mastery (Guskey, 2010) | Trong hệ thống |
|---|---|
| Dạy một đơn vị | Giảng viên dạy như thường, trên lớp hoặc qua Canvas |
| Kiểm tra hình thành lần một | Bài gốc giảng viên đã giao (đề Luyện tập hoặc Kiểm tra) |
| Bổ trợ, khác với dạy lại | Bộ bổ trợ theo chỗ hụt của từng sinh viên |
| Mở rộng cho người đã đạt | Ngoài phạm vi; sinh viên đạt mọi LO không phải làm gì thêm |
| Kiểm tra hình thành lần hai, câu khác, cùng mục tiêu | Câu kiểm tra lại, cùng LO, khác mọi câu đã gặp |

Mỗi bước có một chủ thể rõ ràng. Code quyết định đạt hay chưa đạt và chọn câu. LLM chỉ chấm theo ý và viết câu cho giảng viên duyệt. Giảng viên đặt ngưỡng, chọn chỗ hụt cần sinh câu, và duyệt mọi câu mới.

---

## 4. Các lựa chọn thiết kế và căn cứ

### 4.1 Bảng lựa chọn

| Vấn đề | Lựa chọn | Phương án đã cân nhắc | Căn cứ |
|---|---|---|---|
| Bám vào đâu | Bài giảng viên đã giao | Agent tự lên lộ trình luyện tập, không tính điểm | Mastery learning của Bloom thiết kế cho lớp theo nhịp giảng viên (Guskey, 2010); hiệu quả qua 108 đánh giá (Kulik et al., 1990); bài tự chọn ít người làm nếu không gắn điểm (Kibble, 2007) |
| Đơn vị chẩn đoán | LO và ý rubric | Điểm tổng của bài, như Mastery Paths; mô hình người học BKT | Phản hồi có giải thích mạnh hơn hẳn chỉ báo đúng/sai (Van der Kleij et al., 2015); mỗi bài chỉ có vài câu mỗi LO, BKT không thêm được nhiều |
| Ngưỡng đạt | Tỉ lệ điểm của LO trong bài ≥ θ, mặc định 80% | BKT; "3 câu đúng liên tiếp" | Đơn giản, giảng viên hiểu và chỉnh được; θ là giá trị khởi đầu |
| Nội dung bổ trợ | Chỗ hụt, lời giải thích, chỗ đọc lại, câu luyện | Chỉ mở đáp án; chiếu lại bài giảng | Bổ trợ khác dạy lại (Guskey, 2010); phản hồi sau trắc nghiệm (Butler & Roediger, 2008); luyện bằng kiểm tra (Adesope et al., 2017) |
| Phản hồi nói về gì | Chỗ hụt cụ thể | Nhận xét chung về người học | Phản hồi hướng về bản thân người học có thể gây hại (Kluger & DeNisi, 1996) |
| Kiểm tra lại | Câu khác, cùng LO | Làm lại đúng câu cũ | Câu khác, cùng mục tiêu (Guskey, 2010); thi lại làm tăng kết quả (Morphew et al., 2020) |
| Nguồn câu bổ trợ | Kho câu đã duyệt; thiếu thì sinh theo chỗ hụt phổ biến của lớp, giảng viên duyệt | Sinh riêng cho từng sinh viên ngay lúc làm | 32% gợi ý do ChatGPT viết lỗi trước khi kiểm tra (Pardos & Bhandari, 2024); câu sinh có kiểm tra đạt chất lượng đo lường tốt (Bhandari et al., 2024; Isley et al., 2026) |
| Gộp chỗ hụt của lớp | Đếm theo (LO, ý rubric) và (LO, câu) | Gom cụm câu trả lời | Rubric đã chia ý rời rạc, nên đếm là đủ; gom cụm cần khi câu trả lời là văn bản tự do (Basu et al., 2013) |
| Thời điểm mở bổ trợ | Khi chấm xong, và với đề Kiểm tra: sau khi đáp án đã mở | Ngay sau khi nộp | Tránh lộ đề cho người chưa nộp (Georgiadou et al., 2007) |
| Cách giao trong Canvas | Một bài tập LTI "Bổ trợ sau bài X", nội dung khác nhau theo sinh viên; tuỳ chọn điểm hoàn thành | Chỉ hiện trên trang kết quả | Có hạn nộp và nằm trong danh sách việc của Canvas; gắn điểm làm tăng mức tham gia (Kibble, 2007) |
| Thống kê câu | Độ khó, độ phân biệt, tỉ lệ chọn phương án, từ lượt làm thật | Tin nhãn độ khó do LLM gán | Nhãn độ khó của LLM gần như không khớp thực tế, ρ = 0.06 (arXiv:2609.27063); phân tích câu (Haladyna & Rodriguez, 2013) |
| Đánh giá | Đồng thuận chấm; chất lượng câu sinh; thử nghiệm ngẫu nhiên theo LO | Mô phỏng; so với khoá trước; so người làm với người không làm | Người tự chọn dùng phản hồi vốn giỏi hơn (Thomas et al., 2025); so với khoá trước dễ nhiễu (Hinkle, 2023) |

### 4.2 Vì sao không chọn phương án Learning Agent

Phương án trước là một Agent sau mỗi câu trả lời cập nhật mức thạo theo LO bằng BKT và chọn hoạt động tiếp theo cho sinh viên, có lịch ôn. Phương án này không hợp với LMS vì ba lý do:

1. **LMS chạy theo nhịp giảng viên.** Sinh viên vào Canvas vì có bài được giao, có hạn nộp, có điểm. Luyện tập tự chọn, không tính điểm thì ít người làm (Kibble, 2007). Vòng ngoài kiểu hệ thống dạy học thông minh chạy tốt khi luyện tập là hoạt động chính, với rất nhiều câu ngắn cho mỗi kỹ năng. Một môn đại học chỉ có vài LO mỗi chương và vài chục câu mỗi LO.
2. **Canvas đã có bản đơn giản.** Outcomes tính mức thạo bằng trung bình giảm dần hoặc "đạt n lần"; đó chính là các đối chứng của phương án trước. Mastery Paths mở nội dung theo điểm. Câu hỏi "Canvas có rồi, phần mới là gì?" không có câu trả lời rõ.
3. **Luồng chính gần như không dùng GenAI.** Phần GenAI duy nhất gắn với Agent (sinh câu nhắm chỗ hụt) nằm ở giai đoạn mở rộng.

So sánh ba cách:

| | Canvas Mastery Paths | Learning Agent (phương án trước) | Bổ trợ sau kiểm tra (đề xuất) |
|---|---|---|---|
| Kích hoạt | Điểm của một bài đã chấm | Mỗi câu trả lời | Bài gốc đã chấm xong |
| Đơn vị quyết định | Khoảng điểm của cả bài | Mức thạo BKT theo LO | LO và ý rubric |
| Nội dung | Giảng viên soạn sẵn | Câu trong kho, lịch ôn | Chỗ hụt, đọc lại, câu luyện; câu mới sinh theo chỗ hụt của lớp |
| Sinh viên có làm không | Có, nếu là bài được giao | Phụ thuộc tự giác | Có, là bài tập Canvas có hạn nộp |
| Vai trò GenAI | Không | Phụ | Chấm theo ý; sinh câu theo chỗ hụt |
| Đánh giá được bằng | Không áp dụng | Chủ yếu mô phỏng | Dữ liệu thật quy mô nhỏ |

Phương án mới giữ lại các phần còn đúng của phương án trước: lưu kết quả từng ý, kho câu loại câu thi, chống trùng câu, trỏ về thẻ bài học và trang tài liệu.

---

## 5. Kiến trúc

```text
Canvas ── bài gốc (LTI) ──► core-api: ghi lượt làm
                             worker: chấm tự luận theo ý ─► lưu kết quả từng ý
                │
                │ sinh viên mở trang kết quả hoặc bài bổ trợ; giảng viên mở báo cáo
                ▼
core-api, module bổ trợ
  [1] Chẩn đoán       lượt nộp → sinh viên × LO: tỉ lệ điểm, câu sai, ý hụt, phương án đã chọn   (code)
  [2] Kho câu bổ trợ  đã duyệt · cùng LO · chưa từng ở đề Kiểm tra · sinh viên chưa gặp          (code)
  [3] Bộ bổ trợ       mỗi LO chưa đạt: chỗ hụt + đọc lại + k câu luyện + câu kiểm tra lại        (code)
  [4] Báo cáo lớp     LO × sinh viên · chỗ hụt phổ biến · thống kê câu · cần hỗ trợ             (code)
  [5] Yêu cầu sinh câu  giảng viên chọn chỗ hụt → sự kiện yêu cầu sinh câu kèm chỗ hụt
                │
                ▼
worker: sinh câu nhắm chỗ hụt → kiểm tra tự động → hàng đợi duyệt của giảng viên

Canvas ── bài tập "Bổ trợ sau bài X" (LTI, Deep Linking) ──► trang bổ trợ ──► điểm hoàn thành (AGS)
```

**Bốn quyết định kiến trúc**

1. **Chẩn đoán là hàm thuần trên các lượt làm của một lượt nộp.** Không có bảng trạng thái mức thạo cần đồng bộ. Câu tự luận được chấm xong hoặc được giảng viên chấm lại thì lần tính sau tự thấy kết quả mới. Câu luyện và câu kiểm tra lại là lượt làm bình thường, có ghi nguồn "bổ trợ".
2. **Chạy theo yêu cầu, không chạy nền.** Chẩn đoán và bộ bổ trợ được tính khi sinh viên mở trang; báo cáo được tính khi giảng viên mở. Sinh câu chỉ chạy khi giảng viên bấm, nên giảng viên kiểm soát được chi phí và lượng câu phải duyệt.
3. **Module bổ trợ nằm trong core-api**, cạnh module quiz. Nó dùng lại kho câu, lượt làm, Deep Linking và gửi điểm (AGS) đã có.
4. **LLM nằm trong worker và đi qua các đường sẵn có.** Chấm tự luận dùng luồng chấm hiện tại. Sinh câu dùng luồng sinh câu hiện tại, thêm thông tin chỗ hụt vào yêu cầu; câu sinh ra vào hàng đợi duyệt như mọi câu khác.

---

## 6. Chẩn đoán

### 6.1 Dữ liệu dùng

| Dữ liệu | Có sẵn? |
|---|---|
| LO, loại câu, điểm 0–100 của từng câu trong lượt nộp | Có |
| Phương án sinh viên đã chọn | Có |
| Lời giải thích và đoạn nguồn của câu | Có |
| Kết quả từng ý của câu tự luận: đạt hay chưa, nhận xét | LLM đã tính nhưng chưa lưu; thêm ở giai đoạn 0 |
| Hiểu lầm mà mỗi phương án sai đại diện | Chưa có; nằm trong thiết kế sinh câu đúng yêu cầu. Khi có, chẩn đoán dùng thêm |

### 6.2 Quy tắc

- **Tỉ lệ điểm của LO** = trung bình điểm các câu thuộc LO đó trong bài. Câu tự luận tính theo số ý đạt, nên hụt một trong ba ý vẫn được 67 điểm cho câu đó.
- **LO chưa đạt** khi tỉ lệ < θ, mặc định 80%, giảng viên chỉnh được. Với 2–4 câu mỗi LO, sai bất kỳ câu nào là chưa đạt; từ 5 câu trở lên thì được sai một câu.
- **Chỗ hụt** của một LO chưa đạt gồm: các ý rubric chưa đạt ở câu tự luận; các câu sai, kèm phương án đã chọn với câu trắc nghiệm.
- **Câu đang chờ chấm** (đang chấm, hoặc đang chờ giảng viên vì AI chấm lỗi): LO có câu đó chưa được chẩn đoán. Các LO khác vẫn chẩn đoán bình thường.
- **Câu được giảng viên chấm lại:** dùng kết quả cuối.
- **Câu không gắn LO:** bỏ qua khi chẩn đoán; báo cáo cho giảng viên biết số câu bị bỏ qua.
- **LO chỉ có một câu trong bài:** vẫn chẩn đoán nhưng gắn nhãn "ít bằng chứng".

Một sinh viên đoán đúng câu đúng/sai sẽ không được giao bổ trợ. Lỗi theo chiều này được chấp nhận: bỏ sót một lần bổ trợ ít hại hơn bắt mọi người làm thêm.

### 6.3 Tính tay cho ví dụ ở mục 1.2

| Sinh viên | Trắc nghiệm | Đúng/sai | Tự luận | Tỉ lệ L.O.1.1 | Kết luận | Chỗ hụt |
|---|---|---|---|---|---|---|
| A | 100 | 0 | 67 (2/3 ý) | 56% | Chưa đạt | Ý (1); câu đúng/sai |
| B | 100 | 100 | 100 | 100% | Đạt | Không |

### 6.4 Kho câu bổ trợ

Câu dùng cho bổ trợ và kiểm tra lại phải thoả cả năm điều kiện:

1. đã được giảng viên duyệt;
2. cùng LO;
3. **chưa từng nằm trong đề có chế độ Kiểm tra**, để câu thi không lộ qua bổ trợ (Georgiadou et al., 2007);
4. sinh viên chưa gặp. Câu trùng nội dung (cùng văn bản sau khi chuẩn hoá) coi là một câu, vì ngân hàng hiện có câu lặp lại với nhãn khác nhau;
5. không phải câu của bài gốc.

Trước khi giảng viên mở bài bổ trợ, hệ thống đếm số câu dùng được theo LO và cảnh báo LO nào có dưới 3 câu: 2 câu luyện và 1 câu kiểm tra lại.

---

## 7. Bộ bổ trợ và kiểm tra lại

### 7.1 Nội dung cho mỗi LO chưa đạt

Thứ tự cố định, giống nhau với mọi sinh viên, chỉ khác nội dung:

1. **Chỗ bạn hụt.**
    - Ý rubric chưa đạt: nhận xét của ý đó, lấy từ lúc chấm, ghi rõ "nhận xét do AI".
    - Câu sai: đáp án đúng và lời giải thích có sẵn của câu.
2. **Đọc lại.** Thẻ bài học của LO, hoặc trang của đoạn nguồn gắn với câu sai. Nếu trình xem tài liệu của nhóm có đường dẫn mở đúng trang thì dùng; nếu chưa có thì hiện tên tài liệu và số trang.
3. **Luyện k câu**, mặc định k = 2, có phản hồi ngay sau mỗi câu. Ưu tiên:
    - câu sinh từ đúng chỗ hụt của sinh viên, đã duyệt;
    - câu cùng mức Bloom với câu sai. Nhãn Bloom hiện chỉ là mức được yêu cầu lúc sinh, chưa được kiểm tra lại, nên chỉ dùng để ưu tiên, không dùng để loại câu;
    - khác loại câu với nhau.
4. **Kiểm tra lại 1 câu**, mở sau bước 3. Cùng LO, khác mọi câu đã gặp, ưu tiên cùng loại và cùng mức Bloom với câu sai. Không có phản hồi trước khi nộp.

LO không còn đủ câu trong kho thì chỉ có bước 1–2, kèm dòng "câu luyện sẽ có khi giảng viên duyệt câu mới".

### 7.2 Kết quả của kiểm tra lại

| Kết quả | Trạng thái LO | Việc tiếp theo |
|---|---|---|
| Đúng | Đã khắc phục | Không |
| Sai | Cần hỗ trợ | Vào danh sách của giảng viên; sinh viên vẫn được luyện thêm nếu kho còn câu |
| Câu tự luận đang chờ chấm | Chờ chấm | Cập nhật khi chấm xong |

Một câu là bằng chứng yếu. "Đã khắc phục" có nghĩa là làm đúng một câu mới của LO đó, không có nghĩa là đã thạo. Báo cáo cho giảng viên ghi đúng như vậy. Giảng viên có thể tăng số câu kiểm tra lại lên 2.

### 7.3 Điểm

Bài "Bổ trợ sau bài X" là một bài tập riêng trong Canvas. Giảng viên chọn một trong hai cách:

- **Không chấm điểm.**
- **Điểm hoàn thành** (mặc định): 100 khi sinh viên làm xong mọi LO được giao, đúng hay sai đều được; sinh viên đạt mọi LO thì tự động được 100.

Điểm của bài gốc không bao giờ bị đổi. Guskey (2010) đề xuất "cơ hội thứ hai": người đạt ở lần kiểm tra lại được công nhận như người đạt lần đầu. Cách này tạo động lực, nhưng đổi điểm bài gốc là chính sách của giảng viên và nhà trường, nên để ngoài phạm vi và hỏi ý kiến thầy (Q2).

### 7.4 Giao diện cho sinh viên

```text
┌ Bổ trợ sau Kiểm tra chương 1 ──────────────────────────────────┐
│ L.O.1.1   Chưa đạt                                             │
│ 1. Chỗ bạn hụt                                                 │
│    · Câu tự luận: bạn nêu đúng quy mô, đa dạng và mục đích     │
│      rút ra giá trị, nhưng chưa nói vì sao công nghệ CSDL      │
│      thông thường không xử lý được.         (nhận xét do AI)   │
│    · Câu đúng/sai "…": đáp án là Sai, vì …                     │
│ 2. Đọc lại: thẻ "{tiêu đề thẻ}" · trang {p} của "{tài liệu}"   │
│ 3. Luyện 2 câu                                     [Bắt đầu]   │
│ 4. Kiểm tra lại 1 câu                          (mở sau bước 3) │
│                                                                │
│ L.O.1.2   Đạt                                                  │
└────────────────────────────────────────────────────────────────┘
```

Trang chỉ ghi trạng thái (Đạt, Chưa đạt, Đã khắc phục, Cần hỗ trợ), không ghi phần trăm, để sinh viên không nhầm với điểm. Trang kết quả của bài gốc có thêm một dòng dẫn sang bài bổ trợ.

---

## 8. Sinh câu bổ trợ nhắm chỗ hụt

### 8.1 Gộp chỗ hụt của lớp

Sau khi có kết quả chẩn đoán, báo cáo lớp đếm số sinh viên hụt theo từng chỗ:

- với câu tự luận: theo (LO, ý rubric);
- với câu khác: theo (LO, câu), kèm phương án sai được chọn nhiều nhất.

Danh sách sắp theo số sinh viên. Mỗi dòng ghi thêm số câu còn trong kho cho LO đó.

### 8.2 Khi nào sinh

Giảng viên chọn các chỗ hụt cần sinh câu và bấm "Sinh câu bổ trợ". Hệ thống đề xuất sẵn những chỗ hụt có ít nhất 2 sinh viên và LO có dưới 3 câu trong kho. Mặc định 3 câu cho mỗi chỗ hụt.

Sinh theo chỗ hụt của cả lớp, không theo từng sinh viên, nên mỗi chỗ hụt chỉ tốn một yêu cầu sinh và một lượt duyệt. Với 5 chỗ hụt, giảng viên duyệt 15 câu, và các câu này dùng được cho mọi sinh viên có cùng chỗ hụt.

### 8.3 Nội dung yêu cầu sinh

| Trường | Nội dung |
|---|---|
| LO | LO của chỗ hụt |
| Chỗ hụt | Văn bản của ý rubric bị hụt; hoặc câu bị sai và phương án sai được chọn nhiều nhất |
| Đoạn nguồn | Các đoạn nguồn của câu gốc |
| Loại câu, mức Bloom | Mặc định theo câu gốc; giảng viên đổi được |
| Ràng buộc | Không chép câu gốc; chống trùng với câu gốc và câu trong kho |

Câu sinh ra đi qua pipeline sinh câu hiện có, gồm bước AI kiểm tra đáp án với tài liệu, rồi vào hàng đợi duyệt với nhãn "bổ trợ: {chỗ hụt}". Giảng viên duyệt, sửa hoặc từ chối như mọi câu khác. Các cải tiến trong thiết kế sinh câu đúng yêu cầu (trích nguồn, giám khảo hai lượt, phương án nhiễu gắn hiểu lầm) áp dụng luôn cho câu bổ trợ.

### 8.4 Không làm

- Không sinh câu riêng cho từng sinh viên ngay lúc họ làm bổ trợ: câu chưa qua duyệt, và tỉ lệ lỗi ban đầu của LLM đáng kể (Pardos & Bhandari, 2024).
- Không để LLM viết lời giảng hay trò chuyện tự do với sinh viên trong bổ trợ. AI không ràng buộc có thể làm điểm luyện tập tăng nhưng điểm thi giảm (Bastani et al., 2025). Nhận xét duy nhất do LLM viết là nhận xét theo ý lúc chấm, đã có sẵn.

---

## 9. Báo cáo cho giảng viên

Một trang cho mỗi bài gốc:

1. **Bảng LO × sinh viên.** Mỗi ô: Đạt, Chưa đạt, Đã khắc phục, Cần hỗ trợ, hoặc Chưa làm bổ trợ.
2. **Chỗ hụt phổ biến** (mục 8.1), mỗi dòng kèm 2–3 câu trả lời mẫu và nút sinh câu.
3. **Cần hỗ trợ.** Sinh viên kiểm tra lại vẫn sai, kèm LO và các lượt làm liên quan.
4. **Thống kê câu**, khi câu có ít nhất 20 lượt làm (các ngưỡng ở đây là giá trị mặc định):
    - tỉ lệ đúng (độ khó);
    - độ phân biệt: tương quan giữa điểm câu và điểm phần còn lại của bài;
    - tỉ lệ chọn từng phương án;
    - cờ "nên xem lại" khi: tỉ lệ đúng dưới 20% hoặc trên 95%, độ phân biệt âm, hoặc có phương án sai không ai chọn.

Thống kê áp dụng cho mọi câu, kể cả câu do AI sinh. Đây là cách kiểm tra câu sinh bằng dữ liệu thật, vì nhãn độ khó do LLM gán không đáng tin (arXiv:2609.27063). Nó cũng lấp ô "sau khi sinh viên làm bài" còn trống trong thiết kế sinh câu đúng yêu cầu. Với lớp vài chục sinh viên, các con số còn dao động nhiều, nên hệ thống chỉ gắn cờ để giảng viên xem, không tự loại câu.

```text
┌ Kiểm tra chương 1 · {n} sinh viên đã nộp ──────────────────────────────┐
│ Chỗ hụt phổ biến                           Số SV   Kho                 │
│ L.O.1.1 · ý "giới hạn của CSDL tiêu chuẩn"  {a}    2 câu  [Sinh câu]   │
│ L.O.1.2 · câu "…", hay chọn phương án C     {b}    5 câu               │
│                                                                        │
│ Cần hỗ trợ: {c} sinh viên                                  [Xem]       │
│ Câu nên xem lại: {d} câu                                   [Xem]       │
└────────────────────────────────────────────────────────────────────────┘
```

Giáo viên dùng bảng điều khiển rất khác nhau (Molenaar & Knoop-van Campen, 2019), nên mỗi mục trong báo cáo dẫn tới một việc cụ thể: sinh câu, xem bài của sinh viên, sửa câu.

---

## 10. Kiểm soát chất lượng

| Chỗ dùng LLM | Trạng thái | Kiểm soát |
|---|---|---|
| Chấm tự luận theo từng ý | Đã có | Mỗi ý chỉ một nhãn đạt/chưa đạt, vì với nhãn nhị phân LLM khớp với người tốt hơn nhãn chia mịn (Deng et al., 2025); bài làm đặt giữa hai mốc phân cách và chỉ coi là dữ liệu, để chống cài lệnh vào bài (Milani et al., 2025); lỗi thì chuyển giảng viên chấm, không cho 0 điểm; nhận xét ghi "do AI"; giảng viên chấm lại được |
| Sinh câu bổ trợ | Mới | Giảng viên chọn chỗ hụt; AI kiểm tra đáp án với tài liệu; giảng viên duyệt trước khi sinh viên thấy; thống kê câu sau khi dùng |
| Quyết định đạt/chưa đạt, chọn câu | Không dùng LLM | Code, theo quy tắc ở mục 6 và 7 |

Chẩn đoán sai có hai hướng. Giao bổ trợ cho người đã nắm thì tốn vài phút. Bỏ sót người chưa nắm thì người đó không được hỗ trợ ở vòng này, nhưng vẫn có đáp án và lời giải thích như hiện nay. Không hướng nào làm đổi điểm bài gốc.

---

## 11. Thay đổi trong hệ thống

| Phần | Thay đổi | Giai đoạn |
|---|---|---|
| worker, chấm tự luận | Lưu kết quả từng ý (đạt hay chưa, nhận xét) thay vì chỉ điểm tổng. Phần chấm bài luận qua Canvas đã lưu điểm từng tiêu chí, có thể làm theo cách đó | 0 |
| Cơ sở dữ liệu | Thêm kết quả từng ý và nguồn của lượt làm (bài gốc, bổ trợ, kiểm tra lại); cài đặt của bài bổ trợ (θ, k, số câu kiểm tra lại, cách tính điểm) | 0–2 |
| core-api | Module bổ trợ: chẩn đoán, kho câu bổ trợ, bộ bổ trợ, kiểm tra lại, báo cáo lớp, thống kê câu, gộp chỗ hụt | 1–3 |
| LTI | Loại liên kết mới "bổ trợ" trong Deep Linking, trỏ tới bài gốc | 2 |
| Gửi điểm (AGS) | Điểm hoàn thành cho bài bổ trợ; không đụng tới điểm bài gốc | 2 |
| contracts | Yêu cầu sinh câu có thêm thông tin chỗ hụt | 3 |
| web | Dòng dẫn sang bổ trợ ở trang kết quả; trang bổ trợ; báo cáo lớp; nhãn "bổ trợ" trong hàng đợi duyệt | 1–3 |

Phần trình bày câu và nhập đáp án cho 5 loại câu đã có, trang bổ trợ dùng lại.

---

## 12. Đánh giá

### 12.1 Câu hỏi nghiên cứu

| # | Câu hỏi | Cách trả lời |
|---|---|---|
| RQ1 | Chẩn đoán theo ý của AI khớp với người chấm đến mức nào? | Hai người chấm độc lập trên một mẫu bài thật; so AI với người |
| RQ2 | Câu sinh từ chỗ hụt có dùng được và có nhắm đúng ý bị hụt không? | Giảng viên đánh giá khi duyệt; thống kê câu sau khi dùng |
| RQ3 | Bộ bổ trợ có giúp sinh viên làm đúng LO đó ở lần kiểm tra lại không? | Thử nghiệm nhỏ, chia ngẫu nhiên theo LO trong từng sinh viên |
| RQ4 | Sinh viên có làm bổ trợ không; giảng viên dùng báo cáo thế nào? | Nhật ký sử dụng; phỏng vấn ngắn giảng viên |

### 12.2 RQ1: đồng thuận khi chấm từng ý

- **Mẫu:** khoảng 150–200 cặp (câu trả lời, ý rubric) từ các câu tự luận ngắn, tuỳ lượng bài có được.
- **Người chấm:** hai người chấm độc lập, ví dụ giảng viên hoặc trợ giảng và em, mỗi ý ghi đạt hay chưa đạt. Có thể dùng chung người chấm với phần kiểm chứng của thiết kế sinh câu đúng yêu cầu.
- **Chỉ số:** tỉ lệ khớp và hệ số kappa của Cohen, giữa hai người và giữa AI với từng người. Báo cáo theo từng loại ý (nêu định nghĩa, nêu ví dụ, giải thích).
- **Quyết định:** nếu kappa AI–người thấp hơn kappa người–người quá 0.1 (ngưỡng em đề xuất), chẩn đoán chỉ dùng các câu tự luận đã được giảng viên xác nhận.
- **Tham chiếu:** các nghiên cứu trước cho mức đồng thuận rất khác nhau, từ yếu (Flodén, 2025) đến khá (Jiang & Bosch, 2024). Vì vậy phải đo trên dữ liệu của môn này.

### 12.3 RQ2: chất lượng câu sinh từ chỗ hụt

- Với mỗi chỗ hụt được chọn, sinh 3 câu nhắm chỗ hụt, và 3 câu thường cùng LO, không có thông tin chỗ hụt, để so sánh.
- Giảng viên đánh giá từng câu, không biết câu thuộc nhóm nào:
    - dùng được ngay / sửa nhỏ / bỏ;
    - câu có kiểm tra đúng ý bị hụt không: có / một phần / không.
- Sau khi sinh viên làm: độ khó và độ phân biệt của câu bổ trợ, so với câu do giảng viên duyệt từ trước.

### 12.4 RQ3: thử nghiệm nhỏ với sinh viên thật

**Thiết kế.** Mỗi cặp (sinh viên, LO chưa đạt) được chia ngẫu nhiên vào một trong hai nhóm:

- **Bổ trợ ngay:** làm bộ bổ trợ đầy đủ rồi kiểm tra lại.
- **Bổ trợ sau:** chỉ có những gì trang kết quả đã hiện (điểm, đáp án, lời giải thích, nhận xét theo ý), làm kiểm tra lại, sau đó mới được bộ bổ trợ.

Như vậy thử nghiệm đo phần bộ bổ trợ thêm vào (đọc lại, câu luyện, câu nhắm chỗ hụt), không đo tác dụng của việc cho xem đáp án.

Kết quả đo là tỉ lệ đúng ở câu kiểm tra lại; trong thử nghiệm dùng 2 câu kiểm tra lại cho mỗi LO để bớt nhiễu, nên kho cần ít nhất 4 câu cho mỗi LO của chương thử nghiệm. Nếu có bài kiểm tra sau đó cùng LO, dùng thêm kết quả đó.

**Vì sao chia theo LO trong từng sinh viên.**
- Mỗi sinh viên vừa có LO được bổ trợ ngay, vừa có LO bổ trợ sau, nên khác biệt giữa người giỏi và người yếu không lẫn vào kết quả.
- Không so người tự làm bổ trợ với người không làm, vì người tự chọn vốn khác (Thomas et al., 2025).
- Không so với khoá trước, vì hai khoá khác nhau nhiều mặt (Hinkle, 2023).
- Ai cũng được bổ trợ mọi LO, chỉ khác thời điểm. Không ảnh hưởng điểm bài gốc.

**Quy mô và phân tích.** Ví dụ, 20 sinh viên, mỗi người trung bình 2–3 LO chưa đạt, cho khoảng 40–60 cặp. Báo cáo chênh lệch tỉ lệ đúng giữa hai nhóm, kèm khoảng tin cậy 95% có tính đến việc nhiều cặp thuộc cùng một sinh viên. Với quy mô này, kết quả là thử nghiệm minh hoạ, không đủ để kết luận thống kê.

**Giới hạn.** Học một LO có thể giúp LO khác, làm khác biệt giữa hai nhóm nhỏ đi. Kiểm tra lại đo ngay sau bổ trợ, không đo ghi nhớ lâu dài.

### 12.5 RQ4: mức sử dụng

- Tỉ lệ sinh viên mở bài bổ trợ, làm xong, và thời gian làm, từ nhật ký.
- Phỏng vấn ngắn 1–2 giảng viên sau khi dùng báo cáo lớp: mục nào dẫn tới việc gì, mục nào thừa.

### 12.6 Kiểm thử phần tất định

| Phần | Kiểm thử |
|---|---|
| Chẩn đoán | Tính tay ở mục 6.3; LO có câu đang chờ chấm thì chưa chẩn đoán; dùng kết quả giảng viên chấm lại |
| Thời điểm mở | Đề Kiểm tra chưa mở đáp án thì không có bổ trợ |
| Kho câu bổ trợ | Loại câu từng ở đề Kiểm tra, câu của bài gốc, câu đã gặp, câu trùng văn bản |
| Kiểm tra lại | Câu khác mọi câu đã gặp; trạng thái đúng theo bảng ở mục 7.2 |
| Điểm | Điểm hoàn thành chỉ gửi cho bài bổ trợ; điểm bài gốc không đổi |
| Gộp chỗ hụt | Đếm đúng theo (LO, ý) và (LO, câu) |
| Thống kê câu | So với tính tay trên một bộ lượt làm nhỏ |

---

## 13. Lộ trình

Chưa đặt mốc ngày vì chưa có lịch bảo vệ. Thời lượng là ước lượng thô cho một người làm; tổng cộng khoảng 7–8 tuần.

| Giai đoạn | Việc | Thời lượng ước tính | Đầu ra kiểm chứng được |
|---|---|---|---|
| **0. Nền** | Lưu kết quả từng ý khi chấm tự luận; ghi nguồn lượt làm; lọc kho câu bổ trợ (loại câu thi, gộp câu trùng văn bản); đếm kho theo LO | 1 tuần | Migration và test; bảng đếm kho của môn thử nghiệm |
| **1. Chẩn đoán và báo cáo lớp** | Hàm chẩn đoán; báo cáo lớp (LO × sinh viên, chỗ hụt phổ biến, thống kê câu); dòng chỗ hụt trên trang kết quả | 1.5 tuần | Test theo mục 12.6; báo cáo chạy với dữ liệu thật |
| **2. Bổ trợ và kiểm tra lại** | Trang bổ trợ; chọn câu luyện và câu kiểm tra lại; bài tập "Bổ trợ" qua Deep Linking; điểm hoàn thành; cài đặt; danh sách cần hỗ trợ | 2 tuần | Chạy được trọn vòng trên Canvas |
| **3. Sinh câu nhắm chỗ hụt** | Gộp chỗ hụt; yêu cầu sinh câu kèm chỗ hụt; nhãn trong hàng đợi duyệt; cập nhật contract | 1 tuần | Câu sinh từ chỗ hụt thật vào hàng đợi duyệt |
| **4. Đánh giá** | RQ1–RQ4; viết kết quả. Thử nghiệm với sinh viên chạy song song 1–2 tuần | 2 tuần | Bảng kết quả RQ1–RQ4 |
| **Mở rộng** (nếu còn thời gian) | Cơ hội thứ hai thay một phần điểm bài gốc; mức nắm LO qua nhiều bài; chẩn đoán từ phương án nhiễu gắn hiểu lầm; bổ trợ cho bài luận nộp file qua Canvas | Tuỳ phần | Tuỳ phần |

---

## 14. Rủi ro

| # | Rủi ro | Cách xử lý |
|---|---|---|
| R1 | Sinh viên không làm bổ trợ | Bài tập Canvas có hạn nộp và tuỳ chọn điểm hoàn thành; đo tỉ lệ làm (RQ4) |
| R2 | AI chấm sai ý làm chẩn đoán sai | Nhận xét ghi "do AI"; giảng viên chấm lại được; đo đồng thuận (RQ1); chẩn đoán không đổi điểm |
| R3 | Kho mỏng: LO hết câu luyện | Đếm trước ở giai đoạn 0; sinh câu theo chỗ hụt; LO thiếu câu vẫn có chỗ hụt và chỗ đọc lại |
| R4 | Câu sinh ra sai hoặc kém | Kiểm tra tự động; giảng viên duyệt; thống kê câu và cờ "nên xem lại" |
| R5 | Lộ câu thi | Bổ trợ mở sau khi đáp án đã mở; kho loại câu từng ở đề Kiểm tra |
| R6 | Bài gốc có ít câu mỗi LO, chẩn đoán nhiễu | Nhãn "ít bằng chứng"; θ chỉnh được; khi soạn đề, hiện số câu mỗi LO |
| R7 | Không có lớp thật để thử nghiệm | RQ1, RQ2 làm được với dữ liệu sẵn có và người chấm; RQ3 cần một lớp (Q5) |
| R8 | Nhãn Bloom chưa được kiểm tra | Chỉ dùng để ưu tiên khi chọn câu, không dùng để quyết định |
| R9 | Sinh viên cài lệnh vào bài làm để được điểm cao | Mốc phân cách đã có; giảng viên chấm lại được; chẩn đoán không đổi điểm |
| R10 | Đụng phần của thành viên khác | Chỉ nối qua đường dẫn; trang bổ trợ và báo cáo nằm trong phần của em |

---

## 15. Câu hỏi xin ý kiến thầy

| # | Câu hỏi | Đề xuất của em |
|---|---|---|
| Q1 | Hướng bổ trợ sau kiểm tra, thay cho Learning Agent tự lên lộ trình, có phù hợp với đề tài không? | Có, vì bám vào bài giảng viên đã giao và đặt GenAI ở giữa luồng (mục 4.2) |
| Q2 | Bài bổ trợ có tính điểm không? | Điểm hoàn thành, không đổi điểm bài gốc; "cơ hội thứ hai" để mở rộng nếu thầy thấy cần |
| Q3 | Câu do AI sinh có bắt buộc giảng viên duyệt trước khi sinh viên thấy không? | Có |
| Q4 | Đánh giá gồm đồng thuận chấm, chất lượng câu sinh và thử nghiệm ngẫu nhiên theo LO, có đủ cho đồ án không? | Đủ; thử nghiệm là minh hoạ, không kết luận thống kê |
| Q5 | Có lớp hoặc môn nào để thử nghiệm, và ai có thể làm người chấm thứ hai cho RQ1? | Dùng chung người chấm với phần kiểm chứng sinh câu đúng yêu cầu |
| Q6 | Thử nghiệm với sinh viên cần thủ tục đồng ý thế nào? | Phiếu đồng ý; dữ liệu ẩn danh; không ảnh hưởng điểm |

---

## Tài liệu tham khảo

Danh mục đầy đủ và bảng truy vết ở [bo-tro-sau-kiem-tra-tong-quan-tai-lieu.md](bo-tro-sau-kiem-tra-tong-quan-tai-lieu.md). Dưới đây là các tài liệu được trích trong báo cáo này.

- Adesope, O. O., Trevisan, D. A., & Sundararajan, N. (2017). Rethinking the use of tests: A meta-analysis of practice testing. *Review of Educational Research*, 87(3), 659–701. https://doi.org/10.3102/0034654316689306
- Bastani, H., et al. (2025). Generative AI without guardrails can harm learning: Evidence from high school mathematics. *PNAS*, 122(26), e2422633122. https://doi.org/10.1073/pnas.2422633122
- Basu, S., Jacobs, C., & Vanderwende, L. (2013). Powergrading: A clustering approach to amplify human effort for short answer grading. *Transactions of the Association for Computational Linguistics*, 1, 391–402. https://doi.org/10.1162/tacl_a_00236
- Bhandari, S., Liu, Y., Kwak, Y., & Pardos, Z. A. (2024). Evaluating the psychometric properties of ChatGPT-generated questions. *Computers and Education: Artificial Intelligence*, 7, 100284. https://doi.org/10.1016/j.caeai.2024.100284
- Bloom, B. S. (1968). Learning for mastery. *Evaluation Comment*, 1(2).
- Butler, A. C., & Roediger, H. L. (2008). Feedback enhances the positive effects and reduces the negative effects of multiple-choice testing. *Memory & Cognition*, 36(3), 604–616. https://doi.org/10.3758/MC.36.3.604
- Deng, H., Farber, C., Lee, J., & Tang, D. (2025). Rubric-conditioned LLM grading: Alignment, uncertainty, and robustness [Preprint]. arXiv:2601.08843.
- Flodén, J. (2025). Grading exams using large language models: A comparison between human and AI grading of exams in higher education using ChatGPT. *British Educational Research Journal*, 51(1), 201–224. https://doi.org/10.1002/berj.4069
- Georgiadou, E., Triantafillou, E., & Economides, A. A. (2007). A review of item exposure control strategies for computerized adaptive testing developed from 1983 to 2005. *Journal of Technology, Learning, and Assessment*, 5(8). https://www.ejournals.bc.edu/index.php/jtla/article/view/1647
- Guskey, T. R. (2010). Lessons of mastery learning. *Educational Leadership*, 68(2), 52–57. https://www.ascd.org/el/articles/lessons-of-mastery-learning
- Haladyna, T. M., & Rodriguez, M. C. (2013). *Developing and validating test items*. Routledge.
- Hinkle, J. F. (2023). Personalization and learning outcome in a nursing pathophysiology and pharmacology course: Canvas Mastery adoption pilot study. *SAGE Open Nursing*, 9. https://doi.org/10.1177/23779608231186030
- Isley, C., et al. (2026). Assessing the quality of AI-generated exams: A large-scale field study. In *AAAI 2026*. https://doi.org/10.1609/aaai.v40i45.41205
- Jiang, L., & Bosch, N. (2024). Short answer scoring with GPT-4. In *L@S '24* (pp. 438–442). ACM. https://doi.org/10.1145/3657604.3664685
- Kibble, J. (2007). Use of unsupervised online quizzes as formative assessment in a medical physiology course: Effects of incentives on student participation and performance. *Advances in Physiology Education*, 31(3), 253–260. https://doi.org/10.1152/advan.00027.2007
- Kluger, A. N., & DeNisi, A. (1996). The effects of feedback interventions on performance: A historical review, a meta-analysis, and a preliminary feedback intervention theory. *Psychological Bulletin*, 119(2), 254–284. https://doi.org/10.1037/0033-2909.119.2.254
- Kulik, C.-L. C., Kulik, J. A., & Bangert-Drowns, R. L. (1990). Effectiveness of mastery learning programs: A meta-analysis. *Review of Educational Research*, 60(2), 265–299. https://doi.org/10.3102/00346543060002265
- Milani, A., Franzoni, V., Florindi, E., Omarbekova, A., Bekmanova, G., & Yergesh, B. (2025). When AI is fooled: Hidden risks in LLM-assisted grading. *Education Sciences*, 15(11), 1419. https://doi.org/10.3390/educsci15111419
- Molenaar, I., & Knoop-van Campen, C. A. N. (2019). How teachers make dashboard information actionable. *IEEE Transactions on Learning Technologies*, 12(3), 347–355. https://doi.org/10.1109/TLT.2018.2851585
- Morphew, J. W., Silva, M., Herman, G., & West, M. (2020). Frequent mastery testing with second-chance exams leads to enhanced student learning in undergraduate engineering. *Applied Cognitive Psychology*, 34(1), 168–181. https://doi.org/10.1002/acp.3605
- Pardos, Z. A., & Bhandari, S. (2024). ChatGPT-generated help produces learning gains equivalent to human tutor-authored help on mathematics skills. *PLOS ONE*, 19(5), e0304013. https://doi.org/10.1371/journal.pone.0304013
- *Student use of LLMs and the limits of AI-generated question difficulty in data science courses* (2026) [Preprint]. arXiv:2609.27063.
- Thomas, D. R., Borchers, C., Bhushan, S., Gatz, E., Gupta, S., & Koedinger, K. R. (2025). LLM-generated feedback supports learning if learners choose to use it [Preprint]. arXiv:2506.17006.
- Van der Kleij, F. M., Feskens, R. C. W., & Eggen, T. J. H. M. (2015). Effects of feedback in a computer-based learning environment on students' learning outcomes: A meta-analysis. *Review of Educational Research*, 85(4), 475–511. https://doi.org/10.3102/0034654314564881
