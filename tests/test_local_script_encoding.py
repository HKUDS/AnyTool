import asyncio
import json

from anytool.grounding.backends.shell.transport.local_connector import LocalShellConnector


def test_non_ascii_python_source_is_written_as_utf8():
    result = asyncio.run(LocalShellConnector().run_python_script("import json; print(json.dumps('中文'))"))
    assert result["returncode"] == 0
    assert json.loads(result["output"].strip()) == "中文"
