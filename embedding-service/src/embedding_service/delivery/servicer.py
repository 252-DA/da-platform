"""gRPC servicer for EmbeddingService.

Wire contract: service-sdk/proto/da_platform/embedding/v1/embedding.proto.
Status-code mapping and consistency rules: docs/embedding-service-migration.md §4/§10.

The servicer validates RPC boundaries, serializes model inference, translates
runtime failures to gRPC status codes, and records service metrics. Health is
wired separately in delivery/server.py.
"""

from __future__ import annotations

import time
import threading

import grpc

from da_service_sdk.generated.da_platform.embedding.v1 import (
    embedding_pb2,
    embedding_pb2_grpc,
)
from embedding_service.runtime.base import EmbeddingRuntime
from embedding_service.metrics import (
    INFERENCE_DURATION_SECONDS,
    INFLIGHT_REQUESTS,
    RPC_BATCH_SIZE,
    RPC_REQUESTS_TOTAL,
)


class EmbeddingServicer(embedding_pb2_grpc.EmbeddingServiceServicer):
    def __init__(
        self,
        runtime: EmbeddingRuntime,
        max_rpc_batch_size: int,
        max_token_length: int | None = None,
    ) -> None:
        self._runtime = runtime
        self._max_rpc_batch_size = max_rpc_batch_size
        self._max_token_length = max_token_length or getattr(runtime, "max_token_length", 0)
        self._inference_lock = threading.Semaphore(1)

    def Embed(self, request, context):  # noqa: N802 (gRPC-generated method name convention)
        batch_size = len(request.texts)
        RPC_BATCH_SIZE.observe(batch_size)
        if not 1 <= batch_size <= self._max_rpc_batch_size:
            self._record_rpc("Embed", grpc.StatusCode.INVALID_ARGUMENT)
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"texts must contain 1..{self._max_rpc_batch_size} items",
            )

        INFLIGHT_REQUESTS.inc()
        started = time.perf_counter()
        try:
            with self._inference_lock:
                vectors = self._runtime.encode(list(request.texts))

            if len(vectors) != batch_size or any(
                len(vector) != self._runtime.dimension for vector in vectors
            ):
                raise RuntimeError("runtime returned vectors with an invalid shape")

            self._record_rpc("Embed", grpc.StatusCode.OK)
            return embedding_pb2.EmbedResponse(
                request_id=request.request_id,
                vectors=[embedding_pb2.Vector(values=vector) for vector in vectors],
                model_name=self._runtime.model_name,
                dimension=self._runtime.dimension,
            )
        except grpc.RpcError:
            raise
        except Exception as exc:
            self._record_rpc("Embed", grpc.StatusCode.UNAVAILABLE)
            context.abort(grpc.StatusCode.UNAVAILABLE, f"embedding runtime failed: {exc}")
        finally:
            INFLIGHT_REQUESTS.dec()
            INFERENCE_DURATION_SECONDS.labels(model=self._runtime.model_name).observe(
                time.perf_counter() - started
            )

    def GetModelInfo(self, request, context):  # noqa: N802
        del request
        self._record_rpc("GetModelInfo", grpc.StatusCode.OK)
        return embedding_pb2.GetModelInfoResponse(
            model_name=self._runtime.model_name,
            dimension=self._runtime.dimension,
            max_batch_size=self._max_rpc_batch_size,
            max_token_length=self._max_token_length,
        )

    @staticmethod
    def _record_rpc(method: str, status_code: grpc.StatusCode) -> None:
        RPC_REQUESTS_TOTAL.labels(method=method, status_code=status_code.name).inc()
