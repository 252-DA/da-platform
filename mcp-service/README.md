# mcp-service

MCP delivery for course-context retrieval, split out of
`packages-ai/src/document_chunk/delivery/mcp`. Exposes two tools —
`search_course_chunks` and `retrieve_quiz_context` — used by
`content-generation-worker` for grounded quiz/content generation.

## Why this is a separate service

- `packages-ai`'s old MCP delivery was bundled into the same package as
  domain/adapters/other delivery layers. Splitting it lets this process have
  its own lifecycle, dependencies, and Compose health checks.
- Verified the two tools never touch `graph_store`/Neo4j — this service has
  no Neo4j dependency, unlike the old bundled setup where `mcp-server` in
  Compose waited on `neo4j` for no functional reason.
- Embedding is remote (`GrpcEmbedder` via `da-service-sdk`) — this process
  never loads BGE in-process.

## Layout

- `src/mcp_service/config.py` — wraps `document_chunk.infrastructure.config.Settings`, same pattern as `worker/worker/config.py`.
- `src/mcp_service/container.py` — composition root: Postgres + Qdrant + `GrpcEmbedder`, no Neo4j/MinIO/BullMQ/parsers/chunker.
- `src/mcp_service/delivery/server.py` — `create_mcp_server()` + `serve()`, ported near-verbatim from packages-ai's old `delivery/mcp/server.py`.

## Status

`GrpcEmbedder` (in `packages-ai/src/document_chunk/adapters/embedders/grpc_embedder.py`)
is still a `NotImplementedError` stub. This service's wiring is complete and
correct, but `mcp-service` will not actually start until that adapter is
implemented — see `docs/embedding-service-migration.md` §9 step 8 in
`da-platform`.

## Running locally

```
uv sync
uv run mcp-service
```

Requires `../packages-ai` and `../service-sdk` as sibling directories (path
dependencies).
