import asyncio
import json
import sys

from anytool.grounding.backends.gui.transport.local_connector import LocalGUIConnector
from anytool.grounding.backends.shell.transport.local_connector import LocalShellConnector


def test_local_shell_uses_current_python_even_without_python_on_path():
    code = "import json, sys; print(json.dumps(sys.executable))"
    result = asyncio.run(LocalShellConnector().run_python_script(code, env={"PATH": ""}))
    assert result["returncode"] == 0
    assert json.loads(result["output"].strip()) == sys.executable


def test_local_gui_commands_use_current_python(monkeypatch):
    monkeypatch.setenv("PATH", "")
    connector = LocalGUIConnector(retry_times=1, pkgs_prefix="{command}")
    result = asyncio.run(connector.execute_python_command("import json, sys; print(json.dumps(sys.executable))"))
    assert result is not None
    assert result["returncode"] == 0
    assert json.loads(result["output"].strip()) == sys.executable
