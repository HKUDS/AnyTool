import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from anytool import tool_layer


@pytest.mark.parametrize("limit,expected", [(None, 15), (5, 5), (20, 20)])
def test_explicit_iteration_limits_take_priority_over_agent_defaults(monkeypatch, limit, expected):
    grounding = SimpleNamespace(initialize_all_providers=AsyncMock(), list_providers=lambda: {})
    monkeypatch.setattr(tool_layer, "LLMClient", lambda **kwargs: SimpleNamespace(model="test"))
    monkeypatch.setattr(tool_layer, "GroundingClient", lambda **kwargs: grounding)
    monkeypatch.setattr(tool_layer, "get_config", lambda: object())
    monkeypatch.setattr(tool_layer, "get_agent_config", lambda name: {"max_iterations": 15})
    config = tool_layer.AnyToolConfig() if limit is None else tool_layer.AnyToolConfig(grounding_max_iterations=limit)
    layer = tool_layer.AnyTool(config)
    asyncio.run(layer.initialize())
    assert layer._grounding_agent._max_iterations == expected
    assert layer.config.grounding_max_iterations == expected


def test_config_default_remains_twenty_and_later_assignment_is_explicit():
    config = tool_layer.AnyToolConfig()
    assert config.grounding_max_iterations == 20
    assert not config._grounding_max_iterations_explicit
    config.grounding_max_iterations = 7
    assert config._grounding_max_iterations_explicit
    assert config.grounding_max_iterations == 7
