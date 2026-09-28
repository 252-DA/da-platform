# Chọn model linh hoạt — thiết kế `model routing`

| | |
|---|---|
| Trạng thái | Đề xuất, chưa triển khai |
| Ngày | 2026-09-28 |
| Phạm vi | `ai-sdk` (catalog + registry), `worker` (container, 2 use case), `ai-tutor`, `packages-ai` (xoá adapter trùng), `contracts`, `core-api` (bảng binding + cột log), `docker-compose.yml` |
| Liên quan | [quiz-generation-redesign.md](quiz-generation-redesign.md#L120): đã ghi thành yêu cầu — "cần client thứ hai cho judge (§7.8); temperature riêng cho từng vai trò" — và `generation_meta.judge_model` trong §7.8 chỉ sinh được nếu có thiết kế này. [embedding-service-migration.md](embedding-service-migration.md): phía embedding đã tách backend sẵn, dùng làm tiền lệ |

---

## 0. Tóm tắt

- **Hiện trạng: model là thuộc tính của _process_, không phải của _task_.** Mỗi worker đọc `LLM__*` từ env lúc boot, dựng **một** `ModelClient` rồi dùng suốt đời process. Đổi model = sửa `.env`/compose + restart container. Không có đường nào khác: `get_settings()` bọc `@lru_cache`, container là singleton.
- **Muốn hai task dùng hai model thì phải nhân bản env theo service.** Đó chính là cách `content-generation-worker` đang tách model quiz khỏi phần còn lại: 4 biến `QUIZ_LLM_*` trong compose ([docker-compose.yml:509-512](../docker-compose.yml#L509-L512)). Thêm một task nữa là thêm 4 biến nữa, và task nào nằm chung process thì **không tách được**.
- **Ba lỗi đo lường chặn mọi so sánh model:** `cost_usd` ghi vào `llm_usage_logs` **luôn bằng 0** (M4); enrichment **không ghi usage** dòng nào (M6); `provider` truyền tay xuống use case, mặc định `"unknown"` (M5). Nghĩa là hôm nay không có số liệu nào để nói "DeepSeek rẻ hơn Gemini bao nhiêu".
- **Nguyên tắc: model là thuộc tính của task; chọn bằng _tên profile_ đã allowlist; API key không bao giờ đi qua config động.**
- **Thiết kế:** một `ModelProfile` catalog (khai báo trong `ai-sdk`, có cả bảng giá) + `ModelRegistry.for_task()` cache client theo `(provider, model, base_url)` + `ModelConfigSource` là interface (env hôm nay, Postgres về sau) + chuỗi fallback khi provider lỗi.
- **Bốn giai đoạn:** (1) catalog + 1 biến env mỗi task, vẫn phải restart — ~1 ngày; (2) registry theo task + fallback + tính cost thật; (3) binding trong Postgres, đổi model **không restart**; (4) override theo request để A/B trên cùng tập LO. Giai đoạn 1–2 là phần đáng làm ngay; 3–4 chỉ làm khi có admin UI thật cần.

---

## 1. Hiện trạng

### 1.1 Đường đi của config

```
.env / docker-compose x-common-env
  LLM__PROVIDER, LLM__MODEL, LLM__API_KEY, LLM__BASE_URL
        │
        ├─► packages-ai  LlmConfig (env_prefix "LLM_") ──┐
        │     config.py:201                              │  Settings (env_nested_delimiter "__")
        │                                                │    config.py:233
        │                                                ▼
        │                                      get_settings() @lru_cache
        │                                                │
        │                                                ▼
        │         worker/container.py:104  build_llm_client(settings)
        │                 build_model_client(ModelConfig(...))   ai-sdk/models.py:45
        │                          │
        │                          ├─ GeminiModelClient
        │                          ├─ OpenAICompatibleModelClient
        │                          └─ DeepSeekModelClient  (= OpenAI-compatible + base_url cố định)
        │                          │
        │                          ▼
        │            AIRuntimeLLMClient(AIRuntime(model))     ◄── MỘT instance / process
        │                          │
        │           ┌──────────────┴───────────────┐
        │           ▼                              ▼
        │   EnrichmentWorkerContainer      CurriculumQuizContainer
        │     container.py:223               container.py:239
        │
        └─► ai-tutor  LLMSettings (env_prefix "LLM__") ─► build_tutor_service ─► AIRuntimeTutorModel
              config.py:8                                  container.py:12
```

Điểm chết của tính linh hoạt nằm ở hai chữ: `@lru_cache` trên `get_settings()` và **một** `llm_client` được `_track()` trong `__init__` của container. Sau khi process khởi động, không có API nào đổi được model.

### 1.2 Hai stack adapter song song

| Stack | Vị trí | Provider hỗ trợ | Ai dùng |
|---|---|---|---|
| Mới (`ai-sdk`) | [ai-sdk/src/ai_runtime/models.py:45](../ai-sdk/src/ai_runtime/models.py#L45) | gemini, openai-compatible, deepseek | content-generation-worker, enrichment-worker, ai-tutor |
| Cũ (`packages-ai`) | [container.py:149-159](../packages-ai/src/document_chunk/infrastructure/container.py#L149-L159) → `GeminiLLMClient` | **chỉ** gemini, provider khác `raise ValueError` | `grpc-server` qua `generate_curriculum_quiz_use_case` ([server.py:61](../packages-ai/src/document_chunk/delivery/grpc/server.py#L61)) |

Stack cũ hiện **không chạy**: `grpc-server` nằm trong `profiles: ["legacy"]` ([docker-compose.yml:162](../docker-compose.yml#L162)) và image của nó không có package `worker`, nên `generate_curriculum_quiz_use_case` rơi vào nhánh `ModuleNotFoundError` → trả `None` → `llm_client` không bao giờ được dựng. Nhưng nó là bẫy đang mở: đặt `LLM__PROVIDER=deepseek` vào `x-common-env` rồi bật profile `legacy` thì `grpc-server` chết ngay lúc khởi động với `Unknown LLM provider: deepseek`.

### 1.3 Vấn đề

Cột "Nguồn": **chạy** = đã chạy thử; **code** = kết luận từ đọc code (kèm cách xác minh nếu cần).

| # | Vị trí | Vấn đề | Nguồn | Hệ quả |
|---|---|---|---|---|
| M1 | `config.py` `get_settings()` + `container.py:__init__` | `@lru_cache` trên settings, `llm_client` dựng một lần trong `__init__` | code | đổi model **bắt buộc** restart container; không có đường cho admin UI |
| M2 | [docker-compose.yml:36-38](../docker-compose.yml#L36-L38) vs [509-512](../docker-compose.yml#L509-L512) | Đơn vị cấu hình là process, nên tách model theo task = nhân bản `{PROVIDER, MODEL, API_KEY, BASE_URL}` cho từng service | code | 4 biến/task; hai task **cùng process** (sinh câu và judge trong quiz, cards và quiz trong enrichment) không thể khác model |
| M3 | compose (2 chỗ) + `.env` (`QUIZ_LLM_MODEL`) + default trong `LlmConfig.model` | Chuỗi `gemini-3-flash-preview` / `gemini-2.0-flash` xuất hiện ở ≥ 4 nơi, lệch nhau | code | nâng version model phải sửa rải rác; default trong code đã lạc hậu so với compose |
| M4 | [ai_runtime_llm_client.py:51-56](../worker/worker/adapters/ai_runtime_llm_client.py#L51-L56) đọc `response.usage.cost_usd`, nhưng `TokenUsage` ([models.py:7-11](../ai-sdk/src/ai_runtime/models.py#L7-L11)) **không có** field đó | `getattr(..., "cost_usd", 0)` luôn trả `0` | code (xác minh: `SELECT sum(cost_usd) FROM llm_usage_logs;`) | **mọi dòng `llm_usage_logs.cost_usd` = 0**; repo không có bảng giá model ở đâu cả → cột "AI Cost Monitoring" của schema là vỏ rỗng |
| M5 | [generate_curriculum_quiz.py:142](../worker/worker/use_cases/generate_curriculum_quiz.py#L142) `llm_provider: str = "unknown"`, truyền tay từ [container.py:246](../worker/worker/container.py#L246) | Provider là thuộc tính của client nhưng được bơm song song vào use case chỉ để ghi log | code | đường nào quên truyền thì log ghi `"unknown"`; `packages-ai` container ([:348](../packages-ai/src/document_chunk/infrastructure/container.py#L348)) đúng là **không** truyền |
| M6 | [run_enrichment.py:433,469](../worker/worker/use_cases/run_enrichment.py#L433) chỉ lưu `model_id` vào artifact | `RunEnrichmentUseCase` **không gọi** `record_llm_usage` lần nào | code (grep: `record_llm_usage` chỉ có trong `generate_curriculum_quiz.py`) | toàn bộ token/chi phí của enrichment — đường sinh tự động, chạy mỗi lần ingest — không được đo |
| M7 | [ai_runtime_llm_client.py:41-42](../worker/worker/adapters/ai_runtime_llm_client.py#L41-L42) | Provider lỗi → `Err(LLMError)` → job FAILED. Không có fallback sang model khác | code | một lần 429 của Gemini là mất cả request sinh quiz |
| M8 | `LlmConfig` có `env_prefix="LLM_"`, `Settings` có `env_nested_delimiter="__"` | Cả `LLM_PROVIDER` **và** `LLM__PROVIDER` đều được nhận; đặt cả hai thì `LLM__` thắng. `ai-tutor` chỉ nhận `LLM__` | **chạy** | hai chính tả cho cùng một biến, ưu tiên không hiển nhiên; sai một gạch dưới ở `ai-tutor` là im lặng dùng default `gemini-2.0-flash` |

### 1.4 Phần đang đúng, không được phá

- `ILLMClient` / `ModelClient` là port sạch, use case không biết provider nào → thêm routing **không** phải sửa use case.
- `ModelConfig` là dataclass frozen, đủ field (`temperature`, `timeout`, `max_retries`) → dùng làm giá trị đầu ra của resolver, không cần đổi shape.
- `deepseek` đã là "openai-compatible + base_url cố định" ([deepseek.py](../ai-sdk/src/ai_runtime/providers/deepseek.py)) — đúng hình dạng của một profile. Catalog chỉ là tổng quát hoá ý tưởng đó.
- `llm_usage_logs` đã có sẵn cột `use_case` ([migration.sql:428-444](../core-api/prisma/migrations/0_init/migration.sql#L428-L444)) và use case đã ghi `"quiz_generation" | "quiz_verification" | "quiz_regeneration"`. **Đây chính là khoá task** mà routing cần — không phải phát minh thêm.
- `embedding-service` đã tách `MODEL__BACKEND` (`bge` | `openai`) và ghi rõ ràng buộc reindex trong docstring `ApiConfig` ([config.py:55-59](../embedding-service/src/embedding_service/config.py#L55-L59)). Thiết kế dưới đây đi theo cùng lối.

---

## 2. Nguyên tắc

1. **Model là thuộc tính của task, không phải của process.** Khoá là `use_case` đã có trong `llm_usage_logs`, để log và config nói cùng một ngôn ngữ.
2. **Chọn bằng tên profile, không bằng tham số thô.** Không nơi nào ngoài catalog được đặt `provider`/`base_url`. Config động và payload chỉ mang **tên** profile, đã allowlist.
3. **Secret không bao giờ nằm trong config động.** Catalog lưu *tên biến env* chứa key (`key_env`), không lưu key. DB/payload không bao giờ chạm tới key.
4. **Nguồn config nằm sau interface.** `ModelConfigSource` hôm nay đọc env, mai đọc Postgres; call site không đổi một dòng.
5. **Mỗi lần gọi phải ghi lại profile đã dùng.** Linh hoạt mà không đo được thì chỉ là thêm chỗ để sai.
6. **Không có đường đổi model nào bỏ qua validate.** Tên lạ → lỗi rõ ràng lúc resolve, không im lặng về default.

---

## 3. Thiết kế

### 3.1 `ModelProfile` — catalog khai báo trong `ai-sdk`

```python
# ai-sdk/src/ai_runtime/catalog.py
@dataclass(frozen=True)
class ModelProfile:
    name: str                       # khoá ổn định, dùng trong env/DB/payload/log
    provider: Literal["gemini", "openai-compatible", "deepseek"]
    model: str                      # model id thật của provider
    key_env: str                    # TÊN biến env chứa key — không phải key
    base_url: str | None = None
    temperature: float = 0.2
    timeout_seconds: float = 60
    max_retries: int = 2
    price_in_per_1m: float = 0.0    # USD / 1M input token
    price_out_per_1m: float = 0.0   # USD / 1M output token

PROFILES: dict[str, ModelProfile] = {
    "gemini-flash":  ModelProfile("gemini-flash",  "gemini",   "gemini-3-flash-preview",
                                  key_env="GEMINI_API_KEY",   price_in_per_1m=..., price_out_per_1m=...),
    "gemini-pro":    ModelProfile("gemini-pro",    "gemini",   "gemini-3-pro-preview",
                                  key_env="GEMINI_API_KEY",   price_in_per_1m=..., price_out_per_1m=...),
    "deepseek-chat": ModelProfile("deepseek-chat", "deepseek", "deepseek-chat",
                                  key_env="DEEPSEEK_API_KEY", price_in_per_1m=..., price_out_per_1m=...),
}

TASK_DEFAULTS = {
    "quiz_generation":   "deepseek-chat",
    "quiz_verification": "gemini-flash",   # judge phải khác model sinh — quiz-generation-redesign §7.8
    "quiz_regeneration": "deepseek-chat",
    "enrichment":        "gemini-flash",
    "tutor":             "gemini-flash",
}
```

Bảng giá nằm ngay trong profile là cách rẻ nhất để sửa M4: cost tính được tại chỗ, không cần service giá riêng. Giá phải kèm ngày cập nhật trong comment — sai giá còn tệ hơn giá 0 vì nó trông như đúng.

### 3.2 `ModelConfigSource` — nguồn của binding

```python
class ModelConfigSource(Protocol):
    def binding_for(self, task: str) -> TaskBinding: ...   # profile + fallback + override nhẹ

@dataclass(frozen=True)
class TaskBinding:
    profile: str
    fallback_profile: str | None = None
    temperature: float | None = None     # None = lấy của profile
```

| Giai đoạn | Implementation | Đổi model cần gì |
|---|---|---|
| 1–2 | `EnvConfigSource`: đọc `LLM_PROFILE__<TASK>`, không có thì `TASK_DEFAULTS` | sửa `.env` + restart |
| 3 | `PostgresConfigSource`: đọc `llm_model_bindings`, cache TTL 30s | UPDATE 1 dòng, **không restart** |
| test | `StaticConfigSource(dict)` | — |

`EnvConfigSource` gom `LLM__*` cũ còn **một** biến mỗi task (`LLM_PROFILE__QUIZ_GENERATION=deepseek-chat`), xử luôn M2 và M3. Giai đoạn 1 vẫn đọc `LLM__API_KEY` cũ như fallback để không phá `.env` đang chạy — bỏ hẳn ở cuối giai đoạn 2.

### 3.3 `ModelRegistry` — thay singleton bằng cache có khoá

```python
class ModelRegistry:
    def __init__(self, source: ModelConfigSource, profiles=PROFILES) -> None: ...

    def for_task(self, task: str) -> ILLMClient:
        binding = self._source.binding_for(task)          # có thể đổi giữa các lần gọi
        return self._client(binding.profile, binding)     # cache theo (provider, model, base_url)
```

Ba thay đổi so với hôm nay:

- **Cache theo cấu hình, không phải singleton một client.** Đây là điều kiện cần để đổi model không restart: `binding_for()` trả giá trị khác thì `for_task()` trả client khác, client cũ vẫn nằm trong cache cho task khác dùng.
- **Cùng một process phục vụ nhiều model.** Sinh câu bằng DeepSeek, judge bằng Gemini, trong một `content-generation-worker` — hôm nay không làm được.
- **Fallback (M7).** `for_task` bọc client trong `FallbackClient(primary, fallback)`: gặp `ModelGenerationError`/429 thì thử `fallback_profile` **một** lần, ghi 2 dòng `llm_usage_logs` (`RATE_LIMITED` + `OK`) để chi phí thật vẫn khớp.

Container đổi đúng 2 dòng: `self.llm_client = build_llm_client(settings)` → `self.model_registry = build_model_registry(settings)`, rồi use case nhận `registry` thay vì `llm_client` và gọi `registry.for_task("quiz_generation")` tại chỗ dùng.

### 3.4 Thứ tự ưu tiên khi resolve

| Ưu tiên | Nguồn | Có ở giai đoạn | Chặn gì |
|---|---|---|---|
| 1 | `model_profile` trong payload/request | 4 | chỉ tên trong `PROFILES`, và chỉ role giảng viên/admin |
| 2 | Binding của task trong `ModelConfigSource` | 1 (env) / 3 (DB) | tên phải có trong `PROFILES`, sai thì `ModelConfigurationError` |
| 3 | `TASK_DEFAULTS[task]` | 1 | — |
| 4 | Profile mặc định toàn hệ thống | 1 | — |

Không có mức nào nhận `api_key` hay `base_url` từ bên ngoài. Đó là ranh giới an toàn chính của thiết kế này: nếu payload đặt được `base_url`, một job giả mạo có thể lái prompt sang endpoint bất kỳ **và** mang theo key thật của hệ thống.

### 3.5 Tính `cost_usd`

Sửa M4 tại adapter, chỗ duy nhất biết cả token lẫn profile:

```python
cost = (usage.input_tokens or 0)  / 1_000_000 * profile.price_in_per_1m \
     + (usage.output_tokens or 0) / 1_000_000 * profile.price_out_per_1m
```

`TokenUsage` của `ai-sdk` **không** thêm field giá — SDK không nên biết bảng giá. `LLMUsage.cost_usd` (phía `packages-ai`) đã có sẵn chỗ nhận, nên chỉ là điền vào thay vì `getattr` một field không tồn tại.

### 3.6 Ghi log để so sánh được

- Bỏ tham số `llm_provider` khỏi `GenerateCurriculumQuizUseCase` (M5); lấy từ client đang dùng.
- Thêm cột `model_profile VARCHAR(50)` vào `llm_usage_logs` — `provider` + `model` đã định danh đủ, nhưng profile là khoá mà config/A-B dùng, và là thứ join được với `llm_model_bindings`.
- `RunEnrichmentUseCase` phải gọi `record_llm_usage` (M6), với `use_case='enrichment_cards' | 'enrichment_quiz'`.

### 3.7 Override theo request (giai đoạn 4)

`contracts/integration-events/v1/content-generation-requested.json` đang `additionalProperties: false`, nên đây là **schema change có phiên bản**, không phải thêm field im lặng:

```json
"model_profile": { "type": "string", "enum": ["gemini-flash", "gemini-pro", "deepseek-chat"] }
```

Kèm: cập nhật fixtures ở `contracts/fixtures/v1/valid/`, và `core-api` chỉ được set field này cho role có quyền. `enum` trong contract phải sinh từ `PROFILES` (script kiểm tra trong CI) — hai danh sách chép tay sẽ lệch.

---

## 4. Ngoài phạm vi

| Việc | Lý do |
|---|---|
| **Đổi model embedding động** | Đổi model embedding là **đổi không gian vector**: phải reindex toàn bộ Qdrant, không phải đổi config. Đã có `MODEL__BACKEND` + docstring cảnh báo ở [embedding-service/config.py:55-59](../embedding-service/src/embedding_service/config.py#L55-L59); giữ nguyên ở đó |
| Key riêng theo tenant/khoá học | Chưa có yêu cầu; sẽ kéo theo quản lý secret per-tenant |
| Streaming / tool-calling | `ModelClient` hiện chỉ có `generate(prompt, system)`; mở rộng là thiết kế khác |
| Prompt versioning theo model | Đáng làm, nhưng thuộc [quiz-generation-redesign.md](quiz-generation-redesign.md) |

---

## 5. Kế hoạch

### Giai đoạn 1 — catalog + một biến env mỗi task (vẫn restart)

Sửa: `ai-sdk` (+`catalog.py`, +`config_source.py`), `worker/container.py`, `ai-tutor/container.py`, `docker-compose.yml`, `.env`.

- [ ] `catalog.py`: `ModelProfile`, `PROFILES`, `TASK_DEFAULTS`, giá kèm ngày cập nhật.
- [ ] `EnvConfigSource` đọc `LLM_PROFILE__<TASK>`; vẫn nhận `LLM__*` cũ làm fallback.
- [ ] `build_model_registry(settings)` thay `build_llm_client(settings)`; `ModelRegistry.for_task` (chưa fallback chain).
- [ ] Xoá `GeminiLLMClient` + nhánh `llm_client` trong `packages-ai` container (M6 §1.2) — một stack duy nhất.
- [ ] Thống nhất một chính tả env, `ai-tutor` dùng chung `EnvConfigSource` (M8).
- [ ] Compose: thay 4 biến `QUIZ_LLM_*` bằng `LLM_PROFILE__QUIZ_GENERATION`; key vẫn từ `GEMINI_API_KEY`/`DEEPSEEK_API_KEY`.

**Nghiệm thu:** `LLM_PROFILE__QUIZ_GENERATION=deepseek-chat` + restart → quiz sinh bằng DeepSeek, enrichment vẫn Gemini; profile sai tên → lỗi có tên profile và danh sách hợp lệ, không im lặng về default.

### Giai đoạn 2 — routing theo task + cost + fallback

- [ ] Use case gọi `registry.for_task(...)`; quiz dùng profile **khác** cho `quiz_verification` → cấp đúng `generation_meta.judge_model` mà [quiz-generation-redesign.md §7.8](quiz-generation-redesign.md) yêu cầu.
- [ ] Tính `cost_usd` từ bảng giá (M4); cột `model_profile` trong `llm_usage_logs`.
- [ ] Bỏ `llm_provider` khỏi use case (M5); enrichment ghi usage (M6).
- [ ] `FallbackClient` + `fallback_profile` (M7).

**Nghiệm thu:** một request sinh quiz để lại các dòng `llm_usage_logs` với ≥ 2 profile khác nhau và `cost_usd > 0`; chặn network tới provider chính → job vẫn xong bằng fallback, log có một dòng `RATE_LIMITED`/`ERROR` và một dòng `OK`.

### Giai đoạn 3 — binding trong Postgres, không restart

```sql
CREATE TABLE llm_model_bindings (
    task             VARCHAR(50) PRIMARY KEY,   -- khớp llm_usage_logs.use_case
    profile          VARCHAR(50) NOT NULL,      -- TÊN profile, không phải model id
    fallback_profile VARCHAR(50),
    temperature      NUMERIC(3,2),
    enabled          BOOLEAN NOT NULL DEFAULT TRUE,
    updated_by       UUID REFERENCES lms_user_mappings(internal_user_id),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- [ ] `PostgresConfigSource` + cache TTL 30s + fallback về env khi DB lỗi (không được để DB chết là LLM chết).
- [ ] `core-api`: endpoint admin đọc/ghi binding, validate `profile ∈ PROFILES`, ghi `admin_audit`.

**Nghiệm thu:** `UPDATE llm_model_bindings SET profile='gemini-pro' WHERE task='quiz_generation';` → trong ≤ 30s request mới dùng model mới, **không** restart container nào.

### Giai đoạn 4 — override theo request, A/B

- [ ] `model_profile` vào contract + fixtures + kiểm tra enum↔`PROFILES` trong CI.
- [ ] Chỉ role giảng viên/admin được set.
- [ ] Query so sánh: cost/token/tỉ lệ bị judge loại theo `model_profile` trên cùng tập LO.

---

## 6. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Nhiều model cùng process → RAM/số kết nối tăng | Chỉ client HTTP, không nạp weight (BGE nằm ở `embedding-service` riêng); cache có khoá nên số client bị chặn bởi số profile |
| Giá trong catalog lạc hậu → `cost_usd` sai mà trông như đúng | Ghi ngày cập nhật cạnh mỗi profile; test kiểm tra profile nào giá 0 thì phải khai báo rõ `price_unknown=True` |
| Binding trong DB trỏ profile đã xoá khỏi catalog | Resolve fail-fast kèm tên; endpoint admin validate trước khi ghi; migration xoá profile phải kèm UPDATE binding |
| Đổi model giữa lúc đang chạy → một request dùng 2 model | Resolve **một lần** đầu request, giữ client đó cho tới hết request; ghi profile vào log |
| Đổi provider làm hỏng parse JSON (`generate_structured` repair) | Trước khi đưa profile vào `PROFILES`, chạy bộ prompt quiz thật và đối chiếu tỉ lệ `repaired=True` |
| Mở `model_profile` trong payload thành lỗ chọn model tuỳ ý | `enum` trong contract + allowlist catalog + phân quyền; không bao giờ nhận `base_url`/`api_key` |

---

## 7. Vì sao đáng làm (phần cho báo cáo)

`llm_usage_logs` đã thiết kế để trả lời "AI tốn bao nhiêu, cho ai, cho khoá nào" nhưng hôm nay ghi `cost_usd = 0` mọi dòng và bỏ trắng toàn bộ đường enrichment. Khi model trở thành thuộc tính per-task — và về sau per-request — thì so sánh Gemini vs DeepSeek chạy được trên **cùng** tập LO, **cùng** context, trong **cùng** một lần chạy, thay vì "tuần này chạy Gemini, restart rồi tuần sau chạy DeepSeek" với nội dung đã khác. Đó là khác biệt giữa một bảng số liệu có ý nghĩa và một bảng số liệu không kiểm soát được biến.
