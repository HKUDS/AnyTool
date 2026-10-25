import numpy as np

from anytool.grounding.core.search_tools import ToolRanker
from anytool.grounding.core.tool.base import BaseTool
from anytool.grounding.core.types import BackendType, ToolSchema


class Tool(BaseTool):
    async def _arun(self):
        return "unused"


def make_tool(description):
    tool = Tool(schema=ToolSchema(name="tool", description=description, backend_type=BackendType.MCP))
    return tool.bind_runtime_info(BackendType.MCP, "example", server_name="server")


def test_changed_description_requires_a_new_embedding(tmp_path):
    ranker = ToolRanker(model_name="test-model", cache_dir=tmp_path)
    old = make_tool("old purpose")
    ranker._set_embedding(old, np.array([1.0, 0.0]))
    assert ranker._get_embedding(old) is not None
    assert ranker._get_embedding(make_tool("new purpose")) is None
