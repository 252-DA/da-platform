UPDATE micro_contents
SET video_duration_ms = 69867,
    video_size_bytes = 2497331,
    ai_script = jsonb_set(
        ai_script,
        '{scenes,1,narration}',
        to_jsonb('Hãy quan sát mảng ví dụ gồm các số: hai mươi ba, bảy mươi tám, bốn mươi lăm, tám, ba mươi hai và năm mươi sáu. Ban đầu, phần tử đầu tiên được xem là đã sắp xếp. Các phần tử kế tiếp lần lượt được so sánh để dời chỗ và chèn vào đúng thứ tự. Quá trình tiếp tục tương tự cho các phần tử tám, ba mươi hai và năm mươi sáu, cho đến khi toàn bộ mảng được sắp xếp hoàn chỉnh theo thứ tự tăng dần.'::text)
    )
WHERE micro_content_id = '01a1f973-bf91-741d-9a96-d086704166a8';

UPDATE video_assets
SET duration_ms = 69867,
    size_bytes = 2497331,
    ai_script = jsonb_set(
        ai_script,
        '{scenes,1,narration}',
        to_jsonb('Hãy quan sát mảng ví dụ gồm các số: hai mươi ba, bảy mươi tám, bốn mươi lăm, tám, ba mươi hai và năm mươi sáu. Ban đầu, phần tử đầu tiên được xem là đã sắp xếp. Các phần tử kế tiếp lần lượt được so sánh để dời chỗ và chèn vào đúng thứ tự. Quá trình tiếp tục tương tự cho các phần tử tám, ba mươi hai và năm mươi sáu, cho đến khi toàn bộ mảng được sắp xếp hoàn chỉnh theo thứ tự tăng dần.'::text)
    ),
    scene_timeline = '[
        {"scene_index": 0, "title": "Nguyên lý chèn trực tiếp (Straight Insertion Sort)", "slide_page": 10, "start_ms": 0, "end_ms": 15040, "duration_ms": 15040},
        {"scene_index": 1, "title": "Minh họa từng bước trên mảng dữ liệu (Full 5-Pass Trace)", "slide_page": 11, "start_ms": 15040, "end_ms": 40520, "duration_ms": 25480},
        {"scene_index": 2, "title": "Giải thuật và Mã giả InsertionSort()", "slide_page": 17, "start_ms": 40520, "end_ms": 55680, "duration_ms": 15160},
        {"scene_index": 3, "title": "Độ phức tạp tính toán của thuật toán", "slide_page": 27, "start_ms": 55680, "end_ms": 69840, "duration_ms": 14160}
    ]'::jsonb
WHERE asset_id = '01a20898-59ea-7341-946c-521264ed931b';
