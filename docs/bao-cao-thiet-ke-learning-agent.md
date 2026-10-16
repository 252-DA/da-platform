# Báo cáo thiết kế: Learning Agent cho luyện tập thích ứng

**Đề tài:** Hệ thống LMS tự động tạo Micro-Content & Quiz bằng Generative AI (DA Platform)
**Ngày:** 16/10/2026
**Trạng thái:** phương án đã cân nhắc, không chọn. Đã thay bằng [bao-cao-thiet-ke-bo-tro-sau-kiem-tra.md](bao-cao-thiet-ke-bo-tro-sau-kiem-tra.md) ngày 16/10/2026; lý do ở mục 4.2 của báo cáo mới. Giữ lại để tham khảo.
**Tài liệu kèm:** [learning-agent-tong-quan-tai-lieu.md](learning-agent-tong-quan-tai-lieu.md) tổng hợp 91 tài liệu liên quan và bảng truy vết từ quyết định thiết kế về căn cứ.

---

## Tóm tắt

- **Vấn đề.** Hệ thống đã sinh được câu hỏi theo LO và chấm được tự luận ngắn theo từng ý của rubric. Tuy vậy, mọi sinh viên vẫn làm cùng một đề. Hệ thống không dùng lịch sử làm bài để quyết định sinh viên nên làm gì tiếp, và bỏ đi thông tin sinh viên hụt ý nào.
- **Đề xuất.** Xây một Learning Agent đóng vai **vòng ngoài** của hệ thống dạy học thông minh (VanLehn, 2006). Sau mỗi câu trả lời, Agent cập nhật mức thành thạo của sinh viên theo từng LO, rồi chọn một trong 8 hành động: luyện tiếp, xem lại nguồn, ôn bài đến hạn, sang LO khác, báo giảng viên, v.v. Mỗi đề xuất kèm lý do đọc được.
- **Mô hình người học.** Dùng Bayesian Knowledge Tracing (BKT) với tham số cố định và xác suất đoán theo loại câu. Lý do: chưa có dữ liệu để huấn luyện mô hình phức tạp hơn, và BKT giải thích được cho sinh viên lẫn giảng viên.
- **Vai trò của LLM.** LLM chỉ làm ở những chỗ có kiểm soát: chấm tự luận theo ý (đã có), viết câu hỏi nhắm vào chỗ hụt (mở rộng). Mức thành thạo và hành động tiếp theo do code quyết định. Một biến thể "LLM chọn hành động trong tập hợp lệ" được dùng làm thực nghiệm so sánh.
- **Đánh giá.** Mô phỏng theo ma trận đánh giá vững (Doroudi et al., 2017): 6 chính sách × 3 mô hình người học. Đối chứng gồm cả các tiêu chí đơn giản mà tài liệu cho là mạnh (3 câu đúng liên tiếp, trung bình trượt), không chỉ đề cố định. Chỉ số chính: số câu đến khi thật sự nắm, tỉ lệ "thạo giả", số câu luyện thừa, độ công bằng giữa người học nhanh và chậm. Nếu kịp, thử nghiệm nhỏ với 5–10 sinh viên.
- **Phạm vi đề xuất cho đồ án:** giai đoạn 0–3, khoảng 8–9 tuần (mục 13). Tách mức Bloom để ở giai đoạn mở rộng, vì phụ thuộc phần kiểm tra mức Bloom chưa làm. Sinh câu nhắm chỗ hụt cũng để ở giai đoạn mở rộng, vì lý do khác: câu sinh ra phải chờ giảng viên duyệt nên không dùng được ngay trong phiên, và ở mức LO, mô phỏng không đo được giá trị của việc nhắm đúng ý bị hụt. Phần này nối Agent với phần sinh câu bằng GenAI, nên em xin ý kiến thầy có cần đưa vào phạm vi không (Q7).

---

## 1. Vấn đề

### 1.1 Hệ thống hiện có

- Giảng viên sinh câu hỏi từ tài liệu môn học, chọn LO, mức Bloom và một trong 5 loại câu: trắc nghiệm một đáp án, trắc nghiệm nhiều đáp án, đúng/sai, điền khuyết, tự luận ngắn. Câu sinh ra chờ giảng viên duyệt.
- Giảng viên gom câu thành đề, chế độ Luyện tập hoặc Kiểm tra, và mở trong Canvas qua LTI 1.3. Điểm gửi về sổ điểm Canvas.
- Câu tự luận ngắn được LLM chấm theo rubric: LLM xét từng ý đạt hay chưa, kèm nhận xét; code tính điểm từ số ý đạt.
- Mỗi LO có các thẻ bài học (lesson card). Tài liệu nguồn được chia đoạn, mỗi đoạn biết số trang.

### 1.2 Một ví dụ

Câu tự luận ngắn trong môn Dữ liệu lớn, thuộc L.O.1.1:

> **Câu:** Giải thích ngắn gọn khái niệm dữ liệu lớn dựa trên định nghĩa trong tài liệu.
> **Rubric:** (1) giới hạn của công nghệ CSDL tiêu chuẩn; (2) quy mô, đa dạng và phức tạp; (3) mục đích trích xuất giá trị.

Sinh viên A trả lời: "Dữ liệu lớn là dữ liệu có quy mô lớn, đa dạng và phức tạp, cần phân tích để rút ra giá trị." Câu trả lời đạt ý (2) và (3), chưa đạt ý (1).

**Hiện nay**
- Hệ thống lưu điểm 67/100 và một đoạn nhận xét chung. Kết luận "ý (1) chưa đạt" đã được LLM tính ra nhưng không được lưu.
- Lần sau, A và B (người đạt cả 3 ý) nhận cùng một đề, cùng số câu.
- Không có gì hướng A quay lại phần định nghĩa trong tài liệu.
- Nếu A sai liên tiếp nhiều câu của L.O.1.1, giảng viên chỉ thấy điểm tổng.

**Khi có Agent**
- Hệ thống lưu kết quả từng ý. Mức nắm L.O.1.1 ước tính của A giảm.
- Agent đề xuất A làm thêm một câu về L.O.1.1, kèm nhận xét của ý (1).
- Nếu A sai thêm, Agent đề xuất xem lại thẻ bài học hoặc trang tài liệu có định nghĩa, rồi làm tiếp.
- Khi A đạt ngưỡng, Agent lên lịch ôn L.O.1.1 sau 1 ngày, rồi 3 ngày, 7 ngày.
- B sang LO tiếp theo ngay, không phải làm thêm câu thừa.
- Nếu A vẫn không đạt sau nhiều lần, giảng viên được báo.

### 1.3 Ba khoảng trống

1. **Không thích ứng.** Mọi sinh viên làm cùng đề, cùng số câu. Hệ thống không dùng lịch sử làm bài để chọn việc tiếp theo.
2. **Mất thông tin chẩn đoán.** Hệ thống biết sinh viên thiếu bao nhiêu điểm nhưng không giữ lại sinh viên thiếu ý nào.
3. **Không có ôn và không phát hiện sinh viên bị kẹt.** Kiến thức đã đạt không được ôn lại theo thời gian. Sinh viên làm mãi không đạt cũng không ai biết.

---

## 2. Mục tiêu và phạm vi

**Mục tiêu**

| # | Mục tiêu | Đo bằng |
|---|---|---|
| M1 | Ước lượng mức thành thạo theo LO cho từng sinh viên | Kiểm thử mô hình; mô phỏng: tỉ lệ thạo giả |
| M2 | Sau mỗi câu trả lời, chọn một hoạt động tiếp theo, kèm lý do đọc được | Mô phỏng: số câu đến khi nắm, số câu luyện thừa |
| M3 | Lên lịch ôn; phát hiện sinh viên bị kẹt và báo giảng viên | Mô phỏng có quên; độ chính xác của cờ báo |
| M4 | Chứng minh chính sách tốt hơn các đối chứng hợp lý, không chỉ hơn đề cố định | Ma trận đánh giá vững (mục 12) |

**Không làm**
- Không thay đề Kiểm tra của giảng viên. Hoạt động do Agent chọn là luyện tập, không gửi điểm về Canvas.
- Không huấn luyện mô hình học sâu, vì không đủ dữ liệu.
- Không làm hệ nhiều agent, không làm khung chat.
- Không sửa phần video, trình xem tài liệu và trợ giảng chat. Các phần này do thành viên khác làm; Agent chỉ nối với chúng qua đường dẫn và RPC.
- Không để LLM quyết định mức thành thạo.

---

## 3. Learning Agent là gì

**Định nghĩa dùng trong đồ án.** Learning Agent là một vòng lặp chạy sau mỗi lượt làm bài:

1. **Quan sát:** đọc kết quả các lượt làm bài của sinh viên.
2. **Cập nhật:** tính lại mức thành thạo của sinh viên theo từng LO.
3. **Chọn:** chọn một hành động trong tập hành động đóng, dựa trên trạng thái của sinh viên và giới hạn do giảng viên đặt.
4. **Giải thích:** hiển thị lý do cho sinh viên.
5. **Ghi nhận:** lưu quyết định, lý do, và việc sinh viên có làm theo hay không.

Định nghĩa này khớp với định nghĩa agent kinh điển: hệ thống tự hoạt động, quan sát môi trường và hành động để đạt mục tiêu (Wooldridge & Jennings, 1995). Trong hệ thống dạy học thông minh, đây là **vòng ngoài**: chọn bài tập tiếp theo. Vòng trong hỗ trợ từng bước trong một bài và không thuộc phạm vi này (VanLehn, 2006).

Tính "agent" nằm ở bước 3: cùng một thời điểm, hai sinh viên khác nhau nhận hai hành động khác nhau. Nó không nằm ở việc có gọi LLM hay có nhiều agent.

**Khác với trợ giảng chat của nhóm**

| | Trợ giảng chat | Learning Agent |
|---|---|---|
| Kích hoạt | Sinh viên đặt câu hỏi | Sau mỗi câu trả lời, hoặc khi có bài đến hạn ôn |
| Đầu vào | Câu hỏi và tài liệu | Lịch sử làm bài |
| Quyết định | Trả lời thế nào | Làm gì tiếp |
| Bộ nhớ | Lịch sử hội thoại | Mức thành thạo theo LO |

---

## 4. Các lựa chọn thiết kế chính và căn cứ

| Vấn đề | Lựa chọn | Phương án đã cân nhắc | Căn cứ |
|---|---|---|---|
| Mô hình người học | BKT, tham số cố định, xác suất đoán theo loại câu | DKT; Elo/PFA; LLM | DKT cần nhiều dữ liệu (Gervet et al., 2020); BKT mở rộng gần bằng DKT (Khajah et al., 2016); LLM cập nhật mức thạo không nhất quán (Neshaei et al., 2024; Hooshyar et al., 2025); ít dữ liệu thì khó ước lượng tham số (Beck & Chang, 2007) |
| Tiêu chí thành thạo | P(L) ≥ 0.95 và có ít nhất 3 quan sát | 3 câu đúng liên tiếp; trung bình trượt mũ (EMA) | Hai phương án kia dùng làm đối chứng, vì tài liệu cho thấy chúng mạnh (Kelly et al., 2015; Pelánek & Řihák, 2017) |
| Chọn hành động | Planner theo luật, mỗi luật có căn cứ | Học tăng cường; bandit; LLM | RL cho kết quả lẫn lộn và cần nhiều dữ liệu (Doroudi et al., 2019) |
| Lịch ôn | Hộp Leitner | HLR; FSRS | Leitner đơn giản, giải thích được; lịch thích ứng tốt hơn nhưng cần dữ liệu (Settles & Meeder, 2016; Lindsey et al., 2014) |
| Vai trò của LLM | Chấm theo ý, viết câu; LLM chọn hành động chỉ là thực nghiệm | LLM quyết định toàn bộ | LLM đề xuất, bộ kiểm tra quyết định (Kambhampati et al., 2024) |
| Đánh giá | Ma trận chính sách × mô hình người học | Chỉ so với đề cố định | Chính sách phải tốt trên nhiều mô hình người học (Doroudi et al., 2017) |

---

## 5. Kiến trúc

```text
Sinh viên (web /learn, mở từ Canvas qua LTI)
   │ làm câu → SubmitQuiz (nguồn = AGENT, không gửi điểm về Canvas)
   ▼
core-api ── ghi lượt làm
   │          câu tự luận: worker chấm theo từng ý, ghi lại kết quả từng ý
   │
   │ sinh viên mở trang kết quả hoặc trang luyện tập → GetNextActivity
   ▼
[1] Kho luyện tập      lọc câu: đã duyệt, LO đang mở, không thuộc đề Kiểm tra, chưa gặp
[2] Mô hình người học  BKT trên lịch sử lượt làm → mức nắm theo LO           (code)
[3] Planner            luật R0–R6 → MỘT hành động + lý do + lựa chọn khác     (code)
                       biến thể thực nghiệm: LLM chọn trong tập hành động hợp lệ
[4] Công cụ            chọn câu · trỏ về thẻ bài học hoặc trang tài liệu · lịch ôn
                       · báo giảng viên · (mở rộng) yêu cầu sinh câu → worker → hàng đợi duyệt
   │
   ▼
Nhật ký quyết định: hành động, lý do, chính sách đã dùng, sinh viên có làm theo hay không
```

**Bốn quyết định kiến trúc**

1. **Mô hình người học là một hàm thuần trên lịch sử lượt làm.** Bảng trạng thái chỉ là bộ nhớ đệm, xoá đi tính lại được. Hệ quả:
    - không cần trigger khi worker chấm xong tự luận: lần đọc sau tự thấy kết quả mới;
    - đổi tham số thì tính lại cho mọi người, không phải chuyển đổi dữ liệu;
    - bộ mô phỏng gọi đúng hàm đó, nên thứ được đánh giá chính là thứ chạy thật.

    Ở quy mô đồ án (vài chục sinh viên, vài nghìn lượt làm), tính lại khi đọc là đủ nhanh.
2. **Chạy theo yêu cầu, không chạy nền.** Web gọi `GetNextActivity` khi sinh viên mở trang. Không cần hàng đợi hay lịch chạy định kỳ. Bài đến hạn ôn được phát hiện ở lần mở trang kế tiếp.
3. **Mô hình người học và planner nằm trong core-api.** core-api sở hữu cơ sở dữ liệu và module quiz. Thêm module `learning-agent`.
4. **LLM nằm trong worker, đi qua các đường sẵn có.** Chấm tự luận dùng luồng chấm hiện tại. Sinh câu nhắm chỗ hụt dùng luồng sinh câu hiện tại, thêm trường "ý bị hụt"; câu sinh ra vào hàng đợi duyệt như mọi câu khác.

---

## 6. Dữ liệu đầu vào

### 6.1 Quan sát

Mỗi lượt làm bài là một quan sát cho mô hình người học, theo các quy tắc sau:

| Quy tắc | Lý do |
|---|---|
| Lấy lượt làm từ mọi nguồn: đề Luyện tập, đề Kiểm tra, luyện tập do Agent chọn | Thêm dữ liệu; đề Kiểm tra là quan sát đáng tin |
| Chỉ tính **lần đầu** một sinh viên gặp một câu | Đúng ở lần thứ hai có thể chỉ là nhớ đáp án |
| Câu trùng nội dung (cùng văn bản sau khi chuẩn hoá) coi là cùng một câu | Ngân hàng hiện có câu lặp lại với nhãn khác nhau, ví dụ "Kiến trúc Lambda gồm ba lớp nào?" |
| Câu tự luận đang chờ chấm chưa được tính | Chưa có kết quả |
| Câu được giảng viên chấm lại thì dùng kết quả cuối | Kết quả của người có thẩm quyền |
| Giai đoạn theo LO: câu tự luận là **một** quan sát, đúng khi đạt mọi ý | Các ý cùng thuộc một LO; tính mỗi ý một quan sát sẽ đếm trùng |
| Kết quả từng ý vẫn được lưu và dùng cho phản hồi | Dùng để chẩn đoán, chưa dùng để cập nhật mức nắm |

Khi có đơn vị kiến thức dưới LO (giai đoạn mở rộng), mỗi ý rubric gắn với một đơn vị và trở thành một quan sát riêng cho đơn vị đó.

### 6.2 Kho luyện tập

Câu được Agent giao phải thoả cả bốn điều kiện:

1. đã được giảng viên duyệt;
2. thuộc LO mà giảng viên mở cho Agent;
3. **không nằm trong đề có chế độ Kiểm tra**, để sinh viên không gặp câu thi trước khi thi (cùng mục đích với kiểm soát mức lộ câu trong kiểm tra thích ứng, Georgiadou et al., 2007);
4. sinh viên chưa gặp, tính theo nhóm câu trùng nội dung.

Chiều ngược lại: khi giảng viên soạn đề Kiểm tra, hệ thống cho biết câu nào đã được dùng trong luyện tập và bao nhiêu sinh viên đã gặp.

Trước khi bật Agent cho một khoá học, hệ thống đếm số câu dùng được theo LO × loại câu và cảnh báo LO nào có dưới 6 câu.

---

## 7. Mô hình người học

### 7.1 Theo dõi ở mức nào

| Mức | Nguồn | Ưu | Nhược | Giai đoạn |
|---|---|---|---|---|
| LO | Mỗi câu đã gắn LO | Có sẵn, chạy được ngay | Một LO chứa nhiều ý | 1–3 |
| LO × mức Bloom | Mức Bloom của câu và của LO | Phân biệt nhớ lại với vận dụng | Cần nhãn Bloom đúng; chưa có bước kiểm tra | Mở rộng |
| Đơn vị kiến thức | Gắn lúc sinh câu (LLM đề xuất, giảng viên xác nhận) | Đúng ý mà câu kiểm tra | Chưa làm | Mở rộng |

Lý do bắt đầu ở mức LO: nhãn Bloom hiện chỉ là mức được yêu cầu lúc sinh, chưa được kiểm tra lại. Ví dụ, một câu gắn mức "Vận dụng" nhưng chỉ hỏi kích thước dữ liệu của Earthscope là bao nhiêu. Theo dõi theo mức Bloom trên những nhãn như vậy sẽ cho kết luận sai.

### 7.2 Bayesian Knowledge Tracing

BKT (Corbett & Anderson, 1995) giữ một xác suất P(L) rằng sinh viên đã nắm LO. Sau mỗi quan sát, cập nhật theo công thức Bayes:

$$
P(L \mid \text{đúng}) = \frac{P(L)\,(1-S)}{P(L)\,(1-S) + \bigl(1-P(L)\bigr)\,G}
\qquad
P(L \mid \text{sai}) = \frac{P(L)\,S}{P(L)\,S + \bigl(1-P(L)\bigr)\,(1-G)}
$$

Sau đó tính thêm khả năng sinh viên học được nhờ chính lần làm đó:

$$
P(L_{\text{mới}}) = P(L \mid \text{quan sát}) + \bigl(1 - P(L \mid \text{quan sát})\bigr)\,T
$$

**Tham số**

| Tham số | Ý nghĩa | Giá trị khởi đầu | Lý do |
|---|---|---|---|
| P(L₀) | Đã nắm trước khi luyện | 0.2 | Giả định thận trọng cho nội dung mới của môn học |
| T | Học được sau một lần làm | 0.15 | Giá trị khởi đầu; kiểm tra độ nhạy |
| S | Đã nắm mà vẫn sai | 0.1 | Giá trị khởi đầu; kiểm tra độ nhạy |
| G | Chưa nắm mà vẫn đúng | Theo loại câu, bảng dưới | Gần bằng 1/số phương án với câu chọn; gần 0 với câu phải tự viết |

| Loại câu | G | Ghi chú |
|---|---|---|
| Đúng/sai | 0.5 | Hai phương án |
| Trắc nghiệm một đáp án | 0.25 | Bốn phương án |
| Trắc nghiệm nhiều đáp án | 0.1 | Phải chọn đúng cả tập đáp án trong 4–6 phương án |
| Điền khuyết | 0.05 | Tự viết, so khớp với danh sách cách viết chấp nhận |
| Tự luận ngắn | 0.05 | Tự viết, chấm theo rubric |

Xác suất đoán phụ thuộc loại câu là bản đơn giản của ý tưởng tham số theo độ khó câu (KT-IDEM, Pardos & Heffernan, 2011). Đây là giá trị khởi đầu chưa hiệu chỉnh, vì chưa có dữ liệu. Khi đủ dữ liệu, tham số sẽ được ước lượng bằng pyBKT (Badrinath et al., 2021).

**Những con số này nghĩa là gì.** Bắt đầu từ P(L₀) = 0.2, số câu đúng liên tiếp cần để đạt ngưỡng:

| Loại câu | Đến 0.95 | Đến 0.98 |
|---|---|---|
| Đúng/sai | 6 | 7 |
| Trắc nghiệm một đáp án | 3 | 4 |
| Trắc nghiệm nhiều đáp án | 2 | 3 |
| Điền khuyết | 2 | 2 |
| Tự luận ngắn | 2 | 2 |

Với tiêu chí số quan sát tối thiểu (mục 7.3), các loại cần 2 câu sẽ thành 3 câu.

Một câu trắc nghiệm sai ngay sau khi vừa đạt 0.958 kéo P(L) xuống 0.79: mô hình phản ứng với bằng chứng mới, không giữ kết luận cũ.

**Vì sao tính đến việc đoán.** Luật "3 câu đúng liên tiếp" coi ba câu đúng/sai làm đúng liên tiếp là đã thạo. BKT với G = 0.5 cho P(L) = 0.79 sau ba câu đó, tức chưa đủ. Người chưa biết gì đoán đúng cả ba câu đúng/sai với xác suất 12.5%; với trắc nghiệm bốn phương án là 1.6%. Ngân hàng của hệ thống trộn 5 loại câu, nên khác biệt này có thật. Mục 12 đo nó bằng mô phỏng.

**Câu tự luận hụt một ý.** Câu tự luận chỉ được tính là đúng khi đạt mọi ý (mục 6.1). Với S = 0.1, hụt một trong ba ý kéo P(L) từ 0.553 xuống 0.248 (ví dụ ở mục 8.8). Đây là lựa chọn thận trọng có chủ ý: thà giao thêm một câu còn hơn công nhận thạo sớm. Đổi lại, sinh viên đã nắm vẫn có thể quên nêu một ý, nên xác suất sai khi đã nắm của câu tự luận có lẽ cao hơn 0.1. Nếu S = 0.2 cho riêng câu tự luận, cùng câu trả lời đó chỉ kéo P(L) xuống 0.326. Hai lựa chọn này đổi tỉ lệ thạo giả lấy số câu luyện thừa, nên mục 12.2 chạy cả hai.

### 7.3 Khi nào công nhận thành thạo

Sinh viên được công nhận đã nắm một LO khi **cả hai** điều kiện đúng:
- P(L) ≥ θ, với θ = 0.95. Ngưỡng 0.95 là quy ước từ bài gốc của BKT. Zhang et al. (2025) thấy người đạt 0.98 học bài sau tốt hơn, nên đánh giá chạy cả hai ngưỡng.
- Số quan sát đã tính ≥ 3. Điều kiện này tách "mức hiểu" khỏi "độ chắc chắn của ước lượng" (Pelánek, 2018): hai câu tự luận đúng đã đưa P(L) lên 0.99, nhưng hai câu là quá ít bằng chứng.

### 7.4 Mức Bloom (giai đoạn mở rộng)

Phần này chỉ bật sau khi có bước kiểm tra mức Bloom của câu hỏi.

- Mức nắm được tính riêng cho từng cặp (LO, mức Bloom), chỉ với các mức không vượt quá mức của LO.
- **Mức hiện tại** của một LO là mức thấp nhất chưa đạt ngưỡng.
- **Giả định lan truyền** (bật/tắt được): trả lời đúng ở mức k được tính là một quan sát đúng cho mọi mức thấp hơn của cùng LO; trả lời sai ở mức k chỉ tính cho mức k.
- **Câu dò đầu tiên:** khi sinh viên mới vào một LO, câu đầu tiên ở mức của LO. Nếu đúng, nhờ lan truyền, sinh viên giỏi không phải đi lên lần lượt từ mức 1. Nếu sai, sinh viên bắt đầu từ mức 1.

Giả định lan truyền dựa trên tính thứ bậc của thang Bloom, nhưng thứ bậc đó không chặt. Bản sửa đổi của thang Bloom đã nới lỏng giả định thứ bậc tích luỹ (Krathwohl, 2002). Dữ liệu khoảng 42 triệu lượt làm bài ủng hộ thứ tự từ dễ đến khó nhưng cho thấy các mức chồng lấn (Lalwani & Agrawal, 2018). Cách làm đầy đủ là mô hình hoá quan hệ tiên quyết bằng mạng Bayes động (Käser et al., 2017). Vì vậy, lan truyền là giả định được kiểm tra bằng mô phỏng ở cả hai trạng thái bật và tắt.

### 7.5 Lịch ôn

BKT không mô hình hoá việc quên. Lịch ôn đảm nhận phần đó.

- Khi một LO được công nhận đã nắm, LO vào hộp 1 của hộp Leitner (Leitner, 1972). Khoảng cách ôn của 5 hộp là 1, 3, 7, 14, 30 ngày.
- Ôn đúng: LO lên một hộp. Ôn sai: LO về hộp 1. Nếu câu ôn là lần đầu sinh viên gặp câu đó, kết quả cũng cập nhật BKT. Ví dụ, sai một câu trắc nghiệm khi P(L) = 0.99 kéo P(L) xuống 0.94, dưới ngưỡng, nên LO quay lại trạng thái cần luyện.
- Một ngày tính theo giờ Việt Nam.

Leitner được chọn vì đơn giản và giải thích được. Tài liệu cho thấy lịch thích ứng theo từng người tốt hơn lịch cố định: ôn cá nhân hoá trong một lớp học thật giúp nhớ hơn 10% so với ôn đều (Lindsey et al., 2014); Mettler et al. (2016) không thấy khoảng cách tăng dần tốt hơn khoảng cách đều. Lịch ôn được tách thành một thành phần riêng để thay bằng HLR hoặc FSRS khi có dữ liệu.

### 7.6 Lưu trữ

| Bảng | Nội dung | Ghi chú |
|---|---|---|
| `learner_unit_state` (mới) | Theo sinh viên × khoá học × đơn vị: P(L), số quan sát, số câu sai liên tiếp, số lần đã đề xuất xem lại nguồn, thời điểm đạt, hộp Leitner, hạn ôn, cờ tạm dừng, phiên bản tham số | Bộ nhớ đệm, tính lại được từ lịch sử |
| `agent_course_settings` (mới) | Theo khoá học: bật/tắt, LO mở, số câu tối đa mỗi ngày, cho phép sinh câu mới, ngưỡng | Giảng viên chỉnh |
| `learning_events` (đã có bảng, chưa có code ghi) | Quyết định của Agent, lựa chọn của sinh viên, lần mở thẻ bài học, cờ báo giảng viên | Nhật ký để đánh giá |
| `quiz_attempts` (thêm cột) | Kết quả từng ý của câu tự luận; nguồn của lượt làm (đề, bài học, Agent) | Phục vụ chẩn đoán và phân tích |

---

## 8. Planner

### 8.1 Trạng thái planner dùng

| Biến | Định nghĩa |
|---|---|
| u | LO đang học: LO đầu tiên theo thứ tự chương, trong các LO đang mở, chưa thạo và không bị tạm dừng |
| P_u | Xác suất đã nắm u (ở mức hiện tại, khi có tách mức Bloom) |
| n_u | Số quan sát đã tính trên u |
| sai_u | Số câu sai liên tiếp gần nhất trên u; về 0 khi có câu đúng hoặc khi đề xuất xem lại nguồn |
| xemlai_u | Số lần đã đề xuất xem lại nguồn cho u |
| đến hạn | Các LO đã nắm có hạn ôn ≤ hôm nay |
| hôm nay | Số câu Agent đã giao hôm nay; số câu ôn đã làm hôm nay |

### 8.2 Tập hành động

| Mã | Hành động | Hợp lệ khi | Công cụ |
|---|---|---|---|
| A1 | Làm thêm một câu cùng LO | Kho còn câu chưa gặp của u | Chọn câu trong kho luyện tập |
| A2 | Lên mức Bloom (mở rộng) | Đạt ngưỡng ở mức k < mức của LO | Chọn câu mức k+1 |
| A3 | Xem lại nguồn rồi làm tiếp | Có thẻ bài học của LO, hoặc câu có đoạn nguồn biết số trang | Liên kết đến thẻ bài học hoặc trang tài liệu |
| A4 | Ôn LO đến hạn | Có LO đến hạn | Chọn câu của LO đó |
| A5 | Sang LO tiếp theo | u vừa được công nhận đã nắm | Thứ tự chương và LO |
| A6 | Báo giảng viên | Sinh viên bị kẹt ở u, hoặc kho hết câu | Đánh dấu sinh viên × LO trên trang giảng viên |
| A7 | Sinh câu nhắm chỗ hụt (mở rộng) | Giảng viên bật; kho hết câu cho u | Gửi yêu cầu sinh câu kèm ý bị hụt → hàng đợi duyệt |
| A0 | Nghỉ | Đủ số câu trong ngày, hoặc không còn việc | Không |

### 8.3 Luật chọn

Planner xét các luật theo thứ tự. Luật đầu tiên thoả thì dùng. Mọi ngưỡng là giá trị khởi đầu.

| Luật | Điều kiện | Hành động | Căn cứ |
|---|---|---|---|
| R0 | Số câu hôm nay ≥ giới hạn giảng viên đặt | A0 | Giới hạn tải |
| R1 | Có LO đến hạn ôn và số câu ôn hôm nay < 5 | A4, chọn LO quá hạn lâu nhất | Ôn ngắt quãng (Cepeda et al., 2006); xen kẽ nội dung (Brunmair & Richter, 2019) |
| R2 | n_u ≥ 10 mà chưa thạo, **hoặc** xemlai_u ≥ 2 và sai_u ≥ 2 | A6, tạm dừng u, chuyển sang LO chưa thạo kế tiếp | Giậm chân tại chỗ: sau 10 lần, thêm câu gần như không giúp (Beck & Gong, 2013) |
| R3 | sai_u ≥ 2 | A3, rồi đặt sai_u về 0 | Phản hồi chỉ rõ chỗ thiếu và việc cần làm (Hattie & Timperley, 2007) |
| R4 | P_u < θ hoặc n_u < 3 | A1; hết câu thì A7 nếu giảng viên bật, không thì A6 với lý do "thiếu câu" | Luyện bằng kiểm tra (Adesope et al., 2017) |
| R5 | Đạt ngưỡng ở mức k < mức của LO (mở rộng) | A2 | Mức Bloom của LO là mục tiêu |
| R6 | Đạt ngưỡng ở mức của LO | Đưa u vào lịch ôn, rồi A5; hết LO thì A0 | Mastery learning (Bloom, 1968) |

Với một sinh viên gặp khó liên tục, chuỗi diễn ra như sau: sai 2 câu → xem lại nguồn lần 1 → sai 2 câu → xem lại nguồn lần 2 → sai 2 câu → báo giảng viên. Tổng cộng khoảng 6–8 câu. Luật "10 lần" bắt những trường hợp sai rải rác, không liên tiếp.

### 8.4 Chọn câu cụ thể

Trong A1 và A4, câu được chọn ngẫu nhiên trong kho luyện tập của LO, với ba ưu tiên:
- khác loại câu với câu vừa làm, để đa dạng;
- không chọn câu tự luận nếu sinh viên đang có một câu tự luận cùng LO chờ chấm;
- khi ôn, nếu đã hết câu chưa gặp, lấy câu gặp lâu nhất. Kết quả câu gặp lại vẫn cập nhật hộp Leitner, nhưng không cập nhật BKT.

Chọn câu theo độ khó cần thống kê độ khó thực của từng câu, mà phần này chưa có. Để giai đoạn sau.

### 8.5 Lý do hiển thị

Lý do được ghép từ mẫu, không gọi LLM. Riêng nhận xét về ý bị hụt lấy từ kết quả chấm, do LLM viết lúc chấm.

| Tình huống | Mẫu |
|---|---|
| A1 sau câu tự luận hụt ý | "{nhận xét của ý bị hụt}. Làm thêm một câu về {LO}." |
| A1 khác | "Bạn đang tiến bộ ở {LO}. Làm thêm một câu để chắc chắn." |
| A3 | "Bạn sai {n} câu liên tiếp về {LO}. Xem lại thẻ “{tiêu đề thẻ}” (hoặc trang {p} của “{tài liệu}”), rồi làm tiếp." |
| A4 | "Đến lúc ôn {LO}. Lần cuối bạn làm phần này là {d} ngày trước." |
| A5 | "Bạn đã nắm {LO}. Chuyển sang {LO kế tiếp}." |
| A6 (sinh viên thấy) | "Phần {LO} đang khó với bạn. Giảng viên đã được báo. Bạn có thể học {LO khác} trước." |
| A0 | "Hôm nay bạn đã làm {n} câu. Quay lại vào ngày mai để ôn." |

Giải thích vì sao hệ thống đề xuất giúp người học tin và dùng đề xuất nhiều hơn (Conati et al., 2021). Mức nắm theo LO cũng được hiển thị, theo hướng mô hình người học mở (Bull & Kay, 2016).

### 8.6 Sinh viên vẫn được chọn

Mỗi lần, Agent đưa **một đề xuất chính** và tối đa hai lựa chọn khác lấy từ các hành động hợp lệ: ôn LO đến hạn, chuyển sang LO khác chưa thạo, hoặc nghỉ. Hệ thống thu hẹp lựa chọn, sinh viên quyết định. Cách chia quyền này giữ được hiệu quả và tăng mức tham gia (Corbalan et al., 2008). Mô phỏng của Noh et al. (2026) cũng cho thấy khi người học tự chọn hoàn toàn, một số chiến lược gây luyện thừa nhiều, và ràng buộc của hệ thống sửa được điều đó.

Lựa chọn của sinh viên được ghi lại để đo tỉ lệ làm theo đề xuất.

### 8.7 Giới hạn do giảng viên đặt

- LO nào được mở cho Agent.
- Số câu tối đa mỗi sinh viên mỗi ngày.
- Bật hay tắt A7 (sinh câu mới), vì A7 tốn token và thêm việc duyệt.
- Hạn mức token: dùng lại hai bảng hạn mức LLM đã có trong cơ sở dữ liệu.

### 8.8 Ví dụ chạy tay

Sinh viên A, L.O.1.1, tham số ở mục 7.2:

| # | Câu | Kết quả | P(L) sau | Luật | Đề xuất |
|---|---|---|---|---|---|
| 1 | Trắc nghiệm một đáp án | Đúng | 0.553 | R4 | A1: "Bạn đang tiến bộ ở L.O.1.1. Làm thêm một câu để chắc chắn." |
| 2 | Tự luận ngắn (câu ở mục 1.2) | Hụt ý (1) | 0.248 | R4 | A1, kèm nhận xét về ý (1) |
| 3 | Đúng/sai | Sai | 0.203 | R3 (sai 2 câu liên tiếp) | A3: xem lại thẻ bài học của L.O.1.1 |
| 4 | Trắc nghiệm một đáp án | Đúng | 0.556 | R4 | A1 |
| 5 | Điền khuyết | Đúng | 0.964 (5 quan sát) | R6 | Lên lịch ôn sau 1 ngày; A5: sang L.O.1.2 |
| Hôm sau | | | | R1 | A4: ôn L.O.1.1 |

Cùng chuỗi câu trả lời đó, luật "3 câu đúng liên tiếp" sẽ giao tiếp câu thứ 6, vì A mới đúng 2 câu liên tiếp. Đề cố định thì giao đủ N câu cho mọi sinh viên, bất kể kết quả.

### 8.9 Biến thể: LLM chọn hành động

Biến thể này dùng cho thực nghiệm, để trả lời câu hỏi "LLM có chọn tốt hơn luật không". Nó theo khung LLM-Modulo: LLM đề xuất, code kiểm tra (Kambhampati et al., 2024).

1. Code tính **tập hành động hợp lệ**: mọi hành động có điều kiện thoả, không chỉ hành động của luật đầu tiên.
2. LLM nhận tóm tắt trạng thái: mức nắm theo LO, 5 lượt làm gần nhất, LO đến hạn ôn, các hành động hợp lệ. Không gửi thông tin định danh sinh viên.
3. LLM trả JSON `{action, lo_id, reason}`.
4. Code kiểm tra hành động có nằm trong tập hợp lệ. Sai, lỗi, hoặc quá thời gian thì dùng planner luật.
5. Ghi cả lựa chọn của LLM và của luật để đo mức trùng nhau.

Biến thể chỉ chạy trong mô phỏng. Sinh viên thật chỉ dùng planner luật.

---

## 9. LLM và kiểm soát chất lượng

| Chỗ dùng LLM | Trạng thái | Kiểm soát |
|---|---|---|
| Chấm tự luận theo từng ý | Đã có | Bài làm được đặt giữa hai mốc phân cách và chỉ coi là dữ liệu; lỗi thì chuyển giảng viên chấm, không cho 0 điểm |
| Sinh câu nhắm chỗ hụt (A7) | Mở rộng | Đi qua pipeline sinh câu có kiểm tra; vào hàng đợi duyệt; không hiện ngay trong phiên |
| LLM chọn hành động | Chỉ trong thực nghiệm | Chỉ chọn trong tập hợp lệ do code tính |

**Agent không làm bài hộ sinh viên.** Một thực nghiệm với khoảng 1.000 học sinh cho thấy dùng GPT tự do làm điểm luyện tập tăng, nhưng khi bỏ AI thì điểm thi thấp hơn nhóm không dùng 17% (Bastani et al., 2025). Agent chỉ chọn việc cho sinh viên tự làm, nên không tạo ra kiểu dựa dẫm đó.

**Phụ thuộc vào phần sinh câu (thiết kế QuizGen v2):**
- **Kiểm tra mức Bloom:** cần trước khi tách mức nắm theo mức Bloom.
- **Chống trùng câu:** cần để "câu chưa gặp" là câu mới thật. Trước khi có, dùng tạm quy tắc gộp câu cùng văn bản (mục 6.1).
- **Phương án nhiễu gắn với hiểu lầm:** cho phép chẩn đoán từ câu trắc nghiệm sai, không chỉ từ tự luận (Gierl et al., 2017). Để giai đoạn mở rộng.

---

## 10. Giao diện

**Cho sinh viên** (trong các trang `/learn` của hệ thống):
- **Khung "Bước tiếp theo"** ở trang kết quả sau khi nộp bài, và ở trang khoá học.
- **Trang luyện tập:** mỗi lần một câu, dùng lại phần hiển thị và nhập đáp án đã có cho 5 loại câu.
- **Trang "Mức nắm theo LO":** thanh mức nắm ước tính, số câu đã làm, ngày ôn kế tiếp.

```text
┌ Bước tiếp theo ──────────────────────────────────────────┐
│ L.O.1.1   mức nắm ước tính  ██████░░░░                   │
│ Bạn nêu đúng quy mô, đa dạng, phức tạp và mục đích rút   │
│ ra giá trị, nhưng chưa nói vì sao công nghệ CSDL thông    │
│ thường không xử lý được. Làm thêm một câu về L.O.1.1.    │
│                                                          │
│ [Làm câu tiếp]     Hoặc: [Ôn L.O.0.2 · đến hạn] [Nghỉ]   │
└──────────────────────────────────────────────────────────┘
```

Thanh mức nắm không ghi phần trăm, để sinh viên không nhầm với điểm.

**Cho giảng viên:**
- Bảng LO × sinh viên: mức nắm, số câu đã làm.
- Danh sách sinh viên bị kẹt (từ A6), kèm LO và các lượt làm gần nhất.
- Trang cài đặt Agent cho khoá học (mục 8.7).
- Khi soạn đề Kiểm tra: chỉ báo câu nào đã dùng trong luyện tập.

**Ranh giới với phần của thành viên khác.** A3 mở thẻ bài học, là trang do phần này quản lý. Nếu trình xem tài liệu có đường dẫn mở đúng trang thì dùng đường dẫn đó; nếu chưa có, chỉ hiện tên tài liệu và số trang. Agent không sửa giao diện của người khác; nó chỉ đưa dữ liệu ra qua RPC. Trợ giảng chat có thể gọi `GetLearnerSummary` để biết sinh viên yếu LO nào, nếu nhóm muốn.

---

## 11. Thay đổi trong hệ thống

| Phần | Thay đổi | Giai đoạn |
|---|---|---|
| worker, chấm tự luận | Lưu kết quả từng ý (đạt hay chưa, nhận xét) thay vì chỉ điểm tổng. Phần chấm bài luận qua Canvas đã lưu điểm từng tiêu chí, có thể làm theo cách đó | 0 |
| Cơ sở dữ liệu | Thêm cột vào `quiz_attempts`; thêm `learner_unit_state`, `agent_course_settings`; bắt đầu ghi `learning_events` | 0–2 |
| core-api | Module `learning-agent`: kho luyện tập, mô hình người học, planner, lịch ôn. RPC: `GetNextActivity`, `GetLearnerSummary`, `GetCourseMastery`, `RecordAgentEvent`, `GetAgentSettings`, `UpdateAgentSettings`. `SubmitQuiz` nhận nguồn AGENT và không gửi điểm về Canvas | 1–2 |
| contracts | Định nghĩa proto cho RPC mới; thêm trường "ý bị hụt" vào sự kiện yêu cầu sinh câu | 2; mở rộng |
| web | Khung Bước tiếp theo, trang luyện tập, trang mức nắm; các trang của giảng viên | 1–2 |
| Bộ mô phỏng | Chạy ma trận đánh giá, gọi đúng module mô hình người học và planner của core-api, không viết lại logic | 3 |

---

## 12. Đánh giá

### 12.1 Câu hỏi nghiên cứu

| # | Câu hỏi | Cách trả lời |
|---|---|---|
| RQ1 | Planner có đưa sinh viên đến chỗ thật sự nắm với ít câu hơn đề cố định, và ít "thạo giả" hơn các tiêu chí đơn giản không? | Mô phỏng |
| RQ2 | Kết luận ở RQ1 có còn đúng khi sinh viên ảo học theo cách khác với giả định của planner không? | Ma trận đánh giá vững |
| RQ3 | Tính xác suất đoán theo loại câu có giảm "thạo giả" trong ngân hàng trộn nhiều loại câu không? | So BKT có và không có G theo loại câu; so với 3 câu liên tiếp và EMA |
| RQ4 | LLM chọn hành động trong tập hợp lệ có tốt hơn luật không, với chi phí bao nhiêu? | Mô phỏng, trên tập con |
| RQ5 | Sinh viên thật có làm theo đề xuất và thấy đề xuất hữu ích không? | Thử nghiệm nhỏ, nếu kịp |

### 12.2 Mô phỏng

**Ma trận đánh giá.** Mỗi chính sách được chạy trên nhiều mô hình người học, và chỉ được coi là tốt khi nó tốt trên mọi mô hình, không chỉ trên mô hình nó dùng để ra quyết định (Doroudi et al., 2017).

Chính sách (cột):

| Mã | Chính sách | Mô tả |
|---|---|---|
| P0 | Đề cố định | Mỗi LO đúng N câu theo thứ tự, như một đề luyện tập thường |
| P1 | 3 câu đúng liên tiếp | Luyện đến khi đúng 3 câu liên tiếp; dừng và báo sau 10 câu, như Skill Builder của ASSISTments (Heffernan & Heffernan, 2014; Beck & Gong, 2013) |
| P2 | Trung bình trượt mũ | Thạo khi trung bình trượt mũ của đúng/sai vượt ngưỡng (Pelánek & Řihák, 2017); hệ số và ngưỡng chọn bằng tìm lưới |
| P3a | Chỉ BKT | Luyện đến khi đạt tiêu chí ở mục 7.3, không có các luật xem lại, ôn, báo giảng viên |
| P3 | Planner đề xuất | Đầy đủ R0–R6 |
| P4 | LLM chọn hành động | Mục 8.9 |

P3a so với P3 cho biết các luật thêm vào có giá trị hay không.

Mô hình người học ảo (hàng). Mô hình sinh dữ liệu phải **khác** mô hình planner dùng, để thực nghiệm không tự chứng minh chính nó:

| Mã | Mô hình | Trạng thái "thật sự nắm" |
|---|---|---|
| S1 | BKT với tham số riêng cho từng sinh viên ảo, bốc ngẫu nhiên và khác tham số của planner; gồm nhóm học nhanh và nhóm học chậm | Trạng thái ẩn "đã nắm" |
| S2 | AFM (Cen et al., 2006): xác suất đúng tăng dần theo số lần luyện, cộng xác suất đoán theo loại câu | Xác suất trả lời đúng một câu không đoán được ≥ 0.9 |
| S3 | S1 cộng quên: kiến thức đã nắm có thể mất dần theo số ngày không luyện | Như S1, tại thời điểm đo |

Noh et al. (2026) cũng dùng một mô hình để sinh câu trả lời (AFM) và một mô hình khác để theo dõi (BKT).

**Ngân hàng câu ảo.** Lấy cấu trúc từ ngân hàng thật: số LO, số câu theo loại và mức. Thêm hai kịch bản: ngân hàng dày (≥ 15 câu mỗi LO) và ngân hàng mỏng (5 câu mỗi LO).

**Chỉ số**

| Chỉ số | Định nghĩa | Căn cứ |
|---|---|---|
| Số câu đến khi nắm | Số câu đến khi sinh viên ảo thật sự nắm mọi LO | Hiệu quả |
| Tỉ lệ thạo giả | Số lần chính sách công nhận thạo khi sinh viên ảo chưa nắm, chia cho số lần công nhận | Độ đúng của quyết định |
| Câu luyện thừa | Số câu giao sau khi sinh viên ảo đã thật sự nắm | Noh et al. (2026); Xia et al. (2025) |
| Phát hiện bị kẹt | Độ chính xác và độ phủ của cờ báo giảng viên, so với những sinh viên ảo không thể đạt trong giới hạn | Beck & Gong (2013) |
| Ghi nhớ (S3) | Tỉ lệ đúng ở một bài kiểm tra trễ, ví dụ sau 30 ngày mô phỏng | Lịch ôn |
| Công bằng | Chênh lệch các chỉ số trên giữa nhóm học nhanh và nhóm học chậm | Doroudi & Brunskill (2019) |
| Riêng P4 | Tỉ lệ hành động không hợp lệ, tỉ lệ trùng với luật, token và chi phí mỗi quyết định | Mục 8.9 |

**Phân tích độ nhạy:** ngưỡng 0.95 và 0.98; số quan sát tối thiểu 1 và 3; G theo loại câu và G chung cho mọi loại; câu tự luận tính là đúng khi đạt mọi ý hoặc khi đạt ít nhất 2/3 số ý; S của câu tự luận 0.1 và 0.2; lan truyền mức Bloom bật và tắt (khi có tách mức); kích thước ngân hàng; mức tác dụng của việc xem lại nguồn.

Để chạy được hai biến thể về câu tự luận, sinh viên ảo trả lời câu tự luận theo từng ý: mỗi ý có xác suất hụt riêng, kể cả khi sinh viên ảo đã nắm.

Tác dụng của việc xem lại nguồn được mô hình hoá bằng cách tăng xác suất học được T ở lần làm kế tiếp. Không có dữ liệu cho mức tăng này, nên chạy nhiều mức (×1.0, ×1.5, ×2.0) và báo cáo kết quả theo từng mức.

**Cách chạy:** 1.000 sinh viên ảo mỗi ô, 5 lần gieo ngẫu nhiên; mọi chính sách dùng cùng một tập sinh viên ảo để so sánh theo cặp; báo cáo trung bình và khoảng tin cậy 95%. P4 chạy trên tập con 100 sinh viên ảo mỗi hàng để giới hạn chi phí.

### 12.3 Kiểm thử phần tất định

| Phần | Kiểm thử |
|---|---|
| Hàm BKT | So với các giá trị tính tay ở mục 7.2 và 8.8 |
| Tiêu chí thành thạo | Đủ P(L) nhưng thiếu số quan sát thì chưa công nhận |
| Planner | Mỗi luật R0–R6 một trường hợp, kể cả thứ tự ưu tiên khi nhiều luật cùng thoả |
| Kho luyện tập | Câu thuộc đề Kiểm tra bị loại; câu trùng văn bản tính là đã gặp |
| Mô hình người học | Cùng lịch sử cho cùng trạng thái; thêm một câu tự luận đang chờ chấm thì trạng thái không đổi |
| Biến thể LLM | Hành động ngoài tập hợp lệ thì dùng luật |

### 12.4 Thử nghiệm nhỏ với người thật (nếu kịp)

- 5–10 sinh viên, một chương, 1–2 tuần, có đồng ý tham gia.
- Đo: tỉ lệ làm theo đề xuất (từ nhật ký quyết định), số câu đến khi đạt, thời gian, khảo sát ngắn thang 1–5 về mức hữu ích và mức tin vào lý do đề xuất, phỏng vấn ngắn.
- Không đủ để kết luận thống kê. Mục đích là thấy hệ thống chạy với người thật và lấy dữ liệu đối chiếu với mô phỏng: tỉ lệ đúng theo loại câu, phân phối số câu đến khi đạt.

### 12.5 Giới hạn của cách đánh giá

- Mô phỏng chỉ chứng minh chính sách hoạt động đúng **dưới giả định của các mô hình người học ảo**. Nó không chứng minh sinh viên thật học tốt hơn. Gần một nửa nghiên cứu dùng người học mô phỏng không kiểm chứng mô hình mô phỏng (Käser & Alexandron, 2024). Báo cáo sẽ nói rõ giới hạn này.
- Không dùng LLM đóng vai sinh viên ảo trong thực nghiệm chính, vì LLM khó đóng vai người chỉ biết một phần (Yuan et al., 2026).

---

## 13. Lộ trình

Chưa đặt mốc ngày vì chưa có lịch bảo vệ. Thời lượng dưới đây là ước lượng thô cho một người làm; giai đoạn 0–3 tổng cộng khoảng 8–9 tuần.

| Giai đoạn | Việc | Thời lượng ước tính | Đầu ra kiểm chứng được |
|---|---|---|---|
| **0. Nền** (có ích kể cả khi bỏ hướng Agent) | Lưu kết quả từng ý khi chấm tự luận; ghi nguồn lượt làm; lọc kho luyện tập (bỏ câu thuộc đề Kiểm tra, gộp câu trùng văn bản); đếm ngân hàng theo LO × loại | 1 tuần | Migration và test; bảng đếm ngân hàng của môn thử nghiệm |
| **1. Mô hình người học theo LO** | Hàm BKT và hai tiêu chí đối chứng dưới cùng một giao diện; bộ nhớ đệm; `GetLearnerSummary`; trang mức nắm cho sinh viên và giảng viên | 2 tuần | Test theo mục 12.3; trang chạy với dữ liệu thật |
| **2. Planner và giao diện** | Luật R0–R6; nhật ký quyết định; `GetNextActivity`; trang luyện tập; khung Bước tiếp theo; lịch ôn Leitner; cài đặt của giảng viên; danh sách sinh viên bị kẹt | 3 tuần | Test theo bảng luật; chạy được trọn vòng trên Canvas |
| **3. Đánh giá** | Bộ mô phỏng 6 × 3; phân tích độ nhạy; biến thể LLM; thử nghiệm nhỏ nếu kịp | 2–3 tuần; thử nghiệm nhỏ chạy song song 1–2 tuần | Bảng kết quả RQ1–RQ4 kèm khoảng tin cậy |
| **4. Mở rộng** (nếu còn thời gian) | Tách mức Bloom (sau khi có kiểm tra Bloom); sinh câu nhắm chỗ hụt; gắn đơn vị kiến thức; chẩn đoán từ phương án nhiễu; lịch ôn thích ứng | Tuỳ phần; bản tối giản của sinh câu nhắm chỗ hụt khoảng 1 tuần | Tuỳ phần |

---

## 14. Rủi ro

| # | Rủi ro | Cách xử lý |
|---|---|---|
| R1 | Nhãn Bloom sai làm quyết định theo mức Bloom sai | Giai đoạn 1–3 chỉ theo dõi theo LO; tách mức Bloom sau khi có kiểm tra Bloom |
| R2 | Ngân hàng mỏng: A1 hết câu sau vài lượt | Đếm trước ở giai đoạn 0; sinh bù theo lô trước khi bật Agent; mô phỏng kịch bản ngân hàng mỏng |
| R3 | Tham số BKT chưa được hiệu chỉnh | Phân tích độ nhạy; mô hình sinh dữ liệu khác mô hình planner; ước lượng bằng pyBKT khi có dữ liệu |
| R4 | Mô phỏng không phản ánh người thật | Ma trận đánh giá vững; đối chiếu với dữ liệu thật; thử nghiệm nhỏ; nêu rõ giới hạn |
| R5 | Hội đồng hỏi "Agent ở đâu?" | Định nghĩa ở mục 3; so sánh luật với LLM chọn hành động ở mục 12 |
| R6 | Sinh viên không làm theo đề xuất | Cho sinh viên lựa chọn; đo tỉ lệ làm theo |
| R7 | Lộ câu thi | Lọc kho luyện tập; chỉ báo khi soạn đề Kiểm tra |
| R8 | Đụng phần của thành viên khác | Chỉ nối qua đường dẫn và RPC; giao diện nằm trong trang riêng |
| R9 | Chi phí LLM | LLM chọn hành động chỉ chạy trong mô phỏng, trên tập con; hạn mức token |
| R10 | Hội đồng thấy phần GenAI của Agent mỏng so với tên đề tài | Xin ý kiến thầy ở Q7; nếu cần, đưa bản tối giản của sinh câu nhắm chỗ hụt vào giai đoạn 2 |

---

## 15. Câu hỏi xin ý kiến thầy

| # | Câu hỏi | Đề xuất của em |
|---|---|---|
| Q1 | Phạm vi đồ án nên dừng ở giai đoạn nào? | Dừng ở giai đoạn 3; giai đoạn 4 làm nếu còn thời gian |
| Q2 | Đánh giá bằng mô phỏng cộng thử nghiệm nhỏ có đủ cho đồ án không, hay cần thực nghiệm có đối chứng với lớp thật? | Mô phỏng là kết quả chính, thử nghiệm nhỏ để minh hoạ |
| Q3 | Hoạt động do Agent chọn chỉ để luyện tập, không tính điểm? | Không tính điểm |
| Q4 | Câu do Agent sinh có bắt buộc giảng viên duyệt trước khi sinh viên thấy? | Có |
| Q5 | Thử nghiệm với bạn cùng lớp cần thủ tục đồng ý thế nào? | Phiếu đồng ý; dữ liệu ẩn danh |
| Q6 | Theo dõi theo LO có đủ, hay cần làm đơn vị kiến thức nhỏ hơn LO? | LO cho đồ án; đơn vị kiến thức là hướng phát triển |
| Q7 | Trong giai đoạn 0–3, GenAI chỉ có ở phần chấm tự luận đã có và ở biến thể LLM chọn hành động trong mô phỏng. Như vậy có đủ khớp với tên đề tài, hay cần đưa sinh câu nhắm chỗ hụt vào phạm vi? | Giữ phạm vi 0–3. Nếu thầy thấy cần, em đưa bản tối giản vào giai đoạn 2: khi sinh viên hụt ý hoặc kho hết câu, gửi yêu cầu sinh câu kèm ý bị hụt qua luồng sinh câu hiện có, câu sinh ra vào hàng đợi duyệt. Khoảng 1 tuần |

---

## Tài liệu tham khảo

Danh mục đầy đủ 91 tài liệu và bảng truy vết ở [learning-agent-tong-quan-tai-lieu.md](learning-agent-tong-quan-tai-lieu.md). Dưới đây là các tài liệu được trích trong báo cáo này.

- Adesope, O. O., Trevisan, D. A., & Sundararajan, N. (2017). Rethinking the use of tests: A meta-analysis of practice testing. *Review of Educational Research*, 87(3), 659–701. https://doi.org/10.3102/0034654316689306
- Badrinath, A., Wang, F., & Pardos, Z. (2021). pyBKT: An accessible Python library of Bayesian knowledge tracing models. In *Proceedings of EDM 2021* (pp. 468–474). https://arxiv.org/abs/2105.00385
- Bastani, H., et al. (2025). Generative AI without guardrails can harm learning: Evidence from high school mathematics. *PNAS*, 122(26), e2422633122. https://doi.org/10.1073/pnas.2422633122
- Beck, J. E., & Chang, K.-m. (2007). Identifiability: A fundamental problem of student modeling. In *User Modeling 2007*, LNCS 4511 (pp. 137–146). Springer.
- Beck, J. E., & Gong, Y. (2013). Wheel-spinning: Students who fail to master a skill. In *AIED 2013*, LNCS 7926 (pp. 431–440). Springer.
- Bloom, B. S. (1968). Learning for mastery. *Evaluation Comment*, 1(2).
- Brunmair, M., & Richter, T. (2019). Similarity matters: A meta-analysis of interleaved learning and its moderators. *Psychological Bulletin*, 145(11), 1029–1052. https://doi.org/10.1037/bul0000209
- Bull, S., & Kay, J. (2016). SMILI☺: A framework for interfaces to learning data in open learner models, learning analytics and related fields. *International Journal of Artificial Intelligence in Education*, 26(1), 293–331.
- Cen, H., Koedinger, K., & Junker, B. (2006). Learning factors analysis – A general method for cognitive model evaluation and improvement. In *ITS 2006* (pp. 164–175). Springer.
- Cepeda, N. J., Pashler, H., Vul, E., Wixted, J. T., & Rohrer, D. (2006). Distributed practice in verbal recall tasks: A review and quantitative synthesis. *Psychological Bulletin*, 132(3), 354–380. https://doi.org/10.1037/0033-2909.132.3.354
- Conati, C., Barral, O., Putnam, V., & Rieger, L. (2021). Toward personalized XAI: A case study in intelligent tutoring systems. *Artificial Intelligence*, 298, 103503. https://doi.org/10.1016/j.artint.2021.103503
- Corbalan, G., Kester, L., & van Merriënboer, J. J. G. (2008). Selecting learning tasks: Effects of adaptation and shared control on learning efficiency and task involvement. *Contemporary Educational Psychology*, 33(4), 733–756.
- Corbett, A. T., & Anderson, J. R. (1995). Knowledge tracing: Modeling the acquisition of procedural knowledge. *User Modeling and User-Adapted Interaction*, 4(4), 253–278. https://doi.org/10.1007/BF01099821
- Doroudi, S., Aleven, V., & Brunskill, E. (2017). Robust evaluation matrix: Towards a more principled offline exploration of instructional policies. In *L@S '17* (pp. 3–12). https://doi.org/10.1145/3051457.3051463
- Doroudi, S., Aleven, V., & Brunskill, E. (2019). Where's the reward? A review of reinforcement learning for instructional sequencing. *International Journal of Artificial Intelligence in Education*, 29(4), 568–620. https://doi.org/10.1007/s40593-019-00187-x
- Doroudi, S., & Brunskill, E. (2019). Fairer but not fair enough: On the equitability of knowledge tracing. In *LAK '19* (pp. 335–339). https://doi.org/10.1145/3303772.3303838
- Georgiadou, E., Triantafillou, E., & Economides, A. A. (2007). A review of item exposure control strategies for computerized adaptive testing developed from 1983 to 2005. *Journal of Technology, Learning, and Assessment*, 5(8).
- Gervet, T., Koedinger, K., Schneider, J., & Mitchell, T. (2020). When is deep learning the best approach to knowledge tracing? *Journal of Educational Data Mining*, 12(3), 31–54. https://doi.org/10.5281/zenodo.4143614
- Gierl, M. J., Bulut, O., Guo, Q., & Zhang, X. (2017). Developing, analyzing, and using distractors for multiple-choice tests in education: A comprehensive review. *Review of Educational Research*, 87(6), 1082–1116. https://doi.org/10.3102/0034654317726529
- Hattie, J., & Timperley, H. (2007). The power of feedback. *Review of Educational Research*, 77(1), 81–112. https://doi.org/10.3102/003465430298487
- Heffernan, N. T., & Heffernan, C. L. (2014). The ASSISTments ecosystem: Building a platform that brings scientists and teachers together for minimally invasive research on human learning and teaching. *International Journal of Artificial Intelligence in Education*, 24(4), 470–497. https://doi.org/10.1007/s40593-014-0024-x
- Hooshyar, D., Yang, Y., Šíř, G., Kärkkäinen, T., Hämäläinen, R., Cukurova, M., & Azevedo, R. (2025). Problems with large language models for learner modelling: Why LLMs alone fall short for responsible tutoring in K–12 education [Preprint]. arXiv:2512.23036.
- Kambhampati, S., et al. (2024). Position: LLMs can't plan, but can help planning in LLM-Modulo frameworks. In *ICML 2024*, PMLR 235, 22895–22907. https://proceedings.mlr.press/v235/kambhampati24a.html
- Käser, T., & Alexandron, G. (2024). Simulated learners in educational technology: A systematic literature review and a Turing-like test. *International Journal of Artificial Intelligence in Education*, 34(2), 545–585. https://doi.org/10.1007/s40593-023-00337-2
- Käser, T., Klingler, S., Schwing, A. G., & Gross, M. (2017). Dynamic Bayesian networks for student modeling. *IEEE Transactions on Learning Technologies*, 10(4), 450–462.
- Kelly, K., Wang, Y., Thompson, T., & Heffernan, N. (2015). Defining mastery: Knowledge tracing versus N-consecutive correct responses. In *Proceedings of EDM 2015* (pp. 630–631).
- Khajah, M., Lindsey, R. V., & Mozer, M. C. (2016). How deep is knowledge tracing? In *Proceedings of EDM 2016*. https://arxiv.org/abs/1604.02416
- Krathwohl, D. R. (2002). A revision of Bloom's taxonomy: An overview. *Theory Into Practice*, 41(4), 212–218. https://doi.org/10.1207/s15430421tip4104_2
- Lalwani, A., & Agrawal, S. (2018). Validating revised Bloom's taxonomy using deep knowledge tracing. In *AIED 2018*. https://doi.org/10.1007/978-3-319-93843-1_17
- Leitner, S. (1972). *So lernt man lernen*. Herder.
- Lindsey, R. V., Shroyer, J. D., Pashler, H., & Mozer, M. C. (2014). Improving students' long-term knowledge retention through personalized review. *Psychological Science*, 25(3), 639–647. https://doi.org/10.1177/0956797613504302
- Mettler, E., Massey, C. M., & Kellman, P. J. (2016). A comparison of adaptive and fixed schedules of practice. *Journal of Experimental Psychology: General*, 145(7), 897–917. https://doi.org/10.1037/xge0000170
- Neshaei, S. P., Davis, R. L., Hazimeh, A., Lazarevski, B., Dillenbourg, P., & Käser, T. (2024). Towards modeling learner performance with large language models. In *Proceedings of EDM 2024* (poster). https://arxiv.org/abs/2403.14661
- Noh, H., Chowdhary, A., Ooge, J., Aleven, V., & Borchers, C. (2026). Simulating learners' task-selection strategies and system constraints in mastery learning. In *Proceedings of EDM 2026* (short paper).
- Pardos, Z. A., & Heffernan, N. T. (2011). KT-IDEM: Introducing item difficulty to the knowledge tracing model. In *UMAP 2011* (pp. 243–254). Springer.
- Pelánek, R. (2018). Conceptual issues in mastery criteria: Differentiating uncertainty and degrees of knowledge. In *AIED 2018* (pp. 450–461). https://doi.org/10.1007/978-3-319-93843-1_33
- Pelánek, R., & Řihák, J. (2017). Experimental analysis of mastery learning criteria. In *UMAP '17* (pp. 156–163). https://doi.org/10.1145/3079628.3079667
- Settles, B., & Meeder, B. (2016). A trainable spaced repetition model for language learning. In *ACL 2016* (pp. 1848–1858). https://doi.org/10.18653/v1/P16-1174
- VanLehn, K. (2006). The behavior of tutoring systems. *International Journal of Artificial Intelligence in Education*, 16(3), 227–265.
- Wooldridge, M., & Jennings, N. R. (1995). Intelligent agents: Theory and practice. *The Knowledge Engineering Review*, 10(2), 115–152. https://doi.org/10.1017/S0269888900008122
- Xia, M., Schmucker, R., Borchers, C., & Aleven, V. (2025). Optimizing mastery learning by fast-forwarding over-practice steps. In *EC-TEL 2025*. arXiv:2506.17577.
- Yuan, Z., Xiao, Y., Li, M., Xuan, W., Tong, R., Diab, M., & Mitchell, T. (2026). Towards valid student simulation with large language models [Preprint]. arXiv:2601.05473.
- Zhang, J., Vanacore, K., Baker, R. S., Ch, N., Mills, C., & Henkel, O. (2025). How much mastery is enough mastery? The relationship between mastery in a lesson and the performance on the subsequent lesson. In *Proceedings of EDM 2025* (short paper).
