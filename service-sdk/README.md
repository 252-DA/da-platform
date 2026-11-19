# da-service-sdk

Typed gRPC clients and generated protobuf code for da-platform internal
services. Currently ships `EmbeddingClient` for `embedding-service`.

## Layout

- `proto/` — canonical `.proto` sources. Wire package: `da_platform.embedding.v1`.
- `src/da_service_sdk/generated/` — output of `scripts/generate_proto.py`. Committed, never hand-edited.
- `src/da_service_sdk/` — hand-written client, models, exceptions.
- `tests/unit/` — client tests against an in-process fake server, no real embedding-service dependency.

## Regenerating stubs

```
uv run python scripts/generate_proto.py
git diff --exit-code   # CI fails here if generated code is stale
```

## Versioning

SemVer. `0.1.x` = compatible changes to `da_platform.embedding.v1`. A
breaking wire change gets a new package (`da_platform.embedding.v2`) and a
major version bump.

## Consuming this package

Not published to an index yet. Consumers pin by commit via a Git submodule
(local dev / Compose) and via `.github/actions/materialize@<sha>` (CI) —
these are two independent pins that must be updated separately. See
`docs/embedding-service-migration.md` §5 in `da-platform` for the full
distribution mechanism and the checklist for bumping this SDK.
