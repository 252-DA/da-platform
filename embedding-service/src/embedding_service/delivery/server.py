"""Process entrypoint: build the gRPC server, load the model once, then flip
health to SERVING. See docs/embedding-service-migration.md §9 step 4.

Startup sequence (do not reorder):
  1. Build the grpc.server with GrpcConfig.max_workers threads, register
     EmbeddingServicer and a standard health.HealthServicer (from
     grpc_health.v1.health), reporting NOT_SERVING for both "" (overall) and
     "da_platform.embedding.v1.EmbeddingService".
  2. Start the socket (server.add_insecure_port + server.start()) so the
     health check is reachable — still NOT_SERVING at this point.
  3. Call runtime.load() synchronously — for MODEL__BACKEND=bge this is the
     ~2GB model load, done once here, not lazily inside the first request;
     for MODEL__BACKEND=openai it is one probe request to the embeddings API.
  4. Flip health.set("", SERVING) and
     health.set("da_platform.embedding.v1.EmbeddingService", SERVING).
  5. Start the Prometheus metrics HTTP server on MetricsConfig.port.
  6. Block on server.wait_for_termination().

Thread pool: GrpcConfig.max_workers (4). Inference itself is still
serialized by EmbeddingServicer's semaphore — the thread pool size is about
not blocking GetModelInfo/health RPCs while an Embed call is in flight, not
about parallel inference.
"""

from __future__ import annotations

import concurrent.futures
import time

import grpc
import structlog
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

from da_service_sdk.generated.da_platform.embedding.v1 import embedding_pb2_grpc
from embedding_service.config import Settings, get_settings
from embedding_service.delivery.servicer import EmbeddingServicer
from embedding_service.metrics import MODEL_LOAD_SECONDS
from embedding_service.runtime.base import EmbeddingRuntime
from embedding_service.runtime.bge_runtime import BgeRuntime


def build_runtime(settings: Settings) -> EmbeddingRuntime:
    if settings.model.backend == "openai":
        from embedding_service.runtime.api_runtime import ApiRuntime

        return ApiRuntime(settings.model, settings.api)
    return BgeRuntime(settings.model)


def main() -> None:
    settings = get_settings()
    logger = structlog.get_logger(__name__)
    server = grpc.server(
        concurrent.futures.ThreadPoolExecutor(max_workers=settings.grpc.max_workers)
    )
    service_name = "da_platform.embedding.v1.EmbeddingService"
    health_servicer = health.HealthServicer()
    health_servicer.set("", health_pb2.HealthCheckResponse.NOT_SERVING)
    health_servicer.set(service_name, health_pb2.HealthCheckResponse.NOT_SERVING)
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    runtime = build_runtime(settings)
    embedding_pb2_grpc.add_EmbeddingServiceServicer_to_server(
        EmbeddingServicer(
            runtime,
            max_rpc_batch_size=settings.model.max_rpc_batch_size,
            max_token_length=settings.model.max_length,
        ),
        server,
    )

    address = f"{settings.grpc.host}:{settings.grpc.port}"
    if server.add_insecure_port(address) == 0:
        raise RuntimeError(f"could not bind embedding gRPC server to {address}")
    server.start()
    logger.info("embedding_service.started", address=address, status="NOT_SERVING")

    try:
        started = time.perf_counter()
        runtime.load()
        MODEL_LOAD_SECONDS.observe(time.perf_counter() - started)
        health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
        health_servicer.set(service_name, health_pb2.HealthCheckResponse.SERVING)
        if settings.metrics.enabled:
            from prometheus_client import start_http_server

            start_http_server(settings.metrics.port)
        logger.info(
            "embedding_service.ready",
            backend=settings.model.backend,
            model=runtime.model_name,
        )
        server.wait_for_termination()
    finally:
        health_servicer.set("", health_pb2.HealthCheckResponse.NOT_SERVING)
        health_servicer.set(service_name, health_pb2.HealthCheckResponse.NOT_SERVING)
        server.stop(grace=None)


if __name__ == "__main__":
    main()
