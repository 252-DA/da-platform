"""Công cụ chatbot của MCP server: đăng ký đủ và gọi đúng use case (kho giả)."""
import asyncio
import json
from unittest.mock import MagicMock

from document_chunk.shared.result import Err, Ok

from mcp_service.delivery.server import create_mcp_server

CHATBOT_TOOLS = {
    "get_document_page",
    "list_course_documents",
    "get_course_outline",
    "get_neighbor_chunks",
    "get_concept_relations",
}


def _server(tools=None):
    return create_mcp_server(
        retrieve_quiz_context_use_case=MagicMock(),
        search_chunks_use_case=MagicMock(),
        course_tools_use_case=tools,
    )


def _names(server) -> set[str]:
    return {t.name for t in asyncio.run(server.list_tools())}


def test_chatbot_tools_are_registered_next_to_the_existing_two():
    names = _names(_server(MagicMock()))
    assert {"retrieve_quiz_context", "search_course_chunks"} <= names
    assert CHATBOT_TOOLS <= names


def test_without_course_tools_only_the_original_two_exist():
    assert _names(_server(None)) == {"retrieve_quiz_context", "search_course_chunks"}


def test_tool_call_reaches_the_use_case_and_returns_its_payload():
    tools = MagicMock()
    tools.get_document_page.return_value = Ok({"page": 3, "chunks": []})
    server = _server(tools)
    blocks = asyncio.run(
        server.call_tool("get_document_page", {"course_id": "CO3137", "document_id": "d1", "page": 3})
    )
    tools.get_document_page.assert_called_once_with("d1", 3, "CO3137")
    assert json.loads(blocks[0].text)["page"] == 3


def test_use_case_error_becomes_a_tool_error():
    tools = MagicMock()
    tools.get_concept_relations.return_value = Err(RuntimeError("db down"))
    server = _server(tools)
    try:
        asyncio.run(server.call_tool("get_concept_relations", {"course_id": "c", "concept": "x"}))
    except Exception as exc:  # FastMCP bọc ValueError thành ToolError
        assert "db down" in str(exc)
    else:
        raise AssertionError("expected the tool to fail")
