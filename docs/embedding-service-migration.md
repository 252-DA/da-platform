# Tách embedding-service khỏi packages-ai — kế hoạch triển khai

Trạng thái: đã chốt kiến trúc + cơ chế phân phối; cả 5 cấu phần (`service-sdk`, `embedding-service`, `mcp-service`, `document-inspector`, cộng điểm chạm trong `packages-ai`) đã scaffold xong, đang trong giai đoạn code tay phần logic mới.
Phạm vi: `da-platform` (orchestrator), `packages-ai` (core-chunking), `worker`, `service-sdk` (mới), `embedding-service` (mới), `mcp-service` (mới), `document-inspector` (mới).

**Trạng thái scaffold theo cấu phần** (thứ tự runtime dependency không đổi — mcp-service/document-inspector đã có khung code nhưng chỉ chạy được sau khi `GrpcEmbedder`/`EmbeddingClient` xong, xem §9):
- `service-sdk`: proto + generated stubs, exceptions, models và `EmbeddingClient` đã được implement; client là boundary duy nhất xử lý batching, retry và response validation.
- `embedding-service`: config/metrics viết đầy đủ; `runtime/bge_runtime.py` + `delivery/{servicer,server}.py` là stub — phần code tay chính.
- `packages-ai`: `adapters/embedders/grpc_embedder.py` là stub, phụ thuộc `EmbeddingClient` xong trước.
- `mcp-service`: composition root (`container.py`) và MCP delivery (`delivery/server.py`) viết đầy đủ — thuần lắp lại use case đã có sẵn trong `packages-ai`, không có logic mới. Chỉ chạy được sau khi `GrpcEmbedder` xong.
- `document-inspector`: viết đầy đủ, không phụ thuộc embedding — có thể chạy ngay (`uv sync && uv run uvicorn document_inspector.delivery.app:app`).

---

## 1. Mục tiêu

- `packages-ai` trở thành library thuần: không tự chạy HTTP/gRPC/MCP, không load BGE.
- `embedding-service` là tiến trình duy nhất giữ model và thực hiện inference.
- `service-sdk` sở hữu proto, generated code và client cấp cao để các service gọi nhau.
- Worker tiếp tục điều phối parse → chunk → embed → Qdrant/Postgres; **không** tách thành embedding worker riêng.
- `core-api` tiếp tục sở hữu upload và API nghiệp vụ. Canvas và cloudflared giữ nguyên, ngoài phạm vi đợt này.

## 2. Vì sao — bằng chứng từ code hiện tại

Đây không phải refactor lý thuyết. Các điểm sau đã verify trực tiếp trong repo tại thời điểm viết tài liệu:

- `worker/worker/container.py` import thẳng `BgeEmbedder` từ `packages-ai` (`build_embedder()`), và `worker/pyproject.toml` kéo theo `document-chunk[embeddings]` → FlagEmbedding/BGE-M3 (~2GB) load ngay trong tiến trình worker.
- `packages-ai/src/document_chunk/delivery/{grpc,http,mcp}` bundle chung với domain/adapters trong một package, cùng một composition root `infrastructure/container.py` (357 dòng) nối tất cả lại.
- `docker-compose.yml`: biến `GRPC_HOST` set cho service `web` (trỏ `grpc-server:50051`, tức gRPC cũ của packages-ai) nhưng `web/src/lib/core-api.ts` chỉ đọc `CORE_API_GRPC_HOST` — biến `GRPC_HOST` chết, không có consumer.
- `core-api/src/document/document.controller.ts` đã có đủ list/get/chunks/upload-session/confirm-upload/register+process/delete; `document.service.ts` enqueue job qua BullMQ, **không** gọi gRPC hay HTTP của packages-ai. → `grpc-server` và `http-api` (`packages-ai/delivery`) là bề mặt trùng lặp, an toàn để retire.
- `packages-ai/src/document_chunk/delivery/mcp/server.py` chỉ dùng `SearchChunksUseCase` và `RetrieveQuizContextUseCase`, không đụng `graph_store`/Neo4j. Việc compose bắt `mcp-server` chờ `neo4j` healthy là kế thừa cẩu thả, không phải nhu cầu chức năng thật.
- `EmbedderConfig` (packages-ai): `batch_size: int = 4`, `max_length: int = 1024`, dimension 1024 cho BGE-M3 — đây là các con số baseline phải giữ nguyên khi chuyển sang remote.
- Repo đã có tín hiệu bắt đầu: submodule `packages-ai` đang ở branch `feat/embed-service`; hai thư mục `embedding-service/` và `service-sdk/` đã tồn tại ở root (rỗng, chưa đăng ký submodule) trước khi tài liệu này được viết.

## 3. Kiến trúc đích

```text
web -> core-api -> MinIO/Postgres/BullMQ
                           |
                    document-worker
                  parse -> chunk -> gRPC
                                     |
                              embedding-service
                  Qdrant/Postgres <- vectors

service-sdk          proto + generated code + typed clients
packages-ai          domain + application + adapters
mcp-service           MCP delivery, gọi remote embedding khi search   (phase sau)
document-inspector    FastAPI dev-only để inspect parse/chunk         (phase sau)
```

`embedding-service` và `mcp-service` sẽ là **repo Git độc lập**, đăng ký submodule trong `da-platform` — cùng pattern với `worker`/`packages-ai`/`ai-sdk` hiện tại, **không phải** thư mục con nằm trong cây `da-platform`. Đây là điều kiện tiên quyết để cơ chế pin ở §5 có ý nghĩa.

## 4. Contract embedding v1

- Distribution là `da-service-sdk`; proto canonical đặt tại `service-sdk/proto/da_platform/embedding/v1/embedding.proto`.
- Wire package là `da_platform.embedding.v1`; generated Python được commit, tuyệt đối không sửa tay.
- `EmbeddingService.Embed`: nhận `request_id` và tối đa 32 chuỗi; trả vectors đúng thứ tự, `model_name` và `dimension`.
- `EmbeddingService.GetModelInfo`: trả model, dimension, RPC batch limit và model max token length.
- Dùng chuẩn `grpc.health.v1` cho health/readiness — không tạo health RPC riêng.
- SDK cung cấp synchronous `EmbeddingClient`, context manager/`close()`, tự chia batch tuần tự và kiểm tra số vector/dimension.
- Timeout mỗi RPC: 300 giây. Tối đa 2 lần gọi cho `UNAVAILABLE`/`RESOURCE_EXHAUSTED`. Không retry `INVALID_ARGUMENT` hay `DEADLINE_EXCEEDED` (300s đã rộng; để BullMQ retry cả document đơn giản hơn retry RPC riêng lẻ — quyết định có chủ đích, không phải bỏ sót).
- SDK ném exception riêng; adapter trong `packages-ai` (`GrpcEmbedder`) chuyển chúng thành `Err(EmbedError)` để SDK không phụ thuộc `Result` của domain.
- Codegen bằng một script duy nhất dùng `grpcio-tools`; CI generate lại rồi chạy `git diff --exit-code`.

## 5. Cơ chế phân phối `service-sdk`

> **Cập nhật 2026-09-28 — `service-sdk` KHÔNG tách thành repo riêng.**
> Nó sống in-tree trong `da-platform` như một thư mục thường, không phải
> submodule. Phần "hai pin độc lập" bên dưới vì vậy **không còn áp dụng cho
> `service-sdk`** — consumer cùng repo chỉ cần path dep, không có gitlink nào
> để lệch. §5.1–§5.3 được giữ lại và viết lại cho các dependency **thật sự**
> là submodule: `core-chunking` (nằm ở `packages-ai/`) và `ai-sdk`.
>
> Lý do giữ in-tree: mọi Dockerfile build bằng `context: .` ở root rồi
> `COPY service-sdk`, và các consumer khai `{ path = "../service-sdk" }`, nên
> chúng bắt buộc nằm chung một cây thư mục. Tách ra chỉ thêm một pin phải
> canh mà không đổi được gì.

Hybrid: package có version SemVer, phân phối bằng source pin theo commit. Chưa dựng private PyPI.

**Bốn trách nhiệm tách biệt, không được coi là một pin duy nhất:**

| Trách nhiệm | Cơ chế | Nơi sống |
|---|---|---|
| Version contract | SemVer (`da-service-sdk>=0.1.0,<0.2.0`) trong `project.dependencies` | pyproject.toml của mỗi consumer |
| Dev/Compose pin | gitlink submodule — **chỉ với dep là submodule** (`core-chunking`, `ai-sdk`). `service-sdk` in-tree nên không có | `.gitmodules` + tree của `da-platform` |
| CI pin | SHA 40 ký tự trong `uses: 252-DA/<repo>/.github/actions/materialize@<sha>` | workflow YAML của **từng** consumer repo |
| Runtime install | `uv sync --no-editable` → package thật trong `.venv`, không giữ source | Dockerfile builder stage |

### 5.1 Hai pin độc lập — không tự đồng bộ

Đã verify: `worker.yaml` **không** dùng git submodule của `da-platform` để lấy `packages-ai`/`ai-sdk` trong CI. Nó dùng composite action pin theo SHA ngay trong YAML của chính `worker`:

```yaml
- uses: 252-DA/core-chunking/.github/actions/materialize@<sha>
```

`worker` là repo riêng, workflow của nó chạy trên chính repo `worker`, **không đọc được** `.gitmodules` của `da-platform`. Vậy có hai pin sống ở hai nơi khác nhau, phải cập nhật riêng từng bước:

1. **Dev/Compose pin**: gitlink `packages-ai` / `ai-sdk` trong repo `da-platform` — ảnh hưởng docker-compose dev local.
2. **Consumer CI pin**: SHA trong `uses: .../materialize@<sha>` của repo consumer — ảnh hưởng CI của chính repo đó.

Bump một pin không tự bump pin còn lại. Quên bước 2 khiến CI build ra artefact khác với những gì dev thấy ở local, không có gì báo lỗi trừ khi có check chủ động (§5.3).

**Đã xảy ra thật:** 2026-09-28, PR #11 của `core-chunking` được merge (`d325fc4`) và gitlink trong `da-platform` được bump theo, nhưng `worker.yaml` vẫn pin `a82c1696`. CI của `worker` test trên một bản `packages-ai` khác với Compose và với dev local, im lặng — vì check §5.3 lúc đó chỉ canh `service-sdk`.

**Phạm vi:** chỉ consumer **là repo riêng** mới lệch được. GitHub chỉ chạy `.github/workflows/` ở root của một repo, nên workflow nằm trong thư mục in-tree (`mcp-service/.github/`, `document-inspector/.github/`, `embedding-service/.github/`, `service-sdk/.github/`) **không bao giờ thực thi**. Pin cũ ở đó vô hại cho tới khi service đó được tách ra thật.

### 5.2 Checklist khi SDK thay đổi

1. Sửa proto/client, chạy codegen và test trong `service-sdk`.
2. Bump version SDK, commit, tạo tag Git (`v0.1.x` cho thay đổi tương thích; breaking contract → `da_platform.embedding.v2` + bump major).
3. Cập nhật version constraint và `uv.lock` của từng consumer.
4. Chạy `python3 scripts/check_materialize_pins.py` tại `da-platform`, sau đó mới build Compose/E2E.

`service-sdk` cùng repo nên **không** có bước bump gitlink hay bump SHA materialize. Hai bước đó chỉ cần khi đổi `core-chunking` hoặc `ai-sdk`:

- bump gitlink submodule trong `da-platform`, **và**
- bump SHA `materialize@` trong workflow của mọi consumer là repo riêng (hiện tại chỉ `worker`).

Hai việc đó phải làm cùng một lượt, nếu không sẽ tái hiện đúng sự cố ghi ở §5.1.

### 5.3 `scripts/check_materialize_pins.py`

Chạy trong integration CI của `da-platform` (§7). So sánh gitlink đã **commit** với mọi SHA `materialize@` tìm thấy trong workflow của consumer, fail nếu lệch.

Cả hai vế đều **tự khám phá**, không hardcode: dependency đọc từ `.gitmodules` (tên repo → path — hai thứ này khác nhau, `core-chunking` nằm ở `packages-ai/`), consumer là mọi thư mục top-level có workflow riêng. Thêm submodule hay thêm service đều không phải sửa script.

Chi tiết cài đặt quan trọng: đọc gitlink bằng `git ls-tree HEAD -- <path>`, **không** dùng `git submodule status` trơn — lệnh đó đọc commit đang checkout thật trong working dir, có thể vượt trước những gì đã commit (dev bump local rồi quên commit). Check muốn xác nhận "cái gì đã được chốt", phải đọc từ tree đã commit.

Logic:
```text
repos = parse(.gitmodules)                       # tên repo -> path
for consumer in mọi thư mục top-level có .github/workflows/:
    for (repo, ci_sha) in grep 'materialize@<40 hex>' trong workflow của consumer:
        pinned = git ls-tree HEAD -- repos[repo]
        nếu consumer không phải submodule  -> NOTE  (workflow inert, không chạy)
        nếu ci_sha != pinned               -> FAIL, trừ khi có ngoại lệ khai báo
```

Consumer có thể cố ý dùng bản cũ (đang giữa quá trình nâng cấp dần), nhưng trường hợp đó phải khai báo ngoại lệ tường minh trong `scripts/check_materialize_pins.exceptions.json`, key `"<consumer>/<repo>"` — không được để lệch âm thầm.

### 5.4 Khai báo dependency (uv)

`packages-ai/pyproject.toml`:
```toml
[project.optional-dependencies]
remote-embedding = [
    "da-service-sdk>=0.1.0,<0.2.0",
]

[tool.uv.sources]
da-service-sdk = { path = "../service-sdk", editable = true }
```

`worker/pyproject.toml` (và tương tự `mcp-service`):
```toml
[project]
dependencies = [
    "document-chunk[remote-embedding]",
    # ... các dependency hiện tại
]

[tool.uv.sources]
document-chunk = { path = "../packages-ai", editable = true }
da-service-sdk = { path = "../service-sdk", editable = true }
```

**Quy tắc bắt buộc, áp dụng cho mọi consumer mới sau này**: `tool.uv.sources.da-service-sdk` phải xuất hiện tại project root đang chạy `uv sync`, kể cả khi SDK chỉ là transitive dependency (qua `document-chunk[remote-embedding]`). uv không tự đọc `tool.uv.sources` từ pyproject.toml của một path-dependency khác — override cho transitive dependency phải khai lại ở project đang được resolve. Quên bước này → `uv sync` báo lỗi không tìm thấy `da-service-sdk` trên index (không có index thật nào cả).

`embedding-service` khai báo SDK trực tiếp (không qua `document-chunk`):
```toml
dependencies = [
    "da-service-sdk>=0.1.0,<0.2.0",
]

[tool.uv.sources]
da-service-sdk = { path = "../service-sdk", editable = true }
```

Worker không cần khai báo `da-service-sdk` trong `project.dependencies` — nó không import SDK trực tiếp, chỉ dùng `GrpcEmbedder` (đã bọc sẵn trong `packages-ai`, xử lý exception → `Err(EmbedError)` trước khi trả ra ngoài).

### 5.5 Docker build

Toàn bộ build dùng context root (`context: .`), copy đúng source cần thiết, cài **non-editable** ở stage cuối:

| Image | Source cần trong builder |
|---|---|
| `embedding-service` | `service-sdk`, `embedding-service` |
| `document-worker` | `service-sdk`, `packages-ai`, `ai-sdk`, `worker` |
| `mcp-service` | `service-sdk`, `packages-ai`, `mcp-service` |
| `document-inspector` | `packages-ai`, `document-inspector` |

`packages-ai` là library, không còn image riêng (retire `grpc-server` + `http-api`, xem §9).

```dockerfile
FROM python:3.10-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/
WORKDIR /app
COPY service-sdk /app/service-sdk
COPY packages-ai /app/packages-ai
COPY ai-sdk /app/ai-sdk
COPY worker /app/worker
WORKDIR /app/worker
RUN uv sync --locked --no-dev --no-editable

FROM python:3.10-slim
COPY --from=builder /app/worker/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
CMD ["document-worker"]
```

`--no-editable` biến path dependencies thành package cài trong `.venv`; runtime image không cần giữ source SDK.

## 6. Chuẩn hóa uv trước khi nhân Dockerfile

Đã verify: `astral-sh/setup-uv@v5` được dùng trong `worker`, `ai-sdk`, `ai-tutor` — **cả ba đều không khai `version:`**, và không có `required-version` ở bất kỳ `pyproject.toml` nào trong repo. Nghĩa là rủi ro lệch version CI-vs-Docker **đã tồn tại từ trước** (Docker pin `uv:0.6.14`, CI có thể lấy bản mới nhất qua `setup-uv@v5`), không phải rủi ro mới phát sinh khi thêm service.

Tách một commit chuẩn hóa, áp dụng đồng loạt cho cả workflow/Dockerfile cũ lẫn mới:

- Pin cùng một uv version — `0.11.32` — trong toàn bộ Dockerfile và GitHub Actions.
- Khai báo `with: version: "0.11.32"` cho mọi bước `setup-uv`.
- Chuyển đồng loạt `uv sync --frozen` → `uv sync --locked` (báo lỗi khi `pyproject.toml` và lockfile lệch, thay vì âm thầm dùng lock cũ).
- Docker production giữ `--no-dev --no-editable` là bước riêng, sau `--locked`.
- Regenerate/verify toàn bộ lockfile hiện có bằng đúng version uv này.

## 7. Hai lỗ hổng hạ tầng CI — ĐÃ LẤP (2026-09-28)

Giữ lại phần mô tả để biết vì sao hai file đó tồn tại.

1. ~~**`packages-ai` (core-chunking) không có workflow CI nào.**~~ → đã tạo `packages-ai/.github/workflows/ci.yaml`.
   Trước đó `packages-ai/.github` chỉ chứa `actions/materialize`, nên test suite ở `packages-ai/tests/unit/{adapters,application,delivery,domain,shared}` không được chạy ở đâu cả — `worker.yaml` chỉ chạy `pytest tests/unit` trong thư mục `worker`, không đụng `packages-ai/tests`. Đây là nơi chạy test cho `GrpcEmbedder` adapter (fake gRPC server, dimension mismatch, close channel — xem §11).
2. ~~**`da-platform` (repo root) không có `.github` nào cả.**~~ → đã tạo `.github/workflows/integration.yaml`, chạy `scripts/check_materialize_pins.py` trên `master` và `dev`.

## 8. Giai đoạn migration — dependency worker theo hai checkpoint

```toml
# Trong lúc chạy song song local (BGE) và remote (gRPC) qua cờ migration
"document-chunk[embeddings,remote-embedding]"

# Sau khi remote E2E ổn định và xóa local BGE + cờ migration
"document-chunk[remote-embedding]"
```

## 9. Thứ tự triển khai (17 bước, mỗi bước một commit chạy được)

1. **Ghi baseline**: upload `Architecture Design Specification.pdf`, lưu status cuối, số chunk Postgres, số vector Qdrant, dimension, RSS worker.
2. **Làm SDK**: packaging, proto, generated stubs, model types, exceptions, client. Test bằng in-process fake gRPC server trước khi đụng BGE thật.
3. **Làm embedding runtime**: chuyển logic `BgeEmbedder` sang `embedding-service/runtime` — không phụ thuộc `packages-ai`, DB, Redis, MinIO, Qdrant.
4. **Làm gRPC server**: start socket ở trạng thái `NOT_SERVING`, load BGE một lần, chuyển `SERVING`. Thread pool 4, inference dùng semaphore 1 (tránh nhiều encode cùng ăn RAM).
5. **Giữ thông số hiện tại**: BGE-M3, dimension 1024, `max_length=1024`, encode batch 4. RPC batch 32 chỉ là lớp gom request bên ngoài.
6. **Thêm quan sát**: log model load đúng một lần; metrics cho load time, inference latency, RPC status, batch size, inflight, RSS; port metrics mặc định `9095`.
7. **Đóng gói service**: model tải vào named volume Hugging Face, không bake vào image; gRPC nội bộ `50051`, host dev map `50061:50051`.
8. **Thêm remote adapter**: `GrpcEmbedder` trong `packages-ai/adapters/embedders`; implement nguyên `IEmbedder`, gọi `GetModelInfo` lúc khởi tạo, fail-fast nếu dimension khác Qdrant.
9. **Chuyển document worker**: thêm config `EMBEDDING_SERVICE__TARGET`, timeout, RPC batch, attempts; track adapter trong container để đóng channel khi shutdown. Pipeline core không đổi.
10. **Chạy song song tạm thời**: giữ local BGE qua cờ migration (§8), chạy E2E remote thành công, đổi remote thành mặc định, xóa cờ/local implementation.
11. **Tách MCP**: chuyển MCP delivery sang `mcp-service`; tự compose Postgres, Qdrant, `GrpcEmbedder`. Bỏ dependency Neo4j (đã verify hai MCP tool hiện tại không dùng graph).
12. **Giữ inspector**: chuyển riêng `/health`, `/documents/inspect`, `/documents/inspect/chunking` sang `document-inspector`; không nối DB, chỉ chạy qua Compose profile `tools`.
13. **Retire API cũ**: đưa `grpc-server` và `http-api` vào profile `legacy` trong lúc migration; sau E2E xóa service, toàn bộ `packages-ai/delivery`, `chunking.proto` cũ, generated stubs, test client. Không chuyển contract chết sang SDK.
14. **Xóa composition root cũ**: bỏ `packages-ai/infrastructure/container.py`; worker, MCP, inspector là composition root mới. Loại import ngược từ package sang `worker`.
15. **Thu gọn dependency**: parser, Postgres, Qdrant, MinIO, Neo4j, BullMQ, remote embedding thành optional extras. FastAPI thuộc inspector, MCP thuộc mcp-service, gRPC/protobuf thuộc SDK, FlagEmbedding thuộc embedding-service. Tiện tay dọn `EmbedderConfig.provider` Literal `["bge", "openai", "sentence_transformers"]` — hai provider sau chưa từng có implementation, là dead config.
16. **Cập nhật Compose**: thêm embedding health dependency cho document worker và MCP; bỏ `GRPC_HOST` legacy khỏi web (đã verify: dead, không consumer). Không sửa Canvas, cloudflared, route tunnel.
17. **Cập nhật lock/CI**: worker CI materialize thêm `service-sdk`; mỗi package mới có unit test, codegen check, Docker build. Real BGE smoke test đánh dấu `slow`, không chạy CI thường.

## 10. Lỗi và tính nhất quán

- Empty/oversized batch → `INVALID_ARGUMENT`; service chưa sẵn sàng → `UNAVAILABLE`; quá tải → `RESOURCE_EXHAUSTED`.
- SDK chỉ trả thành công sau khi nhận đủ mọi batch; pipeline không upsert Qdrant nếu response thiếu vector hoặc sai dimension.
- Lỗi remote cuối cùng → `EmbedError`; BullMQ tiếp tục retry toàn document theo chính sách hiện tại, không cần bảng intermediate mới.
- Worker restart không làm model reload; embedding-service restart phải readiness lại trước khi nhận job.
- Không đổi schema Postgres, event JSON trong `contracts/`, status pipeline, Qdrant collection.

## 11. Kiểm thử chấp nhận

- **Unit**: batching `0/1/32/33`, giữ thứ tự, timeout/status mapping, malformed response, dimension mismatch, close channel, health transition.
- **Integration**: fake runtime kiểm tra gRPC server/client; MCP semantic search dùng remote adapter; inspector parse/chunk không ghi storage.
- **E2E**: upload PDF thật qua frontend, đi qua `PARSING → CHUNKING → EMBEDDING → INDEXED`, DB/Qdrant có cùng số chunk và vector 1024 chiều.
- **Resilience**: tắt embedding giữa job phải retry/fail rõ ràng; bật lại rồi retry phải hoàn tất; hai tài liệu liên tiếp chỉ có một log model load, không OOM.
- **Resource**: worker không còn `FlagEmbedding`/BGE model; concurrency worker và inference đều giữ 1 cho đến khi có số liệu mới.

## 12. K3s (sau khi Compose ổn)

- Manifest tạo sau khi E2E Compose ổn: embedding `Deployment` 1 replica, strategy `Recreate`, ClusterIP `50051`, PVC model cache `10Gi`, gRPC startup/readiness/liveness probes.
- Mặc định embedding request `2 CPU/4Gi`, limit `4 CPU/6Gi`; document worker request `1 CPU/1Gi`, limit `2 CPU/3Gi` — con số ước lượng chờ baseline thật ở bước 1.
- Chưa bật HPA trên máy một node. K3s chỉ kiểm soát scheduling/limit, không tạo thêm RAM.
- Canvas, cloudflared tiếp tục chạy như hiện tại, ngoài phạm vi đợt K3s này.

## 13. Giả định đã chốt

- Embedding v1 dùng unary batch gRPC, generated code được commit.
- Giữ inspector dưới dạng dev tool; xóa API nghiệp vụ Python trùng với core-api.
- `ai-sdk`, `core-api/proto`, `contracts/` (async JSON) không chuyển vào `service-sdk` đợt này.
- Giao tiếp nội bộ Compose/K3s chưa dùng TLS; bảo mật transport là phase riêng sau khi service boundary ổn định.
- `embedding-service`, `mcp-service`, `document-inspector` sẽ là repo Git độc lập (§3) — hiện scaffold sẵn dưới dạng thư mục thường trong `da-platform`, tách thành repo/submodule thật khi tới bước 17. Thứ tự **chạy được** (không phải thứ tự scaffold) vẫn đi từ `service-sdk` → `embedding-service` → `packages-ai` (`GrpcEmbedder`) → `mcp-service`, theo đúng §9.
