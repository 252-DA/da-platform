"""Contract the servicer and server depend on — implemented by BgeRuntime
(model in-process) and ApiRuntime (OpenAI-compatible embeddings API)."""

from __future__ import annotations

from typing import Protocol


class EmbeddingRuntime(Protocol):
    @property
    def model_name(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    @property
    def max_token_length(self) -> int: ...

    def load(self) -> None:
        """Called once at startup, before health flips to SERVING."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Dense vectors in input order. Raises on failure."""
