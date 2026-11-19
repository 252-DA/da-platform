"""Unit tests for the embedding gRPC servicer."""

from __future__ import annotations

import concurrent.futures
import threading
import time

import grpc
import pytest

from da_service_sdk.generated.da_platform.embedding.v1 import embedding_pb2
from embedding_service.delivery.servicer import EmbeddingServicer


class AbortError(Exception):
    def __init__(self, code: grpc.StatusCode, details: str) -> None:
        super().__init__(details)
        self.code = code
        self.details = details


class FakeContext:
    def abort(self, code: grpc.StatusCode, details: str) -> None:
        raise AbortError(code, details)


class FakeRuntime:
    model_name = "fake-model"
    dimension = 3
    max_token_length = 128

    def __init__(self, failure: Exception | None = None, delay: float = 0.0) -> None:
        self.failure = failure
        self.delay = delay
        self.active = 0
        self.max_active = 0
        self._lock = threading.Lock()

    def encode(self, texts: list[str]) -> list[list[float]]:
        if self.failure:
            raise self.failure
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            time.sleep(self.delay)
            return [[float(index), float(len(text)), 1.0] for index, text in enumerate(texts)]
        finally:
            with self._lock:
                self.active -= 1


def test_embed_rejects_empty_batch_with_invalid_argument() -> None:
    servicer = EmbeddingServicer(FakeRuntime(), max_rpc_batch_size=32)

    with pytest.raises(AbortError) as exc_info:
        servicer.Embed(embedding_pb2.EmbedRequest(), FakeContext())

    assert exc_info.value.code == grpc.StatusCode.INVALID_ARGUMENT


def test_embed_rejects_oversized_batch_with_invalid_argument() -> None:
    servicer = EmbeddingServicer(FakeRuntime(), max_rpc_batch_size=32)
    request = embedding_pb2.EmbedRequest(texts=["x"] * 33)

    with pytest.raises(AbortError) as exc_info:
        servicer.Embed(request, FakeContext())

    assert exc_info.value.code == grpc.StatusCode.INVALID_ARGUMENT


def test_embed_returns_vectors_in_request_order() -> None:
    servicer = EmbeddingServicer(FakeRuntime(), max_rpc_batch_size=32)
    request = embedding_pb2.EmbedRequest(request_id="request-1", texts=["a", "longer"])

    response = servicer.Embed(request, FakeContext())

    assert response.request_id == "request-1"
    assert response.model_name == "fake-model"
    assert response.dimension == 3
    assert [list(vector.values) for vector in response.vectors] == [
        [0.0, 1.0, 1.0],
        [1.0, 6.0, 1.0],
    ]


def test_runtime_failure_maps_to_unavailable() -> None:
    servicer = EmbeddingServicer(FakeRuntime(failure=RuntimeError("model failed")), 32)

    with pytest.raises(AbortError) as exc_info:
        servicer.Embed(embedding_pb2.EmbedRequest(texts=["x"]), FakeContext())

    assert exc_info.value.code == grpc.StatusCode.UNAVAILABLE
    assert "model failed" in exc_info.value.details


def test_get_model_info_does_not_infer() -> None:
    runtime = FakeRuntime()
    servicer = EmbeddingServicer(runtime, max_rpc_batch_size=32)

    response = servicer.GetModelInfo(embedding_pb2.GetModelInfoRequest(), FakeContext())

    assert response.model_name == "fake-model"
    assert response.dimension == 3
    assert response.max_batch_size == 32
    assert response.max_token_length == 128
    assert runtime.active == 0


def test_concurrent_embed_calls_are_serialized() -> None:
    runtime = FakeRuntime(delay=0.05)
    servicer = EmbeddingServicer(runtime, max_rpc_batch_size=32)

    def call(text: str) -> None:
        servicer.Embed(embedding_pb2.EmbedRequest(texts=[text]), FakeContext())

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(call, ["first", "second"]))

    assert runtime.max_active == 1
