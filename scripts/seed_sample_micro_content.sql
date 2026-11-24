DO $$
DECLARE
    v_course_id UUID := '01a1f94a-71e6-7c70-97a8-eade510d71d2';
    v_user_id UUID := '01a1f94a-71d0-743d-a8e5-74c456b01f70';
    v_lo_id UUID;
    v_doc_id UUID;
    v_mc_id UUID;
    v_script JSONB;
BEGIN
    -- 1. Tạo Learning Outcome LO.3.2 nếu chưa có
    INSERT INTO learning_outcomes (
        code, statement_vi, statement_en, bloom_level, cdio_level, academic_year, version, is_current, course_id
    ) VALUES (
        'LO.3.2',
        'Minh họa cách các thuật toán sắp xếp hoạt động trên mảng dữ liệu (Illustrate how sorting algorithms work on an array)',
        'Illustrate how sorting algorithms work on an array',
        3,
        'II',
        '2025-2026',
        1,
        true,
        v_course_id
    )
    ON CONFLICT (course_id, code, academic_year, version) DO UPDATE SET statement_vi = EXCLUDED.statement_vi
    RETURNING lo_id INTO v_lo_id;

    -- 2. Tạo tài liệu Document Slide Sorting
    INSERT INTO documents (
        course_id, title, file_path, mime_type, status, created_by, source, role
    ) VALUES (
        v_course_id,
        'Sorting algorithms (Data Structures and Algorithms)',
        'courses/CO2003/slides/sorting_algorithms.pdf',
        'application/pdf',
        'INDEXED',
        v_user_id,
        'upload',
        'lecture'
    )
    RETURNING document_id INTO v_doc_id;

    -- 3. Chuẩn bị kịch bản AI (ai_script)
    v_script := '{
        "scenes": [
            {
                "slide_page": 10,
                "title": "Nguyên lý chèn trực tiếp (Straight Insertion Sort)",
                "bullets": [
                    "Danh sách chia thành 2 phần: đã sắp xếp (sorted) và chưa sắp xếp (unsorted)",
                    "Mỗi lượt duyệt: lấy phần tử đầu của phần chưa sắp chèn vào đúng vị trí phần đã sắp"
                ],
                "narration": "Thuật toán sắp xếp chèn trực tiếp hoạt động dựa trên nguyên lý chia danh sách làm hai phần: phần đã sắp xếp và phần chưa sắp xếp. Tại mỗi bước lặp, phần tử đầu tiên của phần chưa sắp xếp sẽ được chọn và chèn vào vị trí thích hợp trong phần đã sắp xếp."
            },
            {
                "slide_page": 11,
                "title": "Minh họa từng bước trên mảng dữ liệu",
                "bullets": [
                    "Mảng đầu vào mẫu: [23, 78, 45, 8, 32, 56]",
                    "Vách ngăn phân cách di chuyển dần từ trái sang phải"
                ],
                "narration": "Hãy quan sát mảng ví dụ gồm các số: hai mươi ba, bảy mươi tám, bốn mươi lăm, tám, ba mươi hai và năm mươi sáu. Ban đầu, phần tử đầu tiên được xem là đã sắp xếp. Các phần tử kế tiếp lần lượt được so sánh để dời chỗ và chèn vào đúng thứ tự."
            },
            {
                "slide_page": 17,
                "title": "Giải thuật và Mã giả InsertionSort()",
                "bullets": [
                    "Vòng lặp ngoài: duyệt current từ 1 đến count - 1",
                    "Vòng lặp trong: dời các phần tử lớn hơn temp sang phải một vị trí",
                    "Gán data[walker + 1] = temp"
                ],
                "narration": "Về mặt thuật toán, vòng lặp ngoài duyệt biến current từ vị trí một đến cuối mảng. Giá trị cần chèn được lưu tạm vào biến temp, trong khi biến walker lùi dần để dời các phần tử lớn hơn temp sang phải, và cuối cùng đặt temp vào vị trí thích hợp."
            },
            {
                "slide_page": 27,
                "title": "Độ phức tạp tính toán của thuật toán",
                "bullets": [
                    "Tổng số phép so sánh tối đa: f(n) = n(n + 1)/2",
                    "Độ phức tạp thời gian trường hợp xấu nhất: O(n^2)"
                ],
                "narration": "Hiệu năng của thuật toán được đo bằng tổng số phép so sánh và số lần di chuyển. Trong trường hợp xấu nhất, hàm f của n bằng n nhân n cộng một chia hai, tương ứng với độ phức tạp thời gian cấp O n bình phương."
            }
        ]
    }'::jsonb;

    -- 4. Tạo Micro-Content
    INSERT INTO micro_contents (
        course_id, title, description, video_source, video_status, passing_score, required_watch_percent,
        status, created_by, source_document_id, source_page_from, source_page_to, lo_id, position,
        script_status, ai_script
    ) VALUES (
        v_course_id,
        'Thuật toán sắp xếp chèn trực tiếp (Straight Insertion Sort)',
        'Bài học vi mô giải thích nguyên lý chia 2 phần mảng, mã giả walker/temp và độ phức tạp O(n^2) bám sát slide 10-17.',
        'AI',
        'READY',
        70,
        90,
        'PUBLISHED',
        v_user_id,
        v_doc_id,
        10,
        17,
        v_lo_id,
        1,
        'READY',
        v_script
    )
    RETURNING micro_content_id INTO v_mc_id;

    -- 5. Tạo 2 câu hỏi củng cố (Micro-Quiz) gắn liền với bài
    INSERT INTO micro_content_questions (
        micro_content_id, position, type, question, options, correct_answer, explanation
    ) VALUES (
        v_mc_id,
        1,
        'MCQ_SINGLE',
        'Trong thuật toán Straight Insertion Sort (sắp xếp chèn trực tiếp), danh sách được chia thành hai phần nào?',
        '[
            {"key": "A", "text": "Phần số chẵn và phần số lẻ"},
            {"key": "B", "text": "Phần đã sắp xếp (sorted) và phần chưa sắp xếp (unsorted)"},
            {"key": "C", "text": "Phần nửa đầu (lowlist) và phần nửa sau (highlist)"},
            {"key": "D", "text": "Phần chứa Pivot và phần không chứa Pivot"}
        ]'::jsonb,
        '"B"'::jsonb,
        'Theo slide 10, nguyên lý cơ bản của Straight Insertion Sort là: The list is divided into two parts: sorted and unsorted.'
    );

    INSERT INTO micro_content_questions (
        micro_content_id, position, type, question, options, correct_answer, explanation
    ) VALUES (
        v_mc_id,
        2,
        'MCQ_SINGLE',
        'Độ phức tạp thời gian trong trường hợp xấu nhất của thuật toán Straight Insertion Sort là bao nhiêu?',
        '[
            {"key": "A", "text": "O(log n)"},
            {"key": "B", "text": "O(n)"},
            {"key": "C", "text": "O(n log n)"},
            {"key": "D", "text": "O(n^2)"}
        ]'::jsonb,
        '"D"'::jsonb,
        'Theo slide 27, Straight insertion sort có hàm số so sánh f(n) = n(n + 1)/2 = O(n^2).'
    );

    RAISE NOTICE 'Đã tạo thành công MicroContent ID: %, LO ID: %, Document ID: %', v_mc_id, v_lo_id, v_doc_id;
END $$;
