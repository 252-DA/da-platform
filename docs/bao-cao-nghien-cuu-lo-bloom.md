# Báo cáo nghiên cứu: Căn chỉnh Learning Outcome, nội dung học và Bloom

**Dự án:** DA Platform — LMS tạo Micro-Content và Quiz bằng Generative AI  
**Ngày tra cứu và đối chiếu code:** 14/10/2026  
**Mục đích:** xác định các hướng nghiên cứu có thể giải quyết việc gắn tài liệu với LO và kiểm chứng mức Bloom của câu hỏi.

## Tóm tắt

DA Platform đã có dữ liệu LO, quan hệ chương–LO, embedding để khớp tài liệu với chương và pipeline sinh câu hỏi theo Bloom. Phần còn thiếu là đánh giá nội dung ở cấp từng LO và kiểm chứng thao tác nhận thức của câu sau khi sinh.

Báo cáo chọn **10 bài nghiên cứu**, gồm hai bài nền tảng về thiết kế dạy học, sáu bài về LO/Bloom/nội dung giáo dục và hai bài về truy xuất văn bản. Nghiên cứu hiện có cung cấp phương pháp, dữ liệu và một số mã nguồn để thử nghiệm. Các kết quả chưa đủ để khẳng định một mô hình sẽ giải quyết trọn vẹn bài toán trên tài liệu tiếng Việt của hệ thống.

**Hướng đề xuất cho dự án:** làm rõ các tiêu chí trong LO; tìm và xác minh bằng chứng từ tài liệu cho từng tiêu chí; đánh giá LO và Bloom của từng câu; lưu kết quả để giảng viên xác nhận. Đây là đề xuất triển khai của báo cáo, chưa phải một quy trình đã được kiểm chứng trên DA Platform.

## 1. Phạm vi và cách chọn tài liệu

Việc tra cứu tập trung vào bốn câu hỏi:

1. Có thể tự động phân loại LO theo Bloom đến mức nào?
2. Có thể tự động gắn nội dung học với LO bằng phương pháp nào?
3. Câu do AI sinh có thực sự đạt Bloom được yêu cầu không?
4. Cần đánh giá bằng chứng nào trước khi đưa các phương pháp này vào hệ thống?

Các truy vấn gồm tên bài báo và các nhóm từ khóa như *learning outcomes Bloom classification*, *multi-label learning objectives*, *cross-dataset Bloom question classification*, *resource–topic alignment*, *educational question generation* và *passage reranking*.

Ưu tiên bản bài báo, trang nhà xuất bản, ACL Anthology, arXiv và trang của tác giả. Đây là **tổng quan có chọn lọc phục vụ thiết kế hệ thống**, không phải tổng quan hệ thống theo PRISMA; không tuyên bố đã tìm hết nghiên cứu liên quan. Một số bài chỉ tiếp cận được tóm tắt hoặc trích đoạn; mức tiếp cận được ghi ở danh mục cuối.

Các con số dưới đây là kết quả tác giả báo cáo. Không chạy lại các mô hình trong bài báo và không dùng kết quả đó như số đo của DA Platform.

## 2. Cần phân biệt những gì?

### 2.1. Căn chỉnh mục tiêu, hoạt động học và đánh giá

Biggs đặt vấn đề thiết kế mục tiêu, hoạt động học và đánh giá sao cho cùng hướng đến năng lực người học phải thể hiện. Cách tiếp cận này thường được gọi là *constructive alignment*. Đây là cơ sở lý luận để kiểm tra cả nội dung học lẫn nhiệm vụ đánh giá, thay vì chỉ gắn một mã LO lên câu hỏi. [Biggs, 1996 — bài nền tảng P1](https://link.springer.com/article/10.1007/BF00138871).

Trong dự án, nên tách ba quyết định:

| Quyết định | Câu hỏi cần trả lời | Ví dụ trong môn Cơ sở dữ liệu |
|---|---|---|
| LO → yêu cầu năng lực | Người học cần làm được gì? | Viết truy vấn SQL đáp ứng yêu cầu nghiệp vụ |
| Nội dung → LO | Đoạn này cung cấp kiến thức, quy trình hay ví dụ cần cho năng lực đó không? | Ví dụ về `JOIN` hỗ trợ viết truy vấn nhiều bảng |
| Câu hỏi → LO/Bloom | Làm đúng câu này chứng minh được thao tác nào? | Viết truy vấn khác với nhắc lại định nghĩa `JOIN` |

Ví dụ do báo cáo xây dựng: câu “SELECT dùng để làm gì?” và nhiệm vụ “Viết truy vấn tìm khách hàng chưa có đơn hàng” cùng liên quan SQL. Mức phù hợp với LO và yêu cầu nhận thức phải được xem xét riêng trên nhiệm vụ, dữ kiện và cách chấm.

### 2.2. Bloom có hai chiều

Bloom sửa đổi có chiều **quá trình nhận thức** và chiều **kiến thức**. Sáu mức nhận thức được tóm tắt dưới đây; kiến thức gồm sự kiện, khái niệm, quy trình và siêu nhận thức. Như vậy, một số 1–6 chưa thể hiện toàn bộ khung phân loại. [Krathwohl, 2002 — P2](https://doi.org/10.1207/s15430421tip4104_2).

| Mức | Thao tác cần được thể hiện |
|---|---|
| 1 — Nhớ | Nhận ra hoặc nhắc lại kiến thức |
| 2 — Hiểu | Diễn giải, phân loại, tóm tắt hoặc giải thích ý nghĩa |
| 3 — Vận dụng | Thực hiện hoặc sử dụng một quy trình |
| 4 — Phân tích | Xác định thành phần, quan hệ hoặc cấu trúc |
| 5 — Đánh giá | Đưa ra nhận định theo tiêu chí |
| 6 — Sáng tạo | Tạo phương án, kế hoạch hoặc sản phẩm |

Bảng là cơ sở xây rubric; không phải bảng thay thế trực tiếp động từ bằng nhãn. Với hệ thống hiện tại, cần đối chiếu cả câu hỏi, đáp án/rubric và bối cảnh môn học khi xác nhận một mức Bloom.

## 3. Hiện trạng DA Platform

### 3.1. Những gì đã xác nhận từ code

| Thành phần | Hiện trạng | Hạn chế còn lại |
|---|---|---|
| Trích xuất Bloom của LO | `_infer_bloom()` chọn động từ khớp ở vị trí sớm nhất; nhãn mang provenance `inferred`. | Không biểu diễn được đầy đủ một LO có nhiều hành vi; phụ thuộc bảng động từ. |
| Khớp tài liệu với chương | `EmbeddingChapterMatcher` so nội dung với hồ sơ chương, có ngưỡng điểm và khoảng cách với chương đứng thứ hai. | Kết quả xác định chương; chưa xác định mức hỗ trợ từng LO. |
| Mapping chunk với LO | `HeuristicLoMapper` nhận chương và duyệt mọi LO được đề cương gắn với chương đó. | Nội dung thân chunk chưa được dùng để quyết định từng cạnh chunk–LO. |
| Confidence của mapping | Chương đơn thuần cho điểm 0,5; có từ trong heading khớp LO thì tăng lên 0,7. | Đây là điểm do luật đặt, chưa phải xác suất đúng được hiệu chỉnh bằng dữ liệu gán nhãn. |
| Sinh và lưu câu | Mức yêu cầu của request được ưu tiên, sau đó đến Bloom của LO; thiếu cả hai thì dùng `understand` và ghi log. | Nhãn lưu phản ánh mục tiêu lúc sinh, chưa phải kết quả phân loại câu. |
| Kiểm tra câu | Verifier xét đáp án, lời giải và khả năng phương án khác cũng đúng theo nguồn. | Chưa nhận LO trong bước kiểm tra; chưa trả Bloom được đánh giá. |
| Dữ liệu | Có `bloom_provenance`, `chunk_lo_mappings.source/provenance` và ma trận LO × Bloom. | Chưa có các trường riêng cho Bloom yêu cầu, AI đánh giá và giảng viên xác nhận của câu. |

Các vị trí đối chiếu:

- [Suy luận Bloom từ LO](../packages-ai/src/document_chunk/adapters/curriculum/dcmh_extractor.py): `_BLOOM_VERBS`, `_infer_bloom`, `_extract_los`.
- [Khớp chương bằng embedding](../packages-ai/src/document_chunk/adapters/curriculum/embedding_chapter_matcher.py): `EmbeddingChapterMatcher.match`.
- [Mapping chunk–LO](../packages-ai/src/document_chunk/adapters/curriculum/heuristic_lo_mapper.py): `HeuristicLoMapper.map`.
- [Nối mapper và chapter matcher trong worker](../worker/worker/container.py): `_build_map_chunks_to_los`.
- [Chọn và lưu Bloom khi sinh câu](../worker/worker/use_cases/generate_curriculum_quiz.py): `execute`.
- [Prompt sinh/kiểm tra](../worker/worker/prompts/curriculum_quiz.py): `generation`, `verification`.
- [Schema hiện tại](../core-api/prisma/schema.prisma): `learning_outcomes`, `chunk_lo_mappings`, `quiz_items`.

### 3.2. Hai kiểm tra tái hiện

**Trường hợp A — LO ghép nhiều hành vi.** Gọi trực tiếp `_infer_bloom()` với “Trình bày và phân tích các phương pháp xử lý dữ liệu” cho kết quả `remember`. Đây là hành vi đúng theo luật hiện tại, nhưng không phản ánh yêu cầu phân tích xuất hiện sau đó.

**Trường hợp B — các LO cùng chương.** Tạo một chương có hai LO: “Viết truy vấn SQL” và “Chuẩn hóa lược đồ quan hệ”. Chunk có heading “SELECT và WHERE”, thân chứa `SELECT name FROM students WHERE age > 18;`. Mapper tạo cạnh đến cả hai LO, mỗi cạnh confidence 0,5.

Hai trường hợp dùng dữ liệu tự dựng để kiểm tra hành vi của code. Chúng chưa cho biết tỷ lệ mapping sai trong dữ liệu môn học thực tế.

**Kiểm tra hồi quy:** 11 test thuộc `TestBloomLevel` và 19 test mapper/document placement đều pass. Lỗi cũ quy đổi khiến mọi câu lưu Bloom 2 đã được sửa. Các test này chưa đo độ chính xác sư phạm của câu sinh thật. Chưa kiểm tra cấu hình hoặc dữ liệu production trong đợt rà soát này.

## 4. Những nghiên cứu có thể áp dụng

### 4.1. Phân loại LO bằng prompt và BERT — Almatrafi & Johri, 2025 [P3]

**Bài toán:** gán một hoặc nhiều mức Bloom cho LO. Tác giả đánh giá GPT-4 trên 1.000 LO lấy từ tập kiểm tra của bộ dữ liệu 21.380 LO; so sánh các prompt với BERT fine-tune.

**Kết quả:** prompt kết hợp ngữ cảnh và hướng dẫn theo mức tốt nhất trong nhóm GPT-4. F1 từng mức của prompt P2+P3 đạt 0,591–0,793; BERT đạt 0,873–0,936. Đây là F1 theo từng nhãn, không phải một điểm accuracy sáu lớp. [Bài báo và bảng 4–6](https://eventosepge.fgv.br/files/leveraging-generative-ai-for-course-learning-o-2025-computers-and-education.pdf).

**Giới hạn và ứng dụng:** kết quả trên tập kiểm tra cùng nguồn chưa chứng minh khả năng chuyển sang LO tiếng Việt. Với dự án, LLM là phương án thử trước khi có dữ liệu huấn luyện; BERT là đối chứng cần xem xét nếu đã tích lũy nhãn đủ tốt.

### 4.2. LO phức hợp và phân loại nhiều nhãn — Kolagar và cộng sự, 2025 [P4]

**Bài toán:** mapping LO trong mô tả môn học với Bloom, cho phép nhiều nhãn. Bộ dữ liệu gồm 35 phần LO, tách thành 159 đoạn; năm chuyên gia gán nhãn, Krippendorff’s α = 0,76.

**Kết quả:** weighted F1 của regex là 0,52; semantic similarity là 0,50; các cách dùng GPT-4 đạt 0,60–0,69. [Bài báo, mục 4 và bảng 2](https://aclanthology.org/anthology-files/pdf/bea/2025.bea-1.32.pdf).

**Giới hạn và ứng dụng:** mẫu nhỏ, xử lý bằng tiếng Anh, một phần dịch từ tiếng Đức. Điểm quan trọng với DA Platform là mô hình hóa LO phức hợp: nên xem xét từng hành vi trước khi quyết định một nhãn mục tiêu cho giao diện. Chỉ thay bảng động từ bằng cosine similarity với tên mức Bloom chưa có bằng chứng là đủ.

### 4.3. Khả năng chuyển sang bộ câu hỏi khác — Faraji và cộng sự, 2026 [P5]

**Bài toán:** phân loại Bloom của câu hỏi trên năm bộ dữ liệu, tổng 4.179 câu; so sánh SVM, BERT và LLM. Bài tự ghi nhận được chấp nhận tại AIED 2026.

**Kết quả:** BERT đạt weighted F1 0,76–0,91 khi kiểm tra cùng nguồn, nhưng 0,31–0,76 khi chuyển nguồn. GPT-5 với ví dụ tuyển chọn và động từ theo miền đạt 0,76–0,84. [Bài báo, bảng 2–3](https://arxiv.org/html/2606.13684v1).

**Giới hạn và ứng dụng:** ví dụ few-shot được lấy theo bộ dữ liệu đích; kết quả không đồng nghĩa tổng quát hóa hoàn toàn không cần thích nghi. Có [liên kết mã, prompt và dữ liệu](https://gitlab.com/zrasoulkhani/bloom-classification-aied2026). Dự án nên đánh giá cả chuyển môn, thay vì chỉ chia ngẫu nhiên một ngân hàng câu.

### 4.4. Sinh câu đúng Bloom và đánh giá bằng chuyên gia — Scaria và cộng sự, 2024 [P6]

**Bài toán:** năm LLM, năm cấu hình prompt, 17 chủ đề Data Science; tổng 2.550 câu. Hai chuyên gia và một LLM đánh giá chất lượng.

**Kết quả:** 78% câu được đánh giá chất lượng cao; trong nhóm này, 65,56% khớp Bloom yêu cầu theo cả hai chuyên gia. Đánh giá tự động chưa ngang đánh giá người. [Bài báo, mục 3](https://arxiv.org/html/2408.04394v1).

**Giới hạn và ứng dụng:** câu được sinh từ kiến thức của model, không nhận đoạn tài liệu môn học như pipeline RAG của dự án. Không thể chuyển trực tiếp tỷ lệ trên sang DA Platform. Có [prompt và dữ liệu đánh giá công khai](https://github.com/nicyscaria/AEQG_Blooms_Evaluation_LLMs) để tham khảo cách tách chất lượng câu khỏi mức khớp Bloom.

### 4.5. Mapping tài nguyên với chủ đề môn học — Gancevska & Ramanauskaitė, 2026 [P7]

**Bài toán:** gắn tên và mô tả tài nguyên Moodle với chủ đề trong đề cương, đối chiếu đánh giá chuyên gia trên bốn môn.

**Kết quả:** theo tóm tắt, phương pháp dùng LLM có MAE/MSE thấp nhất và phù hợp chuyên gia nhất; cấu hình SBERT được thử cho kết quả yếu nhất. [Bài báo trên Applied Sciences](https://www.mdpi.com/2076-3417/16/4/2039).

**Giới hạn và ứng dụng:** đây là resource–topic mapping từ metadata, chưa phải phân tích thân chunk hay chứng minh đạt LO. Đợt tra cứu tiếp cận tóm tắt và phần phương pháp được lập chỉ mục, chưa đối chiếu đầy đủ bảng kết quả. Với dự án, cần giữ keyword và LLM làm đối chứng khi đánh giá mapper embedding.

### 4.6. Hỗ trợ giảng viên viết LO — Gültekin và cộng sự, 2026 [P8]

**Bài toán:** hệ thống dùng LLM hỗ trợ viết và đánh giá CLO, thử với 22 giảng viên.

**Kết quả:** tóm tắt báo cáo điểm SUS trung bình 79,64. Tác giả đồng thời ghi nhận độ đồng thuận chuyên gia thấp ở một số tiêu chí trừu tượng về căn chỉnh Bloom, nên diễn giải các chênh lệch tương ứng như kết quả thăm dò. [Tóm tắt tại cơ sở của tác giả](https://avesis.kocaeli.edu.tr/yayin/a985831b-7cc6-4106-98b8-698b13183619/an-llm-assisted-decision-support-system-for-semantic-analysis-of-blooms-taxonomy-aligned-learning-outcomes).

**Giới hạn và ứng dụng:** SUS đo trải nghiệm sử dụng, không đo accuracy của bộ phân loại. Báo cáo chỉ tiếp cận tóm tắt/trích đoạn. Bài phù hợp để tham khảo quy trình AI đề xuất và giảng viên hiệu chỉnh LO, chưa đủ để chọn model cho DA Platform.

### 4.7. Embedding để tìm ứng viên — Reimers & Gurevych, 2019 [P9]

Sentence-BERT tạo vector câu có thể so sánh bằng cosine similarity, giúp tìm văn bản tương đồng mà không phải chạy mô hình trên mọi cặp câu. [Bài báo tại EMNLP-IJCNLP](https://aclanthology.org/D19-1410/).

Đây là nghiên cứu về biểu diễn và tương đồng văn bản, không đánh giá mức hỗ trợ LO. Áp dụng vào dự án là **suy luận thiết kế**: dùng embedding để tìm các chunk ứng viên theo mô tả LO, rồi đánh giá thêm bằng chứng. Mô hình dùng cho tiếng Việt và văn bản song ngữ vẫn cần chọn bằng bộ kiểm tra riêng.

### 4.8. Đánh giá lại từng cặp truy vấn–đoạn văn — Nogueira & Cho, 2019 [P10]

Bài đề xuất BERT cho passage reranking: xét truy vấn cùng đoạn văn để sắp lại các ứng viên truy xuất. Các thí nghiệm là truy xuất thông tin trên MS MARCO và TREC-CAR. [Preprint, phiên bản đọc v5 cập nhật năm 2020](https://arxiv.org/abs/1901.04085).

Áp dụng reranker cho cặp LO–chunk là **đề xuất của báo cáo**; bài gốc chưa kiểm chứng nhiệm vụ này. Một đoạn được xếp hạng cao có thể liên quan chủ đề nhưng thiếu quy trình hoặc dữ kiện cần để đo LO. Vì vậy, điểm reranker cần đi cùng kiểm tra bằng chứng và tập nhãn đối chứng.

## 5. Lựa chọn phương án cho DA Platform

### 5.1. Những kết luận có thể rút ra

Các nghiên cứu trên giải quyết những nhiệm vụ và bộ dữ liệu khác nhau. Báo cáo không xếp hạng model bằng cách đặt F1 của P3 cạnh F1 của P5: P3 phân loại LO với nhiều nhãn, còn P5 phân loại câu hỏi trên dữ liệu khác.

| Phương án | Vai trò phù hợp trong dự án | Điều cần xác minh |
|---|---|---|
| Luật động từ/heading | Mốc đối chiếu rẻ, dễ giải thích | Lỗi với LO ghép và nội dung có cùng chủ đề |
| LLM theo rubric và ví dụ đã duyệt | Đề xuất Bloom, phân tích tiêu chí và kiểm tra bằng chứng | Độ khớp giảng viên, chi phí, tỷ lệ chưa kết luận được |
| BERT hoặc classifier huấn luyện riêng | Phương án khi đã có dữ liệu gán nhãn ổn định | Chuyển môn, nhãn hiếm, thay đổi phiên bản nội dung |
| Embedding | Tìm ứng viên LO–chunk nhanh | Bỏ sót bằng chứng; nhầm nội dung cùng chủ đề |
| Reranker | Sắp lại ứng viên theo từng cặp | Điểm liên quan có phản ánh mức hỗ trợ LO không |
| Giảng viên xác nhận | Tạo nhãn tham chiếu và quyết định dùng câu | Rubric và cách xử lý bất đồng phải thống nhất |

Một phương pháp có thể tốt ở cùng nguồn dữ liệu nhưng giảm khi chuyển môn hoặc người gán nhãn. Vì vậy, lựa chọn ban đầu nên dựa trên khả năng thử nghiệm và đo đạc của dự án; quyết định cuối dựa trên tập đánh giá tiếng Việt.

### 5.2. Làm rõ LO trước khi mapping

Giữ nguyên văn LO chính thức và tạo các **tiêu chí nội bộ** để vận hành, cho giảng viên xác nhận. Không tự sửa nội dung chuẩn đầu ra của đề cương.

Ví dụ do báo cáo đề xuất:

| LO chính thức | Tiêu chí nội bộ | Nhiệm vụ có thể dùng để kiểm tra |
|---|---|---|
| Trình bày và phân tích các phương pháp xử lý dữ liệu | Trình bày đặc điểm của từng phương pháp | Diễn giải đặc điểm theo yêu cầu chấm đã thống nhất |
| Cùng LO trên | Phân tích sự phù hợp trong tình huống cụ thể | So sánh yêu cầu và phương án xử lý, chỉ ra quan hệ có căn cứ |

Mỗi tiêu chí nên có mô tả hành vi, loại kiến thức, mức Bloom đề xuất, bằng chứng cần có và rubric. Một nhãn Bloom mục tiêu trên giao diện có thể tiếp tục được giữ, nhưng cần ghi rõ đó là quyết định cấu hình đã xác nhận; các tiêu chí cung cấp phần chi tiết.

### 5.3. Mapping nội dung với từng tiêu chí

Đề xuất thử nghiệm theo trình tự:

1. Dùng quan hệ chương–LO để tìm ứng viên ban đầu; giữ đường tìm kiếm theo nội dung cho tài liệu tham khảo.
2. Tìm thêm chunk bằng mô tả tiêu chí và nội dung thân chunk. Chọn số ứng viên theo ngân sách và đo recall, không đặt một ngưỡng cosine chung cho mọi model.
3. So sánh reranker và LLM kiểm tra từng cặp trên cùng bộ nhãn.
4. Phân biệt: hỗ trợ trực tiếp, kiến thức nền, không hỗ trợ và chưa đủ thông tin. Cho phép một LO cần nhiều chunk kết hợp.
5. Lưu đoạn bằng chứng, nguồn, phiên bản LO, phương pháp và trạng thái xác nhận.

Các bước này là thiết kế thử nghiệm của báo cáo. Chương vẫn là tín hiệu hữu ích; việc mọi LO cùng chương nhận cùng chunk cần được kiểm chứng ở cấp nội dung.

### 5.4. Kiểm chứng câu sau khi sinh

Thêm một bước riêng bên cạnh verifier đáp án hiện có. Đầu vào gồm câu hỏi, các phương án hoặc rubric, dữ kiện mà sinh viên thấy, LO/tiêu chí và bối cảnh đã học. Bước này nên trả:

- Mức bám LO: tiêu chí nào được đo, tiêu chí nào còn thiếu.
- Bloom được đề xuất, kèm lý do ngắn dựa vào thao tác cần để trả lời.
- Bằng chứng và những dữ kiện còn thiếu.
- Trạng thái: có thể kết luận, cần giảng viên xem lại hoặc chưa đủ thông tin.

Trong thí nghiệm, có thể ẩn Bloom yêu cầu khỏi bộ phân loại để kiểm tra nguy cơ nó chỉ lặp lại nhãn cấu hình. Đây là lựa chọn kiểm soát cần đo, không được xem là đã loại bỏ thiên lệch của model.

Lưu tách các giá trị sau theo **phiên bản câu**:

| Giá trị | Ý nghĩa |
|---|---|
| `bloom_requested` | Mục tiêu lúc yêu cầu sinh |
| `bloom_assessed` | Kết quả AI đề xuất sau khi xem nhiệm vụ |
| `bloom_confirmed` | Kết quả giảng viên xác nhận |
| `lo_alignment` | Tiêu chí được đo và bằng chứng tương ứng |
| `evaluation_status` | Đã kiểm tra, cần xem lại hoặc chưa kết luận được |

Nếu yêu cầu Vận dụng nhưng câu được xác nhận chỉ ở mức Nhớ, không tính câu đó là đã đáp ứng ô Vận dụng trong ma trận. Có thể sửa câu, sinh thay thế, hoặc giữ làm bài luyện tập mức Nhớ sau khi giảng viên quyết định. Khi câu được sửa, kết quả kiểm tra bản cũ không tiếp tục đại diện cho bản mới.

### 5.5. Công cụ và chuẩn có thể tham khảo

Những nguồn dưới đây là **tài liệu kỹ thuật**, không nằm trong số 10 bài nghiên cứu:

- [Sentence Transformers — Retrieve & Re-Rank](https://sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html): quy trình tìm ứng viên rồi rerank, phù hợp để xây đối chứng kỹ thuật.
- [CaSS — Resource Alignment](https://docs.cassproject.org/v1.6/authoring/competency-properties/): biểu diễn quan hệ `teaches`, `assesses`, `requires`, `desires`; có thể tham khảo để tránh gom mọi quan hệ vào một cạnh “liên quan”.
- [Canvas Outcomes API](https://developerdocs.instructure.com/services/canvas/resources/outcomes): quản lý outcome, rubric, ngưỡng mastery và các alignment; phù hợp nhu cầu tích hợp Canvas của dự án.
- [1EdTech CASE](https://www.1edtech.org/standards/case/about): chuẩn trao đổi framework, outcome, quan hệ và rubric giữa các hệ thống.

Các công cụ/chuẩn này cung cấp hạ tầng quản lý và trao đổi. Muốn tự động đánh giá Bloom trong DA Platform vẫn cần bộ phân loại và quy trình kiểm chứng.

## 6. Kế hoạch đánh giá trước khi chọn model

### 6.1. Tạo ba tập nhãn riêng

Đề xuất bộ thăm dò ban đầu từ ít nhất hai môn: 30–50 LO, 200–300 cặp tiêu chí–chunk và 120–150 câu hỏi. Đây là quy mô khởi đầu để phát hiện lỗi và ước lượng công sức; chưa phải cỡ mẫu chứng minh hiệu quả cho mọi môn và sáu mức Bloom.

| Tập | Dữ liệu người chấm cần thấy | Nhãn tham chiếu |
|---|---|---|
| LO → Bloom | LO nguyên văn, bối cảnh môn và tiêu chí | Một/nhiều mức, hoặc chưa đủ rõ |
| Chunk → LO | Tiêu chí, chunk, nguồn và các đoạn liên quan | Loại hỗ trợ và đoạn bằng chứng |
| Câu → LO/Bloom | Câu, phương án/rubric, nguồn, bối cảnh đã học | LO được đo, Bloom và lỗi cụ thể |

Hai người có chuyên môn gán nhãn độc lập trước khi thảo luận bất đồng. Có lựa chọn “chưa đủ thông tin”; không ép mọi trường hợp vào một mức. Ghi độ đồng thuận trước khi thống nhất nhãn.

Đặc biệt đưa vào tập thử các cặp dễ gây nhầm: hai LO cùng chương, chunk chỉ chứa định nghĩa trong khi LO yêu cầu vận dụng, tài liệu tham khảo khác số chương, câu gần trùng và LO ghép nhiều hành vi.

### 6.2. So sánh các cấu hình trên cùng dữ liệu

| Nhiệm vụ | Các cấu hình cần so sánh |
|---|---|
| Phân loại LO | Luật hiện tại; LLM zero-shot; LLM có rubric và ví dụ; classifier huấn luyện riêng nếu có đủ nhãn |
| Mapping nội dung | Mapper hiện tại; keyword; embedding; embedding + reranker; ứng viên + LLM kiểm chứng |
| Phân loại câu | Nhãn yêu cầu hiện tại; LLM độc lập; LLM có ví dụ theo môn; đối chứng huấn luyện riêng nếu khả thi |

Tách dữ liệu dùng chỉnh prompt/ngưỡng khỏi dữ liệu kiểm tra cuối. Giữ các bản diễn đạt lại của cùng LO/câu và các phiên bản gần trùng trong cùng nhóm, tránh để chúng xuất hiện ở cả hai tập. Bổ sung một lượt kiểm tra trên môn chưa dùng để hiệu chỉnh.

### 6.3. Chỉ số cần báo cáo

- **Bloom:** macro-F1 và kết quả từng mức; với câu một nhãn thêm ma trận nhầm lẫn, với LO nhiều nhãn báo precision/recall từng nhãn.
- **Mapping:** precision và recall của cạnh hỗ trợ trực tiếp; recall@k của bước tìm ứng viên; số LO thiếu bằng chứng.
- **Người chấm:** tỷ lệ đồng thuận, kappa hoặc alpha phù hợp cách gán nhãn; giữ các nhóm bất đồng để phân tích.
- **Vận hành:** tỷ lệ chưa kết luận được, chi phí, độ trễ và thời gian giảng viên xử lý.
- **Đầu ra sinh câu:** số câu được người chấm xác nhận đúng LO và đúng Bloom trên tổng số câu yêu cầu; đồng thời báo số câu bị loại và số câu thiếu.

Không đổi tên weighted F1 thành accuracy, không so trực tiếp các điểm từ bài báo khác tập dữ liệu. Việc loại nhiều câu có thể làm tỷ lệ đạt của số câu còn lại tăng; cần báo cả số câu thực đáp ứng yêu cầu để đánh giá đúng hiệu quả.

## 7. Thứ tự triển khai đề xuất

| Ưu tiên | Công việc | Kết quả có thể kiểm tra |
|---|---|---|
| 1 | Thống nhất rubric và tạo tập nhãn; lưu hồ sơ đánh giá theo phiên bản | Có đối chứng độc lập cho các thử nghiệm |
| 2 | Thêm phân loại Bloom/LO của câu và giảng viên xác nhận | Tách được mức yêu cầu với mức câu thực đo |
| 3 | Làm rõ tiêu chí của LO ghép; bổ sung mapping theo thân chunk | Phân biệt được các LO cùng chương |
| 4 | Hiệu chỉnh tìm ứng viên, reranker và giới hạn gọi LLM | Chất lượng và chi phí được đo trên cùng tập |
| 5 | Đánh giá chuyển môn; cân nhắc classifier huấn luyện riêng | Biết phạm vi sử dụng và nhóm cần người xem lại |

Thứ tự ưu tiên là nhận định của báo cáo dựa trên code đã đọc. Chưa đề xuất thay toàn bộ pipeline: hạ tầng provenance, quan hệ chương–LO, source chunk và ma trận đề hiện có đủ để làm điểm bắt đầu.

Hai tài liệu trong repo có thể dùng để nối việc triển khai: [Thiết kế lại sinh quiz](quiz-generation-redesign.md) và [Báo cáo kiểm soát chất lượng câu hỏi AI](bao-cao-kiem-soat-chat-luong-ai.md). Các mô tả hiện trạng trong tài liệu cũ cần được đối chiếu với code ngày 14/10/2026 ở mục 3.

## 8. Danh mục bài báo và thứ tự đọc

Nếu chỉ có thời gian đọc ba bài, nên bắt đầu với **P4** để hiểu LO phức hợp, **P5** để hiểu khả năng chuyển dữ liệu của bộ phân loại câu, rồi **P6** để hiểu cách đánh giá câu do AI sinh. P3 là đối chứng hữu ích khi cân nhắc fine-tune; P7 liên quan mapper nội dung.

| Mã | Tài liệu gốc | Nơi công bố / trạng thái | Mức tiếp cận trong báo cáo |
|---|---|---|---|
| P1 | Biggs, J. (1996). [Enhancing teaching through constructive alignment](https://link.springer.com/article/10.1007/BF00138871). DOI: 10.1007/BF00138871. | Higher Education, 32, 347–364 | Tóm tắt nhà xuất bản và bản bài được lập chỉ mục |
| P2 | Krathwohl, D. R. (2002). [A Revision of Bloom’s Taxonomy: An Overview](https://doi.org/10.1207/s15430421tip4104_2). | Theory Into Practice, 41(4), 212–218 | [Toàn văn bản lưu tại METU](https://ocw.metu.edu.tr/pluginfile.php/9009/mod_resource/content/1/s15430421tip4104_2.pdf) |
| P3 | Almatrafi, O., & Johri, A. (2025). [Leveraging generative AI for course learning outcome categorization using Bloom’s taxonomy](https://www.sciencedirect.com/science/article/pii/S2666920X2500044X). DOI: 10.1016/j.caeai.2025.100404. | Computers and Education: Artificial Intelligence, 8, 100404 | Toàn văn bản bài lưu tại FGV; bảng 4–6 |
| P4 | Kolagar, Z., Zalkow, F., & Zarcone, A. (2025). [Investigating Methods for Mapping Learning Objectives to Bloom’s Revised Taxonomy in Course Descriptions for Higher Education](https://aclanthology.org/2025.bea-1.32/). DOI: 10.18653/v1/2025.bea-1.32. | BEA 2025, 415–445 | Toàn văn PDF; phương pháp, kết quả và giới hạn |
| P5 | Faraji, A., Molavi, M., Rasoulkhani, Z., Tavakoli, M., & Kismihók, G. (2026). [Cross-Dataset Bloom Question Classification: Supervised Models and Prompted LLMs](https://arxiv.org/abs/2606.13684). | arXiv:2606.13684; bài ghi “Accepted at AIED 2026” | Toàn văn HTML v1; bảng 2–3 |
| P6 | Scaria, N., Chenna, S. D., & Subramani, D. (2024). [Automated Educational Question Generation at Different Bloom’s Skill Levels using Large Language Models: Strategies and Evaluation](https://arxiv.org/abs/2408.04394). DOI bản xuất bản: 10.1007/978-3-031-64299-9_12. | AIED 2024, 165–179; bản đọc là preprint | Toàn văn HTML v1 và repository của tác giả |
| P7 | Gancevska, B., & Ramanauskaitė, S. (2026). [Mapping Moodle Resources to Course Topics Using Text Similarity Methods and Expert Evaluation](https://www.mdpi.com/2076-3417/16/4/2039). DOI: 10.3390/app16042039. | Applied Sciences, 16(4), 2039 | Tóm tắt và phần phương pháp được lập chỉ mục |
| P8 | Gültekin, A., Diri, S., & Özcan, M. (2026). [An LLM-assisted decision-support system for semantic analysis of Bloom’s Taxonomy-aligned learning outcomes](https://www.sciencedirect.com/science/article/pii/S030645732600302X). DOI: 10.1016/j.ipm.2026.104911. | Information Processing & Management | Tóm tắt tại cơ sở tác giả và trích đoạn nhà xuất bản |
| P9 | Reimers, N., & Gurevych, I. (2019). [Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks](https://aclanthology.org/D19-1410/). DOI: 10.18653/v1/D19-1410. | EMNLP-IJCNLP 2019, 3982–3992 | Tóm tắt chính thức tại ACL Anthology |
| P10 | Nogueira, R., & Cho, K. (2019). [Passage Re-ranking with BERT](https://arxiv.org/abs/1901.04085). | arXiv:1901.04085; v5 cập nhật 2020 | Tóm tắt bản v5 |

**Tài nguyên để bắt đầu thử nghiệm:** repository P6 có thư mục prompt và các bảng đánh giá chuyên gia; bài P5 công bố liên kết mã/prompt/dataset nhưng nội dung chi tiết của repository chưa được kiểm tra trong đợt này. Chưa chạy lại thí nghiệm của hai repository.

**Đọc báo cáo theo mục đích:** mục 2 để hiểu khái niệm; mục 3 để xem hệ thống đang thiếu gì; mục 4 để đọc nghiên cứu; mục 5–7 để chuẩn bị thiết kế và đánh giá.
