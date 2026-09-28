"""OpenAI-compatible embeddings API runtime — thay BgeRuntime khi không muốn
giữ BGE-M3 trong RAM. Gọi POST {base_url}/embeddings theo chuẩn OpenAI nên
dùng được với OpenAI, DeepInfra, SiliconFlow, Ollama, vLLM, HF TEI...

Chỉ dùng thư viện chuẩn (urllib) để không thêm dependency vào uv.lock.

Vector trả về được L2-normalize cho khớp BgeRuntime (FlagEmbedding normalize
dense_vecs mặc định). Qdrant dùng COSINE nên kết quả search không đổi, nhưng
dữ liệu lưu vẫn cùng dạng nếu sau này đổi distance.

load() gửi một request thử để fail sớm khi sai URL/key/model hoặc số chiều
không khớp ModelConfig.dimension — health chỉ lên SERVING khi API dùng được.
"""

from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from embedding_service.config import ApiConfig, ModelConfig

_RETRYABLE_STATUS = frozenset({408, 409, 429, 500, 502, 503, 504})
_MAX_BACKOFF_SECONDS = 30.0


class ApiRuntime:
    def __init__(
        self,
        model_config: ModelConfig,
        api_config: ApiConfig,
        *,
        opener: Callable[..., Any] = urllib.request.urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_config.base_url:
            raise ValueError("API__BASE_URL is required when MODEL__BACKEND=openai")
        self._model_config = model_config
        self._api = api_config
        self._url = api_config.base_url.rstrip("/") + "/embeddings"
        self._opener = opener
        self._sleep = sleep
        self._loaded = False

    def load(self) -> None:
        self.encode(["ping"])
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def model_name(self) -> str:
        return self._api.model

    @property
    def dimension(self) -> int:
        return self._model_config.dimension

    @property
    def max_token_length(self) -> int:
        return self._model_config.max_length

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._api.batch_size):
            batch = texts[start : start + self._api.batch_size]
            vectors.extend(self._embed_batch(batch))
        return vectors

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        body: dict[str, Any] = {"model": self._api.model, "input": texts}
        if self._api.dimensions:
            body["dimensions"] = self._api.dimensions
        payload = self._post(body)
        try:
            items = sorted(payload["data"], key=lambda item: item["index"])
            vectors = [item["embedding"] for item in items]
        except (KeyError, TypeError) as exc:
            raise RuntimeError("embeddings API returned an unexpected payload") from exc

        if len(vectors) != len(texts):
            raise RuntimeError(
                f"embeddings API returned {len(vectors)} vectors for {len(texts)} texts"
            )
        for vector in vectors:
            if len(vector) != self.dimension:
                raise RuntimeError(
                    f"embeddings API returned dimension {len(vector)}, expected "
                    f"{self.dimension} (check API__MODEL / API__DIMENSIONS)"
                )
        return [_l2_normalize(vector) for vector in vectors]

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api.key:
            headers["Authorization"] = f"Bearer {self._api.key}"
        data = json.dumps(body).encode()

        for attempt in range(self._api.max_retries + 1):
            request = urllib.request.Request(self._url, data=data, headers=headers, method="POST")
            retry_after: float | None = None
            try:
                with self._opener(request, timeout=self._api.timeout_seconds) as response:
                    return json.load(response)
            except urllib.error.HTTPError as exc:
                detail = exc.read(500).decode(errors="replace")
                if exc.code not in _RETRYABLE_STATUS or attempt == self._api.max_retries:
                    raise RuntimeError(
                        f"embeddings API returned HTTP {exc.code}: {detail}"
                    ) from exc
                retry_after = _parse_retry_after(exc.headers)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if attempt == self._api.max_retries:
                    raise RuntimeError(f"embeddings API unreachable: {exc}") from exc
            self._sleep(min(retry_after or 2.0**attempt, _MAX_BACKOFF_SECONDS))
        raise AssertionError("unreachable")


def _parse_retry_after(headers: Any) -> float | None:
    value = headers.get("Retry-After") if headers else None
    try:
        return float(value) if value else None
    except ValueError:
        return None


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(math.fsum(value * value for value in vector))
    if norm == 0.0:
        raise RuntimeError("embeddings API returned a zero vector")
    return [float(value) / norm for value in vector]
