import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from anytool.grounding.backends.gui.anthropic_client import AnthropicGUIClient


class Response(SimpleNamespace):
    def __await__(self):
        async def get():
            return self
        return get().__await__()


@pytest.mark.parametrize("status", ["success", "error"])
def test_planning_acknowledges_every_tool_id_and_real_execution_status(monkeypatch, status):
    client = AnthropicGUIClient(api_key="test", enable_prompt_caching=False)
    client.messages = [{"role": "assistant", "content": [
        {"type": "tool_use", "id": "first", "name": "computer", "input": {"action": "left_click"}},
        {"type": "tool_use", "id": "second", "name": "computer", "input": {"action": "left_click"}},
    ]}]
    create = Mock(return_value=Response(content=[]))
    sdk = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)), close=AsyncMock())
    monkeypatch.setattr(client, "_create_client", lambda *args: sdk)
    monkeypatch.setattr(client, "_resize_screenshot", lambda data: data)
    asyncio.run(client.plan_action("test", b"image", action_history=[{
        "execution_result": {"status": status, "error": "click failed" if status == "error" else ""},
    }]))
    results = client.messages[1]["content"]
    assert [item["tool_use_id"] for item in results] == ["first", "second"]
    assert results[0]["is_error"] == (status == "error")
    assert results[1]["is_error"] is True
    assert "not executed" in results[1]["content"][-1]["text"].lower()
    assert create.call_args.kwargs["tool_choice"] == {"type": "auto", "disable_parallel_tool_use": True}
