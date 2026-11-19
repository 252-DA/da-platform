# embedding-service

Standalone gRPC service serving BGE-M3 text embeddings. The only process in
da-platform that loads the model — `document-worker` and `mcp-service` call
it remotely via `da-service-sdk`'s `EmbeddingClient`, they never load BGE
in-process.

## Layout

- `src/embedding_service/config.py` — pydantic-settings, `GRPC__*` / `METRICS__*` / `MODEL__*` / `API__*` env vars.
- `src/embedding_service/runtime/bge_runtime.py` — model load + encode, no dependency on packages-ai or any storage layer.
- `src/embedding_service/runtime/api_runtime.py` — same contract, backed by an OpenAI-compatible embeddings API (no model in RAM).
- `src/embedding_service/delivery/servicer.py` — `EmbeddingService` gRPC servicer, enforces the inference semaphore.
- `src/embedding_service/delivery/server.py` — process entrypoint, health-check lifecycle (`NOT_SERVING` → `SERVING`).
- `src/embedding_service/metrics.py` — Prometheus metric definitions.

## Baseline (do not change without updating docs/embedding-service-migration.md)

BGE-M3, dimension 1024, encode batch size 4, max_length 1024. RPC batch limit
32 is a separate, outer request-gathering limit — not the model's encode
batch size.

## Backends

`MODEL__BACKEND` picks where vectors come from; the gRPC contract is the same
either way, so clients (`document-worker`, `mcp-service`) need no change.

| Backend | RAM | Config |
| --- | --- | --- |
| `bge` (default) | ~3 GB (BGE-M3 on CPU) | `MODEL__BGE_MODEL`, downloads to `HF_HOME` on first start |
| `openai` | ~100 MB | `API__BASE_URL`, `API__KEY`, `API__MODEL`, optional `API__DIMENSIONS` |

With `openai`, startup sends one probe request and only reports `SERVING` if
the API answers with `MODEL__DIMENSION` (1024) floats. Keep
`API__MODEL=BAAI/bge-m3` on a provider that hosts it to stay in the same
vector space as `bge`; any other model means re-indexing Qdrant.

## Running locally

```
uv sync
uv run embedding-service
```

Requires `../service-sdk` to exist as a sibling directory (path dependency,
see `[tool.uv.sources]` in pyproject.toml).

## Tests

```
uv run pytest tests/unit -q
```

Real-BGE smoke tests are marked `slow` and excluded from regular CI — see
docs/embedding-service-migration.md §17 in `da-platform`.
