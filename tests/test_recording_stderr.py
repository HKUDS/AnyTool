import subprocess
import sys
import time
import importlib.util
from pathlib import Path
from types import SimpleNamespace

from anytool.local_server.utils.recording import start_recording_stderr, read_recording_stderr, finish_recording_stderr


def test_recording_process_keeps_running_after_stderr_exceeds_pipe_capacity(monkeypatch, tmp_path):
    # Load only the recording adapter code without requiring native accessibility.
    spec = importlib.util.spec_from_file_location(
        "recording_linux_adapter",
        Path(__file__).parents[1] / "anytool/local_server/platform_adapters/linux_adapter.py",
    )
    linux_adapter = importlib.util.module_from_spec(spec)
    with monkeypatch.context() as dependencies:
        dependencies.setitem(sys.modules, "pyatspi", SimpleNamespace(
            Accessible=object, StateType=object, STATE_SHOWING=0,
        ))
        spec.loader.exec_module(linux_adapter)
    marker = tmp_path / "progress"
    code = f"import sys,time; from pathlib import Path; sys.stderr.write('x' * 1000000); sys.stderr.flush(); Path({str(marker)!r}).write_text('progress'); time.sleep(10)"
    original_popen = subprocess.Popen
    processes = []

    def launch(command, **kwargs):
        process = original_popen([sys.executable, "-c", code], **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(linux_adapter.subprocess, "Popen", launch)
    monkeypatch.setattr(linux_adapter.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    monkeypatch.setattr(linux_adapter, "LINUX_LIBS_AVAILABLE", False)
    monkeypatch.setattr(linux_adapter, "pyautogui", SimpleNamespace(size=lambda: SimpleNamespace(width=10, height=10)), raising=False)
    try:
        result = linux_adapter.LinuxAdapter.__new__(linux_adapter.LinuxAdapter).start_recording(str(tmp_path / "recording.mp4"))
        assert result["status"] == "success"
        deadline = time.monotonic() + 2
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert marker.exists()
    finally:
        for process in processes:
            process.kill()
            process.wait(timeout=5)
            finish_recording_stderr(process)
            if process.stderr and not process.stderr.closed:
                process.stderr.close()


def test_recording_startup_errors_are_retained_and_streams_closed():
    process = subprocess.Popen([sys.executable, "-c", "import sys; sys.stderr.write('startup error'); sys.exit(1)"], stderr=subprocess.PIPE, text=True)
    start_recording_stderr(process)
    process.wait(timeout=5)
    assert read_recording_stderr(process) == "startup error"
    assert process.stderr.closed
    assert not process._anytool_stderr_capture.thread.is_alive()
