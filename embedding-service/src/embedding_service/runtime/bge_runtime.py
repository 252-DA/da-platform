"""BGE-M3 inference runtime — no dependency on packages-ai, DB, Redis, MinIO,
or Qdrant. This module is the only place in embedding-service that imports
FlagEmbedding.

Port the model-loading + encode logic from
packages-ai/src/document_chunk/adapters/embedders/bge_embedder.py, with two
deliberate changes:

  1. Drop the `document_chunk.shared.result.Result/Ok/Err` return type — this
     module must not import anything from packages-ai. Raise plain
     exceptions instead; delivery/servicer.py is what translates failures
     into gRPC status codes (see docs/embedding-service-migration.md §10).
  2. Model load stays lazy-once at the Python level (cached_property or
     equivalent works fine), but the *caller* must invoke load() eagerly
     during process startup — before the health service flips to SERVING —
     rather than relying on lazy load on first request. See
     delivery/server.py's startup sequence.

Baseline to preserve exactly (docs/embedding-service-migration.md §9 step 5):
  model = BAAI/bge-m3, dimension = 1024, encode batch_size = 4,
  max_length = 1024.

Concurrency: encode() must run under a semaphore of 1 — do not let two
encode() calls execute concurrently even though the gRPC thread pool has 4
workers. This mirrors why packages-ai's EmbedderConfig.batch_size is capped
at 4 today (CPU OOM risk when two encodes overlap). The semaphore belongs in
delivery/servicer.py, not here — this class should be a thin, stateless-ish
wrapper around the model.
"""

from __future__ import annotations

from functools import cached_property
from typing import Any

from embedding_service.config import ModelConfig


class BgeRuntime:
    def __init__(self, config: ModelConfig) -> None:
        self._config = config

    def load(self) -> None:
        """Load the model once. Call during server startup, not lazily."""
        _ = self._model

    @property
    def is_loaded(self) -> bool:
        return "_model" in self.__dict__

    @property
    def model_name(self) -> str:
        return self._config.bge_model

    @property
    def dimension(self) -> int:
        return self._config.dimension

    @property
    def max_token_length(self) -> int:
        return self._config.max_length

    @cached_property
    def _model(self) -> Any:
        try:
            from FlagEmbedding import BGEM3FlagModel
        except ImportError as exc:
            raise RuntimeError(
                "FlagEmbedding is required to load the BGE runtime"
            ) from exc

        return BGEM3FlagModel(
            self._config.bge_model,
            use_fp16=self._config.bge_use_fp16,
        )

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode texts to dense vectors, same order as input. Raises on
        failure — does not return a Result type, see module docstring."""
        if not texts:
            return []

        output = self._model.encode(
            texts,
            batch_size=self._config.encode_batch_size,
            max_length=self._config.max_length,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        dense_vectors = output["dense_vecs"]
        vectors = dense_vectors.tolist()

        if len(vectors) != len(texts):
            raise RuntimeError("BGE runtime returned an unexpected vector count")
        if any(len(vector) != self.dimension for vector in vectors):
            raise RuntimeError("BGE runtime returned an unexpected vector dimension")

        return [[float(value) for value in vector] for vector in vectors]
