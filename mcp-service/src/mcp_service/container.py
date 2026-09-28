"""Composition root for mcp-service. Same BaseWorkerContainer-style pattern
as worker/worker/container.py (build_* + a container tracking closables for
duck-typed shutdown), but wires only what the two MCP tools need: Postgres
(metadata), Qdrant (vector search) and GrpcEmbedder (remote embedding).

Deliberately absent, unlike packages-ai's old infrastructure/container.py:
  - graph_store / Neo4j — verified neither search_chunks nor
    retrieve_quiz_context touches graph_store. See
    docs/embedding-service-migration.md §2 and §9 step 11.
  - file_storage / MinIO, job_queue / BullMQ, parsers, chunker — this
    process only reads already-processed documents, it never ingests.

GrpcEmbedder performs the startup model-info check and owns the remote gRPC
channel; the container tracks it so shutdown closes that channel.
"""

from document_chunk.adapters.embedders.grpc_embedder import GrpcEmbedder
from document_chunk.adapters.metadata.postgres_metadata_store import PostgresMetadataStore
from document_chunk.adapters.vector_db.qdrant_adapter import QdrantAdapter
from document_chunk.application.use_cases.retrieve_quiz_context import RetrieveQuizContextUseCase
from document_chunk.application.use_cases.search_chunks import SearchChunksUseCase
from document_chunk.domain.ports.embedder import IEmbedder
from document_chunk.domain.ports.metadata_store import IMetadataStore
from document_chunk.domain.ports.vector_store import IVectorStore
from document_chunk.shared.logger import get_logger

from mcp_service.config import McpServiceSettings

logger = get_logger(__name__)


class McpServiceContainer:
    def __init__(self, settings: McpServiceSettings) -> None:
        self.settings = settings
        self._closables: list[tuple[str, object]] = []

        self.metadata_store: IMetadataStore = self._track(
            "metadata_store", PostgresMetadataStore(settings.sql)
        )
        self.vector_store: IVectorStore = self._track(
            "vector_store", QdrantAdapter(settings.qdrant)
        )
        self.embedder: IEmbedder = self._track(
            "embedder",
            GrpcEmbedder(settings.embedder, expected_dimension=settings.qdrant.vector_size),
        )

        self.search_chunks_use_case = SearchChunksUseCase(
            embedder=self.embedder,
            vector_store=self.vector_store,
        )
        self.retrieve_quiz_context_use_case = RetrieveQuizContextUseCase(
            metadata_store=self.metadata_store,
            semantic_search=self.search_chunks_use_case,
        )

    def _track(self, name: str, component):
        self._closables.append((name, component))
        return component

    def close(self) -> None:
        for name, component in reversed(self._closables):
            close = getattr(component, "close", None)
            if not callable(close):
                continue
            try:
                close()
            except Exception as exc:
                logger.warning(
                    "mcp_service_container.close_failed", component=name, error=str(exc)
                )


def build_container(settings: McpServiceSettings | None = None) -> McpServiceContainer:
    return McpServiceContainer(settings or McpServiceSettings())
