"""MCP server exposing bounded learning-context retrieval tools.

Ported from packages-ai/src/document_chunk/delivery/mcp/server.py — the
business logic (SearchChunksUseCase, RetrieveQuizContextUseCase, the two
@server.tool() functions) is unchanged. Only composition differs:
mcp_service.container instead of document_chunk.infrastructure.container,
since this process never loads Neo4j and gets its embedder over gRPC
instead of loading BGE in-process (see container.py docstring).
"""

from dataclasses import asdict

from document_chunk.application.dto.search_dto import SearchRequest
from document_chunk.application.use_cases.retrieve_quiz_context import (
    RetrieveQuizContextRequest,
    RetrieveQuizContextUseCase,
)
from document_chunk.application.use_cases.course_tools import CourseToolsUseCase
from document_chunk.application.use_cases.search_chunks import SearchChunksUseCase
from document_chunk.infrastructure.config import McpConfig
from document_chunk.shared.logger import get_logger, setup_logging
from mcp.server.fastmcp import FastMCP

from mcp_service.config import get_settings
from mcp_service.container import build_container

logger = get_logger(__name__)


def create_mcp_server(
    retrieve_quiz_context_use_case: RetrieveQuizContextUseCase,
    search_chunks_use_case: SearchChunksUseCase,
    config: McpConfig | None = None,
    course_tools_use_case: CourseToolsUseCase | None = None,
) -> FastMCP:
    settings = config or McpConfig()
    server = FastMCP(
        "learning-context",
        instructions=(
            "Retrieve source-addressable course context for grounded quiz, "
            "learning-content generation and the course chatbot."
        ),
        host=settings.host,
        port=settings.port,
        streamable_http_path=settings.path,
        stateless_http=True,
        json_response=True,
    )

    @server.tool()
    def retrieve_quiz_context(
        course_id: str,
        lo_code: str,
        query: str | None = None,
        bloom_level: str | None = None,
        assessment_style: str = "quiz",
        top_k: int = 5,
    ) -> dict:
        """Retrieve bounded, LO-aligned chunks to ground generated questions."""
        result = retrieve_quiz_context_use_case.execute(
            RetrieveQuizContextRequest(
                course_id=course_id,
                lo_code=lo_code,
                query=query,
                bloom_level=bloom_level,
                assessment_style=assessment_style,
                top_k=top_k,
            )
        )
        if result.is_err():
            raise ValueError(str(result.error))
        return asdict(result.unwrap())

    @server.tool()
    def search_course_chunks(
        course_id: str,
        query: str,
        top_k: int = 10,
        score_threshold: float = 0.0,
        document_ids: list[str] | None = None,
    ) -> dict:
        """Semantic-search course chunks and return content with source metadata.

        document_ids narrows the search to those documents — what a reader open on
        one document needs for a follow-up question. Empty means the whole course.
        """
        result = search_chunks_use_case.execute(
            SearchRequest(
                course_id=course_id,
                query=query,
                top_k=top_k,
                score_threshold=score_threshold,
                document_ids=list(document_ids or []),
                # Công cụ này chỉ chatbot dùng: không trả tài liệu bị ẩn ở LMS hay đã xoá cho học viên.
                exclude_hidden=True,
            )
        )
        if result.is_err():
            raise ValueError(str(result.error))
        return result.unwrap().model_dump(mode="json")

    if course_tools_use_case is not None:
        _register_course_tools(server, course_tools_use_case)

    return server


def _unwrap(result) -> dict:
    if result.is_err():
        raise ValueError(str(result.error))
    return result.unwrap()


def _register_course_tools(server: FastMCP, tools: CourseToolsUseCase) -> None:
    """Công cụ tra cứu của chatbot. Course id có thể là UUID hoặc mã môn (CO3137)."""

    @server.tool()
    def get_document_page(
        document_id: str, page: int, course_id: str | None = None
    ) -> dict:
        """Return every chunk on one page of a document, in reading order.

        Use for "explain this slide/page" — an exact lookup, not a similarity search.
        """
        if course_id is not None:
            return _unwrap(tools.get_document_page(document_id, page, course_id))
        return _unwrap(tools.get_document_page(document_id, page))

    @server.tool()
    def list_course_documents(course_id: str, chapter_code: str | None = None) -> dict:
        """List the processed documents of a course (title, role, chapter, page count)."""
        return _unwrap(tools.list_documents(course_id, chapter_code))

    @server.tool()
    def get_course_outline(course_id: str, chapter_code: str | None = None) -> dict:
        """Return chapters, learning outcomes and assessments from the syllabus.

        chapter_code narrows the answer to one chapter and its learning outcomes.
        """
        return _unwrap(tools.get_outline(course_id, chapter_code))

    @server.tool()
    def get_neighbor_chunks(chunk_id: str, window: int = 1) -> dict:
        """Return the chunk and up to `window` chunks before and after it (max 3).

        Use when a retrieved chunk is cut off or only has a title.
        """
        return _unwrap(tools.get_neighbors(chunk_id, window))

    @server.tool()
    def get_concept_relations(
        course_id: str, concept: str, hops: int = 1, limit: int = 15
    ) -> dict:
        """Return typed relations (cause, part_of, contrast, prerequisite, example_of,
        defines, related) around a concept, each with a verbatim source quote.

        hops is 1 or 2. Use for questions about why/how things relate or differ.
        """
        return _unwrap(tools.get_concept_relations(course_id, concept, hops, limit))


def serve() -> None:
    settings = get_settings()
    setup_logging(level=settings.app.log_level, json_logs=settings.app.json_logs)
    container = build_container(settings)
    server = create_mcp_server(
        retrieve_quiz_context_use_case=container.retrieve_quiz_context_use_case,
        search_chunks_use_case=container.search_chunks_use_case,
        config=settings.mcp,
        course_tools_use_case=container.course_tools_use_case,
    )
    logger.info(
        "mcp_service.starting",
        address=f"http://{settings.mcp.host}:{settings.mcp.port}{settings.mcp.path}",
    )
    try:
        server.run(transport="streamable-http")
    finally:
        container.close()


if __name__ == "__main__":
    serve()
