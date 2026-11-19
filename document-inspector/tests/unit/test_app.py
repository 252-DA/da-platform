"""Smoke tests for the document-inspector FastAPI app.

/documents/inspect and /documents/inspect/chunking need real sample files
(PDF/DOCX/PPTX/Markdown) to exercise meaningfully — add fixtures under
tests/fixtures/ and write those once you have some. The health check needs
no fixtures, so it's written here as a real (not skipped) test — it also
doubles as a check that the app boots: imports resolve and build_parsers()
runs without needing a DB connection.
"""

from fastapi.testclient import TestClient

from document_inspector.delivery.app import app


def test_health_check_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_inspect_document_rejects_unsupported_extension() -> None:
    client = TestClient(app)
    response = client.post(
        "/documents/inspect",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == 400


def test_structural_markdown_inspection_reports_tokens(tmp_path, monkeypatch):
    from tokenizers import Tokenizer, models, pre_tokenizers
    from document_inspector.config import get_settings
    tokenizer = Tokenizer(models.WordLevel({'[UNK]': 0}, unk_token='[UNK]'))
    tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
    path = tmp_path/'tokenizer.json'
    tokenizer.save(str(path))
    monkeypatch.setenv('CHUNKER__TOKENIZER_PATH', str(path))
    get_settings.cache_clear()
    try:
        response = TestClient(app).post('/documents/inspect/chunking',
            data={'chunker': 'structural'},
            files={'file': ('test.md', b'# Chapter\n\nUseful content.\n', 'text/markdown')})
        assert response.status_code == 200, response.text
        data = response.json()
        assert data['stats']['chunker_used'] == 'StructuralChunker'
        assert data['stats']['token_max'] > 0
        assert data['stats']['chunks_over_max'] == 0
        assert data['chunks'][0]['heading_path'] == ['Chapter']
    finally:
        get_settings.cache_clear()
