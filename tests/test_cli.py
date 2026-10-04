import os
import subprocess
import sys


def test_module_help_exits_before_initializing_backends():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "anytool", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "--query" in result.stdout
