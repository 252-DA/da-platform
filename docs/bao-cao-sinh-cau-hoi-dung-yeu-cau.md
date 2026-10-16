# Báo cáo: Bảo đảm câu hỏi do AI sinh đúng yêu cầu

**Đề tài:** Hệ thống LMS tự động tạo Micro-Content & Quiz bằng Generative AI (DA Platform)
**Ngày:** 10/2026

Khi sinh câu hỏi, giảng viên chọn **LO, mức Bloom, loại câu, số câu và tài liệu nguồn**. Báo cáo trình bày cách nhóm bảo đảm câu AI sinh ra đúng các yêu cầu đó, và cách kiểm chứng điều này.

---

## 1. "Đúng yêu cầu" nghĩa là gì

| Giảng viên yêu cầu | Câu sinh ra phải bảo đảm |
|---|---|
| LO + tài liệu nguồn | **Đúng nội dung:** câu hỏi về kiến thức của LO, lấy từ tài liệu đã chọn, có căn cứ trong tài liệu |
| (ngầm định) | **Đúng đáp án:** đáp án đúng theo tài liệu, chỉ một phương án đúng, đề đủ thông tin để trả lời; phương án sai đủ hợp lý để sinh viên chưa học không đoán ra đáp án |
| Mức Bloom | **Đúng mức:** câu bắt sinh viên thực hiện đúng thao tác của mức đó |
| Loại câu, số câu | **Đúng hình thức:** đúng cấu trúc của loại câu, đủ số câu |

Mức Bloom của câu được xác định theo **việc sinh viên phải làm để trả lời**, không theo động từ trong câu hỏi (Anderson & Krathwohl, 2001; Krathwohl, 2002).

---

## 2. Vấn đề hiện tại

Hệ thống đã sinh câu từ đúng tài liệu của LO và có một AI kiểm tra đáp án. Tuy vậy, câu sinh ra vẫn có thể lệch yêu cầu. Bốn ví dụ từ môn Dữ liệu lớn, lấy từ dữ liệu nhóm chạy thử. Các câu "đã duyệt" dưới đây do nhóm duyệt bằng tài khoản quản trị, đóng vai giảng viên:

**Ví dụ 1. Yêu cầu mức Vận dụng, câu ra mức Nhớ.**
> *Câu:* "Dựa trên đoạn trích về Earthscope, dữ liệu thu thập được có kích thước là bao nhiêu?" Đáp án: 67 terabyte.
> *Slide trang 5:* "…this observatory records data over 3.8 million square miles, amassing 67 terabytes of data."

Đáp án đúng và có căn cứ, nhưng sinh viên chỉ cần nhớ một con số. Hệ thống vẫn lưu câu này với nhãn "Vận dụng", và câu đã được duyệt.

**Ví dụ 2. Đáp án có căn cứ nhưng câu mơ hồ.**
> *Câu:* "Theo các đoạn trích, dữ liệu lớn thường được mô tả bằng những đặc điểm nào?"
> A. Quy mô, sự đa dạng và độ phức tạp (đáp án) · B. Kích thước, tốc độ sinh, sự đa dạng và tính chính xác · …
> *Lời giải AI viết:* "Đoạn trích [2] và [3] nêu rõ…"

A khớp slide trang 2, nhưng B trùng nguyên văn các đặc điểm nêu trong phát biểu của LO, nên sinh viên học theo LO có thể chọn B. Sinh viên cũng không có "các đoạn trích" mà câu hỏi và lời giải nhắc tới.

**Ví dụ 3. Động từ "giải thích" nhưng thực chất là nhớ.**
> *Câu trả lời ngắn:* "Giải thích ngắn gọn khái niệm dữ liệu lớn dựa trên định nghĩa trong tài liệu." Rubric gồm 3 ý, cả 3 đều là các vế của định nghĩa trên slide.

Câu được gắn mức Hiểu vì có chữ "giải thích", nhưng chép lại đúng định nghĩa là đủ điểm tối đa.

**Ví dụ 4. Không cần học vẫn đoán được đáp án.**
> *Câu:* "Sự phát triển từ kỷ nguyên PC (1 tỷ người dùng) sang kỷ nguyên IoTs với dự kiến 100 tỷ cảm biến vào năm 2025 gây ra áp lực lớn nhất lên những khía cạnh nào của dữ liệu?"
> A. Chỉ về tính chính xác của dữ liệu · B. Kích thước (Volume) và Tốc độ sinh dữ liệu (Velocity) (đáp án) · C. Chỉ về sự đa dạng của các loại cảm biến · D. Giảm bớt nhu cầu về lưu trữ dữ liệu

A và C mở đầu bằng "Chỉ…", nên bị loại ngay. D ngược với chữ "áp lực" trong đề. Đề hỏi "những khía cạnh nào" nhưng chỉ B nêu hai khía cạnh. Sinh viên loại được cả ba phương án sai mà không cần biết Volume hay Velocity là gì, vậy mà câu vẫn được duyệt. Lỗi này ngược với ví dụ 2: ở ví dụ 2 phương án sai *đúng quá*, ở đây phương án sai *sai quá*. Nhiều câu đã duyệt khác có cùng kiểu: đáp án liệt kê đủ các đặc điểm, còn phương án sai là "chỉ một đặc điểm".

**Sáu nguyên nhân:**
1. **Đoạn nguồn không đủ cho mức yêu cầu.** Đoạn Earthscope chỉ nêu một sự kiện (ví dụ 1).
2. **Prompt chỉ ghi tên mức Bloom**, không giải thích mức đó yêu cầu sinh viên làm gì (ví dụ 1, 3). Với câu trắc nghiệm, prompt cũng không nói gì về phương án sai (ví dụ 4).
3. **Căn cứ AI nêu ra không được kiểm tra** (ví dụ 2: "đoạn trích [2] và [3]").
4. **Lỗi cách viết không ai bắt** ("theo các đoạn trích" ở ví dụ 1 và 2; phương án sai mở đầu bằng "Chỉ…" ở ví dụ 4).
5. **AI kiểm tra được xem đáp án trước** và chỉ xét đáp án có khớp tài liệu không. Không có bước nào kiểm tra mức Bloom thực (ví dụ 1, 2, 3). Với phương án sai, AI kiểm tra chỉ đòi chúng phải "sai rõ ràng" (*clearly wrong*) để tránh câu có hai đáp án, nên phương án sai lộ liễu như ở ví dụ 4 lại càng dễ đạt.
6. **Câu sai không được sửa có định hướng, và giảng viên không được chỉ ra chỗ nghi ngờ** (ví dụ 1 và 4 đã được duyệt).

---

## 3. Cách xử lý

Quy trình gồm 6 bước. Mỗi bước sửa một nguyên nhân ở mục 2:

```text
[1] Chọn nguồn → [2] Sinh câu (prompt hướng dẫn mức Bloom và phương án sai)
  → [3] Code kiểm tra trích dẫn → [4] Code kiểm tra cách viết
  → [5] Giám khảo AI: giải trước, chấm sau
  → [6] Sửa theo lý do / loại → giảng viên duyệt kèm lý do
```

Câu không đạt ở bước 3, 4 hoặc 5 được sửa theo lý do cụ thể; sau 2 lần vẫn không đạt thì bị loại và sinh câu khác thay vào. Cảnh báo về mức Bloom và phương án sai không chặn câu, mà đi kèm câu đến giảng viên.

Phương án sai (ví dụ 4) không tách thành bước riêng. Lỗi này có ba phần: AI không được dặn cách viết phương án sai, có dấu hiệu hình thức lộ đáp án, và có phương án vô lý về nội dung. Ba phần đó lần lượt cùng loại với việc của bước 2, 4 và 5, nên được gộp vào các bước này. Cách đo chính xác nhất là xem sinh viên thật có chọn phương án sai hay không. Việc này chỉ làm được sau khi sinh viên làm bài, nên nằm ở mục 4.

### Bước 1. Chọn đoạn nguồn đủ cho mức Bloom

**Vấn đề.** Ở ví dụ 1, đoạn slide về Earthscope chỉ nêu một sự kiện (67 TB). Giảng viên yêu cầu mức Vận dụng, nhưng trong đoạn không có cách làm nào để sinh viên áp dụng, nên AI chỉ có thể hỏi lại con số.

**Vì sao làm thế này.** Thang Bloom sửa đổi định nghĩa Vận dụng là *"thực hiện hoặc sử dụng một quy trình trong một tình huống cụ thể"* (Krathwohl, 2002). Muốn ra câu Vận dụng thì nguồn phải có quy trình để áp dụng. Prompt tốt đến đâu cũng không bù được việc nguồn thiếu nội dung, vì vậy phải xử lý ngay từ bước chọn nguồn.

**Cách làm.** Phân loại từng đoạn slide: sự kiện, định nghĩa, quy trình, ví dụ, so sánh. Khi yêu cầu từ mức Vận dụng trở lên, chỉ chọn các đoạn có quy trình hoặc ví dụ áp dụng. Không có đoạn phù hợp thì báo giảng viên "tài liệu đã chọn chưa đủ nội dung cho mức này", thay vì sinh câu rồi gắn nhãn sai.

### Bước 2. Hướng dẫn mức Bloom và phương án sai trong prompt

**Vấn đề.** Prompt hiện chỉ có một dòng "Bloom level required: apply". AI phải tự đoán "apply" nghĩa là gì, và thường đoán theo động từ. Ví dụ 3 có chữ "giải thích" nên được coi là mức Hiểu, dù chỉ cần chép định nghĩa.

**Vì sao làm thế này.** Các nghiên cứu sinh câu hỏi theo mức Bloom đều đưa định nghĩa của mức vào prompt, và cho kết quả khả quan:
- **Doughty et al. (2024):** prompt có định nghĩa mức Bloom của mục tiêu học tập và ví dụ loại câu. So 651 câu GPT-4 sinh với 449 câu do người viết trong 6 môn Python, câu của GPT-4 rõ ràng, có một đáp án đúng và bám mục tiêu học tập tốt.
- **Elkins et al. (2024):** câu hỏi sinh theo từng mức Bloom được giáo viên dùng để soạn quiz. Quiz soạn từ câu sinh ra không kém quiz giáo viên tự viết.
- **Scaria et al. (2024):** thử 5 LLM; khi được cung cấp đủ ngữ cảnh, các model sinh được câu tốt ở nhiều mức Bloom, nhưng chất lượng chênh nhau nhiều giữa các model.

Các nghiên cứu này cho thấy cách làm là khả thi, nhưng không tách riêng được tác dụng của phần định nghĩa mức trong prompt. Vì vậy hiệu quả trên hệ thống của nhóm phải được đo lại (mục 4).

**Cách làm.** Với mức được yêu cầu, prompt nêu rõ:
- sinh viên phải làm gì ở mức đó;
- 1–2 câu mẫu đúng mức;
- lỗi cần tránh, ví dụ: "có chữ *giải thích* nhưng đáp án chỉ là chép định nghĩa thì vẫn là mức Nhớ".

**Phương án sai.** Prompt hiện không nói gì về phương án sai. Haladyna, Downing & Rodriguez (2002) tổng hợp 31 hướng dẫn viết câu trắc nghiệm, trong đó có: mọi phương án sai đều phải hợp lý; lấy lỗi sinh viên hay mắc làm phương án sai; tránh từ tuyệt đối như "luôn", "không bao giờ"; các phương án dài tương đương nhau. Prompt mới yêu cầu đúng các điều này, và bắt AI ghi kèm mỗi phương án sai **hiểu lầm mà nó đại diện**, ví dụ "nhầm tốc độ sinh dữ liệu với quy mô dữ liệu". Hiểu lầm ghi kèm là căn cứ để giám khảo xét ở bước 5 và để giảng viên xem khi duyệt.

Prompt chỉ cải thiện được một phần. Feng et al. (2024) thử nhiều cách cho LLM sinh phương án sai cho câu trắc nghiệm toán: LLM viết được phương án sai hợp lệ về nội dung, nhưng đoán kém lỗi mà sinh viên thật hay mắc.

### Bước 3. Bắt AI trích nguyên văn, code kiểm tra

**Vấn đề.** AI hay viết "theo tài liệu" hoặc "đoạn trích [2] nêu rõ" (ví dụ 2), nhưng không ai kiểm tra tài liệu có thật sự nói như vậy không.

**Vì sao làm thế này.** Gao et al. (2023) đo chất lượng trích dẫn khi LLM viết câu trả lời kèm nguồn. Ngay cả hệ thống tốt nhất, trên tập ELI5 vẫn có khoảng **50%** câu trả lời không được nguồn trích dẫn ủng hộ đầy đủ. Nghĩa là AI *nói* có căn cứ thì chưa đủ để tin. Cách kiểm tra rẻ và chắc chắn nhất là bắt AI chép nguyên văn câu làm căn cứ, rồi để code so xem câu đó có trong slide hay không.

**Cách làm.** Mỗi câu hỏi phải kèm một câu trích nguyên văn từ slide. Code so chuỗi sau khi chuẩn hoá khoảng trắng và Unicode; không khớp thì trả câu về sửa. Bước này chỉ chứng minh căn cứ *có thật*. Căn cứ có *đủ* để chứng minh đáp án hay không thì giám khảo kiểm tra ở bước 5.

**Ví dụ.** Câu Earthscope trích "amassing 67 terabytes of data". Code tìm thấy chuỗi này ở slide trang 5, nên câu đạt bước này.

### Bước 4. Code kiểm tra cách viết

**Vấn đề.** Ví dụ 1 và 2 đều có cụm "dựa trên đoạn trích" hoặc "theo các đoạn trích". Sinh viên không có đoạn trích đó, nên câu không tự đứng được. Ở ví dụ 4, hai phương án sai mở đầu bằng "Chỉ…" còn đáp án thì không, nên sinh viên loại được chúng nhờ cách viết. Đây là lỗi viết câu, không phải lỗi kiến thức.

**Vì sao làm thế này.** Moore et al. (2023) so hai cách phát hiện 19 loại lỗi viết câu trắc nghiệm trên 200 câu thuộc 4 lĩnh vực. Bộ kiểm tra tự động viết riêng cho từng loại lỗi bắt được **91%** lỗi mà người chấm tìm ra, GPT-4 bắt được **79%**. Bộ kiểm tra này không thuần là code: các lỗi khó như câu mơ hồ hay phương án sai vô lý vẫn dùng model ngôn ngữ. Phần nhóm dựa vào là các lỗi kiểm được bằng độ dài và từ khoá. Với lỗi "đáp án đúng là phương án dài nhất", chỉ cần so độ dài là đạt F1 0,80–1,00 trên 4 lĩnh vực, trong khi GPT-4 chỉ đạt 0,00–0,44. "Dùng từ tuyệt đối" cũng nằm trong 19 lỗi này. Vì vậy những lỗi có dấu hiệu hình thức rõ được giao cho code: rẻ hơn, cho cùng kết quả mỗi lần chạy, và chính xác hơn GPT-4.

**Cách làm.** Code kiểm tra:
- cụm từ phụ thuộc ngữ cảnh ("theo đoạn trích", "đoạn [2]", "tài liệu trên");
- dấu hiệu lộ đáp án: từ tuyệt đối ("chỉ", "luôn", "không bao giờ", "duy nhất") có ở phương án sai mà không có ở đáp án; đáp án dài hơn hẳn các phương án còn lại;
- cấu trúc đúng loại câu;
- các phương án không trùng nhau;
- câu không trùng với câu đã có.

Câu vi phạm được trả về sửa, kèm tên lỗi.

**Ví dụ 4 bị bắt một phần ở đây:** A và C có "Chỉ…", B thì không. Phương án D ("Giảm bớt nhu cầu về lưu trữ dữ liệu") không có dấu hiệu hình thức nào. D vô lý về nội dung, nên phải để giám khảo xét ở bước 5.

### Bước 5. Giám khảo AI: làm thử trước, chấm sau

**Ý tưởng.** Giống như nhờ một đồng nghiệp **làm thử đề trước khi đưa đáp án**. Nếu đồng nghiệp làm ra khác đáp án, hoặc lưỡng lự giữa hai phương án, thì câu đó có vấn đề. "Giám khảo" ở đây là một lần gọi AI thứ hai, dùng model khác với AI đã viết câu hỏi.

**Cách kiểm tra hiện tại bỏ sót gì.** AI kiểm tra hiện được đưa sẵn đáp án rồi hỏi "đáp án này có đúng không". Với ví dụ 2:

```text
Slide:    "Data whose scale, diversity and complexity require…"
Câu hỏi:  A. Quy mô, đa dạng, phức tạp    B. Kích thước, tốc độ sinh, đa dạng, chính xác    …
Đáp án:   A
Câu hỏi cho AI kiểm tra: "A có đúng với slide không? Các phương án còn lại có sai rõ ràng không?"
```

AI thấy slide nói "scale, diversity, complexity" nên trả lời "đúng". Vì đã được báo trước A là đáp án, nó chỉ cần xác nhận A và coi B là sai. Câu được cho qua, dù B hợp lý với sinh viên học theo LO. Cách kiểm tra này cũng không xét mức Bloom, nên ví dụ 1 và 3 lọt qua.

**Cách làm mới: hai lượt.**

**Lượt 1: làm thử, không có đáp án.** Giám khảo nhận phát biểu LO, slide và câu hỏi, các phương án đã xáo thứ tự, không có đáp án. Sinh viên học cả phát biểu LO lẫn slide, nên giám khảo cũng phải có cả hai. Giám khảo chọn một phương án, liệt kê mọi phương án mà người đã học có thể bảo vệ là đúng, hoặc trả lời "tài liệu không đủ để trả lời". Hệ thống so câu trả lời với đáp án:

| Giám khảo trả lời | Nghĩa là | Xử lý |
|---|---|---|
| Trùng đáp án, chỉ một phương án bảo vệ được | Đáp án ổn | Sang lượt 2 |
| Chọn phương án khác | Đáp án sai, hoặc câu mơ hồ | Gắn cờ, gửi đi sửa |
| Từ hai phương án bảo vệ được trở lên | Câu mơ hồ | Gắn cờ, gửi đi sửa |

Lượt 1 chạy **hai lần**, mỗi lần các phương án xếp theo một thứ tự khác. Nếu lần đầu giám khảo chọn A mà lần sau chọn B, nghĩa là nó đang phân vân giữa A và B, tức câu mơ hồ.

**Ví dụ 2 bị bắt ở đây, nhưng chỉ khi giám khảo có phát biểu LO.** Khi chạy thử (phụ lục), giám khảo chỉ có slide thì chọn trùng đáp án cả hai lần, vì slide ghi đúng "scale, diversity and complexity". Có thêm phát biểu LO, một lần giám khảo chọn B, và cả hai lần đều nêu hai phương án bảo vệ được. Giám khảo không lần nào tự trả lời "có nhiều phương án đúng", nên hệ thống gắn cờ theo danh sách phương án bảo vệ được chứ không chỉ theo phương án giám khảo chọn.

Lượt 1 không bắt được phương án sai quá dễ như ở ví dụ 4: giám khảo chọn trùng đáp án thì câu qua, kể cả khi chọn được chỉ nhờ loại trừ.

**Lượt 2: chấm, lúc này mới được xem đáp án.** Lượt này chỉ chạy khi lượt 1 trùng đáp án. Giám khảo trả lời bốn câu:
1. Slide có ủng hộ đáp án không?
2. Câu có hỏi về nội dung của LO không?
3. Câu thực sự ở mức Bloom nào, và vì sao?
4. Với câu trắc nghiệm: từng phương án sai có thể đánh lừa sinh viên chưa nắm LO không, có đúng với hiểu lầm mà AI sinh câu đã ghi kèm không, hay loại được chỉ vì mâu thuẫn với đề?

**Ví dụ 1 và 3 bị bắt ở đây.** Khi chạy thử, ở lượt 1 giám khảo chọn "67 terabyte" cả bốn lần, trùng đáp án. Sang lượt 2, giám khảo đánh giá ví dụ 1 ở mức Nhớ vì sinh viên "chỉ cần tìm và nhận diện trực tiếp thông tin con số 67 terabytes", trong khi yêu cầu là Vận dụng. Ví dụ 3 cũng bị đánh giá mức Nhớ vì đáp án "đã được nêu gần như nguyên văn trong slide", trong khi yêu cầu là Hiểu.

**Ví dụ 4 bị bắt nốt ở đây.** Khi chạy thử, ở câu 4 của lượt 2, giám khảo chỉ ra cả ba phương án sai đều loại được mà không cần kiến thức: A và C vì chữ "chỉ", D vì "mâu thuẫn trực tiếp với ý nghĩa của dữ liệu lớn".

**Vì sao làm như vậy.**

| Lựa chọn | Lý do | Căn cứ |
|---|---|---|
| Dùng AI làm giám khảo | GPT-4 làm giám khảo đồng ý với người chấm trên 80%, ngang mức hai người chấm đồng ý với nhau, nên dùng để sàng lọc số lượng lớn được | Zheng et al. (2023) |
| Giám khảo dùng model khác model sinh câu | LLM có xu hướng chấm dễ cho văn bản do chính nó viết: càng nhận ra văn của mình thì càng thiên vị | Panickssery et al. (2024) |
| Lượt 1 không cho xem đáp án | Đã thấy đáp án thì giám khảo chỉ xác nhận đáp án đó, như cách hiện tại. Phải tự làm thì mới lộ ra câu có hai đáp án hợp lý | Lập luận thiết kế của nhóm; hiệu quả được đo ở mục 4 |
| Lượt 1 có cả phát biểu LO | Sinh viên học cả LO lẫn slide. Khi chỉ có slide, giám khảo không thấy ví dụ 2 mơ hồ | Chạy thử của nhóm (phụ lục) |
| Xáo phương án, làm hai lần | Chỉ đổi thứ tự phương án đã làm độ chính xác của LLM chênh 13–75%, và việc này xảy ra khi model phân vân giữa 2–3 phương án. Nhóm dùng hiện tượng này để phát hiện câu mơ hồ | Pezeshkpour & Hruschka (2024) |
| Kết quả Bloom chỉ là cảnh báo | LLM đánh giá câu hỏi chưa ngang chuyên gia. Hệ thống chỉ hiện "giám khảo cho là mức Nhớ" để giảng viên xem, không tự đổi nhãn hay tự loại câu. Mục 4 đo giám khảo đúng đến đâu | Scaria et al. (2024) |
| Nhận xét về phương án sai xử lý giống kết quả Bloom | Phát hiện phương án sai vô lý chưa đáng tin: với lỗi này, F1 của GPT-4 dao động từ 0,11 đến 0,78 tùy môn, của bộ kiểm tra tự động (dùng model ngôn ngữ cho lỗi này) từ 0,12 đến 0,83. Khi chạy thử, hai giám khảo nhận xét ngược nhau về phương án sai của ví dụ 1 | Moore et al. (2023); phụ lục |

### Bước 6. Sửa theo lý do cụ thể, rồi đưa giảng viên duyệt kèm lý do

**Vấn đề.** Câu bị bắt ở bước 3–5 nếu chỉ bị loại thì đề sẽ thiếu câu so với yêu cầu. Còn câu được giữ lại thì giảng viên duyệt mà không biết hệ thống nghi ngờ điều gì: câu Earthscope đã được duyệt vì nhìn qua thì đáp án đúng.

**Vì sao làm thế này.**
- **Sửa phải kèm lý do cụ thể.**
  - Huang et al. (2024): LLM tự xem lại bài mình mà không có phản hồi từ bên ngoài thì thường không sửa được lỗi, có khi còn tệ hơn.
  - Shinn et al. (2023): khi model nhận phản hồi từ bên ngoài (kết quả chạy test) rồi tự rút kinh nghiệm, nó đạt **91%** trên bộ bài lập trình HumanEval, so với **80%** của GPT-4 trước đó.
  - Vì vậy vòng sửa luôn gửi kèm lý do cụ thể từ code hoặc giám khảo, không yêu cầu kiểu "hãy tự kiểm tra lại".
- **Hiện lý do cho giảng viên.** Bộ 18 nguyên tắc thiết kế hệ thống AI của Amershi et al. (2019) có nguyên tắc *"cho người dùng biết vì sao hệ thống làm như vậy"*. Với hệ thống của nhóm, giảng viên chỉ phát hiện được câu Earthscope sai mức nếu hệ thống chỉ ra điều đó.

**Cách làm.**
- Sửa tối đa 2 lần, mỗi lần kèm lý do, ví dụ: "giám khảo đánh giá mức Nhớ, yêu cầu là Vận dụng; đoạn nguồn chỉ có số liệu".
- Vẫn không đạt thì loại câu và sinh câu khác thay vào, để đủ số câu.
- Lưu riêng **mức được yêu cầu** và **mức giám khảo đánh giá**. Mức chính thức của câu do giảng viên xác nhận khi duyệt.
- Trang duyệt hiện kết quả kiểm tra. Ví dụ với câu Earthscope:

```text
⚠ Mức Bloom: yêu cầu Vận dụng, giám khảo đánh giá Nhớ (chỉ nhắc lại một con số)
⚠ Cách viết: "Dựa trên đoạn trích…", sinh viên không có đoạn trích này
✓ Căn cứ: "…amassing 67 terabytes of data." (slide trang 5) [mở trang]
✓ Giải trước khi xem đáp án: giám khảo chọn "67 terabyte", trùng đáp án
```

Giảng viên vẫn là người quyết định cuối: duyệt, sửa hoặc từ chối.

---

## 4. Kiểm chứng

**Câu hỏi cần trả lời:** quy trình mới có làm tăng tỉ lệ câu đúng yêu cầu so với hiện tại không?

**Cách làm:**
1. Lập khoảng 30–50 yêu cầu sinh, trải trên nhiều LO, các mức Bloom 1–4 và các loại câu.
2. Sinh câu cho mỗi yêu cầu bằng hai cách: quy trình hiện tại và quy trình mới.
3. Hai giảng viên hoặc trợ giảng chấm độc lập từng câu mà **không biết câu do cách nào sinh** và **không biết mức Bloom được yêu cầu**. Mỗi câu chấm: đúng nội dung LO không; đáp án đúng và duy nhất không; mức Bloom thực là mức nào; với câu trắc nghiệm, có loại được phương án sai mà không cần học không.
4. Đo mức đồng thuận giữa hai người chấm bằng Cohen's κ cho từng tiêu chí (Cohen, 1960). Câu nào hai người chấm khác nhau thì hai người thảo luận để thống nhất một nhãn, giống cách Moore et al. (2023) làm với bộ câu của họ.
5. So nhãn đã thống nhất với yêu cầu ban đầu.

**Kết quả cần báo cáo:**

| | Quy trình hiện tại | Quy trình mới |
|---|---|---|
| % câu đúng mức Bloom yêu cầu | | |
| % câu đúng nội dung LO | | |
| % câu có đáp án đúng và duy nhất | | |
| % câu trắc nghiệm loại được phương án sai mà không cần học | | |
| Số câu phải sửa / bị loại | | |
| Độ đồng thuận giữa hai người chấm (κ) | | |

Ngoài ra, so **đánh giá Bloom của giám khảo AI** với **nhãn đã thống nhất của người chấm** (cũng bằng κ), để biết giám khảo ở bước 5 của mục 3 đáng tin đến đâu.

**Khi đã có bài làm của sinh viên.** Hệ thống đã lưu phương án sinh viên chọn ở mỗi lượt làm. Phương án sai được dưới 5% thí sinh chọn được coi là không có tác dụng (Tarrant et al., 2009). Đây là thước đo trực tiếp nhất cho phương án sai, vì dựa trên lựa chọn của sinh viên thật chứ không dựa trên phán đoán của AI hay người chấm. Khi câu có đủ lượt làm, hệ thống báo các phương án này để giảng viên sửa.

---

## 5. Hiện trạng

| Bước | Đã có | Cần bổ sung |
|---|---|---|
| 1. Chọn nguồn | Lấy đúng đoạn slide của LO, trong tài liệu giảng viên chọn | Phân loại đoạn; chọn đoạn theo mức Bloom |
| 2. Prompt | Ghi tên mức Bloom | Định nghĩa mức, câu mẫu, lỗi cần tránh; yêu cầu về phương án sai, ghi kèm hiểu lầm mỗi phương án đại diện |
| 3. Trích dẫn | Lưu id đoạn nguồn | Trích nguyên văn; code kiểm tra |
| 4. Cách viết | Kiểm cấu trúc theo loại câu; chống trùng khi câu giống hệt trong cùng LO | Luật phát hiện cụm phụ thuộc ngữ cảnh và dấu hiệu lộ đáp án; phát hiện câu trùng ý |
| 5. Giám khảo | AI kiểm tra đáp án với tài liệu (thấy đáp án trước); cấu hình được model riêng | Giải trước khi xem đáp án, có phát biểu LO, giải hai lần; chấm mức Bloom, nội dung LO và từng phương án sai. Prompt hai lượt đã chạy thử trên 4 câu (phụ lục) |
| 6. Sửa & duyệt | Sửa theo lý do của AI kiểm tra, câu còn sai không lưu; giảng viên duyệt/sửa/từ chối | Sinh câu thay thế; lưu mức giám khảo đánh giá cạnh mức yêu cầu; hiện kết quả kiểm tra trên trang duyệt |
| Sau khi sinh viên làm bài | Lưu phương án sinh viên chọn ở mỗi lượt làm | Thống kê tỉ lệ chọn từng phương án; báo phương án sai ít người chọn |

---

## 6. Xin ý kiến thầy

1. Cách xác định mức Bloom theo việc sinh viên phải làm (mục 1) có cần bổ sung hay điều chỉnh gì không?
2. Thầy có thể giới thiệu 1–2 giảng viên hoặc trợ giảng làm người chấm cho phần kiểm chứng ở mục 4 không?
3. Nên chọn môn nào để thử nghiệm, để có đủ nội dung cho các mức Bloom 3–4?

---

## Phụ lục. Chạy thử giám khảo hai lượt trên bốn ví dụ

Ngày 16/10/2026, nhóm chạy thử prompt giám khảo của bước 5 trên đúng bốn câu ở mục 2, mỗi cấu hình một lần. Cả bốn câu đều bị gắn cờ, nhưng ví dụ 2 chỉ bị bắt khi giám khảo có phát biểu LO. Kết quả chỉ minh hoạ cơ chế, chưa phải phép đo; phép đo là phần kiểm chứng ở mục 4.

| Ví dụ | Mức yêu cầu | Giám khảo | Lượt 1, chỉ slide | Lượt 1, slide + LO | Lượt 2 | Kết quả |
|---|---|---|---|---|---|---|
| 1. Earthscope | Vận dụng | Gemini 3.6 Flash | 2/2 trùng đáp án | 2/2 trùng đáp án | Mức Nhớ; cả 3 phương án sai loại được nhờ đơn vị đo | Gắn cờ: sai mức Bloom |
| 2. Đặc điểm dữ liệu lớn | Nhớ | DeepSeek (chính model sinh câu) | 2/2 trùng đáp án | 1/2 chọn B; cả 2 lần nêu 2 phương án bảo vệ được | Mức Nhớ, đúng yêu cầu | Gắn cờ: câu mơ hồ, chỉ khi có LO |
| 3. Khái niệm dữ liệu lớn (trả lời ngắn) | Hiểu | DeepSeek (chính model sinh câu) | Không chạy | Không chạy | Mức Nhớ: đáp án "nêu gần như nguyên văn trong slide" | Gắn cờ: sai mức Bloom |
| 4. Kỷ nguyên PC → IoT | Hiểu | DeepSeek | 2/2 trùng đáp án | 2/2 trùng đáp án | Mức Hiểu, đúng yêu cầu; cả 3 phương án sai loại được không cần kiến thức | Gắn cờ: phương án sai |

**Cách chạy.**
- Lượt 1 chạy theo hai cách: chỉ có slide, và có slide kèm phát biểu LO. Mỗi cách chạy với hai thứ tự phương án. Câu trả lời ngắn (ví dụ 3) chỉ chạy lượt 2.
- Lượt 2 chạy cho cả bốn câu để có đủ dữ liệu, dù theo thiết kế lượt này chỉ chạy khi lượt 1 trùng đáp án.
- Giám khảo dùng model khác model sinh câu khi có thể. Ví dụ 2 và 3 do DeepSeek sinh, nhưng hôm đó các model Gemini đã hết quota miễn phí trong ngày, nên phải dùng chính DeepSeek làm giám khảo. Giám khảo chấm câu của chính model mình thì có xu hướng thiên vị (Panickssery et al., 2024), nên nếu nó vẫn bắt được lỗi thì kết quả càng đáng tin.
- Câu sinh theo quy trình hiện tại chưa có câu trích nguyên văn và hiểu lầm ghi kèm, nên câu 4 của lượt 2 chỉ xét phương án sai có loại được mà không cần kiến thức hay không.

**Ba điều rút ra.**
1. Lượt 1 phải có phát biểu LO. Chỉ có slide, giám khảo coi ví dụ 2 là ổn.
2. Giám khảo không lần nào tự trả lời "có nhiều phương án đúng", kể cả khi chính nó nêu hai phương án bảo vệ được. Hệ thống phải gắn cờ theo danh sách đó.
3. Nhận xét về phương án sai chưa ổn định. Với ví dụ 1, Gemini 3 Flash coi cả ba phương án sai là hợp lý, còn Gemini 3.6 Flash cho rằng cả ba loại được nhờ đơn vị đo (số thiết bị, diện tích, không phải dung lượng). Hai giám khảo này cùng đánh giá mức Nhớ. Vì vậy nhận xét về phương án sai chỉ là cảnh báo cho giảng viên.

---

## Tài liệu tham khảo

- Amershi, S. et al. (2019). Guidelines for Human-AI Interaction. *CHI 2019*. https://doi.org/10.1145/3290605.3300233
- Anderson, L. W. & Krathwohl, D. R. (Eds.) (2001). *A Taxonomy for Learning, Teaching, and Assessing: A Revision of Bloom's Taxonomy of Educational Objectives*. Longman.
- Cohen, J. (1960). A Coefficient of Agreement for Nominal Scales. *Educational and Psychological Measurement* 20(1), 37–46. https://doi.org/10.1177/001316446002000104
- Doughty, J. et al. (2024). A Comparative Study of AI-Generated (GPT-4) and Human-crafted MCQs in Programming Education. *ACE 2024*. https://doi.org/10.1145/3636243.3636256
- Elkins, S., Kochmar, E., Cheung, J. C. K., Serban, I. (2024). How Teachers Can Use Large Language Models and Bloom's Taxonomy to Create Educational Quizzes. *AAAI 2024*. https://doi.org/10.1609/aaai.v38i21.30353
- Feng, W., Lee, J., McNichols, H., Scarlatos, A., Smith, D., Woodhead, S., Otero Ornelas, N., Lan, A. (2024). Exploring Automated Distractor Generation for Math Multiple-choice Questions via Large Language Models. *Findings of NAACL 2024*. https://aclanthology.org/2024.findings-naacl.193/
- Gao, T., Yen, H., Yu, J., Chen, D. (2023). Enabling Large Language Models to Generate Text with Citations. *EMNLP 2023*. https://arxiv.org/abs/2305.14627
- Haladyna, T. M., Downing, S. M., Rodriguez, M. C. (2002). A Review of Multiple-Choice Item-Writing Guidelines for Classroom Assessment. *Applied Measurement in Education* 15(3), 309–333. https://doi.org/10.1207/S15324818AME1503_5
- Huang, J. et al. (2024). Large Language Models Cannot Self-Correct Reasoning Yet. *ICLR 2024*. https://arxiv.org/abs/2310.01798
- Krathwohl, D. R. (2002). A Revision of Bloom's Taxonomy: An Overview. *Theory Into Practice* 41(4), 212–218. https://doi.org/10.1207/s15430421tip4104_2
- Moore, S., Nguyen, H. A., Chen, T., Stamper, J. (2023). Assessing the Quality of Multiple-Choice Questions Using GPT-4 and Rule-Based Methods. *EC-TEL 2023*. https://doi.org/10.1007/978-3-031-42682-7_16
- Panickssery, A., Bowman, S. R., Feng, S. (2024). LLM Evaluators Recognize and Favor Their Own Generations. *NeurIPS 2024*. https://arxiv.org/abs/2404.13076
- Pezeshkpour, P. & Hruschka, E. (2024). Large Language Models Sensitivity to The Order of Options in Multiple-Choice Questions. *Findings of NAACL 2024*. https://aclanthology.org/2024.findings-naacl.130/
- Scaria, N., Chenna, S. D., Subramani, D. (2024). Automated Educational Question Generation at Different Bloom's Skill Levels using Large Language Models: Strategies and Evaluation. *AIED 2024*. https://arxiv.org/abs/2408.04394
- Shinn, N. et al. (2023). Reflexion: Language Agents with Verbal Reinforcement Learning. *NeurIPS 2023*. https://arxiv.org/abs/2303.11366
- Tarrant, M., Ware, J., Mohammed, A. M. (2009). An assessment of functioning and non-functioning distractors in multiple-choice questions: a descriptive analysis. *BMC Medical Education* 9, 40. https://doi.org/10.1186/1472-6920-9-40
- Zheng, L. et al. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. *NeurIPS 2023*. https://arxiv.org/abs/2306.05685
