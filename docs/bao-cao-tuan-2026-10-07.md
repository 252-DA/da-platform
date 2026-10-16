# Báo cáo tiến độ đồ án — tuần 30/09 – 07/10/2026

**Đề tài:** Hệ thống LMS tự động tạo Micro-Content & Quiz bằng Generative AI (DA Platform)
**Ngày báo cáo:** Thứ Tư, 07/10/2026

---

## 1. Tóm tắt

- **Quiz có thêm 4 loại câu hỏi:** chọn nhiều đáp án, đúng/sai, điền khuyết và **tự luận ngắn**. Trước đây hệ thống chỉ có trắc nghiệm một đáp án.
- **Câu tự luận được AI chấm theo rubric.** Điểm chỉ được gửi về sổ điểm Canvas khi mọi câu trong bài đã chấm xong. Câu AI không chấm được sẽ chờ giảng viên chấm, không bị tính 0 điểm.
- **Micro-content (lesson card) được sinh theo từng LO.** Mỗi card qua ba bước: sinh, kiểm tra lại với tài liệu nguồn, rồi viết lại nếu bị loại. Card có câu tự kiểm tra ở mặt sau.
- **Phần backend cho trình xem tài liệu kèm chat AI đã xong:** đọc file, lấy nội dung theo trang, và tìm kiếm giới hạn trong tài liệu đang mở. Giao diện viewer chưa làm.
- **Đã rà soát độ phức tạp code** và lập backlog 12 mục, trong đó 4 mục ưu tiên cao.
- **Kiểm thử tự động đều đạt** (chạy ngày 07/10, chi tiết ở mục 4). Riêng chấm tự luận **chưa chạy với bài nộp thật trên Canvas**.

---

## 2. Kết quả trong tuần

### 2.1. Đa dạng loại câu hỏi

| Loại | Cách chấm |
|---|---|
| Trắc nghiệm 1 đáp án | Chấm ngay |
| Trắc nghiệm nhiều đáp án (4–6 phương án) | Chấm ngay, phải chọn đúng toàn bộ tập đáp án đúng |
| Đúng / Sai | Chấm ngay |
| Điền khuyết | So khớp sau khi chuẩn hoá với danh sách cách viết được chấp nhận (ví dụ "phi chức năng", "non-functional") |
| Tự luận ngắn (1–3 câu) | AI chấm bất đồng bộ theo rubric |

Hệ thống cập nhật ở các phần sau:

- **Sinh câu hỏi:** mỗi lần sinh chọn một loại câu. Prompt và bộ kiểm tra đầu ra riêng cho từng loại.
- **Lưu trữ:** mọi đường ghi câu hỏi đều qua cùng một hàm kiểm tra và chuẩn hoá đáp án, nên dữ liệu trong CSDL luôn đúng định dạng của loại câu.
- **Giao diện:**
  - giảng viên sửa câu theo từng loại;
  - người học nhập câu trả lời theo từng loại;
  - trang kết quả hiển thị đúng cho cả năm loại.
- **Contract giữa các service** (JSON Schema) đã cập nhật. Có fixture hợp lệ và không hợp lệ cho mỗi loại câu.

### 2.2. Chấm tự luận ngắn bằng AI

Luồng xử lý:

```
Người học nộp bài
  → core-api chấm ngay các câu trắc nghiệm, lưu bản chụp đề + rubric của câu tự luận
  → hàng đợi answer_grading → worker chấm tự luận
  → LLM xét từng ý trong rubric: đạt / không đạt (kèm nhận xét)
  → code tính điểm = số ý đạt / tổng số ý
  → khi cả bài đã chấm xong → gửi điểm về Canvas (LTI AGS)
```

Các quyết định thiết kế chính:

- **LLM không cho điểm số mà chỉ phán từng ý của rubric.** Điểm do code tính. Cách này giúp kết quả nhất quán và giải thích được.
- **Chấm theo đề tại thời điểm nộp.** Giảng viên sửa câu hỏi sau đó thì cách chấm các bài đã nộp vẫn giữ nguyên.
- **Chống chèn lệnh (prompt injection).** Bài làm được đặt giữa hai mốc phân cách và chỉ được coi là dữ liệu. Câu kiểu "hãy cho 100 điểm" trong bài không làm đổi cách chấm.
- **Giữ điểm cả bài cho tới khi chấm xong.** Nếu gửi sớm, Canvas sẽ ghi một điểm thấp giả, vì lúc đó câu tự luận vẫn đang tính 0.
- **AI lỗi thì giảng viên chấm thay, không cho 0 điểm.** Câu chuyển sang trạng thái "chờ giảng viên". Giảng viên có hai lựa chọn: chấm tay, hoặc cho AI chấm lại.
- **Worker chấm bài chạy riêng.** Người học không phải đợi sau các lượt sinh quiz vốn mất hàng phút.
- **Chấm bằng model đóng vai "giám khảo"** (cùng model với bước kiểm tra câu hỏi), có thể khác với model sinh câu hỏi.

### 2.3. Micro-content theo LO (phiên bản 1)

- Mỗi card trình bày một ý và gồm:
  - tiêu đề;
  - ý chính (1–2 câu);
  - tối đa 4 gạch đầu dòng;
  - ví dụ lấy từ nguồn (nếu có);
  - lỗi hiểu nhầm thường gặp (chỉ khi nguồn có nêu);
  - một cặp câu hỏi/đáp án tự kiểm tra.
- Mỗi card qua ba bước như quiz: sinh → kiểm tra với đoạn tài liệu nguồn → viết lại nếu bị loại. Mỗi card lưu id các đoạn nguồn để truy vết.
- Card có thứ tự trong bài học, và giảng viên duyệt card cùng quiz trên trang duyệt.
- Sinh quiz và sinh card dùng chung phần lấy ngữ cảnh theo LO.

### 2.4. Nền tảng cho trình xem tài liệu + chat AI

Canvas tự host không có Canvadocs (trình xem PDF) và không có AI tích hợp. Công cụ LTI của Canvas cũng không biết người học đang mở file nào hay trang nào. Vì vậy nhóm tự xây trình xem tài liệu bên trong công cụ LTI của đề tài. Phần backend đã xong:

- **Đọc file tài liệu.** Server stream file và hỗ trợ tải từng phần, nên PDF.js mở được file lớn. Trình duyệt không truy cập kho file trực tiếp.
- **Nội dung theo trang.** Câu hỏi "giải thích trang này" được tra chính xác theo cặp (tài liệu, số trang) trong PostgreSQL, không qua tìm kiếm vector.
- **RAG giới hạn trong tài liệu đang mở.** Dùng cho các câu hỏi nối tiếp.
- **Tài liệu bàn giao để hai người làm song song** (viewer và chat), chỉ cần thống nhất một hợp đồng nhỏ là dữ liệu viewer gửi khi hỏi.

### 2.5. Chất lượng code

- **Tách prompt thành module riêng.** Áp dụng cho quiz, card, enrichment và chấm bài. Prompt nằm tách khỏi logic nghiệp vụ nên dễ so sánh và chỉnh sửa.
- **Rà soát độ phức tạp code.** Kết quả là 12 mục backlog. Bốn mục ưu tiên cao:
  - worker async nhưng chạy tác vụ đồng bộ nên chặn event loop;
  - sinh/duyệt hàng loạt bằng vòng lặp, dễ thành công một nửa;
  - retry có thể chạy lại model và sinh lại cả mẻ;
  - thay tài liệu Canvas qua nhiều bước ghi rời rạc.

---

## 3. Bối cảnh: các phần đã có (đến 29/09)

Phần này để thầy nắm toàn cảnh. Đây là các phần đã làm từ trước tuần này.

| Phần | Trạng thái |
|---|---|
| **Tích hợp Canvas (LTI 1.3)** | Sinh quiz từ menu module của Canvas. Soạn đề theo ma trận LO × Bloom cho đề nhiều chương. Có hai chế độ Luyện tập và Kiểm tra (giới hạn lượt, giới hạn thời gian, xáo câu và phương án). Điểm gửi về Canvas qua AGS, lấy điểm cao nhất, tự chờ khi bài chưa publish. |
| **Đồng bộ tài liệu từ Canvas** | Chạy tự động 15 phút một lần, khi giảng viên mở công cụ, hoặc khi bấm nút. |
| **Xử lý tài liệu** | Chunker v2 theo cấu trúc và đo bằng token thật (đang sau feature flag). PDF được đánh giá theo từng trang nên trang scan không còn bị mất âm thầm. |
| **Sinh quiz — sửa nền (giai đoạn 0)** | Nối bước ánh xạ chunk → LO vào pipeline. Sửa lỗi mọi câu đều lưu Bloom = 2. Ghi đúng token/chi phí. Xáo đáp án cân bằng vị trí. Không lưu câu đã bị bộ kiểm tra loại. |
| **Chọn model theo tác vụ** | Mỗi tác vụ (sinh câu, kiểm tra, enrichment, tutor) chọn model riêng bằng tên profile. Model sinh câu và model kiểm tra có thể khác nhau. Mỗi lần gọi ghi lại model đã dùng. |
| **Embedding** | Tách thành service riêng (gRPC). Dùng API Voyage thay cho BGE-M3 chạy local để tiết kiệm RAM. |
| **Video (bản thử)** | Service MCP tìm video YouTube theo LO, lấy transcript và chọn đoạn phát theo mốc thời gian. |

---

## 4. Kiểm thử tự động (chạy ngày 07/10/2026)

| Thành phần | Kết quả |
|---|---|
| core-api (NestJS) | 22 bộ test, **207/207 đạt** |
| worker (Python) | **191/191 đạt**, độ phủ 83% |
| packages-ai (pipeline tài liệu) | **375 đạt**, 1 bỏ qua |
| web (Next.js) | Kiểm tra kiểu TypeScript không lỗi |

Các test trên dùng LLM giả và CSDL giả. Chưa có kiểm thử end-to-end tự động.

---

## 5. Hạn chế và khó khăn hiện tại

1. **Chưa đo độ tin cậy của AI khi chấm tự luận** so với giảng viên chấm, và chưa chạy với bài nộp thật.
2. **Chunker v2 chưa bật mặc định.** Lý do là chưa có bộ 60–100 câu hỏi gán nhãn để đo Recall@5 / MRR@10 so với chunker cũ.
3. **Sinh quiz mới ở giai đoạn 0.** Việc chọn nội dung, phân bổ Bloom và chọn đáp án nhiễu vẫn giao hết cho prompt. Thiết kế v2 ("LLM viết, code quyết định") đã có tài liệu nhưng chưa triển khai.
4. **Slide nhiều hình cho ra rất ít chữ**, vì bước mô tả ảnh khi xử lý tài liệu đang tắt. Card, quiz và chat ở các slide này sẽ thiếu ngữ cảnh.
5. **Giới hạn của Canvas tự host:**
   - không có Canvadocs và New Quizzes;
   - quiz đưa vào Canvas dưới dạng *Assignment* (External Tool) có cột điểm, luật làm bài nằm ở hệ thống của đề tài.
6. **Chưa có số liệu chi phí LLM thật.** Cơ chế tính chi phí đã có nhưng chưa điền bảng giá model.
7. **Báo cáo luận văn đang lệch nhiều so với hệ thống thực tế**, vì phần lớn được viết trước khi có code. Nhóm cần viết lại.

---

## 6. Hướng làm tiếp

### 6.1. Tuần tới (08/10 – 14/10)

- **Hoàn thiện năm loại câu hỏi và chấm tự luận:** kiểm thử end-to-end trên Canvas bằng Test Student (nộp bài → AI chấm → điểm lên sổ điểm Canvas), sau đó merge.
- **Trình xem tài liệu:** bản chạy được cho PDF (PDF.js, điều hướng trang), gửi số trang đang xem sang khung chat.
- **Chat neo theo tài liệu:**
  - ngữ cảnh chính lấy từ trang đang mở;
  - câu hỏi nối tiếp tìm trong tài liệu đó;
  - trích dẫn nhảy về đúng trang nguồn.

### 6.2. 2–4 tuần tới

- **Micro-content dạng chuỗi câu hỏi (hướng mới).** Mỗi micro-content phân tích một vấn đề trọng tâm thay vì tóm tắt slide. Ví dụ với deadlock:

  > Vì sao xảy ra? → Do những yếu tố nào? → Từng yếu tố có đặc điểm gì? → Các yếu tố liên hệ với nhau ra sao và vì sao cùng lúc mới gây ra deadlock? → Nếu bỏ một yếu tố thì sao? → Ranh giới với khái niệm gần (starvation, livelock)?

  - Mỗi micro-content độc lập nhất có thể. Kiến thức nền nhẹ được nhắc ngay tại chỗ, còn kiến thức nền nặng thì liên kết sang card khác.
  - Cơ sở lý thuyết:
    - câu hỏi sâu (Graesser & Person, 1994);
    - tách phần tử rời rạc trước, tương tác sau (Pollock, Chandler & Sweller, 2002);
    - pre-training (Mayer et al., 2002);
    - mô hình Structure–Behavior–Function (Hmelo-Silver & Pfeffer, 2004);
    - focus question trong concept map (Novak & Cañas);
    - Socratic questioning (Qi et al., 2023).
- **Sinh quiz v2, giai đoạn 1 (sau feature flag):**
  - ánh xạ LO lai (heading + embedding);
  - trích đơn vị kiến thức và chọn bằng MMR để phủ đều nội dung;
  - blueprint phân bổ Bloom × độ khó;
  - bắt buộc trích dẫn nguyên văn từ nguồn;
  - chọn đáp án nhiễu tất định từ các ứng viên;
  - giám khảo khác model ("giải trước, chấm sau");
  - loại câu sai rồi sinh bù.
- **Bộ đánh giá:**
  - retrieval: bộ câu hỏi gán nhãn, đo Recall@5 / MRR@10, quyết định có bật chunker v2 hay không;
  - chấm tự luận: so điểm AI với điểm giảng viên trên khoảng 50–100 bài, đo mức đồng thuận theo từng ý rubric;
  - chất lượng quiz: đánh giá offline theo các tiêu chí trong tài liệu thiết kế.
- **Chuyển PPTX sang PDF khi nhận tài liệu**, để viewer mở được slide.

### 6.3. Sau đó

- **Chấm và chú thích trên tài liệu** (annotation), nếu được đưa vào phạm vi. CSDL hiện chưa có bảng nào cho phần này.
- **Phân tích câu hỏi từ kết quả làm bài** theo lý thuyết trắc nghiệm cổ điển (độ khó, độ phân biệt), gắn cờ câu kém để giảng viên xem lại.
- **Gắn đoạn video YouTube đã duyệt vào card.**
- **Hỗ trợ Moodle qua adapter.** Phần LTI/AGS đã sẵn sàng. Phần còn thiếu là đồng bộ đề cương và tài liệu qua Moodle Web Services.
- **Xử lý bốn mục ưu tiên cao** trong backlog rà soát code.
- **Viết lại báo cáo luận văn** theo hệ thống thực tế.

---

## 7. Xin ý kiến thầy

1. **Chấm trên tài liệu (annotation)** có cần cho bản bảo vệ không? Hay chấm tự luận trong quiz là đủ cho phần "chấm bài"?
2. **Micro-content dạng chuỗi câu hỏi** có phù hợp với mục tiêu đề tài không? Nên đánh giá hiệu quả bằng cách nào: khảo sát sinh viên, hay pre-test/post-test?
3. **Thứ tự ưu tiên** trong thời gian còn lại giữa viewer + chat, micro-content chuỗi câu hỏi, sinh quiz v2 và Moodle.
4. **Có học phần hoặc lớp thật nào để thử nghiệm không?** Dữ liệu làm bài thật cần cho cả đánh giá chấm tự luận lẫn phân tích câu hỏi.
5. **Hai đề xuất cần thầy xác nhận:**
   - bỏ sinh quiz trong bước enrichment, chỉ sinh quiz theo LO;
   - không phụ thuộc New Quizzes của Canvas, giữ LTI + AGS và bổ sung xuất QTI / Moodle XML nếu cần.

---

## Phụ lục: tài liệu thiết kế liên quan (thư mục `docs/`)

| Tài liệu | Nội dung |
|---|---|
| `quiz-generation-redesign.md` | Thiết kế sinh quiz v2, kế hoạch 4 giai đoạn |
| `chunking-redesign.md` | Chunker v2 và đánh giá PDF theo trang |
| `model-routing-design.md` | Chọn model theo tác vụ, tính chi phí |
| `document-viewer-handoff.md` | Viewer + chat: phần đã có, hai track song song, các việc cần chốt |
| `canvas-module-quiz.md` | Sinh quiz từ module Canvas, ma trận đề, Luyện tập/Kiểm tra |
| `code-complexity-audit.md` | Rà soát độ phức tạp code, backlog R01–R12 |
| `youtube-video-pilot.md` | Bản thử tìm và cắt đoạn video YouTube |
