"""Settings — mirrors the pydantic-settings convention used in packages-ai
(document_chunk.infrastructure.config): one BaseSettings subclass per
concern, combined with env_nested_delimiter="__" so e.g. GRPC__PORT maps to
settings.grpc.port.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    json_logs: bool = False

    model_config = SettingsConfigDict(env_prefix="APP_")


class GrpcConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 50051
    max_workers: int = 4  # thread pool size — không phải mức song song inference, xem ModelConfig

    model_config = SettingsConfigDict(env_prefix="GRPC_")


class MetricsConfig(BaseSettings):
    enabled: bool = True
    port: int = 9095

    model_config = SettingsConfigDict(env_prefix="METRICS_")


class ModelConfig(BaseSettings):
    """Baseline giữ nguyên từ packages-ai EmbedderConfig — không đổi khi tách
    sang service riêng. Xem docs/embedding-service-migration.md §9 bước 5."""

    # "bge": nạp BGE-M3 vào RAM của process (~3GB trên CPU).
    # "openai": gọi embeddings API tương thích OpenAI, không nạp model — xem ApiConfig.
    backend: Literal["bge", "openai"] = "bge"
    bge_model: str = "BAAI/bge-m3"
    bge_use_fp16: bool = True
    dimension: int = 1024
    encode_batch_size: int = 4  # batch size đưa vào model.encode()
    max_length: int = 1024      # max token length của model
    max_rpc_batch_size: int = 32  # giới hạn gom request ở tầng RPC, không phải encode batch

    model_config = SettingsConfigDict(env_prefix="MODEL_")


class ApiConfig(BaseSettings):
    """Embeddings API tương thích OpenAI (POST {base_url}/embeddings), dùng khi
    MODEL__BACKEND=openai. Giữ model = BAAI/bge-m3 ở provider có host model này
    thì vector cùng không gian với backend "bge" — đổi qua lại không cần index
    lại Qdrant. Đổi sang model khác (kể cả cùng 1024 chiều) thì phải index lại."""

    base_url: str | None = None  # vd. https://api.deepinfra.com/v1/openai
    key: str | None = None       # bỏ trống cho endpoint không cần auth (Ollama, TEI nội bộ)
    model: str = "BAAI/bge-m3"
    dimensions: int | None = None  # gửi field "dimensions" — chỉ đặt khi model hỗ trợ cắt chiều
    batch_size: int = 32           # số text mỗi HTTP request
    timeout_seconds: float = 60.0
    max_retries: int = 3           # retry cho 429/5xx/lỗi mạng, backoff lũy thừa

    model_config = SettingsConfigDict(env_prefix="API_")


class Settings(BaseSettings):
    app: AppConfig = Field(default_factory=AppConfig)
    grpc: GrpcConfig = Field(default_factory=GrpcConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)

    # env_ignore_empty: compose truyền "" cho biến .env không đặt → dùng default.
    model_config = SettingsConfigDict(env_nested_delimiter="__", env_ignore_empty=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
