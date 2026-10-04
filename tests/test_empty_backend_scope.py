import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from anytool import tool_layer


@pytest.mark.parametrize("scope,expected", [([], []), (None, ["mcp"]), (["shell"], ["shell"])])
def test_explicit_backend_scope_overrides_agent_configuration(monkeypatch, scope, expected):
    grounding = SimpleNamespace(initialize_all_providers=AsyncMock(), list_providers=lambda: {})
    monkeypatch.setattr(tool_layer, "LLMClient", lambda **kwargs: SimpleNamespace(model="test"))
    monkeypatch.setattr(tool_layer, "GroundingClient", lambda **kwargs: grounding)
    monkeypatch.setattr(tool_layer, "get_config", lambda: object())
    monkeypatch.setattr(tool_layer, "get_agent_config", lambda name: {"backend_scope": ["mcp"]})
    layer = tool_layer.AnyTool(tool_layer.AnyToolConfig(backend_scope=scope))
    asyncio.run(layer.initialize())
    assert layer._grounding_agent.backend_scope == expected
