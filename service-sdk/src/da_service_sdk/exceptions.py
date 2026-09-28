"""Exceptions raised by EmbeddingClient.

These are SDK-owned and independent of any consumer's domain Result type.
packages-ai's GrpcEmbedder adapter is the one place responsible for catching
these and translating them into `Err(EmbedError)` before returning control to
worker/mcp-service — do not import domain types here, and do not let these
exceptions leak past that adapter boundary.
"""

from __future__ import annotations


class EmbeddingServiceError(Exception):
    """Base class for all errors raised by EmbeddingClient."""


class InvalidRequestError(EmbeddingServiceError):
    """Maps to gRPC INVALID_ARGUMENT — malformed request (empty or >32
    texts). Not retried."""


class ServiceUnavailableError(EmbeddingServiceError):
    """Maps to gRPC UNAVAILABLE — service not ready or unreachable. Retried
    up to the client's max attempts (2)."""


class ServiceOverloadedError(EmbeddingServiceError):
    """Maps to gRPC RESOURCE_EXHAUSTED — server shed the request. Retried up
    to the client's max attempts (2)."""


class RequestTimeoutError(EmbeddingServiceError):
    """Maps to gRPC DEADLINE_EXCEEDED — the 300s per-RPC budget was already
    spent, so this is not retried; let the caller's own retry policy
    (BullMQ job retry) handle it."""


class MalformedResponseError(EmbeddingServiceError):
    """Server returned a response that fails SDK-side validation — vector
    count or dimension mismatch against the request / GetModelInfo. Never
    hand a partial or malformed batch back to the caller."""
