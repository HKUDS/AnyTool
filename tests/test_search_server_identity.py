import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from anytool.grounding.core.search_tools import SearchCoordinator
from anytool.grounding.core.tool.base import BaseTool
from anytool.grounding.core.types import BackendType, ToolSchema


class ReadFile(BaseTool):
    async def _arun(self):
        return "unused"


def test_utility_selection_keeps_server_identity_for_duplicate_tool_names():
    tools = [ReadFile(schema=ToolSchema(name="read_file", backend_type=BackendType.MCP)) for _ in range(2)]
    for tool, server in zip(tools, ["first", "second"]):
        tool.bind_runtime_info(BackendType.MCP, server, server_name=server)
    coordinator = object.__new__(SearchCoordinator)
    coordinator._llm = SimpleNamespace(complete=AsyncMock(return_value={"message": {"content": json.dumps({
        "utility_tools": {"first": ["read_file"]}, "domain_servers": [],
    })}}))
    utility, domain, _ = asyncio.run(coordinator._llm_filter_with_planning("read a file", tools))
    assert utility == [tools[0]]
    assert domain == []
