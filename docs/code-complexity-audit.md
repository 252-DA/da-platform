**Rà soát độ phức tạp code — 29/09/2026**

Mục đích: ghi lại những chỗ khó đọc, trùng logic, khó thay đổi hoặc có rủi ro vận hành để làm backlog tối ưu. Đây là rà soát tĩnh các luồng chính, chưa chạy benchmark, kiểm thử tải hay E2E; các tác động hiệu năng dưới đây là suy luận từ đường đi của code. Không thay đổi source code.

Mốc HEAD đối chiếu: root `80714d1`; core-api `3c71268`; web `17f9349`; worker `1f8da00`; packages-ai `8491fdc`. Rà soát dựa trên working tree lúc đọc; trong thời gian rà soát có thay đổi song song ở luồng xem tài liệu, nên số dòng có thể dịch chuyển so với HEAD hoặc các chỉnh sửa tiếp theo. Số dòng gồm cả comment và dòng trống. Không dùng độ dài file làm tiêu chí duy nhất; mã sinh tự động không nằm trong danh sách refactor.

Phạm vi đọc sâu: soạn/sinh/duyệt/làm quiz, BFF–Core API, worker, truy xuất ngữ cảnh, metadata, LTI launch, đồng bộ Canvas và các entrypoint cũ. Đây không phải kiểm toán toàn bộ repository.

P1 = ưu tiên sớm vì có đường lỗi hoặc cản trở vận hành cụ thể; P2 = giảm chi phí bảo trì khi sửa tính năng; P3 = dọn sau khi hoàn tất migration.

| ID | Mức | Điểm cần xử lý | Lợi ích chính |
| --- | --- | --- | --- |
| R01 | P1 | Worker async chạy tác vụ đồng bộ trực tiếp | Giữ event loop hoạt động khi chờ model/DB |
| R02 | P1 | Sinh/duyệt nhiều câu bằng vòng lặp ở BFF | Tránh kết quả một phần nhưng báo lỗi chung |
| R03 | P1 | Retry, chống trùng và xử lý request treo phân tán | Không sinh lại cả mẻ chỉ vì lỗi ghi trạng thái |
| R04 | P2 | gRPC bọc JSON, kiểu dữ liệu khai báo thủ công | Phát hiện lệch contract sớm |
| R05 | P2 | Hai giao diện soạn quiz và API lặp logic | Sửa hành vi chung tại một chỗ |
| R06 | P2 | QuizSetService ôm nhiều nghiệp vụ | Tách vòng đời đề, lượt thi và báo cáo |
| R07 | P2 | Use case sinh quiz trộn retrieval/model/policy/persistence | Làm rõ chất lượng nguồn và kết quả kiểm chứng |
| R08 | P2 | Metadata port rộng và repository nhiều trách nhiệm | Thu hẹp phụ thuộc của từng use case |
| R09 | P2 | LTI launch gom xác thực, tương thích LMS và session | Giảm tác động dây chuyền khi sửa đăng nhập |
| R10 | P1 | Thay tài liệu Canvas qua nhiều bước ghi rời rạc | Giảm khoảng trống khi thay phiên bản bị lỗi |
| R11 | P2 | Trạng thái tài liệu và alias cũ khó lần theo | Làm rõ tài liệu đã hoàn thành bước nào |
| R12 | P3 | Bề mặt legacy và wiring trùng còn tồn tại | Giảm số đường chạy phải bảo trì |

**R01 — Worker async nhưng công việc thực tế chặn event loop**

- Bằng chứng: [content_generation_worker.py:153,179](../worker/worker/runners/content_generation_worker.py) và [enrichment_worker.py:28,42](../worker/worker/runners/enrichment_worker.py) khai báo `_process_job` là `async`, nhưng cả hai hàm không có `await` và gọi use case đồng bộ trực tiếp. Đường model cũng đồng bộ, ví dụ [openai_compatible.py:34,44](../ai-sdk/src/ai_runtime/providers/openai_compatible.py).
- Hệ quả: trong lúc chờ LLM/DB, event loop của process không chạy được công việc khác; tăng `concurrency` không tự giải quyết điều này. Có rủi ro làm chậm các tác vụ nền của queue; chưa đo mức chậm hoặc tái hiện mất lock.
- Hướng xử lý: đưa khối xử lý đồng bộ sang executor/thread có giới hạn, hoặc chuyển đường I/O sang async. Có mẫu sẵn trong [document_worker.py:151](../worker/worker/runners/document_worker.py), dùng `asyncio.to_thread`. Kiểm tra việc dùng chung client/container giữa các thread trước khi tăng song song.
- Kiểm chứng khi sửa: một job chờ model lâu không chặn heartbeat/timer và job độc lập khác; giới hạn số tác vụ đồng thời vẫn được giữ.

**R02 — BFF điều phối batch bằng vòng lặp, dễ thành công một phần**

- Bằng chứng: [quiz-builder/route.ts:78–118,143–151](../web/src/app/api/quiz-builder/route.ts) vừa kiểm tra từng ô ma trận vừa gọi `createContentGenerationRequest` trong vòng lặp. [deep-link/route.ts:90–112,114–128](../web/src/app/api/lti/deep-link/route.ts) cũng tạo/duyệt từng phần tử bằng các lời gọi tuần tự.
- Tình huống: ô đầu hợp lệ đã tạo request; ô sau có LO/count không hợp lệ, hoặc RPC lỗi, thì API trả lỗi chung dù request trước vẫn tồn tại. Duyệt hàng loạt có cùng vấn đề nếu lỗi ở giữa. Mỗi phần tử còn thêm một lượt BFF→Core API và các truy vấn riêng.
- Hướng xử lý: thêm lệnh batch tại Core API; validate toàn bộ đầu vào trước khi ghi. Tạo request và outbox trong một transaction cho cả batch, hoặc định nghĩa rõ kết quả thành công/thất bại từng phần tử. Thêm batch ID để retry không tạo lại phần đã nhận. Duyệt nhiều câu có thể ghi trạng thái và audit log trong cùng transaction.
- Kiểm chứng khi sửa: phần tử thứ hai hỏng không để lại kết quả mơ hồ; gửi lại cùng batch ID không nhân đôi job.

**R03 — Vòng đời request sinh quiz bị chia giữa BFF, worker và nội dung câu hỏi**

- Bằng chứng: [quiz.ts:81–128](../web/src/lib/quiz.ts) coi request `QUEUED/RUNNING` quá 15 phút là không còn chặn, nhưng không đổi trạng thái trong DB. [content_generation_worker.py:171–196](../worker/worker/runners/content_generation_worker.py) ghi `RUNNING`, chạy sinh/lưu quiz, rồi mới ghi `SUCCEEDED`. [generate_curriculum_quiz.py:293–296](../worker/worker/use_cases/generate_curriculum_quiz.py) tạo ID theo `(LO, nội dung câu hỏi)`.
- Hệ quả: nếu đã lưu câu hỏi nhưng ghi `SUCCEEDED` thất bại, retry chạy lại model. ID tất định chỉ chống trùng khi nội dung được sinh lại giống nhau; model trả nội dung khác vẫn tạo ID khác. Ngưỡng 15 phút mở đường cho yêu cầu mới trong khi job cũ có thể vẫn chạy. Đây là đường rủi ro suy ra từ code, chưa tái hiện bằng fault injection.
- Hướng xử lý: lưu kết quả/checkpoint gắn với `request_id`; hoàn tất nội dung và trạng thái theo transaction hoặc bước phục hồi rõ ràng. Quản lý lease/heartbeat, timeout và retry ở backend; UI chỉ hiển thị trạng thái do backend quyết định.
- Kiểm chứng khi sửa: giả lập lỗi sau khi lưu quiz nhưng trước khi hoàn tất request; retry không gọi lại model và không tạo thêm mẻ. Phân biệt job chạy lâu với job không còn worker xử lý.

**R04 — Contract gRPC chỉ là chuỗi JSON**

- Bằng chứng: [core_api.proto:7–12](../contracts/proto/core_api.proto) định nghĩa `JsonRequest`/`JsonResponse` với `string json`. [grpc-server.service.ts:188–216](../core-api/src/grpc/grpc-server.service.ts) dùng `TBody = any` rồi `JSON.parse(...) as TBody`; [core-api.ts:112–142](../web/src/lib/core-api.ts) cũng ép response thành generic do caller chọn.
- Hệ quả: đổi tên hoặc kiểu field không được compiler kiểm tra xuyên biên dịch vụ; các bên tự viết types, validation và mapping lỗi. Generic ở client không xác thực response lúc chạy.
- Hướng xử lý: chọn một nguồn contract chung. Có thể giữ JSON trước mắt và bổ sung schema kiểm tra runtime cùng type sinh ra; hoặc chuyển dần những RPC quan trọng sang protobuf message có field cụ thể. Không cần đổi transport toàn bộ hệ thống trong một lần.
- Kiểm chứng khi sửa: contract test cho payload sai kiểu/thiếu field và response giữa web–core-api; kiểm tra tương thích trong giai đoạn nâng phiên bản từng service.

**R05 — Hai màn soạn quiz và hai API lặp hành vi chung**

- Bằng chứng: [quiz-builder.tsx:82](../web/src/app/manage/quizzes/new/quiz-builder.tsx) dài 778 dòng, có 17 khai báo `useState`; [quiz-composer.tsx:84](../web/src/app/lti/deep-link/quiz-composer.tsx) dài 585 dòng, có 13. Cả hai tự giữ selected/pending/notice, polling, approve/reject/edit và refresh. Các handler `keep`, `keepMany`, `discard`, `save` lặp cấu trúc.
- API cũng lặp `hasValidAnswer`, validate bốn phương án và xử lý `approveMany`: [quiz-builder/route.ts:57,143,162](../web/src/app/api/quiz-builder/route.ts), [deep-link/route.ts:20,114,141](../web/src/app/api/lti/deep-link/route.ts). Trong khi đó [review.service.ts:118,158](../core-api/src/review/review.service.ts) ghi duyệt/sửa nhưng chưa kiểm tra cùng các ràng buộc đáp án này. Các đường gọi khác phải tự nhớ áp dụng quy tắc.
- Hệ quả: sửa cùng một hành vi phải sửa nhiều nơi; dễ lệch validation, cách xóa lựa chọn sau khi sửa, hoặc xử lý request hoàn tất. UI chứa đồng thời trạng thái workflow và phần render dài.
- Hướng xử lý: giữ phần ma trận nhiều chương và modal Canvas riêng; gom hành vi review/selection/polling vào hook hoặc reducer dùng chung. Đưa ràng buộc nghiệp vụ cuối cùng về Core API; frontend giữ validation phục vụ phản hồi nhanh. `QuestionPicker` và `QuizSettingsBar` đã được dùng chung, có thể tiếp tục theo hướng đó.
- Kiểm chứng khi sửa: approve/reject/edit, đổi chương khi đang tải và chọn nhiều câu cho cả hai entrypoint.

**R06 — QuizSetService có quá nhiều lý do để thay đổi**

- Bằng chứng: [quiz-set.service.ts](../core-api/src/quiz/quiz-set.service.ts) dài 814 dòng; `context` ở 78, `builderContext` ở 194, `create` ở 268, `start` ở 501, `results` ở 564 và `submit` ở 679. Cùng service xử lý Canvas/chương/LO, snapshot đề, phiên thi, quyền xem đáp án, chấm điểm, lịch sử và dữ liệu liên quan AGS.
- Hệ quả: thay đổi quy tắc thi hoặc soạn đề phải đọc chung một lớp lớn; logic đọc và ghi, giao tiếp Canvas và transaction thi bị đan xen.
- Hướng xử lý: tách truy vấn context, tạo snapshot, vòng đời attempt/session và truy vấn báo cáo theo nghiệp vụ. Giữ transaction đóng session + ghi bài ở cùng một ranh giới. Đã có `quiz-set-exam.ts` và `quiz-set-results.ts`; tận dụng những phần tách sẵn này thay vì viết lại.
- Kiểm chứng khi sửa: giữ các kiểm thử nộp hai lần, hết giờ, giới hạn lượt, thời điểm mở đáp án và phạm vi khóa học.

**R07 — Sinh quiz trộn nhiều bước và có chính sách fallback khó nhìn thấy**

- Bằng chứng: [generate_curriculum_quiz.py](../worker/worker/use_cases/generate_curriculum_quiz.py) dài 755 dòng; riêng `execute` từ 159–350. File chứa schema output, resolve LO, retrieval, prompt, gọi writer/judge, sinh lại câu, usage logging, xáo đáp án, tạo ID và lưu DB. [run_enrichment.py](../worker/worker/use_cases/run_enrichment.py) còn lặp schema MCQ và bộ cộng usage tương tự.
- Retrieval có hai đường: `_load_context` ở 352 bỏ MCP khi có `source_document_ids`; nhánh local lấy tối đa năm chunk và cắt 1.200 ký tự/chunk. [retrieve_quiz_context.py:120,154](../packages-ai/src/document_chunk/application/use_cases/retrieve_quiz_context.py) có bước xếp hạng ngữ nghĩa và giới hạn riêng. Vì vậy chọn nguồn tường minh còn thay đổi cả chiến lược retrieval. Đổi cấu hình/source scope có thể đổi chất lượng ngữ cảnh, không chỉ vị trí gọi.
- Chính sách kiểm chứng cũng cần làm rõ: docstring ở 535–537 nói verifier lỗi không phải lý do giữ câu, nhưng nhánh 550–551 trả toàn bộ câu khi verifier trả `None`. [test_generate_curriculum_quiz.py:463](../worker/tests/unit/test_generate_curriculum_quiz.py) chủ động yêu cầu vẫn lưu cho người duyệt. Đây là mâu thuẫn giữa comment với hành vi đã được test ghi nhận, không đủ cơ sở kết luận hành vi đó trái yêu cầu sản phẩm.
- Hướng xử lý: tách context provider, sinh/kiểm chứng câu, chuẩn hóa output và persistence. Chuẩn hóa hợp đồng retrieval có filter nguồn; biểu diễn kết quả kiểm chứng bằng trạng thái riêng cho đạt/không đạt/không kết luận được, thay vì dùng `None` mang chính sách ngầm. Chốt lại comment và hành vi khi verifier hỏng.
- Kiểm chứng khi sửa: lọc nguồn không lẫn chương, phân biệt verifier lỗi với câu bị bác bỏ, giữ câu đã được người dùng duyệt khi retry.

**R08 — Metadata port rộng; tách file repository chưa tách được phụ thuộc**

- Bằng chứng: [metadata_store.py:273](../packages-ai/src/document_chunk/domain/ports/metadata_store.py) có 30 method trong `IMetadataStore`, bao gồm tài liệu/chunk/curriculum/card/quiz/outbox/job status/LLM usage. [postgres_metadata_store.py:36–45](../packages-ai/src/document_chunk/adapters/metadata/postgres_metadata_store.py) kế thừa bảy repository cùng interface này.
- [postgres_curriculum_repository.py](../packages-ai/src/document_chunk/adapters/metadata/postgres_curriculum_repository.py) dài 841 dòng; `upsert_curriculum` từ 135–441 vừa ghi course/chapter/LO/assessment, vừa ghi liên kết/goals/sessions/issues. File còn chứa lưu quiz và cập nhật request sinh nội dung.
- Hệ quả: use case cần đọc vài chunk vẫn phụ thuộc một hợp đồng lớn. Thêm method kéo theo adapter noop/test double; phải lần theo nhiều lớp kế thừa để biết method và tài nguyên dùng chung nằm đâu. Độ dài SQL tự nó không chứng minh query chậm.
- Hướng xử lý: chia port theo nhu cầu consumer, ví dụ đọc context, ghi curriculum, ghi quiz và cập nhật job; inject repository cụ thể qua composition. Tách các bước của `upsert_curriculum` bằng helper nhận cùng transaction/cursor, giữ tính nguyên tử hiện có. Không tách mỗi bảng thành một service mạng.
- Kiểm chứng khi sửa: transaction import vẫn rollback toàn bộ khi một bước lỗi; các use case chỉ cần mock các thao tác thật sự sử dụng.

**R09 — Route LTI launch chứa toàn bộ chuỗi xác thực và thiết lập phiên**

- Bằng chứng: [lti/launch/route.ts](../web/src/app/lti/launch/route.ts) dài 471 dòng. Parsing custom claim/role bắt đầu ở 43; cookie/session fallback ở 112; JWKS và nhánh RSA tương thích ở 173–249; handler `POST` từ 251 còn xử lý Redis state/nonce, xác định LMS/target, gọi Core API, tạo deep-link/session và redirect.
- Hệ quả: sửa hỗ trợ Canvas/Open edX hoặc cookie dễ tác động đường xác thực khác; khó kiểm tra riêng phần chuyển claim thành dữ liệu nghiệp vụ. Việc có nhiều bước xác thực là cần thiết, vấn đề là ranh giới trách nhiệm.
- Hướng xử lý: tách xác minh token, chuẩn hóa launch claims và tạo session/response; route chỉ ghép các bước. Đặt nhánh tương thích vào policy có tên rõ ràng. Giữ nguyên thứ tự kiểm tra state/nonce/claims khi refactor.
- Kiểm chứng khi sửa: token/state/nonce không hợp lệ, launch thường/deep-link, vai trò learner/instructor và cookie/query-session fallback.

**R10 — Đồng bộ Canvas trộn quyết định sync với nhiều bước ghi rời nhau**

- Bằng chứng: [canvas-document-sync.service.ts:91](../core-api/src/document/canvas-document-sync.service.ts) vừa tính placement/chương, so phiên bản, xử lý retry, import và xóa file không còn trong module. `importFile` ở 322–363 thực hiện tải file → ghi object → soft-delete bản cũ → tạo row mới → enqueue; `enqueueProcessingOrMarkError` ở 366 là một cơ chế bù lỗi riêng.
- Đường lỗi cụ thể: nếu DB tạo row mới thất bại sau khi soft-delete bản cũ, bản cũ đã bị ẩn dù bản mới chưa được tạo; object mới cũng đã được ghi. Chưa tái hiện trên môi trường chạy. Hiện code đã bảo vệ trường hợp storage lỗi trước khi ẩn bản cũ, nhưng các bước sau vẫn rời rạc.
- Hướng xử lý: tách bước lập kế hoạch sync khỏi bước áp dụng. Gom các thay đổi DB khi thay phiên bản và ghi outbox trong transaction; dọn object mới nếu transaction thất bại. Consumer enqueue theo outbox để việc ghi row và nhận job có cơ chế phục hồi thống nhất.
- Hiệu năng: vòng sync hiện tuần tự. Chỉ thêm concurrency có giới hạn sau khi làm rõ transaction, giới hạn Canvas và mức dùng bộ nhớ tải file; chưa có số liệu để chọn concurrency.
- Kiểm chứng khi sửa: giả lập lỗi ở storage, create row và enqueue; vẫn truy cập được phiên bản hợp lệ hoặc có trạng thái phục hồi rõ ràng.

**R11 — Trạng thái tài liệu có alias cũ và được chuyển ở nhiều luồng**

- Bằng chứng: [metadata_store.py:14–30](../packages-ai/src/document_chunk/domain/ports/metadata_store.py) định nghĩa `DONE = INDEXED`, `ENRICHED = GENERATED_DRAFT`, `UPSERTING = EMBEDDING`. [_pipeline_core.py:252](../packages-ai/src/document_chunk/application/use_cases/_pipeline_core.py) ghi `INDEXED`; [run_enrichment.py:289,592](../worker/worker/use_cases/run_enrichment.py) ghi `ENRICHED` hoặc trả về `DONE` khi enrichment lỗi; [outbox_projector.py:170](../worker/worker/services/outbox_projector.py) cũng quyết định bước `ENRICHED` sau projection.
- Hệ quả: đọc `DONE` có thể tưởng toàn bộ workflow hoàn tất nhưng giá trị lưu chỉ là `INDEXED`; muốn hiểu thất bại enrichment hoặc lúc nào UI sẵn sàng phải ghép nhiều file. Đây là tương thích có chủ đích, không phải bằng chứng trạng thái hiện đang sai.
- Hướng xử lý: chuẩn hóa tên trạng thái nội bộ; giới hạn alias ở adapter tương thích. Viết rõ transition và bên sở hữu từng bước. Nếu ingestion, projection và generation phát triển độc lập, cân nhắc trạng thái riêng cho từng tác vụ thay vì tiếp tục thêm nghĩa vào trạng thái document.
- Kiểm chứng khi sửa: ingestion thành công nhưng enrichment/projection lỗi vẫn thể hiện đúng khả năng sử dụng tài liệu và bước có thể retry.

**R12 — Dọn phần legacy sau migration, không ưu tiên hơn luồng đang chạy**

- Bằng chứng: [docker-compose.yml:156–167,210–215,243–248](../docker-compose.yml) đặt `grpc-server`, `http-api`, `mcp-server` của packages-ai dưới profile `legacy`. Trong khi đó đã có `mcp-service` và `document-inspector`; entrypoint cũ và [container.py](../packages-ai/src/document_chunk/infrastructure/container.py) vẫn còn. HTTP API cũ dài 786 dòng, gRPC servicer cũ 478 dòng.
- Một dấu hiệu phần cũ đã lệch là [container.py:121–123](../packages-ai/src/document_chunk/infrastructure/container.py) vẫn import `openai_embedder`, trong khi file đó không có trong thư mục adapters/embedders của checkout này. Worker mới chỉ nhận `bge`/`grpc` tại [worker/container.py:85–99](../worker/worker/container.py). Không có căn cứ nói cấu hình mặc định đang đi vào nhánh thiếu file.
- Hệ quả: thêm một bộ đường chạy/config/dependency phải giải thích và duy trì; người đọc README cũ có thể đi nhầm entrypoint.
- Hướng xử lý: hoàn tất tiêu chí migration đã ghi trong [embedding-service-migration.md](embedding-service-migration.md), xác nhận không còn consumer rồi bỏ entrypoint/wiring/extra dependency cũ và cập nhật README. Giữ fallback trong thời gian migration còn cần.

**Các vùng dài nhưng chưa nên refactor chỉ vì số dòng**

- [dcmh_extractor.py](../packages-ai/src/document_chunk/adapters/curriculum/dcmh_extractor.py) dài 829 dòng, xử lý nhiều mẫu đề cương và hàng bảng nối trang; `extract` đã chia thành các bước rõ. Nếu tiếp tục thêm mẫu, tách rule theo loại bảng và củng cố bộ tài liệu mẫu có kết quả chuẩn trước khi đổi thuật toán.
- [neo4j_graph_store.py](../packages-ai/src/document_chunk/adapters/graph/neo4j_graph_store.py) dài 749 dòng nhưng gồm nhiều truy vấn/projection khác nhau. Có thể tách heading/concept/curriculum khi cần sửa phần đó; chưa có dữ liệu để kết luận đây là nút thắt hiệu năng.
- Nhóm PDF parser có logic fallback/đánh giá từng trang và kiểm thử tương ứng. Không nên rút gọn điều kiện nếu chưa kiểm tra trên PDF scan, bảng, nhiều cột và trang ít text.

**Thứ tự thực hiện đề xuất**

1. R01, R02, R03, R10: xử lý chặn worker, batch một phần, retry và thay tài liệu khi lỗi. Đây là các thay đổi cần kiểm thử lỗi/khả năng phục hồi.
2. R04, R05, R06, R07: chuẩn hóa contract và giảm số nơi phải sửa khi thay đổi quiz. Làm từng ranh giới nhỏ, giữ API đang dùng trong giai đoạn chuyển đổi.
3. R08, R09, R11: thu hẹp port, tách LTI và làm rõ trạng thái khi phát triển tính năng liên quan.
4. R12: đóng migration rồi xóa phần cũ. Đo queue latency, số RPC/DB round trip và thời gian từng bước trước khi đặt mục tiêu tăng tốc định lượng.

Kiểm tra đã thực hiện cho bản rà soát: đọc source và các test liên quan, đối chiếu đường gọi giữa service, kiểm đếm AST Python và khai báo state frontend. Chưa chạy bộ test ứng dụng vì chỉ thêm tài liệu; các mục “kiểm chứng khi sửa” là yêu cầu cho đợt triển khai sau, không phải kết quả test đã chạy.
