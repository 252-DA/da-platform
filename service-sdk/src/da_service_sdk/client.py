"""Synchronous gRPC client for EmbeddingService.

Contract: docs/embedding-service-migration.md §4 in da-platform, or
proto/da_platform/embedding/v1/embedding.proto in this repo.

Responsibilities to implement here (not in callers):
  - Open a single grpc.Channel to `target` at construction time; expose
    __enter__/__exit__ and close() to release it.
  - Split an arbitrary-length text list into <=_MAX_RPC_BATCH_SIZE-item RPC
    batches, call Embed sequentially (NOT in parallel — the server enforces a
    semaphore of 1 for inference, concurrent calls just queue), and
    concatenate results while preserving input order.
  - Map grpc.RpcError status codes to the exceptions in exceptions.py:
      INVALID_ARGUMENT      -> InvalidRequestError      (no retry)
      UNAVAILABLE           -> ServiceUnavailableError  (retry, max _MAX_ATTEMPTS)
      RESOURCE_EXHAUSTED    -> ServiceOverloadedError   (retry, max _MAX_ATTEMPTS)
      DEADLINE_EXCEEDED     -> RequestTimeoutError       (no retry)
      other                 -> EmbeddingServiceError
  - Validate every Embed response: len(vectors) == len(batch), and every
    vector's length == dimension (from GetModelInfo, or from this response's
    own `dimension` field). Raise MalformedResponseError otherwise — never
    hand back a partial/malformed batch to embed()'s caller.
  - Per-RPC timeout: _RPC_TIMEOUT_SECONDS.

The generated stubs are used only at this boundary; callers receive the plain
Python types from da_service_sdk.models.
"""

from __future__ import annotations

import uuid

import grpc

from da_service_sdk.exceptions import (
    EmbeddingServiceError,
    InvalidRequestError,
    MalformedResponseError,
    RequestTimeoutError,
    ServiceOverloadedError,
    ServiceUnavailableError,
)
from da_service_sdk.generated.da_platform.embedding.v1 import (
    embedding_pb2,
    embedding_pb2_grpc,
)
from da_service_sdk.models import EmbedResult, ModelInfo

_MAX_RPC_BATCH_SIZE = 32
_RPC_TIMEOUT_SECONDS = 300
_MAX_ATTEMPTS = 2


class EmbeddingClient:
    def __init__(self, target: str) -> None:
        if not target.strip():
            raise ValueError("target must not be empty")
        self._target = target
        self._channel: grpc.Channel | None = grpc.insecure_channel(target)
        self._stub = embedding_pb2_grpc.EmbeddingServiceStub(self._channel)
        self._model_info: ModelInfo | None = None

    def get_model_info(self) -> ModelInfo:
        if self._is_closed():
            raise EmbeddingServiceError("client is closed")

        try:
            response = self._stub.GetModelInfo(
                embedding_pb2.GetModelInfoRequest(),
                timeout=_RPC_TIMEOUT_SECONDS,
            )
        except grpc.RpcError as exc:
            raise self._map_rpc_error(exc) from exc

        model_info = ModelInfo(
            model_name=response.model_name,
            dimension=response.dimension,
            max_batch_size=response.max_batch_size,
            max_token_length=response.max_token_length,
        )
        self._model_info = model_info
        return model_info

    def embed(self, texts: list[str]) -> EmbedResult:
        if self._is_closed():
            raise EmbeddingServiceError("client is closed")
        if not texts:
            raise InvalidRequestError("empty batch")

        model_info = self._model_info or self.get_model_info()

        batches = [texts[index : index + _MAX_RPC_BATCH_SIZE] for index in range(0, len(texts), _MAX_RPC_BATCH_SIZE)]
        all_vectors: list[list[float]] = []
        request_id = uuid.uuid4().hex

        for batch in batches:
            response = self._call_embed_batch(batch, request_id=request_id)
            self._validate_response(batch, response, model_info.dimension)
            all_vectors.extend([list(vector.values) for vector in response.vectors])

        return EmbedResult(
            request_id=request_id,
            vectors=all_vectors,
            model_name=model_info.model_name,
            dimension=model_info.dimension,
        )

    def close(self) -> None:
        if self._channel is None:
            return
        self._channel.close()
        self._channel = None
        self._stub = None

    def __enter__(self) -> "EmbeddingClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _call_embed_batch(self, batch: list[str], request_id: str) -> embedding_pb2.EmbedResponse:
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                return self._stub.Embed(
                    embedding_pb2.EmbedRequest(request_id=request_id, texts=batch),
                    timeout=_RPC_TIMEOUT_SECONDS,
                )
            except grpc.RpcError as exc:
                mapped = self._map_rpc_error(exc)
                if not self._should_retry(exc) or attempt >= _MAX_ATTEMPTS:
                    raise mapped from exc

        raise EmbeddingServiceError("unreachable")

    def _should_retry(self, exc: grpc.RpcError) -> bool:
        return exc.code() in {grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.RESOURCE_EXHAUSTED}

    def _map_rpc_error(self, exc: grpc.RpcError) -> EmbeddingServiceError:
        if exc.code() == grpc.StatusCode.INVALID_ARGUMENT:
            return InvalidRequestError(str(exc))
        if exc.code() == grpc.StatusCode.UNAVAILABLE:
            return ServiceUnavailableError(str(exc))
        if exc.code() == grpc.StatusCode.RESOURCE_EXHAUSTED:
            return ServiceOverloadedError(str(exc))
        if exc.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            return RequestTimeoutError(str(exc))
        return EmbeddingServiceError(str(exc))

    def _validate_response(
        self,
        batch: list[str],
        response: embedding_pb2.EmbedResponse,
        expected_dimension: int,
    ) -> None:
        if len(response.vectors) != len(batch):
            raise MalformedResponseError("vector count mismatch")
        if response.dimension not in (0, expected_dimension):
            raise MalformedResponseError("response dimension mismatch")

        for vector in response.vectors:
            if len(vector.values) != expected_dimension:
                raise MalformedResponseError("vector dimension mismatch")

    def _is_closed(self) -> bool:
        return self._channel is None
