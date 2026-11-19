"""Unit tests for the OpenAI-compatible embeddings API runtime."""

from __future__ import annotations

import io
import json
import math
import urllib.error

import pytest

from embedding_service.config import ApiConfig, ModelConfig, Settings
from embedding_service.delivery.server import build_runtime
from embedding_service.runtime.api_runtime import ApiRuntime
from embedding_service.runtime.bge_runtime import BgeRuntime


class FakeOpener:
    """Stands in for urllib.request.urlopen; replays queued responses."""

    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)
        self.requests: list[dict] = []

    def __call__(self, request, timeout):
        self.requests.append(
            {
                "url": request.full_url,
                "headers": dict(request.header_items()),
                "body": json.loads(request.data),
                "timeout": timeout,
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        if callable(response):
            response = response(self.requests[-1]["body"])
        return io.BytesIO(json.dumps(response).encode())


def embeddings_for(body: dict) -> dict:
    # Reverse order on purpose: the runtime must sort by "index".
    items = [
        {"index": index, "embedding": [3.0, 4.0 + index, 0.0]}
        for index, _ in enumerate(body["input"])
    ]
    return {"data": list(reversed(items))}


def http_error(code: int, headers: dict | None = None) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://api.test/v1/embeddings", code, "err", headers or {}, io.BytesIO(b"boom")
    )


def make_runtime(opener: FakeOpener, **api_overrides) -> tuple[ApiRuntime, list[float]]:
    sleeps: list[float] = []
    api = ApiConfig(base_url="https://api.test/v1/", key="sk-test", **api_overrides)
    runtime = ApiRuntime(ModelConfig(dimension=3), api, opener=opener, sleep=sleeps.append)
    return runtime, sleeps


def test_encode_batches_requests_and_keeps_input_order() -> None:
    opener = FakeOpener(embeddings_for, embeddings_for)
    runtime, _ = make_runtime(opener, batch_size=2)

    vectors = runtime.encode(["a", "b", "c"])

    assert [len(request["body"]["input"]) for request in opener.requests] == [2, 1]
    assert opener.requests[0]["url"] == "https://api.test/v1/embeddings"
    assert opener.requests[0]["headers"]["Authorization"] == "Bearer sk-test"
    assert opener.requests[0]["body"] == {"model": "BAAI/bge-m3", "input": ["a", "b"]}
    assert vectors[0] == pytest.approx([0.6, 0.8, 0.0])
    assert vectors[1] == pytest.approx([3 / math.sqrt(34), 5 / math.sqrt(34), 0.0])
    assert vectors[2] == pytest.approx([0.6, 0.8, 0.0])


def test_dimensions_sent_only_when_configured_and_auth_omitted_without_key() -> None:
    opener = FakeOpener(embeddings_for)
    runtime = ApiRuntime(
        ModelConfig(dimension=3),
        ApiConfig(base_url="http://ollama:11434/v1", model="bge-m3", dimensions=3),
        opener=opener,
    )

    runtime.encode(["a"])

    assert opener.requests[0]["body"]["dimensions"] == 3
    assert "Authorization" not in opener.requests[0]["headers"]


def test_retries_rate_limit_and_honours_retry_after() -> None:
    opener = FakeOpener(http_error(429, {"Retry-After": "7"}), http_error(503), embeddings_for)
    runtime, sleeps = make_runtime(opener)

    assert len(runtime.encode(["a"])) == 1
    assert sleeps == [7.0, 2.0]


def test_retries_network_errors_then_gives_up() -> None:
    opener = FakeOpener(*(urllib.error.URLError("down") for _ in range(4)))
    runtime, sleeps = make_runtime(opener, max_retries=3)

    with pytest.raises(RuntimeError, match="unreachable"):
        runtime.encode(["a"])
    assert sleeps == [1.0, 2.0, 4.0]


def test_client_errors_are_not_retried() -> None:
    opener = FakeOpener(http_error(401))
    runtime, sleeps = make_runtime(opener)

    with pytest.raises(RuntimeError, match="HTTP 401: boom"):
        runtime.encode(["a"])
    assert sleeps == []


def test_dimension_mismatch_fails_load() -> None:
    opener = FakeOpener({"data": [{"index": 0, "embedding": [1.0, 0.0]}]})
    runtime, _ = make_runtime(opener)

    with pytest.raises(RuntimeError, match="dimension 2, expected 3"):
        runtime.load()
    assert not runtime.is_loaded


def test_load_probes_api() -> None:
    opener = FakeOpener(embeddings_for)
    runtime, _ = make_runtime(opener)

    runtime.load()

    assert runtime.is_loaded
    assert opener.requests[0]["body"]["input"] == ["ping"]


def test_requires_base_url() -> None:
    with pytest.raises(ValueError, match="API__BASE_URL"):
        ApiRuntime(ModelConfig(), ApiConfig())


def test_build_runtime_selects_backend_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL__BACKEND", "openai")
    monkeypatch.setenv("API__BASE_URL", "https://api.test/v1")
    monkeypatch.setenv("API__DIMENSIONS", "")  # compose passes "" for unset .env vars

    runtime = build_runtime(Settings())

    assert isinstance(runtime, ApiRuntime)
    assert runtime.model_name == "BAAI/bge-m3"


def test_build_runtime_defaults_to_bge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MODEL__BACKEND", raising=False)

    assert isinstance(build_runtime(Settings()), BgeRuntime)
