import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from anytool.grounding.core.grounding_client import GroundingClient
from anytool.grounding.core.types import BackendType


def test_list_session_tools_forwards_keyword_only_cache_option():
    client = object.__new__(GroundingClient)
    client._sessions = {"example": object()}
    client._session_info = {"example": SimpleNamespace(backend_type=BackendType.SHELL)}
    tools = [object()]
    client._fetch_tools = AsyncMock(return_value=tools)
    assert asyncio.run(client.list_session_tools("example", use_cache=True)) == tools
    client._fetch_tools.assert_awaited_once_with(
        BackendType.SHELL, session_name="example", use_cache=True
    )
