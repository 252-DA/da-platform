"""Prometheus metrics for embedding-service, exposed on METRICS__PORT
(default 9095). Definitions only — wire up .observe()/.inc()/.set() calls
from delivery/servicer.py and delivery/server.py.
"""

from prometheus_client import Counter, Gauge, Histogram

MODEL_LOAD_SECONDS = Histogram(
    "embedding_service_model_load_seconds",
    "Time to load the BGE-M3 model at startup",
)

INFERENCE_DURATION_SECONDS = Histogram(
    "embedding_service_inference_duration_seconds",
    "encode() latency per batch",
    ["model"],
)

RPC_REQUESTS_TOTAL = Counter(
    "embedding_service_rpc_requests_total",
    "Embed/GetModelInfo RPCs by resulting gRPC status code",
    ["method", "status_code"],
)

RPC_BATCH_SIZE = Histogram(
    "embedding_service_rpc_batch_size",
    "Number of texts per Embed request",
    buckets=(1, 2, 4, 8, 16, 32),
)

INFLIGHT_REQUESTS = Gauge(
    "embedding_service_inflight_requests",
    "Embed RPCs currently being processed",
)

PROCESS_RSS_BYTES = Gauge(
    "embedding_service_process_rss_bytes",
    "Resident set size of this process",
)
