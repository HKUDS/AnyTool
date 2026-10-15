import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from anytool.grounding.backends.gui.tool import GUIAgentTool
from anytool.grounding.backends.gui.transport.connector import GUIConnector
from anytool.grounding.backends.gui.transport.local_connector import LocalGUIConnector


@pytest.mark.parametrize("result", [
    {"status": "error", "returncode": 1, "error": "execution failed"},
    {"status": "success", "returncode": 1, "output": "execution failed"},
    {"status": "success", "returncode": 0, "output": "done"},
    None,
])
@pytest.mark.parametrize("path", ["http", "local", "planning"])
def test_gui_reports_the_command_result_instead_of_dictionary_truthiness(result, path):
    expected = "success" if result and result.get("status") == "success" and result.get("returncode", 0) == 0 else "error"
    execute = AsyncMock(return_value=result)
    if path == "planning":
        tool = GUIAgentTool(SimpleNamespace(execute_python_command=execute))
        actual = asyncio.run(tool._execute_planned_action({
            "action_type": "PYAUTOGUI_COMMAND", "command": "print(1)",
        }))
    else:
        connector = object.__new__(GUIConnector if path == "http" else LocalGUIConnector)
        connector.execute_python_command = execute
        actual = asyncio.run(connector.execute_action("CLICK", {"x": 1, "y": 2}))
    assert actual["status"] == expected
    if result and expected == "error":
        assert actual["error"] == "execution failed"
    execute.assert_awaited_once()
