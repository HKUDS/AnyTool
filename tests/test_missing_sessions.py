import asyncio

import pytest

from anytool.grounding.core.exceptions import ErrorCode, GroundingError
from anytool.grounding.core.grounding_client import GroundingClient


@pytest.mark.parametrize("method", ["get_session", "get_session_info", "list_tools", "list_session_tools"])
def test_unknown_session_raises_a_structured_grounding_error(method):
    client = object.__new__(GroundingClient)
    client._sessions = {}
    client._session_info = {}
    with pytest.raises(GroundingError) as error:
        if method == "list_tools":
            asyncio.run(client.list_tools(session_name="missing"))
        elif method == "list_session_tools":
            asyncio.run(client.list_session_tools("missing"))
        else:
            getattr(client, method)("missing")
    assert error.value.code == ErrorCode.SESSION_NOT_FOUND
    assert error.value.context["session_name"] == "missing"
