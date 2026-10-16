# Gán Bloom cho LO: sửa luật suy luận

| | |
|---|---|
| Trạng thái | Đề xuất, chưa triển khai. Đã chạy thử bản nguyên mẫu trên dữ liệu dev ngày 14/10/2026 |
| Ngày | 2026-10-14 |
| Phạm vi | Giai đoạn 1: `packages-ai` (`dcmh_extractor.py`). Giai đoạn 2: `postgres_curriculum_repository.py`, `core-api` (`learning-outcome.controller.ts`), `web` (`/manage/curriculum`) |
| Liên quan | [bao-cao-nghien-cuu-lo-bloom.md](bao-cao-nghien-cuu-lo-bloom.md) §3.2 (trường hợp A); [learning-agent-design.md](learning-agent-design.md) (mastery tách theo mức Bloom) |

---

## 0. Tóm tắt

- Bloom của LO là **mục tiêu năng lực**: sinh viên phải đạt LO đó ở mức nào. Mục tiêu sai thì báo cáo năng lực sai. Đặt thấp thì sinh viên được tính là đạt quá sớm; đặt cao thì đề đòi hỏi vượt chuẩn đầu ra.
- Luật hiện tại lấy **động từ xuất hiện sớm nhất** trong câu tiếng Việt. Trên 18 LO thật trong DB dev, 16 LO ra đúng mức theo động từ. Hai LO sai (L.O.3, L.O.3.3), và cả hai đều là LO mức cao. Một LO khác (L.O.4) mất hành vi "evaluate" vì hệ thống chỉ đọc bản tiếng Việt.
- **Không dùng cách "lấy mức cao nhất trong cả câu".** Thử trên cùng dữ liệu, cách này nâng sai 4 LO vì "phân tích dữ liệu" là cụm danh từ, không phải hành vi của sinh viên.
- **Đề xuất:** chỉ xét **chuỗi động từ ở đầu câu**, tức động từ đầu tiên và các động từ nối với nó bằng dấu phẩy, "và", "hoặc". Mục tiêu là mức cao nhất trong chuỗi đó. Đi kèm: bổ sung bảng động từ, sửa các động từ lệch Krathwohl, đối chiếu bản tiếng Anh, và gắn cờ những LO luật không chắc chắn.
- **Kết quả nguyên mẫu:** 16/18 LO giữ nguyên. L.O.3 và L.O.3.3 lên mức Đánh giá. Hai LO bị gắn cờ để giảng viên xem (L.O.4, L.O.4.3).
- **Giai đoạn 2:** giảng viên sửa và xác nhận Bloom. Import lại đề cương không ghi đè LO đã xác nhận. Không cần đổi schema.
- Không dùng embedding hay LLM ở bước này; lý do ở §5.

---

## 1. Bloom của LO được dùng ở đâu

| Chỗ dùng | Vị trí | Ảnh hưởng khi mức sai |
|---|---|---|
| Bloom mặc định khi sinh câu (chế độ "auto") | [quiz-composer.tsx](../web/src/app/lti/deep-link/quiz-composer.tsx), [generate_curriculum_quiz.py:315](../worker/worker/use_cases/generate_curriculum_quiz.py#L315) | Sinh câu sai mức. LO không có Bloom thì lặng lẽ dùng Hiểu |
| Ma trận đề LO × Bloom | [quiz-blueprint.ts](../core-api/src/quiz/quiz-blueprint.ts) | Không kiểm tra được đề có đo đủ mức của LO hay không |
| Báo cáo "Theo chuẩn đầu ra" | [quiz-set-results.ts:188-196](../core-api/src/quiz/quiz-set-results.ts#L188-L196) | Hiện chưa xét Bloom; khi bổ sung thì cần mục tiêu đúng |
| Mastery của Learning Agent | [learning-agent-design.md](learning-agent-design.md) §5.1 | Mastery chỉ tính các mức không vượt quá mức của LO, nên mục tiêu sai thì điểm dừng sai |

## 2. Hiện trạng

- Bảng động từ và hàm suy luận: [dcmh_extractor.py:51-72](../packages-ai/src/document_chunk/adapters/curriculum/dcmh_extractor.py#L51-L72) (`_BLOOM_VERBS`, `_infer_bloom`).
- Chỉ gọi với `statement_vi` và luôn gán `bloom_provenance="inferred"`: [dcmh_extractor.py:382-383](../packages-ai/src/document_chunk/adapters/curriculum/dcmh_extractor.py#L382-L383).
- Import lại đề cương ghi đè cả `bloom_level` lẫn `bloom_provenance`: [postgres_curriculum_repository.py:367-368](../packages-ai/src/document_chunk/adapters/metadata/postgres_curriculum_repository.py#L367-L368).
- Trang đề cương chỉ hiển thị Bloom kèm nhãn "(đề xuất)", không cho sửa: [page.tsx:197-199](../web/src/app/manage/curriculum/page.tsx#L197-L199). API LO chỉ có `GET`.

### 2.1. Kết quả trên dữ liệu dev

DB dev hiện có một môn (Dữ liệu lớn) với 18 LO. Ba LO có vấn đề:

| LO | Nguyên văn | Hiện tại | Đề xuất | Nguyên nhân |
|---|---|---|---|---|
| L.O.3 | Giải thích, so sánh và lựa chọn được kiến trúc dữ liệu lớn phù hợp cho bài toán. | Hiểu (2) | Đánh giá (5) | Lấy "giải thích" vì đứng đầu; "lựa chọn" không có trong bảng |
| L.O.3.3 | So sánh và lựa chọn được kiến trúc dữ liệu lớn cho từng bài toán. | Phân tích (4) | Đánh giá (5) | "lựa chọn" không có trong bảng |
| L.O.4 | VI: Có khả năng vận dụng các thư viện/công cụ để phát triển các giải pháp xử lý cho bài toán dữ liệu.<br>EN: Be able to use libraries/tools to develop solutions used for big data problems **and evaluate them**. | Vận dụng (3) | Vận dụng, kèm cờ | Bản EN có thêm "evaluate" mà bản VI không có; hệ thống chỉ đọc VI |

Ngoài ra, L.O.3 (cha) đang ở mức 2 trong khi L.O.3.3 (con) ở mức 4: mục tiêu của LO cha thấp hơn LO con.

"Đề xuất" là cách đọc của tài liệu này. "Lựa chọn kiến trúc phù hợp cho bài toán" là đưa ra quyết định theo tiêu chí, nên xếp vào Đánh giá. Giảng viên vẫn phải xác nhận.

### 2.2. Câu tự dựng

Dùng để thử các lỗi chưa xuất hiện trong dữ liệu dev:

| Câu | Hiện tại | Lỗi |
|---|---|---|
| Viết truy vấn SQL đáp ứng yêu cầu nghiệp vụ | `None` | Thiếu "viết" |
| Lựa chọn kiến trúc phù hợp cho bài toán | `None` | Thiếu "lựa chọn" |
| Cài đặt và kiểm thử thuật toán sắp xếp | `None` | Thiếu "cài đặt", "kiểm thử" |
| Có kiến thức về bộ nhớ ảo và vận dụng vào quản lý tiến trình | Nhớ | Khớp "nhớ" trong "bộ nhớ" |
| Xác định yêu cầu của người sử dụng | Vận dụng | Khớp "sử dụng" trong "người sử dụng" |
| Lập kế hoạch dự án phần mềm | Vận dụng | Bảng xếp "lập kế hoạch" vào Vận dụng |
| Trình bày và phân tích các phương pháp xử lý dữ liệu | Nhớ | Lấy động từ đầu, bỏ "phân tích" |

Khi kết quả là `None`, lúc sinh câu hệ thống dùng Hiểu. Có ghi log nhưng giảng viên không thấy.

### 2.3. Bảng động từ lệch Krathwohl

Báo cáo nghiên cứu lấy Krathwohl (2002) làm cơ sở, nhưng bảng hiện tại xếp một số động từ khác:

| Động từ | Bảng hiện tại | Krathwohl (2002) |
|---|---|---|
| so sánh (*comparing*) | Phân tích | Hiểu (2.6) |
| phân loại (*classifying*) | Phân tích | Hiểu (2.3) |
| phân biệt (*differentiating*) | Hiểu | Phân tích (4.1) |
| lập kế hoạch (*planning*) | Vận dụng | Sáng tạo (6.2) |

## 3. Đề xuất giai đoạn 1: chỉ sửa extractor

Giai đoạn này không đổi schema, API hay giao diện. Cờ được đưa vào `ctx.issues` và tự hiện ở khung "Cần soát" của trang đề cương ([page.tsx:144-148](../web/src/app/manage/curriculum/page.tsx#L144-L148)).

### 3.1. Lấy chuỗi động từ ở đầu câu

1. Chuẩn hóa: chữ thường, gộp khoảng trắng, bỏ ngoặc bao ngoài (bản EN nằm trong ngoặc).
2. Bỏ tiền tố: "sinh viên có khả năng", "sinh viên có thể", "người học có thể", "có khả năng", "có thể". Với EN: "students will be able to", "be able to", "ability to", "able to".
3. Tại đầu câu, khớp **động từ dài nhất** trong bảng ("hiểu biết" được ưu tiên hơn "hiểu"). Động từ phải kết thúc ở ranh giới từ. Bỏ qua chữ "được" nếu đứng ngay sau.
4. Nếu tiếp theo là dấu nối (`,`, `và`, `, và`, `hoặc`, `/`) **và ngay sau dấu nối là một động từ trong bảng**, thêm động từ đó vào chuỗi rồi lặp lại bước 4. Nếu không thì dừng: phần còn lại là tân ngữ.
5. Mục tiêu là **mức cao nhất trong chuỗi**.

Lý do: chuỗi đầu câu là việc sinh viên phải làm. Động từ xuất hiện sau đó thường thuộc tân ngữ, như "công cụ **phân tích** dữ liệu" hay "kỹ thuật **sử dụng** trong…", và không phải yêu cầu.

So sánh ba cách trên dữ liệu dev:

| LO | Động từ sớm nhất (hiện tại) | Cao nhất cả câu | Chuỗi đầu câu |
|---|---|---|---|
| L.O.1 "Hiểu biết và giải thích được các khái niệm, kỹ thuật sử dụng trong phân tích dữ liệu lớn" | Hiểu ✓ | Phân tích ✗ | Hiểu ✓ |
| L.O.2 "…quy trình các bước trong phân tích dữ liệu lớn" | Hiểu ✓ | Phân tích ✗ | Hiểu ✓ |
| L.O.3 "Giải thích, so sánh và lựa chọn được…" | Hiểu ✗ | Phân tích ✗ | Đánh giá ✓ |
| L.O.4.2 "…vận dụng các thư viện/công cụ phân tích dữ liệu…" | Vận dụng ✓ | Phân tích ✗ | Vận dụng ✓ |
| L.O.4.3 "…truyền dẫn dữ liệu và phân tích dữ liệu…" | Vận dụng ✓ | Phân tích ✗ | Vận dụng ✓ |

Phác thảo:

```python
def _head_chain(text: str, table, prefixes, sep: re.Pattern) -> tuple[list[tuple[str, str]], str, int]:
    s = _normalize(text)
    for p in prefixes:
        if s.startswith(p + " "):
            s = s[len(p) + 1:]
            break
    chain, i = [], 0
    while (m := _verb_at(s, i, table)) is not None:   # khớp dài nhất + ranh giới từ
        verb, level, i = m
        chain.append((verb, level))
        if (o := _RE_DUOC.match(s, i)):                 # bỏ "được"
            i = o.end()
        sp = sep.match(s, i)
        if not sp or _verb_at(s, sp.end(), table) is None:
            break
        i = sp.end()
    return chain, s, i   # i: vị trí kết thúc chuỗi, dùng cho cờ §3.4
```

`_infer_bloom` đổi thành `_infer_bloom(statement_vi, statement_en) -> BloomGuess(level, chain, flags)`. `_extract_los` lấy `level` để lưu và đẩy `flags` vào `ctx.add(...)` kèm `SourceRef` của LO.

### 3.2. Bảng động từ

**VI** (in đậm: thêm mới hoặc đổi mức):

| Mức | Động từ |
|---|---|
| 1 Nhớ | nhớ, **ghi nhớ**, **nhắc lại**, liệt kê, **nêu**, **kể tên**, định nghĩa, **nhận biết**, trình bày\*, mô tả\* |
| 2 Hiểu | hiểu, **hiểu biết**, **hiểu được**, **nắm được**, **nắm vững**, giải thích, tóm tắt, **diễn giải**, **minh họa**, **phân loại**\*, **so sánh**\* |
| 3 Vận dụng | áp dụng, vận dụng, **ứng dụng**, thực hiện, sử dụng\*, **cài đặt**, **viết**, **lập trình**, **tính**, **tính toán**, **giải**, **triển khai**, **kiểm thử**, giao tiếp\*, quản lý\* |
| 4 Phân tích | phân tích, **phân biệt**\* |
| 5 Đánh giá | đánh giá, nhận xét, phê bình, **lựa chọn**, **biện luận**, **thẩm định** |
| 6 Sáng tạo | thiết kế, xây dựng\*, đề xuất, tạo ra, **lập kế hoạch**, tổng hợp\*, **phát triển**\*, **sáng tạo** |

**EN:**

| Mức | Động từ |
|---|---|
| 1 | list, name, define, recall, state, identify, describe\*, present\* |
| 2 | understand, explain, summarize/summarise, interpret, illustrate, classify, compare |
| 3 | apply, use\*, implement, execute, write, calculate, solve, perform, communicate, manage |
| 4 | analyze/analyse, differentiate, distinguish |
| 5 | evaluate, assess, judge, select, choose, justify, critique |
| 6 | design, create, construct, propose, plan, build\*, formulate, synthesize, develop\* |

\* **Động từ đa nghĩa:** vẫn có mức mặc định, nhưng nếu mục tiêu của LO đến từ động từ này thì gắn cờ. Ví dụ "trình bày" và "mô tả" có thể là Nhớ (nhắc lại) hoặc Hiểu (diễn đạt bằng lời mình); "phát triển giải pháp" có thể là Vận dụng hoặc Sáng tạo.

**Cố ý không đưa vào bảng:**
- "xác định": nghĩa trải từ nhận ra (Nhớ) đến xác định nguyên nhân (Phân tích).
- "chọn" đứng một mình: dễ khớp nhầm, ví dụ "chọn lọc dữ liệu".

LO bắt đầu bằng những từ này sẽ ra `None` kèm cờ, thay vì ra một mức sai.

Bảng này cần được thống nhất với giảng viên hoặc quy định của khoa (§6).

### 3.3. Đối chiếu bản tiếng Anh

- Chạy chuỗi đầu câu cho cả VI và EN.
- VI không có động từ ở đầu nhưng EN có: dùng mức của EN và gắn cờ.
- Cả hai đều có nhưng mức khác nhau: giữ mức của VI (bản chính thức) và gắn cờ.

Bản EN ít bị lỗi cụm danh từ hơn, vì danh từ và động từ có dạng khác nhau ("analysis" khác "analyze"). Nhưng EN là bản dịch và có thể lệch nội dung: trong dữ liệu dev, L.O.3 bản VI ghi "kiến trúc", bản EN ghi "techniques". Vì vậy EN chỉ dùng để đối chiếu.

### 3.4. Cờ cho giảng viên

| Mã | Mức | Điều kiện | Ví dụ |
|---|---|---|---|
| `lo.bloom_unknown` | warning | VI và EN đều không có động từ ở đầu câu → `bloom_level = None` | "Có kiến thức về bộ nhớ ảo…", "Xác định yêu cầu…" |
| `lo.bloom_from_english` | info | VI không có động từ, mức lấy từ EN | — |
| `lo.bloom_vi_en_mismatch` | warning | Mức theo VI khác mức theo EN | — |
| `lo.bloom_ambiguous_verb` | info | Mục tiêu đến từ động từ có dấu \* | "Sử dụng công cụ…" |
| `lo.bloom_secondary_verb` | info | Sau chuỗi đầu câu có động từ mức cao hơn mục tiêu: VI chỉ xét sau "để"; EN xét sau "and", "to", "then" | L.O.4: "để phát triển", "and evaluate them" |
| `lo.bloom_parent_below_child` | warning | Mức của LO cha thấp hơn mức cao nhất của các LO con | L.O.3 = 2 < L.O.3.3 = 4 (hiện tại) |

Với cờ `secondary_verb`, bản VI chỉ xét sau "để" vì "và phân tích dữ liệu" trong tiếng Việt thường vẫn là cụm danh từ. Nếu xét cả "và", toàn bộ LO chứa "phân tích dữ liệu" của môn này sẽ bị gắn cờ.

Mục `lo.bloom_inferred` hiện có ([dcmh_extractor.py:820](../packages-ai/src/document_chunk/adapters/curriculum/dcmh_extractor.py#L820)) giữ nguyên.

### 3.5. Kết quả chạy thử nguyên mẫu

Nguyên mẫu là script độc lập: dùng bảng ở §3.2 và thuật toán ở §3.1, chạy trên 18 LO đọc từ DB dev (chỉ đọc) và các câu ở §2.2. Code trong repo chưa thay đổi.

**Dữ liệu dev:**

| LO | Hiện tại | Sau khi sửa | Cờ |
|---|---|---|---|
| L.O.3 | Hiểu | **Đánh giá** | — |
| L.O.3.3 | Phân tích | **Đánh giá** | — |
| L.O.4 | Vận dụng | Vận dụng | `secondary_verb`: phát triển, develop, evaluate |
| L.O.4.3 | Vận dụng | Vận dụng | `secondary_verb`: phát triển, develop |
| 14 LO còn lại | — | không đổi | — |

Sau khi sửa không còn cờ `parent_below_child`, vì L.O.3 và L.O.3.3 cùng ở mức 5.

**Câu tự dựng:**

| Câu | Hiện tại | Sau khi sửa |
|---|---|---|
| Viết truy vấn SQL đáp ứng yêu cầu nghiệp vụ | `None` | Vận dụng |
| Lựa chọn kiến trúc phù hợp cho bài toán | `None` | Đánh giá |
| Cài đặt và kiểm thử thuật toán sắp xếp | `None` | Vận dụng |
| Có kiến thức về bộ nhớ ảo và vận dụng vào quản lý tiến trình | Nhớ | `None` + `bloom_unknown` |
| Xác định yêu cầu của người sử dụng | Vận dụng | `None` + `bloom_unknown` |
| Lập kế hoạch dự án phần mềm | Vận dụng | Sáng tạo |
| Trình bày và phân tích các phương pháp xử lý dữ liệu | Nhớ | Phân tích |
| Sử dụng công cụ phân tích dữ liệu | Vận dụng | Vận dụng + `ambiguous_verb` |

**Giới hạn:**
- Chỉ có một môn với 18 LO. Đề cương này dùng động từ đơn giản, nên chưa đại diện cho các đề cương khác.
- "Đúng" ở đây là đánh giá theo cách đọc của tài liệu, chưa có nhãn của giảng viên.
- Trước khi nói về độ chính xác, cần một tập LO từ ít nhất hai môn, có giảng viên gán nhãn.

### 3.6. Test cần thêm

Thêm vào [test_dcmh_extractor.py](../packages-ai/tests/unit/test_dcmh_extractor.py):
- Test tham số hóa cho `_infer_bloom` với các câu ở §2.1 và §2.2: kiểm tra mức và danh sách cờ.
- Test `_extract_los` đẩy đúng mã cờ vào `issues`, bao gồm `parent_below_child`.
- Test hiện có `test_bloom_and_cdio_are_marked_as_system_suggestions` giữ nguyên, vì `provenance` vẫn là `inferred`.

## 4. Đề xuất giai đoạn 2: giảng viên xác nhận

Không cần đổi schema: `bloom_provenance` đã nhận giá trị `confirmed` ([curriculum.py:19](../packages-ai/src/document_chunk/domain/entities/curriculum.py#L19), [schema.prisma](../core-api/prisma/schema.prisma) `learning_outcomes`).

1. **API:** thêm `PATCH /api/learning-outcomes/:id` với body `{ bloom_level: 1..6 }`. Endpoint ghi `bloom_provenance = 'confirmed'`, dùng `BffJwtGuard` như `GET` hiện có ([learning-outcome.controller.ts](../core-api/src/curriculum/learning-outcome.controller.ts)) và kiểm tra người gọi là giảng viên của môn.
2. **Giao diện:** ở bảng LO trên `/manage/curriculum`:
   - đổi ô Bloom thành ô chọn;
   - phân biệt "đề xuất" với "đã xác nhận";
   - hiện cờ ở §3.4 ngay cạnh LO tương ứng, thay vì chỉ hiện trong khung chung.
3. **Import lại:** sửa upsert ở [postgres_curriculum_repository.py:367-368](../packages-ai/src/document_chunk/adapters/metadata/postgres_curriculum_repository.py#L367-L368) để không ghi đè giá trị đã xác nhận nếu nguyên văn LO không đổi:

   ```sql
   bloom_level = CASE
       WHEN learning_outcomes.bloom_provenance = 'confirmed'
        AND learning_outcomes.statement_vi = EXCLUDED.statement_vi
       THEN learning_outcomes.bloom_level ELSE EXCLUDED.bloom_level END,
   bloom_provenance = CASE
       WHEN learning_outcomes.bloom_provenance = 'confirmed'
        AND learning_outcomes.statement_vi = EXCLUDED.statement_vi
       THEN 'confirmed' ELSE EXCLUDED.bloom_provenance END,
   ```

   Khi nguyên văn LO đã đổi, giá trị xác nhận cũ không còn chắc đúng. Lúc đó quay về `inferred` để giảng viên xác nhận lại.

**Để sau:** lưu đủ các mức của một LO ghép, ví dụ `[2, 2, 5]` cho L.O.3. Hiện chưa có chỗ nào cần dữ liệu này; danh sách động từ đã nằm trong nội dung cờ. Chỉ thêm khi mastery cần tính theo từng hành vi.

## 5. Không làm

- **Không dùng embedding để gán Bloom.** Kolagar và cộng sự (2025) thử so độ tương đồng ngữ nghĩa giữa LO và mô tả mức Bloom, được weighted F1 0,50, thấp hơn regex (0,52). Xem [báo cáo nghiên cứu](bao-cao-nghien-cuu-lo-bloom.md) §4.2.
- **Không dùng LLM ở bước import, ít nhất là ở giai đoạn này.** Mỗi môn chỉ vài chục LO, nên giảng viên xác nhận rẻ hơn và chắc hơn. LLM có thể thêm sau để giải thích các LO bị gắn cờ, nhưng không tự quyết định mức.
- **Không sửa nguyên văn LO.** Cờ chỉ đề nghị giảng viên xem lại.
- **Không đụng đến Bloom của câu hỏi.** Việc kiểm tra câu sinh ra có đúng mức hay không là một việc riêng.

## 6. Câu hỏi mở

1. Bảng động từ theo Krathwohl hay theo quy định của khoa/trường? Cần chốt cho các động từ có dấu \*, nhất là "trình bày", "mô tả", "phân biệt", "phát triển".
2. Mục tiêu của LO cha lấy bằng mức cao nhất của các LO con, hay giảng viên đặt riêng?
3. LO dạng "Có kiến thức về X" không có động từ hành vi. Nên mặc định mức Hiểu kèm cờ, hay để `None`?
4. Khi LO có Bloom là `None`, composer ở chế độ "auto" có nên buộc giảng viên chọn mức thay vì lặng lẽ dùng Hiểu?
