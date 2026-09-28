"""Response models for the inspect endpoints — ported verbatim from
packages-ai/src/document_chunk/delivery/http/api.py.
"""

from __future__ import annotations

from pydantic import BaseModel

from document_chunk.domain.entities.document import DocumentType


class SectionInspect(BaseModel):
    index: int
    element_type: str
    heading: str | None
    heading_level: int
    page_number: int | None
    content_length: int
    content_preview: str
    has_images: bool


class ParseStats(BaseModel):
    total_sections: int
    page_count: int
    element_counts: dict[str, int]
    image_count: int
    total_content_length: int
    headings_outline: list[str]
    language: str | None
    parser_used: str
    parse_duration_ms: float


class ParseInspectResponse(BaseModel):
    file_name: str
    file_size_bytes: int
    stats: ParseStats
    sections: list[SectionInspect]


class ChunkInspect(BaseModel):
    index: int
    chunk_id: str
    heading_path: list[str]
    page_number: int | None
    content_type: str | None
    is_toc: bool
    char_count: int
    content_preview: str
    embedding_input_preview: str


class ChunkingStats(BaseModel):
    token_p50: int | None = None
    token_p95: int | None = None
    token_max: int | None = None
    chunks_over_max: int | None = None
    chunks_under_min: int | None = None
    toc_blocks_removed: int = 0
    lcp_merges: int = 0
    total_chunks: int
    toc_chunks: int
    chunker_used: str
    chunk_size_tokens: int | None
    chunk_overlap_tokens: int | None
    avg_chars: float
    min_chars: int
    max_chars: int
    parse_duration_ms: float
    chunk_duration_ms: float


class ChunkInspectResponse(BaseModel):
    file_name: str
    file_size_bytes: int
    stats: ChunkingStats
    chunks: list[ChunkInspect]


EXT_TO_DOC_TYPE: dict[str, DocumentType] = {
    ".pdf": DocumentType.PDF,
    ".docx": DocumentType.DOCX,
    ".pptx": DocumentType.PPTX,
    ".md": DocumentType.MARKDOWN,
    ".markdown": DocumentType.MARKDOWN,
}
