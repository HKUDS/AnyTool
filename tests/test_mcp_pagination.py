import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from mcp.types import ListToolsResult, ListResourcesResult, ListPromptsResult

from anytool.grounding.backends.mcp.transport.connectors.http import HttpConnector


@pytest.mark.parametrize("kind", ["tools", "resources", "prompts"])
@pytest.mark.parametrize("jsonrpc", [False, True])
def test_mcp_lists_follow_all_pages(monkeypatch, kind, jsonrpc):
    connector = HttpConnector("http://127.0.0.1")
    connector._use_jsonrpc = jsonrpc
    monkeypatch.setattr(connector, "_ensure_connected", AsyncMock())
    items = {
        "tools": [{"name": "one", "inputSchema": {}}, {"name": "two", "inputSchema": {}}],
        "resources": [{"name": "one", "uri": "file:///one"}, {"name": "two", "uri": "file:///two"}],
        "prompts": [{"name": "one"}, {"name": "two"}],
    }[kind]
    pages = [{kind: [items[0]], "nextCursor": "next"}, {kind: [items[1]]}]
    if jsonrpc:
        call = AsyncMock(side_effect=pages)
        monkeypatch.setattr(connector, "_send_jsonrpc_request", call)
    else:
        model = {"tools": ListToolsResult, "resources": ListResourcesResult, "prompts": ListPromptsResult}[kind]
        call = AsyncMock(side_effect=[model(**page) for page in pages])
        connector.client_session = SimpleNamespace(**{f"list_{kind}": call})
    result = asyncio.run(getattr(connector, f"list_{kind}")())
    assert [item.name for item in result] == ["one", "two"]
    if jsonrpc:
        assert call.call_args.args == (f"{kind}/list", {"cursor": "next"})
    else:
        assert call.call_args.kwargs == {"cursor": "next"}


@pytest.mark.parametrize("jsonrpc", [False, True])
def test_repeated_pagination_cursor_does_not_loop(monkeypatch, jsonrpc):
    connector = HttpConnector("http://127.0.0.1")
    page = {"tools": [], "nextCursor": "same"}
    if jsonrpc:
        call = AsyncMock(return_value=page)
        monkeypatch.setattr(connector, "_send_jsonrpc_request", call)
        operation = connector._list_jsonrpc_pages("tools")
    else:
        call = AsyncMock(return_value=ListToolsResult(**page))
        connector.client_session = SimpleNamespace(list_tools=call)
        operation = connector._list_pages("list_tools", "tools")
    with pytest.raises(RuntimeError, match="Repeated MCP pagination cursor"):
        asyncio.run(asyncio.wait_for(operation, 1))
    assert call.await_count == 2
