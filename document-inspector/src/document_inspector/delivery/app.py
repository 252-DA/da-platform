"""FastAPI app: dev-only inspection of parse/chunk quality — no storage, no
DB, no embedding. Ported from packages-ai's delivery/http/api.py
(inspect_document / inspect_chunking — the only two endpoints kept; the rest
of that API duplicated core-api and was retired, see
docs/embedding-service-migration.md §9 steps 12/13).

Only run via Compose profile `tools` — this is a dev tool, not part of the
production request path.
"""

from __future__ import annotations
from document_chunk.adapters.chunkers.structural.inspect import inspection_metrics

import tempfile
import time
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from document_chunk.adapters.chunkers.heading_chunker import HeadingChunker
from document_chunk.domain.entities.document import ElementType
from document_chunk.domain.ports.parser import IParser
from document_chunk.infrastructure.config import ChunkerConfig, LlamaIndexChunkerConfig
from document_chunk.shared.logger import get_logger, setup_logging

from document_inspector.config import get_settings
from document_inspector.container import build_parsers
from document_inspector.schemas import (
    EXT_TO_DOC_TYPE,
    ChunkInspect,
    ChunkInspectResponse,
    ChunkingStats,
    ParseInspectResponse,
    ParseStats,
    SectionInspect,
)

logger = get_logger(__name__)

_VERSION = "0.1.0"


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = _VERSION


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(level=settings.app.log_level, json_logs=settings.app.json_logs)

    app = FastAPI(
        title="Document Inspector",
        summary="Dev-only: inspect parse/chunk quality. No storage, no DB, no embedding.",
        version=_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.state.parsers = build_parsers(settings)
    return app


app = create_app()


def _get_parsers() -> list[IParser]:
    return app.state.parsers


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
    summary="Health check",
)
def health_check() -> HealthResponse:
    return HealthResponse()


@app.post(
    "/documents/inspect",
    response_model=ParseInspectResponse,
    tags=["inspect"],
    summary="Inspect parse quality — no storage, no chunking",
    description=(
        "Upload a document và xem raw parser output: sections, element types, headings, "
        "content previews. Không lưu DB, không chunk, không embed. "
        "Dùng để kiểm tra chất lượng parse trước khi full processing."
    ),
)
async def inspect_document(
    file: Annotated[
        UploadFile,
        File(description="PDF, DOCX, PPTX, hoặc Markdown để inspect."),
    ],
    preview_length: Annotated[
        int,
        Form(description="Số ký tự preview mỗi section (default 300, max 2000)."),
    ] = 300,
    parsers: list[IParser] = Depends(_get_parsers),
) -> ParseInspectResponse:
    original_file_name = _normalize_optional(file.filename)
    if original_file_name is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file name is required",
        )

    file_data = await file.read()
    if not file_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="uploaded file is empty",
        )

    preview_length = max(50, min(preview_length, 2000))

    suffix = Path(original_file_name).suffix.lower()
    doc_type = EXT_TO_DOC_TYPE.get(suffix)
    if doc_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: '{suffix}'. Supported: {sorted(EXT_TO_DOC_TYPE)}",
        )

    parser = next((p for p in parsers if p.supports(doc_type)), None)
    if parser is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No parser registered for {doc_type.value}",
        )

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_data)
            tmp_path = Path(tmp.name)

        t0 = time.perf_counter()
        result = parser.parse(tmp_path)
        parse_ms = round((time.perf_counter() - t0) * 1000, 1)

        if result.is_err():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Parse failed: {result.error}",
            )

        parsed = result.unwrap()

    finally:
        await file.close()
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()

    element_counts: dict[str, int] = {}
    for s in parsed.sections:
        key = s.element_type.value
        element_counts[key] = element_counts.get(key, 0) + 1

    headings_outline = [
        f"{'  ' * max(0, s.heading_level - 1)}{'#' * s.heading_level} {s.content}"
        for s in parsed.sections
        if s.element_type == ElementType.HEADING
    ]

    section_inspects = [
        SectionInspect(
            index=i,
            element_type=s.element_type.value,
            heading=s.heading,
            heading_level=s.heading_level,
            page_number=s.page_number,
            content_length=len(s.content),
            content_preview=s.content[:preview_length],
            has_images=bool(s.images),
        )
        for i, s in enumerate(parsed.sections)
    ]

    return ParseInspectResponse(
        file_name=original_file_name,
        file_size_bytes=len(file_data),
        stats=ParseStats(
            total_sections=len(parsed.sections),
            page_count=parsed.page_count,
            element_counts=element_counts,
            image_count=len(parsed.images),
            total_content_length=parsed.total_content_length,
            headings_outline=headings_outline,
            language=parsed.language,
            parser_used=type(parser).__name__,
            parse_duration_ms=parse_ms,
        ),
        sections=section_inspects,
    )


@app.post(
    "/documents/inspect/chunking",
    response_model=ChunkInspectResponse,
    tags=["inspect"],
    summary="Inspect chunking quality — no storage, no embedding",
    description=(
        "Upload a document và xem chunk output của từng chunker strategy: "
        "**heading** (custom HeadingChunker), **sentence** (LlamaIndex SentenceSplitter), "
        "**token** (LlamaIndex TokenTextSplitter), **semantic** (LlamaIndex SemanticSplitter — chậm, cần GPU/CPU embed). "
        "Không lưu DB, không embed vào pipeline chính. Dùng để so sánh chất lượng chunking."
    ),
)
async def inspect_chunking(
    file: Annotated[
        UploadFile,
        File(description="PDF, DOCX, PPTX, hoặc Markdown để inspect."),
    ],
    chunker: Annotated[
        Literal["heading", "structural", "sentence", "token", "semantic"],
        Form(description="Chunker strategy: heading | structural | sentence | token | semantic."),
    ] = "heading",
    chunk_size: Annotated[
        int,
        Form(description="Token chunk size cho LlamaIndex chunkers (default 375 ≈ 1500 chars). Bỏ qua với heading."),
    ] = 375,
    chunk_overlap: Annotated[
        int,
        Form(description="Token overlap cho LlamaIndex chunkers (default 50)."),
    ] = 50,
    preview_length: Annotated[
        int,
        Form(description="Số ký tự preview mỗi chunk (default 300, max 2000)."),
    ] = 300,
    parsers: list[IParser] = Depends(_get_parsers),
) -> ChunkInspectResponse:
    original_file_name = _normalize_optional(file.filename)
    if original_file_name is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file name is required")

    file_data = await file.read()
    if not file_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="uploaded file is empty")

    preview_length = max(50, min(preview_length, 2000))
    chunk_size = max(50, min(chunk_size, 4096))
    chunk_overlap = max(0, min(chunk_overlap, chunk_size // 2))

    suffix = Path(original_file_name).suffix.lower()
    doc_type = EXT_TO_DOC_TYPE.get(suffix)
    if doc_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: '{suffix}'. Supported: {sorted(EXT_TO_DOC_TYPE)}",
        )

    parser = next((p for p in parsers if p.supports(doc_type)), None)
    if parser is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No parser registered for {doc_type.value}",
        )

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_data)
            tmp_path = Path(tmp.name)

        t0 = time.perf_counter()
        parse_result = parser.parse(tmp_path)
        parse_ms = round((time.perf_counter() - t0) * 1000, 1)

        if parse_result.is_err():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Parse failed: {parse_result.error}",
            )

        parsed = parse_result.unwrap()

    finally:
        await file.close()
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()

    # Build chunker
    if chunker == "structural":
        from document_chunk.adapters.chunkers.structural import StructuralChunker
        try:
            _chunker = StructuralChunker(get_settings().chunker.model_copy(update={"strategy": "structural"}))
        except ValueError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        chunk_size_out = _chunker.config.max_tokens
        chunk_overlap_out = _chunker.config.overlap_tokens
    elif chunker == "heading":
        _chunker = HeadingChunker(ChunkerConfig())
        chunk_size_out: int | None = None
        chunk_overlap_out: int | None = None
    else:
        from document_chunk.adapters.chunkers.llamaindex_chunkers import (
            LlamaIndexSemanticChunker,
            LlamaIndexSentenceChunker,
            LlamaIndexTokenChunker,
        )
        llama_cfg = LlamaIndexChunkerConfig(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunk_size_out = chunk_size
        chunk_overlap_out = chunk_overlap
        if chunker == "sentence":
            _chunker = LlamaIndexSentenceChunker(llama_cfg)
        elif chunker == "token":
            _chunker = LlamaIndexTokenChunker(llama_cfg)
        else:
            _chunker = LlamaIndexSemanticChunker(LlamaIndexChunkerConfig())

    t1 = time.perf_counter()
    chunk_result = _chunker.chunk(parsed)
    chunk_ms = round((time.perf_counter() - t1) * 1000, 1)

    if chunk_result.is_err():
        err = chunk_result.error
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        if "chưa được cài" in str(err) or "Thiếu dependency" in str(err):
            status_code = status.HTTP_501_NOT_IMPLEMENTED
        raise HTTPException(status_code=status_code, detail=str(err))

    chunks = chunk_result.unwrap()

    char_counts = [len(c.content) for c in chunks] if chunks else [0]
    toc_count = sum(1 for c in chunks if c.metadata.content_type == "toc")

    return ChunkInspectResponse(
        file_name=original_file_name,
        file_size_bytes=len(file_data),
        stats=ChunkingStats(
            total_chunks=len(chunks),
            toc_chunks=toc_count,
            chunker_used=type(_chunker).__name__,
            chunk_size_tokens=chunk_size_out,
            chunk_overlap_tokens=chunk_overlap_out,
            avg_chars=round(sum(char_counts) / len(char_counts), 1),
            min_chars=min(char_counts),
            max_chars=max(char_counts),
            parse_duration_ms=parse_ms,
            chunk_duration_ms=chunk_ms,
            **inspection_metrics(chunks, _chunker, get_settings().chunker),
        ),
        chunks=[
            ChunkInspect(
                index=i,
                chunk_id=c.id,
                heading_path=list(c.metadata.heading_path),
                page_number=c.metadata.page_number,
                content_type=c.metadata.content_type,
                is_toc=c.metadata.content_type == "toc",
                char_count=len(c.content),
                content_preview=c.content[:preview_length],
                embedding_input_preview=c.embedding_input[:preview_length],
            )
            for i, c in enumerate(chunks)
        ],
    )
