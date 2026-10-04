import asyncio

import pytest

from anytool.grounding.core.tool.base import BaseTool
from anytool.grounding.core.types import BackendType, ToolSchema
from anytool.llm.client import _execute_tool_call


class CaptureTool(BaseTool):
    async def _arun(self, **kwargs):
        self.received = kwargs
        return "received"


@pytest.mark.parametrize("extra_schema", [
    {"additionalProperties": True},
    {"additionalProperties": {"type": "string"}},
    {"patternProperties": {"^custom_": {"type": "string"}}, "additionalProperties": False},
    {},
])
def test_schema_permitted_extra_arguments_reach_the_tool(extra_schema):
    tool = CaptureTool(schema=ToolSchema(
        name="capture", backend_type=BackendType.MCP,
        parameters={"type": "object", "properties": {"name": {"type": "string"}}, **extra_schema},
    ))
    tool.bind_runtime_info(BackendType.MCP, "example")
    result = asyncio.run(_execute_tool_call(tool, {"function": {"arguments": {
        "name": "example", "custom_value": "preserve", "skip_visual_analysis": True,
    }}}))
    assert result.is_success, result.error
    assert tool.received == {"name": "example", "custom_value": "preserve"}


def test_forbidden_extra_arguments_are_validated_instead_of_silently_removed():
    tool = CaptureTool(schema=ToolSchema(
        name="capture", backend_type=BackendType.MCP,
        parameters={"type": "object", "properties": {"name": {"type": "string"}}, "additionalProperties": False},
    ))
    tool.bind_runtime_info(BackendType.MCP, "example")
    result = asyncio.run(_execute_tool_call(tool, {"function": {"arguments": {
        "name": "example", "unexpected": "value",
    }}}))
    assert result.is_error
    assert not hasattr(tool, "received")
