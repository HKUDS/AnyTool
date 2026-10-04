import asyncio
import subprocess
import sys

import pytest

from anytool.grounding.backends.shell.transport.local_connector import LocalShellConnector
from anytool.grounding.backends.gui.transport.local_connector import LocalGUIConnector


@pytest.mark.parametrize("shell", [False, True])
def test_timeout_stops_script_before_it_can_write_a_marker(tmp_path, shell):
    marker = tmp_path / "still-running"
    script = tmp_path / "script.py"
    script.write_text(f"import time; from pathlib import Path; time.sleep(0.8); Path({str(marker)!r}).write_text('alive')", encoding="utf-8")

    async def run():
        connector = LocalShellConnector()
        command = [sys.executable, str(script)]
        if shell:
            command_text = subprocess.list2cmdline(command) if sys.platform == "win32" else __import__("shlex").join(command)
            result = await connector._run_shell_command(command_text, timeout=0.2)
        else:
            result = await connector._run_subprocess(command, timeout=0.2)
        assert result["status"] == "error"
        await asyncio.sleep(1)
        assert not marker.exists()

    asyncio.run(run())


@pytest.mark.parametrize("cancel", [False, True])
def test_gui_timeout_or_cancellation_stops_local_command(tmp_path, cancel):
    marker = tmp_path / "gui-still-running"
    code = f"import time; from pathlib import Path; time.sleep(0.8); Path({str(marker)!r}).write_text('alive')"

    async def run():
        connector = LocalGUIConnector(timeout=10 if cancel else 0.2, retry_times=1, pkgs_prefix="{command}")
        task = asyncio.create_task(connector.execute_python_command(code))
        if cancel:
            await asyncio.sleep(0.2)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            assert await task is None
        await asyncio.sleep(1)
        assert not marker.exists()

    asyncio.run(run())


@pytest.mark.parametrize("shell", [False, True])
def test_shell_cancellation_stops_local_command(tmp_path, shell):
    marker = tmp_path / "cancelled-still-running"
    script = tmp_path / "script.py"
    script.write_text(f"import time; from pathlib import Path; time.sleep(0.8); Path({str(marker)!r}).write_text('alive')", encoding="utf-8")

    async def run():
        connector = LocalShellConnector()
        command = [sys.executable, str(script)]
        if shell:
            text = subprocess.list2cmdline(command) if sys.platform == "win32" else __import__("shlex").join(command)
            task = asyncio.create_task(connector._run_shell_command(text))
        else:
            task = asyncio.create_task(connector._run_subprocess(command))
        await asyncio.sleep(0.2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(1)
        assert not marker.exists()

    asyncio.run(run())
