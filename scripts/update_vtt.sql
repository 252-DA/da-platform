
    UPDATE video_assets
    SET vtt_subtitles_key = 'micro-content/01a1f94a-71e6-7c70-97a8-eade510d71d2/01a1f973-bf91-741d-9a96-d086704166a8/ai-hybrid-pilot.vtt',
        transcript_text = $transcript$[Cảnh 1] Nguyên lý chèn trực tiếp (Straight Insertion Sort): Thuật toán sắp xếp chèn trực tiếp hoạt động dựa trên nguyên lý chia danh sách làm hai phần: phần đã sắp xếp và phần chưa sắp xếp. Tại mỗi bước lặp, phần tử đầu tiên của phần chưa sắp xếp sẽ được chọn và chèn vào vị trí thích hợp trong phần đã sắp xếp.

[Cảnh 2] Minh họa từng bước trên mảng dữ liệu (Full 5-Pass Trace): Hãy quan sát mảng ví dụ gồm các số: hai mươi ba, bảy mươi tám, bốn mươi lăm, tám, ba mươi hai và năm mươi sáu. Ban đầu, phần tử đầu tiên được xem là đã sắp xếp. Các phần tử kế tiếp lần lượt được so sánh để dời chỗ và chèn vào đúng thứ tự. Quá trình tiếp tục tương tự cho các phần tử tám, ba mươi hai và năm mươi sáu, cho đến khi toàn bộ mảng được sắp xếp hoàn chỉnh theo thứ tự tăng dần.

[Cảnh 3] Giải thuật và Mã giả InsertionSort(): Về mặt thuật toán, vòng lặp ngoài duyệt biến current từ vị trí một đến cuối mảng. Giá trị cần chèn được lưu tạm vào biến temp, trong khi biến walker lùi dần để dời các phần tử lớn hơn temp sang phải, và cuối cùng đặt temp vào vị trí thích hợp.

[Cảnh 4] Độ phức tạp tính toán của thuật toán: Hiệu năng của thuật toán được đo bằng tổng số phép so sánh và số lần di chuyển. Trong trường hợp xấu nhất, hàm f của n bằng n nhân n cộng một chia hai, tương ứng với độ phức tạp thời gian cấp O n bình phương.$transcript$,
        scene_timeline = '[{"scene_index": 0, "title": "Nguy\u00ean l\u00fd ch\u00e8n tr\u1ef1c ti\u1ebfp (Straight Insertion Sort)", "start_ms": 0, "end_ms": 15040, "duration_ms": 15040, "slide_page": 10}, {"scene_index": 1, "title": "Minh h\u1ecda t\u1eebng b\u01b0\u1edbc tr\u00ean m\u1ea3ng d\u1eef li\u1ec7u (Full 5-Pass Trace)", "start_ms": 15040, "end_ms": 40520, "duration_ms": 25480, "slide_page": 11}, {"scene_index": 2, "title": "Gi\u1ea3i thu\u1eadt v\u00e0 M\u00e3 gi\u1ea3 InsertionSort()", "start_ms": 40520, "end_ms": 55680, "duration_ms": 15160, "slide_page": 17}, {"scene_index": 3, "title": "\u0110\u1ed9 ph\u1ee9c t\u1ea1p t\u00ednh to\u00e1n c\u1ee7a thu\u1eadt to\u00e1n", "start_ms": 55680, "end_ms": 69840, "duration_ms": 14160, "slide_page": 27}]'::jsonb
    WHERE asset_id = '01a20898-59ea-7341-946c-521264ed931b';
    