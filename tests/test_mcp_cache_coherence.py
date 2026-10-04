import pytest

from anytool.grounding.backends.mcp.tool_cache import MCPToolCache


@pytest.mark.parametrize("operation", ["save", "save_server", "clear"])
def test_raw_tool_changes_invalidate_the_derived_sanitized_cache(tmp_path, operation):
    raw = tmp_path / "raw.json"
    sanitized = tmp_path / "sanitized.json"
    cache = MCPToolCache(raw, sanitized)
    old = [{"name": "old", "parameters": {}}]
    new = [{"name": "new", "parameters": {}}]
    cache.save({"server": old})
    cache.save_sanitized({"server": old})
    assert cache.has_sanitized_cache()
    if operation == "save":
        cache.save({"server": new})
    elif operation == "save_server":
        cache.save_server("server", new)
    else:
        cache.clear()
    assert not cache.has_sanitized_cache()
    assert not MCPToolCache(raw, sanitized).has_sanitized_cache()
    if operation != "clear":
        assert cache.get_server_tools("server") == new


def test_failed_server_metadata_does_not_invalidate_unchanged_tool_schemas(tmp_path):
    cache = MCPToolCache(tmp_path / "raw.json", tmp_path / "sanitized.json")
    tools = [{"name": "old", "parameters": {}}]
    cache.save({"server": tools})
    cache.save_sanitized({"server": tools})
    cache.save_failed_server("unavailable", "connection failed")
    assert cache.get_all_sanitized_tools() == {"server": tools}
