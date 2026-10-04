import builtins
import importlib.util
from pathlib import Path


def test_linux_adapter_imports_without_optional_accessibility_libraries(monkeypatch):
    original_import = builtins.__import__

    def without_pyatspi(name, *args, **kwargs):
        if name == "pyatspi" or name.startswith("pyatspi."):
            raise ImportError("optional dependency unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_pyatspi)
    source = Path(__file__).parents[1] / "anytool/local_server/platform_adapters/linux_adapter.py"
    spec = importlib.util.spec_from_file_location("linux_adapter_without_pyatspi", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    adapter = module.LinuxAdapter()
    assert not adapter.available
    assert adapter.get_accessibility_tree() == {"error": "Linux accessibility libraries not available"}
