# Báo cáo: Kiểm soát chất lượng câu hỏi do AI sinh

**Đề tài:** Hệ thống LMS tự động tạo Micro-Content & Quiz bằng Generative AI (DA Platform)  
**Cập nhật:** 08/10/2026  
**Mục đích:** đề xuất quy trình kiểm soát câu hỏi và cách kiểm chứng hiệu quả trước khi dùng để đánh giá sinh viên.

Hệ thống đã sinh được câu hỏi từ tài liệu môn học, kiểm tra đáp án bằng AI và hỗ trợ giảng viên duyệt. Tuy nhiên, các câu đã rà soát cho thấy **đáp án có trong tài liệu chưa đủ để câu hỏi đạt chất lượng**: câu vẫn có thể lệch mục tiêu học tập, gắn sai mức Bloom, có phương án nhiễu quá dễ loại hoặc trùng với câu đã có.

Đề xuất của báo cáo là kiểm tra câu hỏi theo các tiêu chí riêng, lưu bằng chứng để giảng viên duyệt và đo hiệu quả trên bộ câu hỏi được người có chuyên môn gán nhãn. Trọng tâm là trắc nghiệm một đáp án và mức Bloom; chấm bài tự luận là một bài toán đánh giá riêng, trình bày ở Phụ lục A. Các cơ chế bổ sung dưới đây là **đề xuất cần kiểm chứng**; hiện trạng mã nguồn được đối chiếu ở mục 5.

## 1. Những vấn đề đã quan sát

Bốn trường hợp dưới đây được giữ từ đợt rà soát câu hỏi môn Dữ liệu lớn trong bản báo cáo ban đầu. Theo ghi nhận của đợt rà soát, trường hợp 1 và 3 có câu đã được giảng viên duyệt. Đây là các trường hợp minh họa lỗi, chưa phải mẫu thống kê để ước lượng tỷ lệ lỗi của toàn hệ thống. Khi lập bộ đánh giá, cần bổ sung ID câu hỏi, phiên bản và bản chụp tài liệu nguồn để tái kiểm tra.

### 1.1. Đáp án đúng nhưng câu hỏi không đo được mức Vận dụng

> **Câu hỏi:** Dựa trên đoạn trích về Earthscope, dữ liệu thu thập được có kích thước là bao nhiêu?  
> A. 67 terabyte — đáp án được đánh dấu  
> B. 2.5 tỷ điện thoại thông minh  
> C. 100 tỷ cảm biến  
> D. 3.8 triệu dặm vuông  
> **Bloom lưu trong hệ thống:** 3 — Vận dụng.
>
> **Nguồn, slide trang 5:** “The Earthscope is the world's largest science project… this observatory records data over 3.8 million square miles, amassing 67 terabytes of data.”

Đoạn nguồn xác nhận con số 67 terabyte. Tuy nhiên, thao tác cần để trả lời chỉ là nhớ hoặc nhận ra một dữ kiện; câu chưa yêu cầu áp dụng cách làm nào. Ba phương án còn lại khác loại đơn vị, nên người học còn có thể loại chúng mà không biết kiến thức về Earthscope. Cụm “dựa trên đoạn trích” cũng thiếu điểm tham chiếu nếu đề không hiển thị đoạn trích đó.

**Vấn đề cần giải quyết:** kiểm tra căn cứ, mức Bloom và chất lượng phương án nhiễu phải cho ra các kết quả riêng.

### 1.2. Câu dẫn chưa đủ rõ để loại phương án khác

> **LO L.O.1.1:** Hiểu biết và giải thích được các vấn đề về dữ liệu lớn: kích thước, tốc độ sinh, sự đa dạng và tính chính xác.
>
> **Câu hỏi:** Theo các đoạn trích, dữ liệu lớn thường được mô tả bằng những đặc điểm nào?  
> A. Quy mô, sự đa dạng và độ phức tạp — đáp án được đánh dấu  
> B. Kích thước, tốc độ sinh, sự đa dạng và tính chính xác  
> C. Khối lượng, độ phức tạp, tính linh hoạt và khả năng mở rộng  
> D. Số lượng, chất lượng, tần suất và nguồn gốc
>
> **Nguồn, slide trang 2:** “Data whose scale, diversity and complexity require… analytics to manage it…”

A bám đoạn slide được trích; B lại trùng các đặc điểm nêu trong LO. Câu dẫn không chỉ rõ đang hỏi theo định nghĩa hay mô hình nào. Đây là **dấu hiệu mơ hồ cần giảng viên xác nhận**, chưa đủ để kết luận A và B luôn cùng đúng trong mọi ngữ cảnh. Lời giải “Đoạn trích [2] và [3] nêu rõ…” cũng không giúp người học kiểm tra nếu các đoạn này không có trong đề.

**Vấn đề cần giải quyết:** xác định tính đúng của từng phương án trong ngữ cảnh người học được cung cấp, đồng thời phát hiện cách diễn đạt phụ thuộc tài liệu chỉ AI nhìn thấy.

### 1.3. Cùng nội dung nhưng lặp lại với nhãn Bloom khác nhau

Câu “Kiến trúc Lambda được phân loại rộng rãi thành ba lớp nào?” được ghi nhận xuất hiện ba lần: hai lần nguyên văn ở hai LO và một lần diễn đạt lại, mang nhãn Bloom 1, 1 và 2. Nguồn trang 6 liệt kê Batch Layer, Speed Layer và Serving Layer.

Các câu cần được đối chiếu để xác định mức trùng và ngữ cảnh sử dụng. Với cùng yêu cầu liệt kê ba lớp, việc đổi LO hoặc đổi yêu cầu lúc sinh chưa tạo ra bằng chứng rằng thao tác nhận thức đã thay đổi.

**Vấn đề cần giải quyết:** kiểm tra trùng trong ngân hàng câu và đánh giá Bloom từ yêu cầu thực tế của câu hỏi.

### 1.4. Động từ trong đề chưa chứng minh được mức Bloom

Câu tự luận “Giải thích ngắn gọn khái niệm dữ liệu lớn dựa trên định nghĩa trong tài liệu” được gắn mức 2 — Hiểu. Rubric gồm ba ý lấy từ định nghĩa: giới hạn của công nghệ CSDL tiêu chuẩn; quy mô, đa dạng và phức tạp; mục đích trích xuất giá trị.

Nếu nhắc lại các ý này đã đủ điểm tối đa, rubric chưa chứng minh rằng câu đo được mức Hiểu. Cần xem cách chấp nhận câu trả lời: người học có phải diễn giải ý nghĩa, phân loại ví dụ hay giải thích quan hệ không. Chỉ từ chữ “giải thích” không thể kết luận mức Bloom; cũng chưa nên tự động đổi nhãn về mức 1 khi chưa xem yêu cầu chấm đầy đủ.

**Vấn đề cần giải quyết:** đánh giá đồng thời câu hỏi, đáp án hoặc rubric và nội dung người học đã được học.

## 2. Tiêu chí để một câu hỏi được sử dụng

### 2.1. Đánh giá chất lượng theo từng tiêu chí

Báo cáo đề xuất năm tiêu chí sau. Một câu cần được xem xét trên tất cả các tiêu chí áp dụng cho loại câu đó.

| Tiêu chí | Điều cần xác nhận | Bằng chứng cần lưu |
|---|---|---|
| Có căn cứ và đúng kiến thức | Nguồn hỗ trợ đáp án, lời giải và các giả định cần thiết | Đoạn trích, trang nguồn, kết quả đối chiếu nội dung |
| Có thể chấm rõ ràng | Trắc nghiệm một đáp án có đúng một phương án hợp lý; tự luận có rubric nhất quán | Nhận xét từng phương án hoặc từng tiêu chí rubric |
| Đúng mục tiêu và mức nhận thức | Câu đo được LO và yêu cầu người học thực hiện thao tác phù hợp với mức Bloom đặt ra | LO, Bloom yêu cầu, Bloom được đánh giá, lý do |
| Diễn đạt phù hợp | Đủ dữ kiện; phương án nhiễu hợp lý; không có dấu hiệu làm lộ đáp án | Lỗi cụ thể và vị trí xuất hiện |
| Phù hợp với bộ đề | Không lặp ý ngoài chủ đích; đáp ứng phân bổ nội dung và Bloom | Câu tương tự, vị trí trong ma trận đề |

Kết quả kiểm tra cần phân biệt **đạt**, **có vấn đề** và **chưa đủ thông tin**. Lỗi dịch vụ AI hoặc thiếu ngữ cảnh thuộc nhóm cuối. Những dấu hiệu như đáp án dài hơn, có từ “luôn luôn” hay độ tương đồng cao chỉ nên tạo cảnh báo; chúng cần được xét trong ngữ cảnh trước khi loại câu.

### 2.2. Xác định mức Bloom bằng thao tác người học phải thực hiện

Thang Bloom sửa đổi mô tả sáu quá trình nhận thức và bốn loại kiến thức. Khi gán mức cho câu hỏi, cần xét thao tác cần thiết để đạt đáp án hoặc rubric, cùng ngữ cảnh đã học. Bảng dưới là rubric làm việc đề xuất cho người chấm và AI; cần được thống nhất trên các ví dụ của môn học. Cơ sở phân loại: [Krathwohl (2002)](https://doi.org/10.1207/s15430421tip4104_2).

| Mức | Dấu hiệu cần tìm trong yêu cầu trả lời |
|---|---|
| 1. Nhớ | Nhận ra hoặc nhắc lại kiến thức đã học |
| 2. Hiểu | Diễn giải ý nghĩa, phân loại, tóm tắt, suy ra hoặc giải thích quan hệ |
| 3. Vận dụng | Thực hiện hoặc sử dụng một quy trình trong tình huống cụ thể |
| 4. Phân tích | Tách các thành phần và xác định quan hệ, vai trò hoặc cấu trúc |
| 5. Đánh giá | Đưa ra nhận định theo tiêu chí hoặc chuẩn đã xác định |
| 6. Sáng tạo | Tạo phương án, kế hoạch hoặc sản phẩm đáp ứng yêu cầu |

Ví dụ Earthscope ở mục 1.1 chưa có thao tác của mức Vận dụng. Muốn xây một câu ở mức này, người soạn phải bổ sung nhiệm vụ và dữ kiện phù hợp với quy trình đã học, thay vì chỉ đổi động từ trong câu dẫn. Việc bổ sung tình huống cũng phải được kiểm tra về căn cứ và tính đủ dữ kiện.

Loại kiến thức trong slide là tín hiệu để chọn nguồn. Một đoạn ngắn có thể cần ghép với đoạn khác; thiếu quy trình trong một chunk chưa đủ để kết luận cả chương không thể sinh câu Vận dụng. Tương tự, chọn một thiết kế có sẵn chưa chứng minh được năng lực tự tạo thiết kế ở mức Sáng tạo. Các nhận định này cần xét trên toàn nhiệm vụ và rubric.

**Đề xuất lưu riêng ba giá trị:** mức Bloom được yêu cầu khi sinh; mức AI đề xuất sau kiểm tra; mức giảng viên xác nhận. Nếu chúng khác nhau, câu được sửa hoặc chuyển duyệt cùng lý do. Hệ thống không tự ghi đè nhãn yêu cầu bằng phán đoán của AI, cũng không tính một câu đã đổi xuống mức Nhớ là đã đáp ứng yêu cầu sinh câu Vận dụng.

## 3. Quy trình kiểm soát đề xuất

### 3.1. Trước khi sinh: xác định câu cần đo gì

Mỗi yêu cầu sinh cần nêu LO, mức Bloom, loại câu, số lượng và nguồn kiến thức. Hệ thống chọn các đoạn liên quan và kiểm tra xem có đủ dữ kiện để tạo nhiệm vụ mong muốn không. Thiếu nội dung thì tìm bổ sung hoặc báo chưa đáp ứng được yêu cầu.

Prompt cần có mô tả thao tác nhận thức, ví dụ phù hợp với môn học và lỗi cần tránh. Với Earthscope, lỗi cần tránh là lấy một câu nhắc lại số liệu rồi gắn nhãn Vận dụng. Cách hướng dẫn này là giả thuyết thiết kế cần đo: [Scaria et al. (2024)](https://arxiv.org/abs/2408.04394) cho thấy chất lượng sinh câu phụ thuộc thông tin trong prompt và model, đồng thời đánh giá tự động chưa ngang đánh giá chuyên gia.

### 3.2. Sau khi sinh: kiểm tra kỹ thuật rồi kiểm tra nội dung

**Kiểm tra bằng code.** Thực hiện các phép kiểm có thể xác định rõ: cấu trúc câu và đáp án, ID nguồn hợp lệ, trích dẫn có xuất hiện trong nguồn sau chuẩn hóa, câu trùng nguyên văn. Các luật về tham chiếu thiếu ngữ cảnh, độ dài phương án hoặc từ tuyệt đối tạo cờ để xem lại. Kiểm tra tương đồng nghĩa giúp tìm câu có khả năng trùng; cần hiệu chỉnh ngưỡng và xem cả đáp án, tình huống để tránh loại nhầm.

Mỗi câu nên kèm đoạn trích hỗ trợ đáp án. So chuỗi chỉ xác nhận **đoạn trích tồn tại**; giám khảo hoặc giảng viên còn phải xác nhận đoạn đó có đủ sức chứng minh đáp án. Với câu suy luận hoặc vận dụng, bằng chứng có thể gồm nhiều đoạn và cách áp dụng kiến thức. Đây là lựa chọn triển khai của nhóm, dựa trên nhu cầu kiểm tra chất lượng trích dẫn được nghiên cứu trong [ALCE — Gao et al. (2023)](https://arxiv.org/abs/2305.14627).

**Kiểm tra bằng giám khảo AI.** Với trắc nghiệm một đáp án, đề xuất thực hiện theo hai bước:

1. **Giải trước khi xem đáp án.** Giám khảo nhận câu hỏi, các phương án và dữ kiện mà người học được cung cấp. Giám khảo chọn phương án hoặc báo nhiều phương án hợp lý, không có phương án đúng hay thiếu dữ kiện. Nếu cần tài liệu để đối chiếu, tài liệu nguồn được phân biệt rõ với dữ kiện có trong đề; giám khảo phải chỉ ra câu có phụ thuộc vào thông tin bị thiếu khỏi đề hay không.
2. **Đối chiếu và đánh giá.** Sau khi đã lưu kết quả giải, giám khảo được xem đáp án dự kiến, lời giải, nguồn và LO. Kết quả gồm căn cứ hỗ trợ đáp án, nhận xét từng phương án, mức bám LO và Bloom đề xuất kèm lý do. Khi phân loại Bloom, chưa cho xem nhãn Bloom yêu cầu để hạn chế việc đánh giá theo nhãn có sẵn.

Giải lại với thứ tự phương án khác có thể dùng cho các câu bị nghi ngờ hoặc trong thí nghiệm. So sánh theo nội dung hoặc ID phương án gốc, không theo chữ A/B/C/D sau khi xáo. Kết quả thay đổi là dấu hiệu giám khảo chưa ổn định; cần xem lại trước khi kết luận câu mơ hồ. Nghiên cứu về [độ nhạy với thứ tự phương án](https://aclanthology.org/2024.findings-naacl.130/) là cơ sở để thử phép kiểm này.

Đề xuất cấu hình model kiểm tra khác model sinh nhằm giảm nguy cơ tự ưu ái. Tuy vậy, hai model vẫn có thể cùng mắc lỗi; việc tách model chưa chứng minh giám khảo đủ chính xác. Nghiên cứu của [Panickssery et al. (2024)](https://arxiv.org/abs/2404.13076) ghi nhận thiên lệch khi LLM đánh giá chính đầu ra của mình.

### 3.3. Xử lý kết quả: sửa, chuyển duyệt hoặc loại

| Kết quả | Cách xử lý đề xuất |
|---|---|
| Sai cấu trúc hoặc trích dẫn không khớp nguồn | Trả lý do cụ thể để sửa; kiểm tra lại bản sửa |
| Giám khảo phát hiện đáp án có vấn đề hoặc thiếu căn cứ | Giữ lại bằng chứng; yêu cầu sửa hoặc chuyển giảng viên xác minh; chưa đưa vào đề |
| Lệch Bloom hoặc chưa bám LO | Sửa nhiệm vụ; nếu giữ ở mức khác thì cần giảng viên xác nhận và phân bổ lại đề |
| Có dấu hiệu lỗi viết hoặc gần trùng | Hiện vị trí nghi ngờ và câu đối chiếu để giảng viên quyết định |
| Giám khảo lỗi hoặc chưa kết luận được | Lưu trạng thái “chưa kiểm tra xong”; thử lại trong giới hạn hoặc chuyển duyệt có cảnh báo |
| Hoàn tất kiểm tra, không phát hiện vấn đề | Đưa vào hàng đợi giảng viên duyệt với hồ sơ kiểm tra |

Mỗi câu sửa tối đa 1–2 lần theo chính sách thử nghiệm. Bản sửa phải chạy lại các kiểm tra liên quan vì thay câu dẫn hoặc phương án có thể tạo lỗi mới. Nếu vẫn không đạt, loại ứng viên và sinh thay thế trong ngân sách cho phép; hết ngân sách thì báo rõ số câu còn thiếu. Phản hồi phải nêu lỗi đã phát hiện, không chỉ yêu cầu AI tự xem lại. [Huang et al. (2024)](https://arxiv.org/abs/2310.01798) cho thấy tự sửa suy luận khi thiếu phản hồi bên ngoài có thể không cải thiện kết quả.

### 3.4. Giảng viên duyệt bằng chứng và quyết định sử dụng

Theo quy trình đề xuất, mọi câu dùng tính điểm đều cần giảng viên duyệt. Hồ sơ đi kèm mỗi phiên bản câu gồm nguồn, kết quả kiểm tra, lý do gắn cờ, các nhãn Bloom và lịch sử sửa. Các câu cần xử lý được ưu tiên theo loại và mức ảnh hưởng của vấn đề.

Với câu Earthscope, hồ sơ kỳ vọng có thể trình bày như sau. Đây là minh họa giao diện, chưa phải kết quả của một lần chạy giám khảo mới:

| Nội dung | Thông tin giảng viên thấy |
|---|---|
| Mục tiêu | Yêu cầu mức 3 — Vận dụng |
| Đánh giá Bloom | Đề xuất mức 1 — câu chỉ yêu cầu nhận ra số liệu |
| Căn cứ | “amassing 67 terabytes of data”, slide trang 5; liên kết mở trang |
| Cách viết | “Dựa trên đoạn trích” nhưng cần kiểm tra đề có hiển thị đoạn đó không |
| Phương án nhiễu | Ba phương án còn lại không biểu diễn kích thước dữ liệu |
| Quyết định cần đưa ra | Viết lại để đo Vận dụng, hoặc xác nhận giữ ở mức Nhớ và sửa các lỗi khác |

Giảng viên có thể duyệt, sửa hoặc từ chối kèm lý do. Kết quả kiểm tra phải gắn với phiên bản câu đã được kiểm tra; khi nội dung thay đổi, không tiếp tục hiển thị kết quả cũ như bằng chứng cho bản mới.

### 3.5. Sau khi sử dụng: đối chiếu với dữ liệu làm bài

Đề xuất bổ sung độ phân biệt của câu và tỷ lệ chọn từng phương án, bên cạnh tỷ lệ trả lời đúng hiện có. Khi tính độ phân biệt, có thể dùng tương quan giữa điểm câu và tổng điểm các câu còn lại. Dữ liệu phải được nhóm theo phiên bản câu và cách sử dụng; không gộp tùy ý các lượt luyện tập lặp lại với bài kiểm tra chính thức.

Các chỉ số này dùng để đưa câu trở lại hàng đợi xem xét. Câu có tỷ lệ đúng cao có thể phù hợp với mục tiêu kiểm tra kiến thức nền; tỷ lệ đúng thấp có thể do nhiều nguyên nhân. Phương án nhiễu được dưới 5% người làm chọn là một ngưỡng tham khảo từ [Tarrant et al. (2009)](https://doi.org/10.1186/1472-6920-9-40), cần đi kèm cỡ mẫu và ngữ cảnh bài thi trước khi kết luận.

## 4. Kế hoạch kiểm chứng

Cần trả lời riêng hai câu hỏi: **bộ kiểm tra có nhận xét đúng không**, và **toàn quy trình có tạo ra bộ câu tốt hơn với chi phí chấp nhận được không**. Dùng chính giám khảo AI để tuyên bố câu đã tốt hơn sẽ không cung cấp được đối chứng độc lập.

### 4.1. Kiểm chứng bộ kiểm tra và bộ phân loại Bloom

Đề xuất xây bộ ban đầu khoảng 120–150 câu từ ít nhất hai môn. Bộ này cần có cả câu tốt, câu có lỗi và trường hợp khó phân loại; bốn trường hợp ở mục 1 là ứng viên để đưa vào sau khi bổ sung nguồn truy xuất. Giai đoạn đầu tập trung mức 1–4. Nếu cần kết luận cho mức 5–6, phải bổ sung mẫu và loại nhiệm vụ phù hợp.

Hai giảng viên hoặc trợ giảng chấm độc lập theo cùng rubric. Người chấm được xem câu hỏi, phương án hoặc rubric, nguồn và ngữ cảnh môn học; chưa xem cấu hình sinh, nhận xét của AI hoặc nhãn Bloom yêu cầu. Để xét đáp án trắc nghiệm, người chấm tự giải trước, rồi mới đối chiếu đáp án dự kiến. Với Bloom, người chấm ghi mức đề xuất và lý do; được phép đánh dấu thiếu ngữ cảnh hoặc còn tranh luận.

Đo mức đồng thuận trước khi hai người thảo luận các bất đồng. Sau đó tạo nhãn tham chiếu đã thống nhất; giữ lại những trường hợp chưa thể thống nhất để phân tích riêng. Tách tập dùng chỉnh prompt/ngưỡng khỏi tập đánh giá cuối, đồng thời tránh để các bản diễn đạt lại của cùng câu xuất hiện ở cả hai tập.

| Cần biết | Chỉ số và cách đọc |
|---|---|
| Người chấm có hiểu rubric thống nhất không? | Tỷ lệ đồng thuận và Cohen's kappa giữa hai người trước thảo luận |
| AI có phát hiện lỗi đúng không? | Precision và recall theo từng loại lỗi: gắn cờ đúng bao nhiêu, bỏ sót bao nhiêu |
| AI có phân loại Bloom phù hợp không? | Macro-F1, kết quả từng mức và ma trận nhầm lẫn so với nhãn tham chiếu |
| Bộ kiểm tra có thường xuyên không kết luận được không? | Tỷ lệ thiếu ngữ cảnh, lỗi dịch vụ và đầu ra không hợp lệ |

Báo cáo kèm số mẫu và các trường hợp bất đồng, tránh chỉ đưa một điểm tổng. Các trường hợp AI không kết luận được phải được ghi nhận riêng, không bị âm thầm bỏ khỏi báo cáo.

Có thể dùng [bộ dữ liệu và mã đánh giá Cross-Dataset Bloom Classification](https://gitlab.com/zrasoulkhani/bloom-classification-aied2026) để thử trước khả năng phân loại. Nghiên cứu liên quan đánh giá trên nhiều bộ câu hỏi và cho thấy khả năng tổng quát hóa cần được kiểm tra. Tuy nhiên, kết quả trên dữ liệu công khai chưa đủ để kết luận cho câu hỏi tiếng Việt của các môn trong hệ thống. [Faraji et al. (2026)](https://arxiv.org/html/2606.13684v1).

### 4.2. Kiểm chứng hiệu quả của toàn quy trình

Sau khi có rubric và bộ kiểm tra được đánh giá, thực hiện thí nghiệm tăng dần thành phần:

| Cấu hình | Thành phần được sử dụng | So sánh cần thực hiện |
|---|---|---|
| A | Pipeline hiện tại, cố định phiên bản code, prompt và model | Mốc đối chiếu |
| B | A + trích dẫn được kiểm tra + các luật viết câu và tìm trùng | B so với A: nhóm kiểm tra này cải thiện gì? |
| C | B + giải trước khi xem đáp án + đánh giá nội dung theo tiêu chí | C so với B: giám khảo bổ sung giá trị gì? |
| D | C + chọn nguồn, hướng dẫn sinh và kiểm tra Bloom theo rubric | D so với C: gói kiểm soát Bloom cải thiện gì? |

Ở C chưa bật kiểm tra Bloom; D bổ sung cả ba thành phần liên quan đến Bloom. Thí nghiệm này đánh giá tác dụng của **cả gói**, chưa tách được đóng góp riêng của chọn nguồn, prompt hay bộ phân loại. Muốn trả lời sâu hơn cần một thí nghiệm tiếp theo.

Mỗi cấu hình nhận cùng danh sách yêu cầu về LO, Bloom, loại câu và số lượng; dùng cùng kho tài liệu. Cố định model sinh, tham số sinh và chính sách sửa, ghi rõ ngân sách cho mỗi cấu hình. Với D, việc chọn đoạn nguồn là biến thay đổi có chủ đích. Ví dụ, 30 yêu cầu một câu × 4 cấu hình tạo tối đa 120 câu đầu ra để chấm, ngoài bộ hiệu chỉnh ở mục 4.1; số câu thực nhận có thể ít hơn nếu bị loại.

Người chấm độc lập đánh giá đầu ra trước khi giảng viên sửa, được ẩn cấu hình và kết quả AI. Đối chiếu nhãn Bloom do người chấm đưa ra với mức yêu cầu sau khi chấm xong. Cần báo cáo đồng thời:

- Tỷ lệ đáp án sai, câu mơ hồ, lỗi viết và câu đúng mức Bloom trên đầu ra được giữ lại.
- Số câu đạt toàn bộ tiêu chí theo người chấm trên tổng số câu được yêu cầu; số câu thiếu và số lần sửa.
- Tổng chi phí sinh, kiểm tra, sửa và sinh thay thế trên mỗi câu đạt; thời gian giảng viên duyệt mỗi câu.
- Kiểm tra một mẫu ứng viên bị loại để biết hệ thống có loại nhầm câu tốt hay không.

Báo cáo tỷ lệ cùng số mẫu và khoảng tin cậy. Quy mô ban đầu là thí nghiệm thăm dò để phát hiện nhóm lỗi và ước lượng chi phí; chưa đủ để kết luận riêng cho mọi môn, mọi loại câu và cả sáu mức Bloom. Chỉ xem chất lượng cải thiện khi giảm lỗi mà vẫn giữ được số câu đáp ứng yêu cầu, thay vì đạt tỷ lệ đẹp bằng cách loại gần hết câu.

## 5. Hiện trạng và thứ tự triển khai

### 5.1. Những gì xác nhận được từ mã nguồn

Bảng dưới phản ánh working tree được đọc ngày 08/10/2026; chưa xác nhận cấu hình hay dữ liệu đang chạy trên môi trường triển khai.

| Thành phần | Đã có trong code | Phần cần bổ sung theo đề xuất |
|---|---|---|
| Nguồn và sinh câu | Lấy ngữ cảnh theo LO; lưu ID nguồn; prompt nhận Bloom yêu cầu | Bằng chứng trích nguyên văn; kiểm tra đủ dữ kiện; hướng dẫn Bloom cụ thể |
| Kiểm tra đáp án | Prompt đã yêu cầu xét đáp án và khả năng phương án khác cũng đúng; giám khảo thấy đáp án từ đầu | Giải trước khi xem đáp án; kết quả riêng cho từng tiêu chí |
| Model kiểm tra | Có cấu hình riêng cho tác vụ sinh và kiểm tra; vẫn có thể trỏ cùng profile | Ghi model thực dùng trong hồ sơ và đối chiếu chất lượng giám khảo |
| Xử lý lỗi | Có vòng sửa; ứng viên còn bị bác sau giới hạn sửa không được lưu | Khi giám khảo lỗi, code hiện giữ nguyên mẻ; cần lưu rõ trạng thái chưa kiểm tra xong và hiển thị khi duyệt |
| Bloom | Quy đổi tên/số và lưu mức yêu cầu hoặc mức của LO; có unit test | Phân loại nội dung câu theo rubric; lưu nhãn AI và giảng viên riêng |
| Trùng lặp | ID tất định theo LO và văn bản câu; kiểu câu cũng tham gia khóa với các loại ngoài MCQ_SINGLE | Tìm gần trùng và trùng giữa các LO trong môn |
| Duyệt | Có duyệt, sửa, từ chối và lịch sử thay đổi | Hồ sơ kiểm tra theo phiên bản, cờ, lý do và xác nhận Bloom |
| Sau khi dùng | Có thống kê trả lời đúng theo câu | Độ phân biệt, phân bố lựa chọn và quy tắc đưa câu trở lại hàng đợi |

Các điểm đối chiếu chính:

- [Prompt sinh và kiểm tra](../worker/worker/prompts/curriculum_quiz.py); [luồng sinh và lưu câu](../worker/worker/use_cases/generate_curriculum_quiz.py).
- [Vòng kiểm tra và sửa](../worker/worker/use_cases/verification.py); [cấu hình model theo tác vụ](../worker/worker/container.py).
- [Test Bloom hiện tại](../worker/tests/unit/test_quizgen_phase0.py): kiểm tra quy đổi và lưu nhãn với LLM được mock; chưa kiểm chứng câu hỏi thực đạt mức Bloom.
- [Luồng giảng viên duyệt](../core-api/src/review/review.service.ts); [thống kê kết quả](../core-api/src/quiz/quiz-set-results.ts).

### 5.2. Triển khai theo thứ tự có thể kiểm chứng

| Ưu tiên | Việc thực hiện | Đầu ra để kiểm tra |
|---|---|---|
| 1 | Thống nhất rubric, lưu hồ sơ kiểm tra theo phiên bản; chuẩn bị mẫu gán nhãn | Truy xuất được câu, nguồn, yêu cầu sinh và kết quả từng bước |
| 2 | Kiểm tra trích dẫn và các luật; hiển thị cờ trên trang duyệt | Thấy đúng vị trí bị gắn cờ, đối chiếu được các lỗi ở mục 1 |
| 3 | Bổ sung giải mù, nhận xét từng phương án và Bloom đề xuất | Đánh giá giám khảo trên bộ có nhãn, gồm cả lỗi bị bỏ sót và cảnh báo sai |
| 4 | Bổ sung chọn nguồn và hướng dẫn sinh theo Bloom; sửa hoặc sinh thay thế có giới hạn | Giữ được mục tiêu ma trận đề, ghi rõ số câu thiếu và tổng chi phí |
| 5 | Cố định các cấu hình A–D và chạy thí nghiệm | Có kết quả do người chấm xác nhận, tách khỏi điểm AI tự đánh giá |
| 6 | Khi có dữ liệu làm bài phù hợp, bổ sung phân tích câu hỏi | Các cảnh báo thống kê gắn với đúng phiên bản câu và cỡ mẫu |

## 6. Nội dung cần trao đổi với giảng viên hướng dẫn

1. **Rubric và phạm vi thử nghiệm:** thống nhất cách xác định mức Bloom; giai đoạn đầu tập trung mức 1–4 và trắc nghiệm một đáp án có phù hợp không?
2. **Người chấm và dữ liệu:** chọn hai môn, người chấm độc lập và quy mô khả thi cho bộ hiệu chỉnh lẫn thí nghiệm A–D; có thể thu bài làm thật cho bước phân tích sau sử dụng không?
3. **Tiêu chí chấp nhận:** mức lỗi, tỷ lệ câu đáp ứng yêu cầu và chi phí nào phù hợp với mục đích luyện tập hoặc kiểm tra tính điểm? Cần thống nhất trước khi xem kết quả cuối.
4. **Chấm tự luận:** trong thời gian chưa có dữ liệu đối chiếu, điểm AI nên được sử dụng ở vai trò nào và cần cơ chế xác nhận nào?

## Phụ lục A. Kiểm soát chấm tự luận ngắn

Chất lượng câu hỏi và chất lượng chấm bài cần được đánh giá riêng. Câu hỏi, đáp án mẫu và rubric phải được duyệt trước; sau đó mới kiểm chứng khả năng đối chiếu bài làm của AI với rubric.

**Cơ chế hiện có trong code:** AI nhận xét từng ý trong rubric và trả đạt/chưa đạt; code tính điểm theo tỷ lệ số ý đạt. Với ba ý có trọng số bằng nhau, đạt hai ý được làm tròn thành 67/100. Đề và rubric được chụp lại lúc nộp; bài chưa chấm xong được giữ trạng thái chờ trước khi gửi điểm về Canvas. Khi AI không chấm được sau các lượt thử, bài chuyển sang giảng viên xử lý. Xem [luồng chấm](../worker/worker/use_cases/grade_short_answers.py), [dữ liệu chấm lúc nộp](../core-api/src/quiz/answer-grading.ts) và [xử lý bài cần duyệt](../core-api/src/quiz/essay-grading.service.ts).

Code tính điểm giúp công thức nhất quán, nhưng độ đúng vẫn phụ thuộc phán đoán của AI ở từng ý. Prompt hiện phân cách bài làm và yêu cầu bỏ qua chỉ dẫn bên trong bài; hiệu quả chống việc chèn lệnh phải được kiểm thử bằng các trường hợp cụ thể, không suy ra chỉ từ việc đã có dấu phân cách.

**Đánh giá đề xuất:** dùng khoảng 50–100 bài làm thật làm thí nghiệm ban đầu; hai người chấm độc lập với AI trên cùng rubric. Đo đồng thuận từng tiêu chí, sai lệch điểm và quadratic weighted kappa; so với mức đồng thuận giữa người chấm. Phân tích riêng bài diễn đạt khác đáp án mẫu, đúng một phần, sai kiến thức và bài có chèn yêu cầu thay đổi điểm.

Nghiên cứu của [Chamieh et al. (2024)](https://aclanthology.org/2024.bea-1.25/) ghi nhận hạn chế của LLM khi chấm câu trả lời ngắn, nhất là nhiệm vụ cần suy luận hoặc kiến thức chuyên ngành. Vì vậy cần bằng chứng trên bài làm của hệ thống trước khi quyết định phạm vi dùng điểm AI. Nếu chọn ngưỡng như kappa 0,70, phải ghi đó là ngưỡng thử nghiệm được thống nhất cho mục đích cụ thể; một chỉ số đạt ngưỡng chưa đủ để quyết định tự động ghi điểm chính thức.

## Phụ lục B. Cơ sở nghiên cứu cho các lựa chọn thiết kế

Các nghiên cứu dưới đây hỗ trợ lựa chọn phương pháp. Kết quả của chúng không thay cho kết quả thực nghiệm trên DA Platform.

| Câu hỏi thiết kế | Cơ sở tham khảo | Ý nghĩa và giới hạn áp dụng |
|---|---|---|
| Vì sao cần xem cả thao tác nhận thức? | Krathwohl (2002), *A Revision of Bloom's Taxonomy: An Overview*. [Bài báo](https://doi.org/10.1207/s15430421tip4104_2) | Phân loại cần xét nhiệm vụ và kiến thức; bảng rubric của nhóm vẫn cần được thống nhất với người chấm |
| Kiểm tra trích dẫn nhằm giải quyết gì? | Gao et al. (2023), *Enabling Large Language Models to Generate Text with Citations*. [EMNLP](https://arxiv.org/abs/2305.14627) | ALCE phân biệt độ đúng và chất lượng trích dẫn; so chuỗi là bước kiểm tra nguồn của nhóm, chưa xác nhận nội dung suy ra là đúng |
| Có nên dùng luật trước AI? | Moore et al. (2023), *Assessing the Quality of Multiple-Choice Questions Using GPT-4 and Rule-Based Methods*. [EC-TEL](https://arxiv.org/abs/2307.08161); Moore et al. (2024), *An Automatic Question Usability Evaluation Toolkit*. [SAQUET](https://arxiv.org/abs/2405.20529) | Nghiên cứu 2023 báo cáo bộ luật phát hiện 91% lỗi người chấm ghi nhận, GPT-4 là 79%, trên 200 câu thuộc bốn lĩnh vực. Đây là căn cứ thử bộ luật, chưa chứng minh mọi luật tiếng Việt đều hiệu quả |
| Vì sao kiểm tra giám khảo qua thứ tự phương án và model? | Pezeshkpour & Hruschka (2024). [Findings of NAACL](https://aclanthology.org/2024.findings-naacl.130/); Panickssery et al. (2024). [NeurIPS](https://arxiv.org/abs/2404.13076) | Có bằng chứng về độ nhạy thứ tự và thiên lệch tự ưu ái; đổi thứ tự hoặc tách model là biện pháp cần kiểm chứng, không phải bảo đảm đúng |
| Vì sao vòng sửa cần phản hồi cụ thể? | Huang et al. (2024), *Large Language Models Cannot Self-Correct Reasoning Yet*. [ICLR](https://arxiv.org/abs/2310.01798) | Trong các bài suy luận được khảo sát, tự sửa thiếu phản hồi bên ngoài có thể không cải thiện; không thể suy rộng rằng mọi cách tự sửa đều thất bại |
| Vì sao phải đối chiếu Bloom với người chấm? | Scaria et al. (2024). [AIED](https://arxiv.org/abs/2408.04394); Faraji et al. (2026), *Cross-Dataset Bloom Question Classification*. [Bản thảo nghiên cứu](https://arxiv.org/html/2606.13684v1) | Chất lượng sinh và phân loại thay đổi theo model, prompt và bộ dữ liệu; cần đánh giá trên ngữ cảnh môn học đích |
| Dữ liệu làm bài bổ sung bằng chứng gì? | Tarrant, Ware & Mohammed (2009). [BMC Medical Education](https://doi.org/10.1186/1472-6920-9-40) | Phân tích hiệu quả phương án nhiễu giúp phát hiện vấn đề sau sử dụng; ngưỡng thống kê cần xét cùng cỡ mẫu và mục đích bài thi |
| Vì sao chấm tự luận là một thí nghiệm riêng? | Chamieh, Zesch & Giebermann (2024). [BEA](https://aclanthology.org/2024.bea-1.25/); Williamson, Xi & Breyer (2012), *A Framework for Evaluation and Use of Automated Scoring*. [Bài báo](https://doi.org/10.1111/j.1745-3992.2011.00223.x) | Cần đánh giá đồng thuận và sự phù hợp với mục đích sử dụng điểm; cơ chế tính điểm tất định chưa chứng minh nhận xét của AI chính xác |
