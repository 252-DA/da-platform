"""Settings — reuses document_chunk.infrastructure.config.Settings wholesale
(same pattern as worker/worker/config.py) rather than redeclaring SqlConfig /
QdrantConfig / EmbedderConfig / McpConfig. Only exposes the sub-configs
mcp-service actually needs; deliberately omits neo4j/minio/redis/parser/
chunker/llm — this process never touches those.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from document_chunk.infrastructure.config import Settings as CoreSettings


class McpServiceSettings(BaseSettings):
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
    def sql(self):
        return self.core.sql

    @property
    def qdrant(self):
        return self.core.qdrant

    @property
    def embedder(self):
        return self.core.embedder

    @property
    def mcp(self):
        return self.core.mcp

    @property
    def metrics(self):
        return self.core.metrics


@lru_cache
def get_settings() -> McpServiceSettings:
    return McpServiceSettings()
