# Kiểm soát chất lượng nội dung do AI sinh trong DA Platform

> **Mục đích:** mô tả các kỹ thuật dùng để phát hiện và hạn chế lỗi trong nội dung do LLM sinh: sai sự thật, suy diễn vượt nguồn, câu hỏi lệch LO hoặc lệch mức Bloom, đáp án nhiễu kém, chấm bài sai. Mỗi kỹ thuật đều kèm cơ sở tham khảo.
>
> **Phạm vi:** các loại nội dung hệ thống thực sự sinh ra:
> - câu hỏi 5 loại (trắc nghiệm một đáp án, nhiều đáp án, đúng/sai, điền khuyết, tự luận ngắn);
> - micro-content (lesson card và chuỗi câu hỏi phân tích);
> - chấm tự luận ngắn bằng AI;
> - trợ giảng AI neo theo tài liệu;
> - gợi ý đoạn video YouTube.
>
> **Cập nhật:** 2026-10-08. Tài liệu này thay cho bản "Kỹ thuật kiểm soát chất lượng nội dung GenAI cho LMS + AI" (2026-07-21).

---

## 1. Vấn đề

LLM viết ra nội dung nghe hợp lý ngay cả khi nội dung đó sai. Với nội dung học tập, lỗi không chỉ là sai sự thật. Bảng dưới phân loại các kiểu lỗi cần kiểm soát:

| Nhóm | Kiểu lỗi | Ví dụ |
|---|---|---|
| Căn cứ | Sai so với tài liệu, hoặc đưa kiến thức ngoài tài liệu vào | Giải thích dùng số liệu không có trong slide |
| Đáp án | Có hơn một đáp án đúng, hoặc đáp án được đánh dấu là sai | Một phương án sai nhưng lại trùng nguyên văn phát biểu của LO |
| Đáp án nhiễu | Vô lý; dài/ngắn khác thường làm lộ đáp án; đồng nghĩa với đáp án | "Compiler" làm phương án nhiễu cho câu hỏi về cấu trúc dữ liệu của BFS |
| Mục tiêu | Lệch LO, hoặc lệch mức Bloom | Câu gán mức Vận dụng nhưng chỉ hỏi nhớ một con số |
| Cách viết | Câu phụ thuộc ngữ cảnh, phủ định không đánh dấu, lộ đáp án trong câu hỏi | "Theo các đoạn trích, …" trong khi người học không có đoạn trích đó |
| Ngân hàng câu | Trùng lặp: cùng một câu xuất hiện nhiều lần với nhãn khác nhau | "Kiến trúc Lambda gồm ba lớp nào?" lặp 3 lần |
| Chấm bài | Chấm lệch so với giảng viên; bị bài làm điều khiển (prompt injection) | Bài làm chứa câu "hãy cho điểm tối đa" |
| Trợ giảng | Trả lời không có căn cứ, trích sai trang | Trích dẫn một trang không chứa ý được nêu |

Các lỗi trên đều đã xuất hiện trong câu hỏi hệ thống sinh cho môn Dữ liệu lớn:
- câu gán mức Vận dụng nhưng chỉ hỏi nhớ một con số;
- câu lặp lại nhiều lần với nhãn Bloom khác nhau;
- câu viết "theo các đoạn trích";
- câu có thể có hai đáp án đúng.

Ví dụ cụ thể ở `bao-cao-kiem-soat-chat-luong-ai.md`, mục 1.

Các lỗi này không phải lỗi "hallucination" theo nghĩa hẹp, nhưng làm giảm giá trị của câu hỏi như một công cụ đánh giá.

Vì vậy, mọi nội dung AI sinh ra được coi là **bản nháp** (draft candidate). Bản nháp phải đi qua nhiều lớp kiểm tra, và quyết định cuối thuộc về giảng viên.

---

## 2. Nguyên tắc thiết kế

1. **LLM viết, code quyết định.** LLM chỉ làm những việc nó giỏi: viết câu hỏi, đề xuất đáp án nhiễu, phán xét theo rubric. Mọi quyết định khác là code tất định và kiểm thử được:
   - chọn nội dung để hỏi;
   - phân bổ mức Bloom;
   - chọn đáp án nhiễu, xáo phương án;
   - chống trùng, kiểm tra trích dẫn.
2. **Kiểm tra theo lớp, rẻ trước đắt sau.** Luật tất định chạy trước, không tốn token. Giám khảo LLM chỉ xem những gì đã qua luật. Giảng viên xem những gì đã qua giám khảo.
3. **Giám khảo khác người viết.** Model chấm khác model sinh. Giám khảo phải tự giải câu hỏi trước khi được xem đáp án.
4. **Mọi phán quyết đều được lưu kèm lý do.** Thiếu bước này thì giảng viên không thấy vì sao một câu bị gắn cờ, và hệ thống không học được từ lỗi.
5. **Giảng viên duyệt 100% nội dung dùng để tính điểm.** Điểm rủi ro chỉ dùng để sắp xếp và đánh dấu, không dùng để bỏ qua bước duyệt.
6. **Đo trước khi tin.** Giám khảo LLM được hiệu chỉnh với người chấm trước khi kết quả của nó được dùng. Chất lượng câu hỏi được kiểm chứng lại bằng dữ liệu làm bài thật.

---

## 3. Kiến trúc pipeline

```text
Tài liệu môn học (slide, giáo trình, đề cương, LO)
   │
   ▼
[1] Nguồn & ngữ cảnh        parse → chunk → ánh xạ chunk–LO → chọn đoạn hợp mức Bloom, phủ đều (MMR)
   │
   ▼
[2] Sinh có ràng buộc       schema JSON, hướng dẫn theo mức Bloom, bắt buộc trích dẫn nguyên văn
   │
   ▼
[3] Kiểm tra tất định       schema, trích dẫn là chuỗi con của nguồn, luật viết câu hỏi, trùng lặp
   │                         lỗi → sửa hoặc bỏ, không tốn token
   ▼
[4] Giám khảo LLM           giải mù → kiểm căn cứ → chấm rubric (Bloom, LO, đáp án nhiễu)
   │
   ▼
[5] Sửa có giới hạn         phản hồi cụ thể → sinh lại tối đa N lần → vẫn sai thì bỏ
   │
   ▼
[6] Lưu kèm hồ sơ kiểm tra  verdict, lý do, cờ, mức Bloom đánh giá, model, phiên bản prompt, chi phí
   │
   ▼
[7] Hàng đợi duyệt          sắp theo rủi ro, hiện cờ và bằng chứng; giảng viên duyệt 100%
   │
   ▼
[8] Giảng viên quyết định   duyệt / sửa / từ chối kèm mã lý do
   │
   ▼
Dùng trong LMS (Canvas qua LTI 1.3)
   │
   ▼
[9] Đánh giá sau khi dùng   độ khó, độ phân biệt, hiệu quả đáp án nhiễu, phản hồi người học
   │
   ▼
[10] Vòng cải thiện         lỗi lặp lại → sửa prompt/luật; câu đã sửa → ví dụ few-shot
```

---

## 4. Các kỹ thuật

### 4.1 RAG và ánh xạ nội dung–LO

**Ý tưởng:** LLM không viết từ trí nhớ của nó mà từ các đoạn tài liệu môn học được đưa vào prompt (Lewis et al., 2020).

**Áp dụng:**
- Tài liệu được chia thành chunk theo cấu trúc heading và đo bằng token thật. Mỗi chunk mang `heading_path`, `page_number`, chương.
- Chunk được ánh xạ tới LO, kết hợp heading và độ tương đồng embedding. Câu hỏi của một LO chỉ được sinh từ các chunk của LO đó.
- Mỗi lần sinh chọn các đoạn vừa liên quan tới LO vừa khác nhau, theo Maximal Marginal Relevance (Carbonell & Goldstein, 1998). Nhờ vậy nhiều câu không cùng hỏi về một ý.
- Mỗi câu hỏi và mỗi card lưu `source_chunk_ids`.

**Giới hạn:** RAG là lớp neo nội dung, không phải bảo đảm đúng. Retrieval sai thì LLM vẫn viết sai một cách tự tin. Nếu chính tài liệu nguồn thiếu (ví dụ slide toàn hình, ít chữ) thì câu hỏi cũng nghèo theo. RAG giải quyết được câu hỏi "dựa vào đâu", không trả lời được câu hỏi "có đúng không". Phần đó cần các lớp sau.

**Đánh giá retrieval:** dùng một bộ câu hỏi có gán nhãn đoạn đúng, đo Recall@k và MRR. Các tiêu chí context relevance và faithfulness theo RAGAS (Es et al., 2024) và ARES (Saad-Falcon et al., 2024).

**Nên ghi trong report:**
> RAG is used as a grounding layer, not as a correctness guarantee.

**Tài liệu:** Lewis et al. (2020); Carbonell & Goldstein (1998); Es et al. (2024); Saad-Falcon et al. (2024).

---

### 4.2 Trích dẫn nguyên văn và kiểm tra bằng code

**Ý tưởng:** mỗi câu hỏi phải kèm một **trích dẫn nguyên văn** (`evidence_quote`) từ đoạn nguồn đủ để chứng minh đáp án. Trích dẫn này kiểm tra được bằng code: sau khi chuẩn hoá Unicode (NFC) và khoảng trắng, nó phải là chuỗi con của chunk được dẫn. Không cần gọi LLM, và không thể "gần đúng".

**Vì sao:** "LLM bảo câu này có căn cứ" là một phán đoán. "Câu này được chứng minh bởi đoạn X ở trang 12, đây là nguyên văn" thì giảng viên tự kiểm tra trong vài giây. Hướng này đi theo các nghiên cứu về attribution: đánh giá văn bản sinh ra dựa trên nguồn được dẫn (Rashkin et al., 2023), và đo độ chính xác/độ phủ của trích dẫn (Gao et al., 2023).

**Áp dụng:**
- Không có trích dẫn, hoặc trích dẫn không khớp nguồn → yêu cầu sửa một lần, vẫn không được thì bỏ câu.
- Giao diện duyệt hiện trích dẫn kèm liên kết mở đúng trang tài liệu.
- Với nội dung nhiều mệnh đề (card, câu trả lời của trợ giảng), mỗi mệnh đề quan trọng có trích dẫn riêng (xem 4.8).

**Giới hạn:** trích dẫn đúng nguyên văn chưa chắc *đủ* để chứng minh đáp án. Bước "đủ hay không" vẫn cần giám khảo (4.4) và giảng viên.

**Tài liệu:** Rashkin et al. (2023); Gao et al. (2023).

---

### 4.3 Luật viết câu hỏi tất định (item-writing flaws)

**Ý tưởng:** nhiều lỗi của câu trắc nghiệm đã được nghiên cứu từ lâu dưới tên *item-writing flaws*:
- bộ hướng dẫn viết câu hỏi của Haladyna, Downing & Rodriguez (2002);
- Tarrant et al. (2006) thấy 46,2% câu trong các kỳ thi điều dưỡng có ít nhất một lỗi viết; câu ở mức nhận thức thấp dễ mắc lỗi hơn;
- Downing (2005) cho thấy lỗi viết làm sai lệch điểm của người học.

Phần lớn các lỗi này phát hiện được bằng luật. Moore et al. (2023) so sánh trên 200 câu thuộc bốn lĩnh vực: phương pháp dựa trên luật bắt được khoảng 91% lỗi mà người chấm tìm ra, GPT-4 chỉ bắt được khoảng 79%. Bộ công cụ SAQUET của cùng nhóm tự động hoá 19 loại lỗi (Moore et al., 2024).

**Luật áp dụng trước khi gọi giám khảo:**

| # | Luật | Khi vi phạm |
|---|---|---|
| R1 | JSON đúng schema của từng loại câu | sửa JSON một lần |
| R2 | `evidence_quote` là chuỗi con của chunk nguồn (4.2) | sửa một lần, không được thì bỏ |
| R3 | Các phương án khác nhau sau chuẩn hoá | thay phương án nhiễu |
| R4 | Không dùng phương án cấm: "tất cả đều đúng", "không có phương án nào đúng" | thay phương án nhiễu |
| R5 | Không lộ đáp án qua độ dài (đáp án dài hơn hẳn các phương án khác) | thay phương án nhiễu, rồi mới sửa câu |
| R6 | Câu hỏi không chứa nguyên văn đáp án | sửa |
| R7 | Câu hỏi tự đứng được: không khớp mẫu "theo đoạn (văn/trích) trên", "theo tài liệu", "in the passage above" | sửa |
| R8 | Câu phủ định phải đánh dấu rõ ("KHÔNG") | sửa |
| R9 | Không trùng: cosine(câu hỏi + đáp án, mọi câu cùng LO đã có) < ngưỡng (ví dụ 0,92) | bỏ, chuyển sang nội dung dự phòng |
| R10 | Giới hạn độ dài; ngôn ngữ khớp tài liệu nguồn | sửa |
| R11 | Đúng/sai: mệnh đề không dùng từ tuyệt đối gây gợi ý ("luôn luôn", "không bao giờ") | sửa |
| R12 | Điền khuyết: đúng một chỗ trống `____`; đáp án không xuất hiện trong phần còn lại của câu | sửa |
| R13 | Nhiều đáp án: còn ít nhất một phương án sai; không phải mọi phương án đều đúng | sửa |

**Giá trị:** không tốn token, có unit test, kết quả giải thích được ("vi phạm R7"). Hội đồng dễ chấp nhận một luật có test hơn một phán đoán của LLM.

**Giới hạn:** luật chỉ bắt được lỗi về hình thức. Câu viết đúng hình thức vẫn có thể sai nội dung hoặc lệch mục tiêu.

**Tài liệu:** Haladyna et al. (2002); Tarrant et al. (2006); Downing (2005); Moore et al. (2023, 2024).

---

### 4.4 Giám khảo LLM: giải trước, chấm sau

**Ý tưởng:** dùng LLM để sàng lọc ở quy mô lớn, nhưng thiết kế sao cho tránh các thiên lệch đã biết của LLM-as-a-judge:
- **thiên vị bài của chính mình:** model chấm cao bài của chính nó, và mức thiên vị tăng theo khả năng nhận ra văn của mình (Panickssery et al., 2024);
- **thiên vị vị trí:** đổi thứ tự trình bày là đổi được kết quả chấm (Wang et al., 2024; Zheng et al., 2023);
- **nhạy với thứ tự phương án** khi trả lời câu trắc nghiệm: độ chính xác dao động khoảng 13–75% chỉ do xáo phương án (Pezeshkpour & Hruschka, 2024), và LLM có thiên lệch chọn nhãn (Zheng et al., 2024);
- **hợp lý hoá đáp án khi đã thấy đáp án.**

**Áp dụng (hai lượt gọi, model khác model sinh, temperature 0):**

1. **Giải mù.** Giám khảo nhận đoạn nguồn, câu hỏi và các phương án đã xáo theo một thứ tự khác thứ tự cuối cùng. Nó **không thấy đáp án**. Nó phải chọn phương án đúng chỉ dựa trên tài liệu, hoặc trả `AMBIGUOUS` (có hơn một phương án đúng) hay `NOT_IN_SOURCE`. Chọn khác đáp án nghĩa là đáp án sai hoặc câu mơ hồ.
2. **Chấm rubric.** Chỉ chạy khi lượt giải mù chọn đúng. Lúc này giám khảo mới thấy đáp án, và trả về:
   - `verdict`: `supported` / `contradicted` / `not_enough_evidence`, kèm lý do;
   - `bloom_assessed`: mức 1–6, kèm động từ nhận thức làm căn cứ (xem 4.5);
   - `lo_alignment`: thang 1–5;
   - `distractor_verdicts[]`: với mỗi phương án nhiễu là `wrong`, `also_correct` hoặc `unclear`;
   - `issues[]`: gợi ý đáp án, phụ thuộc ngữ cảnh, ngữ pháp không khớp…

**Luật chấp nhận:**

| Tình huống | Hành động |
|---|---|
| Giải mù chọn sai, hoặc `AMBIGUOUS` / `NOT_IN_SOURCE` | sửa một lần theo lý do; vẫn trượt → bỏ |
| `contradicted` | sửa một lần; vẫn trượt → bỏ |
| Một phương án nhiễu bị đánh `also_correct` | thay bằng ứng viên còn lại (không gọi LLM), giải mù lại |
| `bloom_assessed` thấp hơn mức yêu cầu | sửa một lần; vẫn thấp → lưu theo mức đánh giá, gắn cờ `bloom_below_target` |
| `bloom_assessed` cao hơn mức của LO | bỏ (hỏi vượt LO) |
| `lo_alignment` ≤ 2 | bỏ |
| Giám khảo lỗi (gọi hoặc parse hỏng) | thử lại một lần; vẫn lỗi → giữ câu với cờ `unverified`, **không** coi là đạt |

**Giới hạn:** giám khảo LLM không phải "truth oracle". Hai model khác nhau vẫn có thể cùng sai. Kết quả của giám khảo chỉ được tin sau khi đã hiệu chỉnh với người chấm (mục 7), và chỉ là tín hiệu để sàng lọc, không thay giảng viên.

**Nên ghi trong report:**
> LLM-as-a-judge is used as a scalable pre-screening mechanism; it solves each item before seeing the key, runs on a different model from the generator, and is calibrated against human raters before its verdicts are trusted.

**Tài liệu:** Zheng et al. (2023); Wang et al. (2024); Panickssery et al. (2024); Pezeshkpour & Hruschka (2024); Zheng, C. et al. (2024).

---

### 4.5 Kiểm soát mức Bloom

**Vấn đề:** kiểm soát Bloom thường bị coi là việc của bước kiểm tra, nhưng nguyên nhân phần lớn nằm ở bước sinh:
1. **Nội dung không đủ cho mức được yêu cầu.** Slide chỉ có định nghĩa thì không có quy trình hay tình huống để ra câu Vận dụng. Giám khảo giỏi đến đâu cũng chỉ loại được câu dở, không tạo ra được câu tốt.
2. **Prompt chỉ ghi tên mức** ("Bloom level required: apply"), không có định nghĩa, động từ hay mẫu câu.
3. **Nhãn lưu vào DB là mức được yêu cầu**, không phải mức thực của câu. Vì vậy cùng một câu hỏi có thể mang nhãn 1, 2 hoặc 3.
4. **Động từ trong câu hỏi không quyết định mức.** Câu "Giải thích khái niệm X dựa trên định nghĩa trong tài liệu" dùng động từ "giải thích", nhưng nếu đáp án chỉ là chép lại định nghĩa thì người học chỉ cần *nhớ* (mức 1). Mức Bloom là quá trình nhận thức người học phải thực hiện *so với những gì họ đã được học*, không phải từ ngữ của câu hỏi (Anderson & Krathwohl, 2001; Krathwohl, 2002).

Nhãn Bloom sai không chỉ là lỗi hiển thị. Nó đi vào thống kê theo LO/Bloom, ma trận đề và mô hình người học trong phần học thích ứng.

**Kỹ thuật (bốn tầng):**

1. **Lập kế hoạch theo loại nội dung.** Mỗi mức Bloom chỉ ghép với loại đơn vị kiến thức phù hợp (bảng dưới). Mức Vận dụng cần nội dung kiểu quy trình, công thức hoặc ví dụ. Không có nội dung phù hợp thì hạ mức và gắn cờ, thay vì để LLM bịa tình huống.
2. **Hướng dẫn theo mức trong prompt:** định nghĩa, động từ cho phép, 2 mẫu câu và lỗi hay gặp của mức đó. Cách đưa định nghĩa mức Bloom và ví dụ vào prompt đã được dùng trong Doughty et al. (2024) và Elkins et al. (2024).
3. **Giám khảo đánh giá mức** (4.4) và **lưu mức đánh giá**, không lưu mức yêu cầu. Thêm một tín hiệu tất định: nếu đáp án gần như trùng nguyên văn một câu trong nguồn và câu hỏi chỉ diễn đạt lại câu đó, thì nhiều khả năng đây là câu nhớ lại. Gắn cờ để xem lại.
4. **Không vượt mức của LO.** Theo nguyên tắc căn chỉnh (constructive alignment), đánh giá phải khớp với mục tiêu học tập (Biggs, 1996).

**Bảng Bloom dùng trong prompt và planner** (thang Bloom sửa đổi, Anderson & Krathwohl, 2001):

| Mức | Tên | Người học làm được | Động từ | Mẫu câu hỏi | Nội dung phù hợp | Loại câu |
|---|---|---|---|---|---|---|
| 1 | Nhớ | nhận biết, nhắc lại | nêu, liệt kê, nhận biết, định nghĩa | "X là gì?"; "Thuật ngữ nào mô tả …?" | định nghĩa, sự kiện, tính chất | trắc nghiệm, đúng/sai, điền khuyết |
| 2 | Hiểu | giải thích, phân loại, so sánh, lấy ví dụ | giải thích, phân biệt, so sánh, phân loại | "Ví dụ nào minh hoạ đúng X?"; "Vì sao …?" | định nghĩa, so sánh, ví dụ, nhân–quả | trắc nghiệm, đúng/sai, tự luận ngắn |
| 3 | Vận dụng | áp dụng quy trình vào tình huống mới | tính, áp dụng, thực hiện | "Cho …, kết quả của … là?"; "Trong tình huống …, cần dùng …?" | quy trình, công thức, nguyên lý, ví dụ | trắc nghiệm có tình huống, nhiều đáp án |
| 4 | Phân tích | chia nhỏ, tìm quan hệ, chẩn đoán | phân tích, xác định nguyên nhân, phát hiện lỗi | "Thiết kế sau vi phạm điều gì, vì sao?" | quy trình, nguyên lý, nhân–quả | trắc nghiệm có tình huống, tự luận ngắn |
| 5 | Đánh giá | phán đoán theo tiêu chí | đánh giá, chọn phương án tốt nhất, biện minh | "Giải pháp nào phù hợp nhất với yêu cầu …, vì sao?" | nguyên lý, so sánh | trắc nghiệm "tốt nhất", tự luận ngắn |
| 6 | Sáng tạo | tạo ra sản phẩm mới | thiết kế, xây dựng, đề xuất | — | — | không chấm tự động bằng trắc nghiệm; dùng bài tập mở do giảng viên chấm |

**Giới hạn:** chính việc đánh giá mức Bloom tự động cũng chưa đáng tin. Scaria et al. (2024) thấy LLM sinh được câu hỏi tốt ở nhiều mức khi có đủ ngữ cảnh, nhưng việc đánh giá tự động bằng LLM *chưa ngang bằng* chuyên gia. Vì vậy giám khảo Bloom phải được hiệu chỉnh với người chấm (mục 7). Kết quả cần báo cáo cả tỉ lệ khớp đúng mức lẫn tỉ lệ lệch không quá một mức.

**Tài liệu:** Anderson & Krathwohl (2001); Krathwohl (2002); Biggs (1996); Scaria et al. (2024); Elkins et al. (2024); Doughty et al. (2024); Kurdi et al. (2020).

---

### 4.6 Chất lượng đáp án nhiễu

**Ý tưởng:** câu trắc nghiệm có đáp án đúng vẫn có thể là câu tồi nếu các phương án nhiễu vô lý, vì người học loại trừ được mà không cần hiểu bài. Phương án nhiễu tốt phải *sai chắc chắn* nhưng *hợp lý* với người chưa nắm bài, và lý tưởng là phản ánh một hiểu nhầm thường gặp (Gierl et al., 2017; Haladyna et al., 2002).

**Áp dụng:**
- **LLM đề xuất, code chọn.** LLM đề xuất 6 ứng viên, code chọn 3 theo luật:
  - không bị giám khảo đánh `also_correct`;
  - không thuộc phương án cấm;
  - độ dài nằm trong dải của đáp án;
  - độ tương đồng ngữ nghĩa với đáp án nằm trong một **dải**: không quá gần (dễ thành đồng nghĩa với đáp án), không quá xa (vô lý);
  - các phương án khác nhau về ý.
- Còn ứng viên dự phòng thì thay phương án hỏng không cần gọi lại LLM.
- **Sau khi dùng:** một phương án nhiễu được coi là *không hoạt động* khi dưới 5% người làm chọn nó, hoặc khi nó có độ phân biệt dương (người giỏi chọn nó nhiều hơn người yếu). Đây là định nghĩa trong phần phương pháp của Tarrant et al. (2009). Phương án như vậy được gắn cờ để giảng viên thay. Ngay cả người viết đề cũng khó viết được nhiều phương án nhiễu hợp lý: Tarrant et al. (2009) thấy chỉ khoảng một nửa số phương án nhiễu thật sự hoạt động (xem thêm Haladyna & Downing, 1993).

**Giới hạn:** chưa có đồng thuận về cách đánh giá phương án nhiễu tự động. Một số độ đo dùng trong nghiên cứu không phản ánh đúng hiệu quả của phương án nhiễu trong kỳ thi thật (Benedetto et al., 2025). Dữ liệu làm bài thật (4.12) là thước đo cuối cùng.

**Tài liệu:** Haladyna et al. (2002); Gierl et al. (2017); Haladyna & Downing (1993); Tarrant et al. (2009); Raina et al. (2023); Alhazmi et al. (2024); Benedetto et al. (2025).

---

### 4.7 Sửa có giới hạn (Reflexion)

**Ý tưởng:** trước khi tới tay giảng viên, nội dung bị loại được sinh lại dựa trên **phản hồi cụ thể** của bước kiểm tra (Shinn et al., 2023; Madaan et al., 2023). Chain-of-Verification là một biến thể: model tự đặt câu hỏi kiểm chứng rồi trả lời độc lập (Dhuliawala et al., 2024).

**Điểm quan trọng:** LLM tự sửa *không có phản hồi từ bên ngoài* thường không cải thiện được, thậm chí còn làm kết quả tệ hơn (Huang et al., 2024). Vì vậy vòng sửa trong hệ thống luôn dựa trên tín hiệu bên ngoài:
- luật nào bị vi phạm;
- giám khảo (model khác) chọn phương án nào khi giải mù;
- trích dẫn nào không khớp nguồn.

Không bao giờ dùng kiểu "hãy xem lại câu của chính mình".

**Áp dụng:**

```text
sinh → luật tất định → giám khảo
       │ lỗi
       ▼
   phản hồi cụ thể (luật vi phạm / lý do của giám khảo / đoạn nguồn)
       ▼
   sinh lại đúng câu đó (temperature thấp hơn) → kiểm tra lại
       │ tối đa N lần (N = 1–2)
       ▼
   vẫn lỗi → bỏ câu, sinh bù câu khác cùng vị trí trong kế hoạch
```

- Câu còn bị loại sau khi hết lượt **không được lưu** như câu bình thường.
- Sinh bù giữ nguyên mức Bloom, độ khó và vị trí đáp án của câu bị bỏ, để phân bổ của đề không bị lệch.

**Tài liệu:** Shinn et al. (2023); Madaan et al. (2023); Dhuliawala et al. (2024); Huang et al. (2024).

---

### 4.8 Micro-content: kiểm tra theo từng mệnh đề

**Ý tưởng:** một card hoặc một chuỗi câu hỏi phân tích chứa nhiều mệnh đề. Chấm cả card là "đạt" hay "không đạt" sẽ bỏ sót trường hợp 80% đúng, 20% sai. FActScore tách văn bản thành các mệnh đề nguyên tử rồi kiểm từng mệnh đề với nguồn (Min et al., 2023). SAFE làm tương tự, với bước tìm bằng chứng tự động (Wei et al., 2024).

**Áp dụng cho lesson card:**
- Mỗi `key_insight` và mỗi gạch đầu dòng là một mệnh đề, có trích dẫn riêng và verdict riêng.
- `example` phải lấy từ nguồn. `misconception` chỉ được viết khi nguồn có nêu hoặc hàm ý rõ; nếu không thì để `null`.
- Câu tự kiểm tra ở mặt sau phải trả lời được bằng chính nội dung của card.
- Luật tất định: một card một ý (giới hạn số gạch đầu dòng và độ dài), không chứa mệnh đề ngoài các chunk đã dẫn.

**Áp dụng cho micro-content dạng chuỗi câu hỏi:** một vấn đề trọng tâm được phân tích qua chuỗi câu hỏi sâu: hiện tượng → các yếu tố → từng yếu tố → quan hệ giữa các yếu tố → nếu bỏ một yếu tố → ranh giới với khái niệm gần (Graesser & Person, 1994). Ngoài kiểm từng mệnh đề, cần kiểm thêm:
- mỗi câu hỏi con có câu trả lời nằm trong nguồn;
- thứ tự chuỗi tôn trọng quan hệ phụ thuộc: không dùng một khái niệm trước khi giải thích nó;
- toàn chuỗi thực sự trả lời câu hỏi trọng tâm;
- kiến thức nền nặng được liên kết sang card khác thay vì giải thích lại nửa vời.

**Tài liệu:** Min et al. (2023); Wei et al. (2024); Thorne et al. (2018); Graesser & Person (1994).

---

### 4.9 Chấm tự luận ngắn bằng AI

**Rủi ro:** đây là nơi lỗi của LLM tác động trực tiếp tới điểm của người học. Chamieh et al. (2024) thấy LLM chấm câu trả lời ngắn theo kiểu zero-shot/few-shot còn yếu, nhất là với câu đòi hỏi suy luận hoặc kiến thức chuyên ngành, và kết luận chưa có cơ sở vững để dùng LLM chấm thay người. Ngoài ra bài làm là văn bản người học tự gõ, nên có thể chứa lệnh nhằm điều khiển model chấm (Greshake et al., 2023; OWASP, 2025).

**Kỹ thuật:**
1. **LLM phán từng ý, code tính điểm.** Mỗi câu có đáp án mẫu và rubric 1–6 ý. LLM chỉ quyết định từng ý "đạt / không đạt" kèm nhận xét. Điểm = số ý đạt / tổng số ý. Như vậy điểm giải thích được theo từng ý và nhất quán giữa các lần chấm.
2. **Rào bài làm.** Bài làm được đặt giữa hai mốc phân cách và chỉ được coi là dữ liệu. Mọi lời nhắn về cách chấm bên trong bài đều bị bỏ qua. Bài quá dài bị cắt bớt.
3. **Chấm theo đề lúc nộp.** Đề và rubric được chụp lại lúc người học nộp. Giảng viên sửa câu hỏi sau đó không làm đổi cách chấm bài đã nộp.
4. **Không gửi điểm khi chưa chấm xong.** Cả lượt nộp chỉ được gửi về sổ điểm LMS khi mọi câu tự luận đã có điểm, để tránh gửi một điểm thấp giả.
5. **AI không chấm được thì chuyển cho giảng viên, không cho 0 điểm.** Câu chuyển sang "chờ giảng viên"; giảng viên chấm tay hoặc cho AI chấm lại.
6. **Giám khảo chấm là model đóng vai kiểm tra**, có thể khác model sinh câu hỏi.

**Đánh giá trước khi dùng cho điểm chính thức:**
- So điểm AI với điểm giảng viên trên một tập bài thật.
- Đo quadratic weighted kappa (Cohen, 1968) và độ đồng thuận theo từng ý rubric.
- Quy ước thường dùng trong chấm tự động (Williamson et al., 2012): QWK người–máy ≥ 0,70, và không thấp hơn QWK người–người quá 0,10.
- Chưa đạt ngưỡng thì AI chỉ dùng để gợi ý điểm cho giảng viên, không ghi điểm trực tiếp.

**Tài liệu:** Burrows et al. (2015); Chamieh et al. (2024); Williamson et al. (2012); Cohen (1968); Greshake et al. (2023); OWASP (2025).

---

### 4.10 Trợ giảng AI neo theo tài liệu

**Ý tưởng:** trợ giảng trả lời trong ngữ cảnh tài liệu người học đang mở. Câu "giải thích trang này" là tra cứu chính xác theo (tài liệu, số trang), không phải tìm kiếm tương đồng. Câu hỏi nối tiếp thì tìm trong phạm vi tài liệu đó.

**Kiểm soát:**
- Mọi câu trả lời có trích dẫn tới trang nguồn. Người học bấm vào là nhảy tới trang đó.
- Không đủ bằng chứng thì trả lời "tài liệu không đề cập" và gợi ý phần liên quan, thay vì tự bịa.
- Đánh giá offline: faithfulness và answer relevance (Es et al., 2024); độ chính xác và độ phủ của trích dẫn (Gao et al., 2023).
- Nội dung người học gõ vào chat được xử lý như dữ liệu, giống bài tự luận (4.9).

**Tài liệu:** Es et al. (2024); Saad-Falcon et al. (2024); Gao et al. (2023).

---

### 4.11 Gợi ý đoạn video

Hệ thống **không sinh video**. Chi phí sinh video tính theo giây và cao hơn sinh văn bản nhiều bậc, sửa một lỗi lại phải render lại.

Thay vào đó, hệ thống tìm video YouTube có sẵn theo LO và chọn một **đoạn** (mốc đầu–cuối) giải thích đúng nội dung:
- Bằng chứng là **transcript**: đoạn được chọn phải tương ứng với một dải cue liên tiếp có thật trong phụ đề. Backend kiểm tra dải cue và tính mốc thời gian từ nguồn, không lấy mốc do LLM tự đưa ra.
- Mỗi gợi ý lưu lý do chọn và đoạn transcript làm bằng chứng.
- Giảng viên xem đoạn video và transcript trước khi gắn vào card. Không có bằng chứng phù hợp thì hệ thống trả về "không có gợi ý".

---

### 4.12 Đánh giá sau khi dùng (phân tích câu hỏi)

**Ý tưởng:** duyệt trước khi phát hành vẫn chưa đủ. Chất lượng của một câu hỏi như một công cụ đo chỉ thấy được qua dữ liệu làm bài thật. Bhandari et al. (2024) đã dùng cách tiếp cận này để so câu hỏi do ChatGPT sinh với câu trong giáo trình, dựa trên độ khó và độ phân biệt.

**Chỉ số (lý thuyết trắc nghiệm cổ điển, Crocker & Algina, 1986):**

| Chỉ số | Ý nghĩa | Gắn cờ khi |
|---|---|---|
| Độ khó p | tỉ lệ trả lời đúng | quá cao (gần như ai cũng đúng) hoặc quá thấp (có thể đáp án sai) |
| Độ phân biệt (point-biserial hoặc chỉ số D) | câu có phân biệt được người giỏi và người yếu không | < 0,20 cần xem lại; âm thì gần như chắc chắn có vấn đề (ngưỡng kinh nghiệm thường dẫn theo Ebel & Frisbie, 1991) |
| Tỉ lệ chọn từng phương án nhiễu | phương án nhiễu có hoạt động không | < 5% người chọn (4.6) |
| KR-20 / Cronbach's α | độ nhất quán nội bộ của cả đề | thấp so với mục đích của đề (Kuder & Richardson, 1937; Cronbach, 1951) |

**Lưu ý thực tế:**
- Chỉ dùng **lượt làm đầu tiên** của mỗi người học (hoặc lượt ở chế độ Kiểm tra). Chế độ Luyện tập cho làm lại không giới hạn, nên các lượt sau làm sai lệch độ khó.
- Với lớp nhỏ, các chỉ số dao động mạnh. Cờ chỉ có nghĩa là "cần giảng viên xem", không phải phán quyết. Mô hình IRT cần mẫu lớn hơn nhiều, để sau.
- Câu bị gắn cờ quay lại hàng đợi duyệt, kèm các chỉ số của nó.

**Tài liệu:** Crocker & Algina (1986); Ebel & Frisbie (1991); Kuder & Richardson (1937); Cronbach (1951); Bhandari et al. (2024).

---

### 4.13 Điểm rủi ro: sắp xếp hàng đợi, không tự duyệt

**Ý tưởng:** gom các tín hiệu thành một điểm rủi ro để giảng viên xem câu nghi ngờ trước.

**Tín hiệu:**
- luật tất định bị vi phạm và đã sửa;
- giám khảo đánh `not_enough_evidence`, `unclear` hoặc `bloom_below_target`;
- cờ `unverified`;
- câu phải sửa nhiều lần mới đạt;
- độ liên quan của đoạn nguồn thấp;
- hai lần giải mù độc lập (xáo phương án khác nhau) cho kết quả khác nhau. Đây là một dạng self-consistency (Wang, X. et al., 2023; Manakul et al., 2023).

**Vì sao không auto-pass:**
1. Ngưỡng tự duyệt cần hiệu chỉnh trên dữ liệu có nhãn. Đo được tỉ lệ "lọt lưới" của câu tự duyệt thì phải audit rất nhiều câu.
2. Câu hỏi đi vào sổ điểm LMS, sai một câu là sai điểm của cả lớp.
3. Lợi ích thật của điểm rủi ro, tức giảm thời gian duyệt, vẫn đạt được khi giảng viên duyệt 100% nhưng theo thứ tự ưu tiên và có cờ dẫn đường.

Semantic entropy (Farquhar et al., 2024) là tín hiệu bất định mạnh hơn nhưng phải sinh nhiều lần cho mỗi câu. Để làm hướng phát triển.

**Tài liệu:** Wang, X. et al. (2023); Manakul et al. (2023); Farquhar et al. (2024).

---

### 4.14 Giảng viên trong vòng lặp và giao diện duyệt

**Ý tưởng:** giảng viên không viết lại từ đầu, nhưng có quyền quyết định cuối (Wu et al., 2022). Vai trò này chỉ phát huy khi giao diện cho giảng viên thấy **vì sao** một câu bị gắn cờ và cho **sửa nhanh**. Đây là hai hướng dẫn trong bộ nguyên tắc tương tác người–AI của Amershi et al. (2019).

**Giao diện duyệt hiển thị:**
- trích dẫn nguyên văn, bấm vào mở đúng trang tài liệu;
- các cờ kèm lý do ("vi phạm R7: câu phụ thuộc ngữ cảnh", "giám khảo đánh giá mức 1, yêu cầu mức 3");
- mức Bloom yêu cầu cạnh mức Bloom đánh giá;
- với câu đã dùng: độ khó, độ phân biệt, tỉ lệ chọn từng phương án.

**Thao tác:** duyệt, sửa, từ chối. Từ chối phải chọn **mã lý do**: sai sự thật, nhiều đáp án đúng, phương án nhiễu yếu, lệch Bloom, lệch LO, mơ hồ, trùng, phụ thuộc ngữ cảnh, khác.

**Lưu vết:** mọi thao tác ghi người thực hiện, thời điểm, bản trước và bản sau khi sửa. Đây vừa là audit trail vừa là dữ liệu cho 4.15.

**Nên ghi trong report:**
> The system does not replace instructors; it reduces drafting and screening effort while keeping instructors as the final authority over learning content.

**Tài liệu:** Wu et al. (2022); Amershi et al. (2019).

---

### 4.15 Vòng cải thiện (data flywheel)

Mỗi lần giảng viên sửa hoặc từ chối là một mẫu dữ liệu có nhãn. Dữ liệu này dùng để:
- **thống kê lỗi theo phiên bản prompt và model:** tỉ lệ duyệt không cần sửa, phân bố mã lý do từ chối. Prompt mới chỉ được giữ khi các chỉ số này tốt hơn;
- **bổ sung luật tất định** cho các lỗi lặp lại có hình thức nhận diện được;
- **few-shot động:** đưa câu đã được giảng viên sửa của cùng LO hoặc cùng mức Bloom làm ví dụ trong prompt;
- **về lâu dài:** cặp (bản AI, bản giảng viên sửa) là dữ liệu cho học theo sở thích như DPO (Rafailov et al., 2023). Việc này cần nhiều dữ liệu và chi phí huấn luyện, nên để làm hướng phát triển.

---

## 5. Dữ liệu cần lưu cho mỗi nội dung

Kiểm soát chất lượng chỉ giải thích được và cải thiện được khi kết quả của từng bước được lưu cùng nội dung. Ví dụ hồ sơ của một câu hỏi:

```json
{
  "quiz_id": "uuid",
  "type": "MCQ_SINGLE",
  "bloom_target": 3,
  "bloom_assessed": 1,
  "evidence": [{"chunk_id": "uuid", "page": 12, "quote": "…nguyên văn…"}],
  "rules": {"violations_fixed": ["R5"], "violations_open": []},
  "judge": {
    "solve_choice": 2, "solve_matches_key": true,
    "verdict": "supported", "reason": "…",
    "lo_alignment": 4,
    "distractors": ["wrong", "wrong", "unclear"],
    "issues": []
  },
  "flags": ["bloom_below_target"],
  "repair_rounds": 1,
  "writer": {"profile": "deepseek-chat", "prompt_version": "quiz_generation@3"},
  "judge_model": {"profile": "gemini-flash", "prompt_version": "quiz_verification@2"},
  "cost_usd": 0.0041,
  "risk_score": 0.62
}
```

Không có hồ sơ này thì các mục 4.13–4.15 và mục 6 đều không làm được.

---

## 6. Chi phí

### 6.1 Tính theo nội dung được duyệt

Đơn vị đúng là **chi phí trên mỗi nội dung được duyệt**, không phải chi phí mỗi lần sinh. Câu bị bỏ, lượt sửa và lượt giám khảo đều phải được tính vào:

```text
C_per_accepted = (tổng chi phí của mọi lượt sinh, kiểm tra, sửa, sinh bù) / (số nội dung được duyệt)
```

Chi phí một lần gọi LLM:

```text
C_call = input_tokens/1e6 × giá_input + cached_tokens/1e6 × giá_cache + output_tokens/1e6 × giá_output
```

Kỳ vọng chi phí cho một câu trắc nghiệm:

```text
E[C_MCQ] = C_sinh + C_giải_mù + C_chấm_rubric
         + p_sửa × số_lượt_sửa_TB × (C_sinh_lại + C_kiểm_lại)
         + p_bỏ × C_sinh_bù
         + C_duyệt_người
```

Các bước luật tất định có chi phí token bằng 0. Đây là một lý do nữa để đặt chúng trước giám khảo.

### 6.2 Ghi theo từng bước

Mỗi lần gọi LLM ghi một dòng gồm:
- `request_id`, `use_case` (sinh, sửa, kiểm tra, chấm bài…), `course_id`;
- provider, model, profile, phiên bản prompt;
- token input / cache / output;
- số thứ tự lượt sửa, độ trễ, `cost_usd`, trạng thái.

Giá lấy từ bảng giá của profile model, ghi kèm ngày tra giá.

Khi cần báo cáo chi phí, dùng giá của **đúng các model đang chạy**. Chỉ ghi "giá tham khảo tại thời điểm khảo sát" kèm nguồn chính thức:
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [DeepSeek API pricing](https://api-docs.deepseek.com/quick_start/pricing)
- [Voyage AI pricing](https://docs.voyageai.com/docs/pricing) (embedding)

### 6.3 Thời gian của giảng viên

Với nội dung văn bản, công duyệt của giảng viên thường lớn hơn chi phí token nhiều lần. Vì vậy chỉ số đáng báo cáo nhất là **số phút duyệt trên mỗi câu được duyệt**. Số này phải đo từ giao diện duyệt (thời điểm mở câu đến thời điểm ra quyết định), không giả định. Mục tiêu của các lớp kiểm tra tự động là giảm số này mà không làm tăng tỉ lệ lỗi lọt qua.

**Chỉ số nên báo cáo:**

```text
cost_per_accepted_item
review_minutes_per_accepted_item
approve_without_edit_rate
rejection_reasons_distribution
repair_rate, drop_rate
generation_latency, verification_latency
```

---

## 7. Kế hoạch đánh giá

### 7.1 Chất lượng câu hỏi

**Bộ dữ liệu:**
- khoảng 100–150 câu, trải trên nhiều LO, nhiều mức Bloom và cả 5 loại câu;
- lấy từ ít nhất 2 môn để tránh kết luận chỉ đúng với một kiểu tài liệu.

**Thí nghiệm loại bỏ (ablation)** để đo đóng góp của từng lớp:

| Cấu hình | Gồm |
|---|---|
| A | chỉ sinh (RAG + schema) |
| B | A + luật tất định |
| C | B + giám khảo (giải mù, kiểm căn cứ) + sửa |
| D | C + kế hoạch và hướng dẫn Bloom + giám khảo Bloom |

**Người chấm:**
- 2 người (giảng viên hoặc trợ giảng) chấm **mù**: không biết câu thuộc cấu hình nào, không biết mức Bloom được yêu cầu;
- tiêu chí: đúng/sai; có đúng một đáp án đúng; bám LO (1–5); mức Bloom (chọn 1–6); phương án nhiễu hợp lý (1–5); rõ ràng (1–5).

**Độ đo:**
- **Đồng thuận người–người:** Cohen's κ cho tiêu chí nhị phân (Cohen, 1960); weighted κ cho thang thứ bậc, kể cả mức Bloom (Cohen, 1968). Diễn giải theo Landis & Koch (1977), và ghi rõ các mức đó chỉ là quy ước.
- **Bloom:** tỉ lệ khớp đúng mức và tỉ lệ lệch không quá một mức, giữa mức gán và mức người chấm đồng thuận.
- **Hiệu chỉnh giám khảo:** so phán quyết của giám khảo LLM với nhãn đồng thuận của người. Đồng thuận thấp thì chỉnh rubric hoặc đổi model trước khi tin giám khảo (Scaria et al., 2024 cho thấy đây là bước không bỏ được).
- **So sánh các cấu hình:**
  - tỉ lệ lỗi đúng/sai;
  - tỉ lệ câu đúng mức Bloom;
  - điểm phương án nhiễu;
  - tỉ lệ trùng;
  - chi phí và thời gian duyệt trên mỗi câu được duyệt.

### 7.2 Chấm tự luận

- 50–100 bài làm thật, được giảng viên chấm độc lập với AI.
- Một phần bài được chấm bởi hai người, để có QWK người–người làm mốc.
- Báo cáo QWK người–máy, độ đồng thuận theo từng ý rubric, và độ lệch điểm trung bình. Đối chiếu với ngưỡng 0,70 và mức giảm ≤ 0,10 (Williamson et al., 2012).
- Thử thêm các bài làm có chèn lệnh để kiểm tra khả năng chống prompt injection.

### 7.3 Sau khi dùng

Chạy phân tích câu hỏi (4.12) trên lớp thật. Báo cáo tỉ lệ câu bị gắn cờ theo từng loại cờ, và xem câu bị gắn cờ có trùng với câu giảng viên từng sửa hay không.

---

## 8. Phạm vi và giới hạn

**Không đưa vào phạm vi chính:**
- tự động duyệt (auto-pass) nội dung dùng để tính điểm;
- sinh video, giọng đọc hay hình ảnh;
- fine-tune hoặc DPO;
- semantic entropy cho mọi câu trả lời thời gian thực;
- tranh luận nhiều agent (multi-agent debate). Với cùng số lần gọi, cách này không tốt hơn self-consistency (Huang et al., 2024).

**Giới hạn cần nói rõ khi bảo vệ:**
- Giám khảo LLM và luật tất định giảm lỗi chứ không loại hết lỗi. Giảng viên vẫn là người quyết định.
- Mức Bloom 6 không đo được bằng câu chấm tự động.
- Với lớp nhỏ, chỉ số phân tích câu hỏi chỉ là tín hiệu.
- Chất lượng đầu ra bị giới hạn bởi tài liệu nguồn: slide nghèo nội dung thì câu hỏi nghèo nội dung.

---

## 9. Đoạn có thể dùng trong báo cáo

**English:**

> AI-generated learning content is treated as a draft rather than final material. Each item is generated from retrieved course materials and must carry a verbatim evidence quote that is checked deterministically against its source. Deterministic item-writing rules run before any model-based check. A judge model, different from the generator, first solves each multiple-choice item without seeing the key, then rates factual support, learning-outcome alignment, Bloom level and distractor quality. Failed items are repaired using this external feedback for a bounded number of rounds and otherwise discarded. Every verdict is stored with the item, so instructors see why an item was flagged; instructors review all content used for grading, with a risk score only ordering the queue. Short answers are graded rubric point by rubric point, with the score computed by code and ungradable answers routed to the instructor. The judge is calibrated against human raters, and item quality is re-examined with classical item analysis on real learner responses.

**Tiếng Việt:**

> Nội dung học tập do AI sinh được coi là bản nháp, không phải nội dung cuối. Mỗi câu hỏi được sinh từ tài liệu môn học truy xuất được và phải kèm trích dẫn nguyên văn. Trích dẫn này được kiểm tra bằng code so với đoạn nguồn. Các luật viết câu hỏi tất định chạy trước mọi bước kiểm tra bằng model. Một model giám khảo, khác model sinh, tự giải câu trắc nghiệm khi chưa thấy đáp án, sau đó đánh giá căn cứ, mức bám LO, mức Bloom và chất lượng phương án nhiễu. Câu lỗi được sửa dựa trên phản hồi này trong một số lượt giới hạn, vẫn lỗi thì bị loại. Mọi phán quyết được lưu cùng câu hỏi để giảng viên thấy lý do gắn cờ. Giảng viên duyệt toàn bộ nội dung dùng để tính điểm; điểm rủi ro chỉ dùng để sắp xếp hàng đợi. Câu tự luận được chấm theo từng ý của rubric, điểm do code tính; câu AI không chấm được được chuyển cho giảng viên. Giám khảo được hiệu chỉnh với người chấm, và chất lượng câu hỏi được kiểm tra lại bằng phân tích câu hỏi trên dữ liệu làm bài thật.

---

## 10. Tài liệu tham khảo

| Chủ đề | Tài liệu |
|---|---|
| RAG | Lewis, P. et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *NeurIPS 2020*. https://arxiv.org/abs/2005.11401 |
| Đánh giá RAG | Es, S. et al. (2024). RAGAS: Automated Evaluation of Retrieval Augmented Generation. *EACL 2024 (Demo)*. https://arxiv.org/abs/2309.15217 |
| Đánh giá RAG | Saad-Falcon, J. et al. (2024). ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems. *NAACL 2024*. https://arxiv.org/abs/2311.09476 |
| Đa dạng khi chọn nội dung | Carbonell, J. & Goldstein, J. (1998). The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries. *SIGIR 1998*. https://doi.org/10.1145/290941.291025 |
| Trích dẫn / attribution | Rashkin, H. et al. (2023). Measuring Attribution in Natural Language Generation Models. *Computational Linguistics* 49(4). https://arxiv.org/abs/2112.12870 |
| Trích dẫn / attribution | Gao, T., Yen, H., Yu, J., Chen, D. (2023). Enabling Large Language Models to Generate Text with Citations. *EMNLP 2023*. https://arxiv.org/abs/2305.14627 |
| Kiểm chứng sự thật | Thorne, J. et al. (2018). FEVER: a Large-scale Dataset for Fact Extraction and VERification. *NAACL 2018*. https://aclanthology.org/N18-1074/ |
| Kiểm theo mệnh đề | Min, S. et al. (2023). FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation. *EMNLP 2023*. https://aclanthology.org/2023.emnlp-main.741/ |
| Kiểm theo mệnh đề | Wei, J. et al. (2024). Long-form factuality in large language models (SAFE). *NeurIPS 2024*. https://arxiv.org/abs/2403.18802 |
| Lỗi viết câu hỏi | Haladyna, T. M., Downing, S. M., Rodriguez, M. C. (2002). A Review of Multiple-Choice Item-Writing Guidelines for Classroom Assessment. *Applied Measurement in Education* 15(3), 309–333. https://doi.org/10.1207/S15324818AME1503_5 |
| Lỗi viết câu hỏi | Tarrant, M., Knierim, A., Hayes, S. K., Ware, J. (2006). The frequency of item writing flaws in multiple-choice questions used in high stakes nursing assessments. *Nurse Education Today* 26(8), 662–671. https://doi.org/10.1016/j.nedt.2006.07.006 |
| Lỗi viết câu hỏi | Downing, S. M. (2005). The effects of violating standard item writing principles on tests and students. *Advances in Health Sciences Education* 10(2), 133–143. https://doi.org/10.1007/s10459-004-4019-5 |
| Luật vs LLM | Moore, S., Nguyen, H. A., Chen, T., Stamper, J. (2023). Assessing the Quality of Multiple-Choice Questions Using GPT-4 and Rule-Based Methods. *EC-TEL 2023*, LNCS, 229–245. https://doi.org/10.1007/978-3-031-42682-7_16 |
| Luật vs LLM | Moore, S., Costello, E., Nguyen, H. A., Stamper, J. (2024). An Automatic Question Usability Evaluation Toolkit. *AIED 2024*. https://arxiv.org/abs/2405.20529 |
| LLM-as-a-judge | Zheng, L. et al. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. *NeurIPS 2023 Datasets and Benchmarks*. https://arxiv.org/abs/2306.05685 |
| Thiên lệch giám khảo | Wang, P. et al. (2024). Large Language Models are not Fair Evaluators. *ACL 2024*. https://aclanthology.org/2024.acl-long.511/ |
| Thiên lệch giám khảo | Panickssery, A., Bowman, S. R., Feng, S. (2024). LLM Evaluators Recognize and Favor Their Own Generations. *NeurIPS 2024*. https://arxiv.org/abs/2404.13076 |
| Thứ tự phương án | Pezeshkpour, P. & Hruschka, E. (2024). Large Language Models Sensitivity to The Order of Options in Multiple-Choice Questions. *Findings of NAACL 2024*. https://aclanthology.org/2024.findings-naacl.130/ |
| Thứ tự phương án | Zheng, C. et al. (2024). Large Language Models Are Not Robust Multiple Choice Selectors. *ICLR 2024*. https://arxiv.org/abs/2309.03882 |
| Bloom | Anderson, L. W. & Krathwohl, D. R. (Eds.) (2001). *A Taxonomy for Learning, Teaching, and Assessing: A Revision of Bloom's Taxonomy of Educational Objectives*. Longman. |
| Bloom | Krathwohl, D. R. (2002). A Revision of Bloom's Taxonomy: An Overview. *Theory Into Practice* 41(4), 212–218. https://doi.org/10.1207/s15430421tip4104_2 |
| Căn chỉnh mục tiêu | Biggs, J. (1996). Enhancing teaching through constructive alignment. *Higher Education* 32(3), 347–364. https://doi.org/10.1007/BF00138871 |
| Sinh câu theo Bloom | Scaria, N., Chenna, S. D., Subramani, D. (2024). Automated Educational Question Generation at Different Bloom's Skill Levels using Large Language Models: Strategies and Evaluation. *AIED 2024*. https://arxiv.org/abs/2408.04394 |
| Sinh câu theo Bloom | Elkins, S., Kochmar, E., Cheung, J. C. K., Serban, I. (2024). How Teachers Can Use Large Language Models and Bloom's Taxonomy to Create Educational Quizzes. *AAAI 2024*, 38(21), 23084–23091. https://doi.org/10.1609/aaai.v38i21.30353 |
| Sinh câu theo LO | Doughty, J. et al. (2024). A Comparative Study of AI-Generated (GPT-4) and Human-crafted MCQs in Programming Education. *ACE 2024*. https://doi.org/10.1145/3636243.3636256 |
| Tổng quan sinh câu hỏi | Kurdi, G. et al. (2020). A Systematic Review of Automatic Question Generation for Educational Purposes. *IJAIED* 30, 121–204. https://doi.org/10.1007/s40593-019-00186-y |
| Đáp án nhiễu | Gierl, M. J., Bulut, O., Guo, Q., Zhang, X. (2017). Developing, Analyzing, and Using Distractors for Multiple-Choice Tests in Education: A Comprehensive Review. *Review of Educational Research* 87(6), 1082–1116. https://doi.org/10.3102/0034654317726529 |
| Đáp án nhiễu | Haladyna, T. M. & Downing, S. M. (1993). How Many Options is Enough for a Multiple-Choice Test Item? *Educational and Psychological Measurement* 53, 999–1010. |
| Đáp án nhiễu | Tarrant, M., Ware, J., Mohammed, A. M. (2009). An assessment of functioning and non-functioning distractors in multiple-choice questions: a descriptive analysis. *BMC Medical Education* 9, 40. https://doi.org/10.1186/1472-6920-9-40 |
| Đáp án nhiễu | Raina, V., Liusie, A., Gales, M. (2023). Assessing Distractors in Multiple-Choice Tests. *Eval4NLP 2023*. https://aclanthology.org/2023.eval4nlp-1.2/ |
| Đáp án nhiễu | Alhazmi, E. et al. (2024). Distractor Generation in Multiple-Choice Tasks: A Survey of Methods, Datasets, and Evaluation. *EMNLP 2024*. https://aclanthology.org/2024.emnlp-main.799/ |
| Đáp án nhiễu | Benedetto, L., Taslimipoor, S., Buttery, P. (2025). A Survey on Automated Distractor Evaluation in Multiple-Choice Tasks. *BEA 2025*. https://aclanthology.org/2025.bea-1.5/ |
| Tự sửa | Shinn, N. et al. (2023). Reflexion: Language Agents with Verbal Reinforcement Learning. *NeurIPS 2023*. https://arxiv.org/abs/2303.11366 |
| Tự sửa | Madaan, A. et al. (2023). Self-Refine: Iterative Refinement with Self-Feedback. *NeurIPS 2023*. https://arxiv.org/abs/2303.17651 |
| Tự sửa | Dhuliawala, S. et al. (2024). Chain-of-Verification Reduces Hallucination in Large Language Models. *Findings of ACL 2024*. https://aclanthology.org/2024.findings-acl.212/ |
| Giới hạn tự sửa | Huang, J. et al. (2024). Large Language Models Cannot Self-Correct Reasoning Yet. *ICLR 2024*. https://arxiv.org/abs/2310.01798 |
| Câu hỏi sâu | Graesser, A. C. & Person, N. K. (1994). Question Asking During Tutoring. *American Educational Research Journal* 31(1), 104–137. https://doi.org/10.3102/00028312031001104 |
| Chấm tự luận ngắn | Burrows, S., Gurevych, I., Stein, B. (2015). The Eras and Trends of Automatic Short Answer Grading. *IJAIED* 25, 60–117. https://doi.org/10.1007/s40593-014-0026-8 |
| Chấm tự luận ngắn | Chamieh, I., Zesch, T., Giebermann, K. (2024). LLMs in Short Answer Scoring: Limitations and Promise of Zero-Shot and Few-Shot Approaches. *BEA 2024*, 309–315. https://aclanthology.org/2024.bea-1.25/ |
| Chấm tự động | Williamson, D. M., Xi, X., Breyer, F. J. (2012). A Framework for Evaluation and Use of Automated Scoring. *Educational Measurement: Issues and Practice* 31(1), 2–13. https://doi.org/10.1111/j.1745-3992.2011.00223.x |
| Prompt injection | Greshake, K. et al. (2023). Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection. *AISec 2023*. https://arxiv.org/abs/2302.12173 |
| Prompt injection | OWASP (2025). LLM01:2025 Prompt Injection. *OWASP Top 10 for LLM Applications*. https://genai.owasp.org/llmrisk/llm01-prompt-injection/ |
| Bất định | Wang, X. et al. (2023). Self-Consistency Improves Chain of Thought Reasoning in Language Models. *ICLR 2023*. https://arxiv.org/abs/2203.11171 |
| Bất định | Manakul, P., Liusie, A., Gales, M. (2023). SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative LLMs. *EMNLP 2023*. https://arxiv.org/abs/2303.08896 |
| Bất định | Farquhar, S., Kossen, J., Kuhn, L., Gal, Y. (2024). Detecting hallucinations in large language models using semantic entropy. *Nature* 630, 625–630. https://doi.org/10.1038/s41586-024-07421-0 |
| Người trong vòng lặp | Wu, X. et al. (2022). A survey of human-in-the-loop for machine learning. *Future Generation Computer Systems* 135, 364–381. https://doi.org/10.1016/j.future.2022.05.014 |
| Tương tác người–AI | Amershi, S. et al. (2019). Guidelines for Human-AI Interaction. *CHI 2019*. https://doi.org/10.1145/3290605.3300233 |
| Phân tích câu hỏi | Crocker, L. & Algina, J. (1986). *Introduction to Classical and Modern Test Theory*. Holt, Rinehart and Winston. |
| Phân tích câu hỏi | Ebel, R. L. & Frisbie, D. A. (1991). *Essentials of Educational Measurement* (5th ed.). Prentice-Hall. |
| Độ tin cậy của đề | Kuder, G. F. & Richardson, M. W. (1937). The theory of the estimation of test reliability. *Psychometrika* 2(3), 151–160. https://doi.org/10.1007/BF02288391 |
| Độ tin cậy của đề | Cronbach, L. J. (1951). Coefficient alpha and the internal structure of tests. *Psychometrika* 16(3), 297–334. https://doi.org/10.1007/BF02310555 |
| Câu hỏi do LLM sinh, đo bằng dữ liệu thật | Bhandari, S., Liu, Y., Kwak, Y., Pardos, Z. A. (2024). Evaluating the psychometric properties of ChatGPT-generated questions. *Computers and Education: Artificial Intelligence* 7, 100284. |
| Đồng thuận người chấm | Cohen, J. (1960). A Coefficient of Agreement for Nominal Scales. *Educational and Psychological Measurement* 20(1), 37–46. https://doi.org/10.1177/001316446002000104 |
| Đồng thuận người chấm | Cohen, J. (1968). Weighted kappa: Nominal scale agreement with provision for scaled disagreement or partial credit. *Psychological Bulletin* 70(4), 213–220. https://doi.org/10.1037/h0026256 |
| Đồng thuận người chấm | Landis, J. R. & Koch, G. G. (1977). The Measurement of Observer Agreement for Categorical Data. *Biometrics* 33(1), 159–174. https://doi.org/10.2307/2529310 |
| Học theo sở thích | Rafailov, R. et al. (2023). Direct Preference Optimization: Your Language Model is Secretly a Reward Model. *NeurIPS 2023*. https://arxiv.org/abs/2305.18290 |

---

## 11. Kết luận

```text
AI viết bản nháp → code kiểm tra luật → giám khảo khác model giải và chấm → sửa có giới hạn
  → lưu kèm lý do → giảng viên duyệt → người học dùng → dữ liệu làm bài kiểm chứng lại
  → lỗi quay về cải thiện prompt và luật
```

- **RAG và trích dẫn nguyên văn** cho nội dung một căn cứ kiểm tra được.
- **Luật tất định** bắt lỗi hình thức rẻ, nhanh, có test.
- **Giám khảo giải trước, chấm sau, khác model** tránh được các thiên lệch đã biết của LLM-as-a-judge.
- **Kiểm soát Bloom bắt đầu từ bước chọn nội dung và viết câu**, không chỉ ở bước kiểm tra.
- **Giảng viên giữ quyền quyết định**, với giao diện cho thấy lý do và thứ tự ưu tiên.
- **Dữ liệu làm bài thật** là thước đo cuối cùng của chất lượng câu hỏi.

Cách trình bày này an toàn về mặt học thuật: thừa nhận LLM có lỗi, đặt giới hạn rõ cho từng lớp kiểm tra, và đề xuất cách đo hiệu quả của từng lớp bằng dữ liệu.
