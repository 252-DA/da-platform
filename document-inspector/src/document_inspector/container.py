"""No DB, no storage, no embedding — only parsers, used by
/documents/inspect and /documents/inspect/chunking. Identical in spirit to
worker/worker/container.py's build_parsers(), which is already DB-free;
document-inspector just never builds the rest (metadata_store, vector_store,
embedder, job_queue) at all.
"""

from document_chunk.adapters.parsers.adaptive_pdf_parser import AdaptivePdfParser
from document_chunk.adapters.parsers.docx_parser import DocxParser
from document_chunk.adapters.parsers.markdown_parser import MarkdownParser
from document_chunk.adapters.parsers.pptx_parser import PptxParser
from document_chunk.domain.ports.parser import IParser

from document_inspector.config import InspectorSettings


def build_parsers(settings: InspectorSettings) -> list[IParser]:
    return [
        AdaptivePdfParser(settings.parser),
        DocxParser(settings.parser),
        PptxParser(settings.parser),
        MarkdownParser(settings.parser),
    ]
