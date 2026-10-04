import asyncio
from unittest.mock import AsyncMock

import pytest

from anytool.grounding.backends.shell.transport.connector import ShellConnector


@pytest.mark.parametrize("method", ["run_python_script", "run_bash_script"])
def test_script_timeout_is_forwarded_to_http_request(monkeypatch, method):
    connector = ShellConnector("127.0.0.1")
    request = AsyncMock(return_value={"status": "success"})
    monkeypatch.setattr(connector, "post_json", request)
    asyncio.run(getattr(connector, method)("pass", timeout=120))
    assert request.call_args.kwargs["payload"]["timeout"] == 120
    assert request.call_args.kwargs["timeout"] == 180
