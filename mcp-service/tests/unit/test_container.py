"""Unit tests for McpServiceContainer wiring.

These should not hit real Postgres/Qdrant/embedding-service — construct the
container with fakes/mocks substituted via monkeypatching the adapter
imports, or refactor container.py to accept pre-built adapters if that proves
easier to test. Left unimplemented deliberately: GrpcEmbedder itself is still
a stub, so a real construction test can't pass yet — write this once
GrpcEmbedder exists.

Coverage worth having once unblocked:
  - search_chunks_use_case and retrieve_quiz_context_use_case share the same
    embedder/vector_store/metadata_store instances (no duplicate construction)
  - close() calls close() on metadata_store, vector_store and embedder, and
    tolerates a component that has no close() method
  - no graph_store / Neo4j import anywhere in this module (regression guard
    for docs/embedding-service-migration.md §9 step 11's "no Neo4j" decision)
"""

import pytest


@pytest.mark.skip(reason="TODO: blocked on GrpcEmbedder implementation")
def test_container_wires_shared_dependencies_once() -> None:
    ...


@pytest.mark.skip(reason="TODO: blocked on GrpcEmbedder implementation")
def test_close_is_tolerant_of_components_without_close() -> None:
    ...
