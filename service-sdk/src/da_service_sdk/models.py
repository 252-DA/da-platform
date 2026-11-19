"""Plain-Python request/response types.

Callers should not touch generated pb2 messages directly — EmbeddingClient
converts to/from these at the boundary, so the rest of the codebase (and
packages-ai's GrpcEmbedder in particular) never imports anything from
`da_service_sdk.generated`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    model_name: str
    dimension: int
    max_batch_size: int
    max_token_length: int


@dataclass(frozen=True)
class EmbedResult:
    request_id: str
    vectors: list[list[float]]
    model_name: str
    dimension: int
