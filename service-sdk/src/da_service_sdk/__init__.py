"""da-service-sdk — typed gRPC clients for da-platform internal services."""

from da_service_sdk.client import EmbeddingClient
from da_service_sdk.exceptions import (
    EmbeddingServiceError,
    InvalidRequestError,
    MalformedResponseError,
    RequestTimeoutError,
    ServiceOverloadedError,
    ServiceUnavailableError,
)
from da_service_sdk.models import EmbedResult, ModelInfo

__all__ = [
    "EmbeddingClient",
    "EmbedResult",
    "ModelInfo",
    "EmbeddingServiceError",
    "InvalidRequestError",
    "ServiceUnavailableError",
    "ServiceOverloadedError",
    "RequestTimeoutError",
    "MalformedResponseError",
]
