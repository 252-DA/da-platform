# document-inspector

Dev-only FastAPI tool to inspect parse/chunk quality — no storage, no DB, no
embedding. Ported from the two useful endpoints of packages-ai's old
`delivery/http/api.py` (`/documents/inspect`, `/documents/inspect/chunking`);
the rest of that API duplicated `core-api`'s business endpoints and was
retired, not kept anywhere.

Only meant to run via the Compose `tools` profile — never wire this into the
production request path.

## Endpoints

- `GET /health`
- `POST /documents/inspect` — raw parser output: sections, element types, headings, previews.
- `POST /documents/inspect/chunking` — chunk output per strategy (`heading` | `sentence` | `token` | `semantic`).

## Layout

- `src/document_inspector/config.py` — wraps `document_chunk.infrastructure.config.Settings`, exposes only `app`/`parser`/`metrics`.
- `src/document_inspector/container.py` — `build_parsers()`, no DB.
- `src/document_inspector/schemas.py` — response models, ported verbatim.
- `src/document_inspector/delivery/app.py` — the FastAPI app.

## Running locally

```
uv sync
uv run uvicorn document_inspector.delivery.app:app --reload --port 8002
```

Requires `../packages-ai` as a sibling directory (path dependency). Docs at
`http://localhost:8002/docs`.

## Tests

```
uv run pytest tests/unit -q
```

`/documents/inspect` and `/documents/inspect/chunking` need real sample
files to test meaningfully — add fixtures under `tests/fixtures/` as you
write those; the health check test needs none.
