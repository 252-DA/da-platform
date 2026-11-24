SET client_encoding = 'UTF8';

DO $$
DECLARE
    v_mc_id UUID := '01a1f973-bf91-741d-9a96-d086704166a8';
    v_lo_id UUID := '01a1f973-bf6a-7966-b446-99bd4e92f993';
    v_doc_id UUID := '01a1f973-bf7f-7bf2-920b-ff10691f715e';
    v_script JSONB;
BEGIN
    -- 1. Cập nhật Learning Outcome chuẩn UTF-8
    UPDATE learning_outcomes
    SET statement_vi = 'Minh họa cách các thuật toán sắp xếp hoạt động trên mảng dữ liệu (Illustrate how sorting algorithms work on an array)'
    WHERE lo_id = v_lo_id;

    -- 2. Cập nhật Document Title chuẩn UTF-8
    UPDATE documents
    SET title = 'Sorting algorithms (Data Structures and Algorithms)'
    WHERE document_id = v_doc_id;

    -- 3. Chuẩn bị Kịch bản ai_script chuẩn UTF-8
    v_script := '{
        "voice": "vi-VN-HoaiMyNeural",
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

    -- 4. Cập nhật Micro Content: sửa tiêu đề, mô tả, ai_script và đặt video_status = 'NONE'
    UPDATE micro_contents
    SET
        title = 'Thuật toán sắp xếp chèn trực tiếp (Straight Insertion Sort)',
        description = 'Bài học vi mô giải thích nguyên lý chia 2 phần mảng, mã giả walker/temp và độ phức tạp O(n^2) bám sát slide 10-17.',
        video_status = 'NONE',
        video_source = 'AI',
        video_object_key = NULL,
        video_duration_ms = NULL,
        video_size_bytes = NULL,
        script_status = 'READY',
        ai_script = v_script,
        status = 'PUBLISHED'
    WHERE micro_content_id = v_mc_id;

    -- 5. Xóa câu hỏi cũ bị lỗi font và tạo lại chuẩn UTF-8
    DELETE FROM micro_content_questions WHERE micro_content_id = v_mc_id;

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

    RAISE NOTICE 'Đã cập nhật hoàn tất UTF-8 và đặt video_status = NONE cho MicroContent ID: %', v_mc_id;
END $$;
