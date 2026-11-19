"""Settings — reuses document_chunk.infrastructure.config.Settings wholesale,
same pattern as worker/worker/config.py and mcp_service/config.py. Exposes
only `app`, `parser` and `metrics` — this process never touches
sql/qdrant/neo4j/minio/redis/embedder/llm/mcp.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from document_chunk.infrastructure.config import Settings as CoreSettings


class InspectorSettings(BaseSettings):
    core: CoreSettings = Field(default_factory=CoreSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @property
    def app(self):
        return self.core.app

    @property
    def parser(self):
        return self.core.parser

    @property
    def chunker(self):
        return self.core.chunker

    @property
    def metrics(self):
        return self.core.metrics


@lru_cache
def get_settings() -> InspectorSettings:
    return InspectorSettings()
