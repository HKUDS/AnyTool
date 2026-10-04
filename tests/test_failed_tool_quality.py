import asyncio

import pytest

from anytool.grounding.core import quality
from anytool.grounding.core.quality.manager import ToolQualityManager
from anytool.grounding.core.tool.base import BaseTool


class FailingTool(BaseTool):
    async def _arun(self):
        raise ValueError("execution failed")


@pytest.mark.parametrize("handle_errors", [True, False])
def test_raised_tool_failures_are_counted_once_in_quality_statistics(monkeypatch, handle_errors):
    manager = ToolQualityManager(enable_persistence=False)
    monkeypatch.setattr(quality, "get_quality_manager", lambda: manager)
    tool = FailingTool(handle_errors=handle_errors)
    if handle_errors:
        result = asyncio.run(tool.arun())
        assert result.is_error
        assert result.error == "execution failed"
    else:
        with pytest.raises(ValueError, match="execution failed"):
            asyncio.run(tool.arun())
    record = manager.get_record(tool)
    assert record.total_calls == 1
    assert record.success_rate == 0
    assert record.recent_executions[0].error_message == "execution failed"
    assert manager._global_execution_count == 1
