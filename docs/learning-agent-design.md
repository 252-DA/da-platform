# AI Learning Agent: đề xuất thiết kế

| | |
|---|---|
| Trạng thái | Đề xuất cũ. Bản chi tiết hơn, có căn cứ tài liệu: [bao-cao-thiet-ke-learning-agent.md](bao-cao-thiet-ke-learning-agent.md) (14/10/2026) |
| Ngày | 2026-10-08 |
| Phạm vi | `core-api` (Learner Model, planner, RPC), `worker` + `packages-ai` (lưu kết quả chấm theo ý, sinh câu nhắm chỗ hụt), `web` (khung "Bước tiếp theo" ở trang sinh viên) |
| Liên quan | [quiz-generation-redesign.md](quiz-generation-redesign.md): Agent dùng ngân hàng câu và cần kiểm tra Bloom ở §7.8; [kiem-soat-chat-luong-genai.md](kiem-soat-chat-luong-genai.md): nguyên tắc "LLM viết, code quyết định" |

---

## 0. Tóm tắt

- **Đề xuất:** mở rộng phần sinh câu hỏi thành một Learning Agent. Agent theo dõi mức thành thạo của từng sinh viên và chọn hoạt động học tiếp theo. Sinh câu hỏi, chấm điểm AI và lịch ôn là công cụ của Agent. Kiến trúc hiện tại giữ nguyên.
- **Agent chỉ có giá trị khi nó chọn giữa nhiều hành động.** Một luồng cố định học → quiz → chấm → ôn chưa phải Agent. Ở đây Agent chọn trong một tập 8 hành động đóng, theo trạng thái người học và giới hạn giảng viên đặt.
- **Giữ nguyên "LLM viết, code quyết định".** Learner Model và planner là code tất định, kiểm thử được. LLM chỉ chấm tự luận (đã có) và viết câu hỏi nhắm vào chỗ hụt. Chế độ LLM chọn hành động được làm như một biến thể để so sánh.
- **Phần khó là Learner Model, không phải LLM.** Cần gắn câu hỏi với đơn vị kiến thức, và ước lượng mức thành thạo khi chưa có dữ liệu thật. Đề xuất dùng BKT với tham số cố định, tính lại từ `quiz_attempts`.
- **Điều kiện tiên quyết:** câu hỏi phải đúng mức Bloom ghi trên nhãn. Hiện `bloom_level` chỉ là mức được yêu cầu, chưa được đánh giá. Nếu không sửa, quyết định "nâng mức Bloom" của Agent vô nghĩa.
- **Việc rẻ nhất, giá trị cao nhất:** lưu kết quả chấm từng ý rubric. Hệ thống đang tính ra rồi bỏ đi.
- **Đánh giá:** mô phỏng người học, so planner với thứ tự cố định theo số câu cần để đạt thành thạo.

---

## 1. Bối cảnh

Video, chat (ai-tutor) và trình xem tài liệu đã giao cho thành viên khác. Phần còn lại của tài liệu này là sinh câu hỏi và chấm điểm. Micro-content cần video nên không còn là hướng chính của phần này.

QuizGen v2 §13 (Q5) đã ghi "chọn câu thích ứng theo người học" là ngoài phạm vi. Tài liệu này nhận phần đó.

Agent khác trợ giảng ở chỗ nó tự đề xuất, dựa trên lịch sử học:

| | Trợ giảng (ai-tutor) | Learning Agent |
|---|---|---|
| Kích hoạt | sinh viên hỏi | sau mỗi lượt làm bài, hoặc khi đến hạn ôn |
| Đầu vào | câu hỏi + tài liệu | lịch sử làm bài + Learner Model |
| Quyết định | trả lời thế nào | học, ôn hay kiểm tra gì tiếp |
| Bộ nhớ | lịch sử hội thoại | trạng thái thành thạo theo đơn vị kiến thức |
| Người làm | thành viên khác | phần này |

---

## 2. Định nghĩa và phạm vi

**Định nghĩa dùng trong đồ án.** Learning Agent là một vòng lặp:

1. **Quan sát:** đọc kết quả các lượt làm bài.
2. **Cập nhật:** tính lại mức thành thạo của từng đơn vị kiến thức.
3. **Chọn hành động:** chọn một hành động trong tập đóng, theo trạng thái và mục tiêu (mức Bloom của LO).
4. **Ghi nhận:** lưu quyết định, lý do, và việc sinh viên có làm theo hay không.

Tính "agent" nằm ở bước 3: hành động thay đổi theo trạng thái của từng người. Nó không nằm ở việc có gọi LLM hay không.

**Mục tiêu**
- Ước lượng mức thành thạo của từng sinh viên theo LO, sau đó theo đơn vị kiến thức (KU).
- Sau mỗi lượt làm bài, đề xuất một hoạt động tiếp theo kèm lý do đọc được.
- Lên lịch ôn cho các đơn vị đã thạo.
- Chứng minh bằng thực nghiệm rằng planner tốt hơn thứ tự cố định.

**Không làm**
- Không multi-agent: một planner, các dịch vụ sẵn có đóng vai công cụ.
- Không ước lượng tham số BKT, IRT hay DKT từ dữ liệu thật, vì không đủ sinh viên.
- Không dựng khung chat riêng, không sửa video và viewer.
- Không gửi điểm của hoạt động do Agent chọn về Canvas qua AGS. Đây là luyện tập.

---

## 3. Hiện trạng

### 3.1 Đã có

| Thành phần | Hiện trạng | Agent dùng để |
|---|---|---|
| `quiz_attempts` | mỗi câu một dòng: `is_correct`, `score`, `chosen_answer`, `response_time_ms`, `attempted_at` | quan sát chính |
| `quiz_items` | `lo_id`, `bloom_level`, `source_chunk_ids`, `status`; 5 loại câu (`MCQ_SINGLE`, `MCQ_MULTI`, `TRUE_FALSE`, `FILL_BLANK`, `SHORT_ANSWER`) | ngân hàng câu |
| Chấm tự luận ngắn | LLM phán từng ý rubric đạt hay chưa, kèm nhận xét ([grade_short_answers.py](../worker/worker/use_cases/grade_short_answers.py)) | chẩn đoán chỗ hụt |
| `lesson_cards` | thẻ theo LO; video gắn riêng qua `card_video_attachments`, nên thẻ chữ vẫn dùng được khi không có video | hành động "đọc lại" |
| `chunk_lo_mappings`, `chunks` | chunk có `page_number`; nối chunk với LO | trỏ về trang tài liệu nguồn |
| `learning_outcomes` | `bloom_level` của LO (có `bloom_provenance`) | mục tiêu cần đạt |
| `chapter_los` | chương ↔ LO theo đề cương | thứ tự học |
| mcp-service | `retrieve_quiz_context`, `search_course_chunks` | lấy ngữ cảnh khi sinh câu |
| `user_llm_quota`, `scope_llm_quota` | bảng hạn mức LLM; có bảng, chưa có code dùng | giới hạn chi phí |

### 3.2 Còn thiếu

| # | Thiếu | Hệ quả |
|---|---|---|
| G1 | Kết quả từng ý rubric bị bỏ. `score_from_points` gộp thành điểm; `save_answer_grade` chỉ lưu `score`, `is_correct`, `feedback` | không biết sinh viên hụt ý nào, chỉ biết thiếu bao nhiêu |
| G2 | Không có đơn vị kiến thức dưới LO. KU (QuizGen v2 §7.3) chưa có code. `chunk_concepts` lấy khái niệm từ heading | chỉ theo dõi được ở mức LO, quá thô |
| G3 | `bloom_level` của câu là mức được yêu cầu, chưa có bước đánh giá | "nâng mức Bloom" có thể chỉ là hỏi thêm câu nhớ lại |
| G4 | Ngân hàng có câu trùng với nhãn khác nhau (ví dụ "Kiến trúc Lambda gồm ba lớp nào?" lặp 3 lần) | "hỏi câu mới" có thể là hỏi lại cùng một câu |
| G5 | Không có bảng mastery. `flashcard_reviews` và `learning_events` có bảng nhưng không code nào ghi | phải tự xây |
| G6 | Trang sinh viên không có chỗ hiện gợi ý: `/learn/dashboard` chỉ chuyển sang trang khoá học | cần một khung mới |

G3 và G4 là việc của QuizGen v2. Tài liệu này chỉ ghi chúng là điều kiện tiên quyết.

---

## 4. Kiến trúc

```text
Sinh viên (web /learn, mở qua LTI)
   │ nộp bài: SubmitQuiz, SubmitQuizSet
   ▼
core-api ── ghi quiz_attempts (câu tự luận: worker chấm rồi ghi lại)
   │
   │ sinh viên mở trang kết quả → GetNextActivity
   ▼
[1] Learner Model        tính lại từ quiz_attempts, cache vào learner_unit_state   (code)
   │
   ▼
[2] Chẩn đoán            ý rubric hụt → đơn vị kiến thức; distractor đã chọn → hiểu lầm (code, tra bảng)
   │
   ▼
[3] Planner              luật theo thứ tự, ra MỘT hành động trong tập đóng          (code)
   │                     biến thể so sánh: LLM chọn trong các hành động hợp lệ
   ▼
[4] Công cụ
   ├─ chọn câu chưa làm trong ngân hàng đã duyệt
   ├─ trỏ về lesson card hoặc trang tài liệu nguồn
   ├─ đặt lịch ôn
   └─ yêu cầu sinh câu nhắm chỗ hụt → worker → hàng đợi duyệt của giảng viên
   │
   ▼
learning_events          ghi quyết định, lý do, chính sách đã dùng
```

**Quyết định thiết kế**

1. **Learner Model là một hàm thuần trên lịch sử `quiz_attempts`.** Bảng `learner_unit_state` chỉ là cache. Hệ quả:
    - không cần trigger hay event khi worker chấm xong tự luận: lần đọc sau tự thấy điểm mới;
    - đổi tham số thì tính lại cho mọi người, không phải migrate;
    - mô phỏng (§9) chạy đúng hàm đó trên lịch sử giả.

    Ở quy mô đồ án (vài chục sinh viên, vài nghìn lượt), tính lại khi đọc là đủ nhanh.
2. **Planner chạy theo yêu cầu (pull), không đẩy.** Web gọi `GetNextActivity` khi sinh viên mở trang kết quả hoặc trang khoá học. Không cần hàng đợi hay lịch chạy nền.
3. **Learner Model và planner nằm trong core-api.** core-api sở hữu DB và đã có module `quiz`. Thêm module `learning-agent`.
4. **LLM nằm trong worker, đi qua đường sinh câu hiện có.** Sinh câu nhắm chỗ hụt là một `content-generation-requested` có thêm trường "ý bị hụt". Câu sinh ra vào hàng đợi duyệt như mọi câu khác.

---

## 5. Learner Model

### 5.1 Theo dõi ở mức nào

| Mức | Nguồn | Ưu | Nhược |
|---|---|---|---|
| LO | `quiz_items.lo_id`, có sẵn | chạy được ngay | một LO chứa nhiều ý; đúng ý này không nói gì về ý kia |
| Khái niệm | `chunk_concepts` | có sẵn | lấy từ heading của chunk, không phải từ ý câu hỏi kiểm tra |
| KU | QuizGen v2 §7.3 | đúng ý câu hỏi kiểm tra | chưa làm |

**Đề xuất:** giai đoạn 1 theo dõi theo LO. Khi QuizGen v2 có KU thì chuyển sang KU: mỗi câu gắn một KU chính, mỗi ý rubric gắn một KU. Gắn lúc sinh câu, lưu trong `generation_meta`, nên lúc chạy không cần LLM để chẩn đoán.

Mức thành thạo tách theo mức Bloom: trả lời đúng câu nhớ lại không nói gì về khả năng vận dụng. Mỗi (sinh viên, đơn vị, mức Bloom) có một giá trị riêng, chỉ tính các mức không vượt quá mức của LO.

### 5.2 Công thức: BKT với tham số cố định

Bayesian Knowledge Tracing (Corbett và Anderson, 1995) giữ một xác suất P(L) rằng sinh viên đã nắm đơn vị. Sau mỗi quan sát:

```latex
P(L \mid \text{đúng}) = \frac{P(L)\,(1-S)}{P(L)\,(1-S) + (1-P(L))\,G}
\qquad
P(L \mid \text{sai}) = \frac{P(L)\,S}{P(L)\,S + (1-P(L))\,(1-G)}
```

```latex
P(L_{\text{sau}}) = P(L \mid \text{quan sát}) + \bigl(1 - P(L \mid \text{quan sát})\bigr)\,T
```

| Tham số | Ý nghĩa | Giá trị khởi đầu |
|---|---|---|
| P(L₀) | đã biết trước khi học | 0.2 |
| T | học được sau một lần làm | 0.15 |
| S | biết mà vẫn sai | 0.1 |
| G | không biết mà vẫn đúng | theo loại câu: `MCQ_SINGLE` 0.25, `TRUE_FALSE` 0.5, `MCQ_MULTI` 0.1, `FILL_BLANK` 0.05, `SHORT_ANSWER` 0.05 |

Ngưỡng thành thạo: P(L) ≥ 0.95, mốc thường dùng từ bài gốc.

Với các giá trị này:
- 3 câu `MCQ_SINGLE` đúng liên tiếp đưa P(L) từ 0.2 lên 0.958;
- `TRUE_FALSE` cần 6 câu đúng liên tiếp (5 câu mới tới 0.945), vì đoán đúng dễ;
- 2 câu `SHORT_ANSWER` đạt mọi ý đã tới 0.991;
- một câu `MCQ_SINGLE` sai sau khi đã thạo kéo P(L) từ 0.958 xuống 0.79.

Đây là giá trị khởi đầu chưa hiệu chỉnh. Báo cáo phải ghi rõ điều đó (R3).

**Quy tắc quan sát**
- Chỉ tính **lần đầu** một sinh viên gặp một câu. Làm lại cùng câu thì ghi nhận nhưng không cập nhật, vì đúng lần hai có thể chỉ là nhớ đáp án.
- `SHORT_ANSWER` khi đã gắn ý → mỗi ý rubric là một quan sát trên đơn vị của ý đó. Chưa gắn ý → một quan sát, đúng khi `is_correct` (đạt mọi ý).
- Câu đang chờ chấm (`grading_status` khác `GRADED`) chưa được tính.

### 5.3 Vì sao không dùng tỉ lệ đúng

Làm đúng 8/10 câu không có nghĩa là thạo 80%. Bảng dưới cho thấy mỗi tín hiệu được xử lý ở đâu:

| Tín hiệu | Xử lý |
|---|---|
| Đoán đúng | G theo loại câu |
| Mức Bloom | mastery tách theo mức |
| Làm lại cùng câu | chỉ tính lần đầu |
| Quên theo thời gian | BKT không mô hình hoá; lịch ôn (§5.4) lo phần này |
| Đã được trợ giúp (chat) | ngoài phạm vi giai đoạn đầu: `chat_messages` không gắn LO |
| Độ khó câu | chưa dùng; cần `quiz_item_stats` (QuizGen v2 §7.11) |

### 5.4 Lịch ôn

Dùng hộp Leitner: mỗi đơn vị đã thạo có một tầng 1–5, khoảng cách 1, 3, 7, 14, 30 ngày.
- Ôn đúng → lên một tầng.
- Ôn sai → về tầng 1, và câu sai được tính như một quan sát BKT, nên P(L) giảm.

Leitner đủ để giải thích trong báo cáo. Có thể thay bằng FSRS sau nếu cần.

### 5.5 Lưu trữ

Bảng mới, chỉ là cache, có thể xoá và tính lại:

```text
learner_unit_state(
  user_id, course_id,
  unit_type      'lo' | 'ku',
  unit_id,
  bloom_level,
  p_mastery,
  observations,           -- số quan sát đã tính
  review_stage,           -- 0 = chưa thạo, 1–5 = tầng Leitner
  next_due_at,
  params_version,         -- đổi tham số → tính lại
  computed_at
)
```

`flashcard_reviews` hiện không được dùng. Nó khoá theo `card_id` nên không hợp với lịch ôn theo đơn vị. Đề xuất để nguyên và không dùng; quyết định xoá sau.

---

## 6. Planner

### 6.1 Tập hành động

| # | Hành động | Công cụ |
|---|---|---|
| A1 | Hỏi câu mới cùng mức | chọn câu `APPROVED` chưa làm, cùng đơn vị, cùng mức Bloom |
| A2 | Nâng mức Bloom | chọn câu mức k+1 của cùng đơn vị |
| A3 | Đọc lại nguồn rồi hỏi lại | lesson card của LO, hoặc trang tài liệu từ `source_chunk_ids` → `page_number` |
| A4 | Sinh câu nhắm chỗ hụt | yêu cầu sinh câu → hàng đợi duyệt |
| A5 | Lên lịch ôn | ghi `next_due_at` |
| A6 | Ôn đơn vị đến hạn | chọn câu chưa làm của đơn vị đó |
| A7 | Sang LO kế tiếp | thứ tự chương và `chapter_los` |
| A8 | Báo giảng viên | đánh dấu sinh viên × đơn vị bị kẹt |

### 6.2 Luật chọn

Xét theo thứ tự, luật đầu tiên khớp thì dùng. Mọi ngưỡng là giá trị khởi đầu.

1. Có đơn vị đến hạn ôn, và phiên này ôn chưa quá 3 câu → **A6**.
2. Đã đọc lại (A3) mà vẫn sai thêm 2 câu ở cùng đơn vị → **A8**, rồi sang đơn vị khác để không kẹt.
3. Sai 2 câu liên tiếp ở mức hiện tại, hoặc P(L) < 0.4 sau ít nhất 2 quan sát → **A3**.
4. P(L) < 0.95 ở mức hiện tại → **A1**. Hết câu phù hợp → **A4** nếu giảng viên bật, không thì **A8**.
5. P(L) ≥ 0.95 và mức hiện tại thấp hơn mức Bloom của LO → **A2**.
6. Đạt mức Bloom của LO → **A5** cho đơn vị này, rồi **A7**.

Luật 4 cần ngân hàng đủ dày, xem R2.

### 6.3 Giới hạn do giảng viên đặt

- LO nào được mở cho Agent.
- Số câu tối đa mỗi sinh viên mỗi ngày.
- Bật hay tắt A4 (sinh câu mới), vì A4 tốn token và thêm việc duyệt.
- Hạn mức token, dùng lại `user_llm_quota` và `scope_llm_quota`.

### 6.4 Lý do hiện cho sinh viên

Mỗi đề xuất kèm một câu lý do, ghép từ mẫu, không gọi LLM:
- A3: "Bạn sai 2 câu liên tiếp về {LO}. Đọc lại thẻ "{tiêu đề thẻ}" rồi thử lại."
- A1 sau câu tự luận: lấy nhận xét của ý rubric bị hụt, ví dụ "Bạn nêu đúng cấu trúc cây nhưng chưa nói vì sao giảm số lần đọc đĩa."
- A2: "Bạn đã nắm phần {mức k} của {LO}. Thử một câu {mức k+1}."

Nhận xét theo ý chỉ có sau khi sửa G1.

### 6.5 Biến thể: LLM chọn hành động

Để so sánh trong thực nghiệm, và để trả lời câu hỏi "Agent dùng LLM ở đâu":
- Code tính tập hành động hợp lệ (các luật có điều kiện thoả).
- LLM nhận tóm tắt trạng thái: mastery theo đơn vị và mức, 5 lượt gần nhất, các hành động hợp lệ.
- LLM trả JSON `{action, unit_id, reason}`.
- Code kiểm tra hành động có trong tập hợp lệ. Sai, hoặc gọi lỗi → dùng planner luật.

Chi phí: một lần gọi cho mỗi quyết định, nằm trong hạn mức ở §6.3.

---

## 7. LLM và kiểm soát chất lượng

LLM xuất hiện ở ba chỗ, không chỗ nào quyết định một mình:

| Chỗ | Trạng thái | Kiểm soát |
|---|---|---|
| Chấm tự luận theo ý rubric | đã có | bài làm bị rào giữa hai mốc, coi là dữ liệu; lỗi → `NEEDS_REVIEW`, giảng viên chấm |
| Sinh câu nhắm chỗ hụt (A4) | mới | đi qua pipeline sinh câu có kiểm tra; vào hàng đợi duyệt |
| LLM-planner (§6.5) | biến thể | chỉ chọn trong tập hợp lệ do code tính |

**Phụ thuộc vào QuizGen v2:**
- Kiểm tra Bloom (§7.8, `bloom_assessed`): không có nó, A2 không đáng tin.
- Chống trùng (`quiz_item_index`): không có nó, A1 có thể hỏi lại cùng một câu dưới nhãn khác. Khi đó quy tắc "chỉ tính lần đầu" cũng hỏng.
- Distractor kèm hiểu lầm (`generation_meta.distractors[].misconception`): cho phép chẩn đoán từ câu trắc nghiệm sai, không chỉ từ tự luận.

**Câu do Agent sinh.** Nguyên tắc 5 của tài liệu kiểm soát chất lượng chỉ bắt buộc duyệt câu tính điểm. Câu luyện tập thì nhóm tự chọn. Khuyến nghị: vẫn duyệt (Q1), nên A4 không cho kết quả ngay trong phiên.

---

## 8. Ranh giới với phần của thành viên khác

| Phần | Agent cần gì | Cách nối |
|---|---|---|
| Chat (ai-tutor) | không cần để chạy | đưa ra RPC `GetLearnerSummary`; tutor tự quyết có dùng để biết điểm yếu của sinh viên hay không |
| Trình xem tài liệu | A3 mở tài liệu đúng trang | link vào route của viewer với `document_id` và trang |
| Video | không cần | thẻ có video thì vẫn hiện như cũ |
| Trang `/learn` | chỗ hiện "Bước tiếp theo" | thống nhất vị trí với người đang sửa trang (Q4) |

Nguyên tắc: Agent không sửa UI của người khác. Nó chỉ đưa dữ liệu ra qua RPC.

---

## 9. Đánh giá

### 9.1 Người học mô phỏng (thực nghiệm chính)

- **Sinh viên ảo:** mỗi đơn vị có trạng thái ẩn "đã nắm / chưa", tiến triển theo BKT. Tham số ẩn bốc ngẫu nhiên cho từng sinh viên, **khác** tham số planner dùng, để thực nghiệm không tự chứng minh chính nó.
- **Ngân hàng câu:** lấy cấu trúc từ DB dev (số LO, mức Bloom, loại câu, số câu mỗi LO).
- **Ba chính sách:**
    1. thứ tự cố định: mỗi LO N câu theo thứ tự, giống một bài quiz thường;
    2. planner luật;
    3. LLM-planner.
- **Chỉ số:**
    - số câu đến khi mọi LO thật sự được nắm;
    - tỉ lệ **thạo giả**: planner báo P(L) ≥ 0.95 khi trạng thái ẩn vẫn là chưa nắm;
    - số câu thừa hỏi sau khi đã nắm;
    - với LLM-planner: số lần chọn hành động không hợp lệ, chi phí token.
- **Giả định về A3:** đọc lại làm tăng T ở lần làm kế tiếp. Không có dữ liệu cho mức tăng này, nên chạy với nhiều mức và báo cáo độ nhạy.

Mô phỏng chỉ chứng minh planner hoạt động đúng **dưới giả định của mô hình**. Nó không chứng minh sinh viên học tốt hơn. Báo cáo phải nói rõ.

### 9.2 Kiểm thử phần tất định

- Hàm cập nhật BKT: so với các giá trị tính tay ở §5.2.
- Planner: test theo bảng, mỗi luật ở §6.2 một trường hợp, kể cả thứ tự ưu tiên.
- Learner Model: cùng lịch sử thì ra cùng trạng thái; thêm câu tự luận đang chờ chấm thì không đổi.

### 9.3 Thử nghiệm nhỏ (nếu kịp)

5–10 bạn cùng lớp, một chương, một tuần. Đo số câu, thời gian, tỉ lệ làm theo đề xuất (từ `learning_events`), và khảo sát cảm nhận. Không đủ để kết luận thống kê, chỉ để thấy hệ thống chạy với người thật.

---

## 10. Lộ trình

Chưa có mốc ngày; cần khớp với lịch bảo vệ (Q5).

**Giai đoạn 0: nền, có ích kể cả khi bỏ hướng Agent**
- [ ] Lưu kết quả từng ý rubric khi chấm tự luận (G1): thêm `points[]` vào `quiz_attempts`, qua `grading_input` hoặc một cột mới.
- [ ] Kiểm tra Bloom cho câu sinh ra (QuizGen v2 §7.8).
- [ ] Chống trùng câu (QuizGen v2 R9, `quiz_item_index`).

**Giai đoạn 1: Learner Model theo LO**
- [ ] Hàm BKT trên `quiz_attempts`, kèm test §9.2.
- [ ] Bảng `learner_unit_state` (cache) và RPC `GetLearnerSummary`.
- [ ] Trang sinh viên hiện mức thành thạo theo LO.

**Giai đoạn 2: Planner**
- [ ] Planner luật A1–A8, ghi mọi quyết định vào `learning_events`.
- [ ] RPC `GetNextActivity` và khung "Bước tiếp theo" ở trang kết quả quiz.
- [ ] Lịch ôn Leitner.
- [ ] Giới hạn do giảng viên đặt.

**Giai đoạn 3: Đánh giá**
- [ ] Bộ mô phỏng và ba chính sách (§9.1).
- [ ] LLM-planner.
- [ ] Thử nghiệm nhỏ.

**Giai đoạn 4: Mở rộng, nếu còn thời gian**
- [ ] Chuyển từ LO sang KU khi QuizGen v2 có KU.
- [ ] A4: sinh câu nhắm chỗ hụt.
- [ ] Chẩn đoán từ distractor đã chọn.

---

## 11. Rủi ro và câu hỏi mở

| # | Vấn đề | Đề xuất |
|---|---|---|
| R1 | Câu sai nhãn Bloom làm planner quyết định sai | làm giai đoạn 0 trước giai đoạn 2 |
| R2 | Ngân hàng mỏng: ít câu `APPROVED` mỗi LO và mỗi mức, A1 hết câu sau vài lượt | đếm số câu `APPROVED` theo (LO, mức Bloom) trước khi làm planner; thiếu thì sinh bù theo lô, không chờ A4 |
| R3 | Tham số BKT không hiệu chỉnh được vì không có dữ liệu thật | ghi rõ trong báo cáo; mô phỏng với tham số ẩn khác tham số planner |
| R4 | Hội đồng hỏi "đâu là Agent?" | §2 định nghĩa; §6.5 và §9.1 so sánh planner luật với LLM-planner |
| R5 | Đụng phần người khác ở trang `/learn` | thống nhất chỗ hiện gợi ý trước khi làm UI |
| Q1 | Câu do Agent sinh có cần giảng viên duyệt trước khi hiện không? | khuyến nghị **có** |
| Q2 | Quan hệ tiên quyết giữa các LO lấy ở đâu? Hiện chỉ có thứ tự chương và `chapter_los` | dùng thứ tự chương; đồ thị tiên quyết (Neo4j) để sau |
| Q3 | Có tính điểm hoạt động Agent chọn không? | khuyến nghị **không**, chỉ luyện tập |
| Q4 | Hiện "Bước tiếp theo" ở đâu: trang kết quả quiz, trang khoá học, hay trong chat? | khuyến nghị trang kết quả quiz trước |
| Q5 | Lịch bảo vệ | quyết định dừng ở giai đoạn nào |

---

## Tài liệu tham khảo

- Corbett, A. T., & Anderson, J. R. (1995). Knowledge tracing: Modeling the acquisition of procedural knowledge. *User Modeling and User-Adapted Interaction*, 4(4), 253–278.
- Pelánek, R. (2017). Bayesian knowledge tracing, logistic models, and beyond: An overview of learner modeling techniques. *User Modeling and User-Adapted Interaction*, 27, 313–350.
- Piech, C., et al. (2015). Deep knowledge tracing. *NeurIPS 2015*. (Lý do không dùng: cần nhiều dữ liệu.)
- Roediger, H. L., & Karpicke, J. D. (2006). Test-enhanced learning: Taking memory tests improves long-term retention. *Psychological Science*, 17(3), 249–255.
- Cepeda, N. J., et al. (2006). Distributed practice in verbal recall tasks: A review and quantitative synthesis. *Psychological Bulletin*, 132(3), 354–380.
- Leitner, S. (1972). *So lernt man lernen*. Herder.
