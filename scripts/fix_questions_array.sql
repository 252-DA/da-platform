-- Cập nhật định dạng chuẩn chuỗi (array of strings) cho micro_content_questions
-- Bài học: Straight Insertion Sort (micro_content_id = '01a1f973-bf91-741d-9a96-d086704166a8')

DO $$
DECLARE
    v_mc_id uuid := '01a1f973-bf91-741d-9a96-d086704166a8';
BEGIN
    DELETE FROM micro_content_questions WHERE micro_content_id = v_mc_id;

    -- Câu 1 (Remember):
    INSERT INTO micro_content_questions (
        micro_content_id, position, type, question, options, correct_answer, explanation
    ) VALUES (
        v_mc_id,
        1,
        'MCQ_SINGLE',
        'Trong thuật toán Straight Insertion Sort (sắp xếp chèn trực tiếp), danh sách được chia thành hai phần nào?',
        '[
            "Phần số chẵn và phần số lẻ",
            "Phần đã sắp xếp (sorted) và phần chưa sắp xếp (unsorted)",
            "Phần nửa đầu (lowlist) và phần nửa sau (highlist)",
            "Phần chứa Pivot và phần không chứa Pivot"
        ]'::jsonb,
        '"Phần đã sắp xếp (sorted) và phần chưa sắp xếp (unsorted)"'::jsonb,
        'Theo slide 10, nguyên lý cơ bản của Straight Insertion Sort là chia danh sách thành 2 phần: sorted và unsorted. Tại mỗi bước lặp, phần tử đầu tiên của phần chưa sắp xếp sẽ được chèn vào vị trí thích hợp trong phần đã sắp xếp.'
    );

    -- Câu 2 (Remember):
    INSERT INTO micro_content_questions (
        micro_content_id, position, type, question, options, correct_answer, explanation
    ) VALUES (
        v_mc_id,
        2,
        'MCQ_SINGLE',
        'Độ phức tạp thời gian trong trường hợp xấu nhất của thuật toán Straight Insertion Sort là bao nhiêu?',
        '[
            "O(log n)",
            "O(n)",
            "O(n log n)",
            "O(n^2)"
        ]'::jsonb,
        '"O(n^2)"'::jsonb,
        'Theo slide 27, Straight insertion sort có số phép so sánh tối đa là f(n) = n(n + 1)/2 tương ứng với cấp độ phức tạp O(n^2).'
    );

    -- Câu 3 (Understand - Multimodal trace):
    INSERT INTO micro_content_questions (
        micro_content_id, position, type, question, options, correct_answer, explanation
    ) VALUES (
        v_mc_id,
        3,
        'MCQ_SINGLE',
        'Cho mảng ban đầu [23, 78, 45, 8, 32, 56]. Sau khi biến current = 2 hoàn thành vòng lặp ngoài (chèn xong phần tử 45), trạng thái mảng là gì?',
        '[
            "[23, 45, 78, 8, 32, 56]",
            "[23, 78, 45, 8, 32, 56]",
            "[8, 23, 45, 78, 32, 56]",
            "[45, 23, 78, 8, 32, 56]"
        ]'::jsonb,
        '"[23, 45, 78, 8, 32, 56]"'::jsonb,
        'Sau 2 lượt lặp ngoài, phần tử 45 được chèn vào giữa 23 và 78 (sau khi 78 đã dời sang phải), tạo thành mảng con đã sắp [23, 45, 78], các phần tử còn lại chưa xét giữ nguyên.'
    );

    -- Câu 4 (Apply - Pseudocode logic):
    INSERT INTO micro_content_questions (
        micro_content_id, position, type, question, options, correct_answer, explanation
    ) VALUES (
        v_mc_id,
        4,
        'MCQ_SINGLE',
        'Trong hàm InsertionSort, khi biến temp nhỏ hơn toàn bộ các phần tử trong phần đã sắp xếp, điều kiện nào sẽ làm dừng vòng lặp while (walker >= 0 && data[walker] > temp)?',
        '[
            "Biến walker giảm về giá trị -1, làm sai điều kiện walker >= 0",
            "Biến walker dừng tại giá trị 0 do gặp phần tử bằng với temp",
            "Vòng lặp gặp lệnh ngắt cưỡng bức break",
            "Biến current chạm đến chỉ số cuối cùng của mảng"
        ]'::jsonb,
        '"Biến walker giảm về giá trị -1, làm sai điều kiện walker >= 0"'::jsonb,
        'Khi temp nhỏ hơn tất cả phần tử bên trái, biến walker sẽ lùi dần qua index 0 và trở thành -1. Điều kiện walker >= 0 trở thành false, vòng lặp kết thúc và data[walker+1] tức data[0] được gán bằng temp.'
    );

    RAISE NOTICE 'Đã cập nhật thành công 4 câu hỏi trắc nghiệm định dạng chuỗi chuẩn cho bài %', v_mc_id;
END $$;
