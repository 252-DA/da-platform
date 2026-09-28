"""Unit tests for EmbeddingClient."""

from __future__ import annotations

import concurrent.futures
from typing import Any

import grpc
import pytest

from da_service_sdk.client import EmbeddingClient
from da_service_sdk.generated.da_platform.embedding.v1 import (
    embedding_pb2,
    embedding_pb2_grpc,
)


class FakeEmbeddingServicer(embedding_pb2_grpc.EmbeddingServiceServicer):
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def Embed(self, request: embedding_pb2.EmbedRequest, context: Any) -> embedding_pb2.EmbedResponse:  # noqa: N802
        self.calls.append(list(request.texts))
        vectors = [
            embedding_pb2.Vector(values=[float(index + 1), float(len(text)), float(len(text) + index)])
            for index, text in enumerate(request.texts)
        ]
        return embedding_pb2.EmbedResponse(
            request_id=request.request_id,
            vectors=vectors,
            model_name="demo-model",
            dimension=3,
        )

    def GetModelInfo(self, request: embedding_pb2.GetModelInfoRequest, context: Any) -> embedding_pb2.GetModelInfoResponse:  # noqa: N802
        return embedding_pb2.GetModelInfoResponse(
            model_name="demo-model",
            dimension=3,
            max_batch_size=32,
            max_token_length=1024,
        )


def test_embed_splits_33_texts_into_two_rpc_batches() -> None:
    server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=1))
    servicer = FakeEmbeddingServicer()
    embedding_pb2_grpc.add_EmbeddingServiceServicer_to_server(servicer, server)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()

    try:
        with EmbeddingClient(f"127.0.0.1:{port}") as client:
            texts = [f"text-{index}" for index in range(33)]
            result = client.embed(texts)

        assert result.request_id
        assert len(result.vectors) == 33
        assert result.model_name == "demo-model"
        assert result.dimension == 3
        assert servicer.calls == [texts[:32], texts[32:]]
        assert [vector[0] for vector in result.vectors][:5] == [1.0, 2.0, 3.0, 4.0, 5.0]
        assert len(result.vectors) == 33
    finally:
        server.stop(None)
