import copy
import json

import jsonschema
import pytest

from anytool.grounding.backends.mcp.tool_converter import _sanitize_mcp_schema
from anytool.grounding.backends.mcp.tool_cache import MCPToolCache


@pytest.mark.parametrize("value,valid", [
    ({"record": {"name": "ok"}, "free": 42}, True),
    ({"record": {"name": 42}, "free": 42}, False),
    ({"record": {}, "free": 42}, False),
])
def test_nested_references_and_unconstrained_properties_keep_their_validation(value, valid):
    schema = {
        "type": "object", "$defs": {"Record": {
            "type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"],
        }}, "properties": {"record": {"$ref": "#/$defs/Record"}, "free": {}},
        "required": ["record", "free"],
    }
    original = copy.deepcopy(schema)
    sanitized = _sanitize_mcp_schema(schema)
    jsonschema.Draft202012Validator.check_schema(sanitized)
    assert jsonschema.Draft202012Validator(sanitized).is_valid(value) == valid
    assert schema == original


@pytest.mark.parametrize("property_schema,value,valid", [
    (True, 42, True), (False, "anything", False),
    ({"const": "fixed"}, "fixed", True),
    ({"enum": [None, "value"]}, None, True),
    ({"type": "array", "items": True}, [42, "ok"], True),
    ({"type": "array", "items": False}, [42], False),
    ({"type": "number", "exclusiveMinimum": 1}, 1, False),
])
def test_standard_property_schemas_are_not_replaced_by_inferred_types(property_schema, value, valid):
    schema = {"type": "object", "properties": {"value": property_schema}}
    sanitized = _sanitize_mcp_schema(schema)
    assert jsonschema.Draft202012Validator(sanitized).is_valid({"value": value}) == valid


def test_const_values_are_not_treated_as_schema_nodes():
    value = {"title": "literal", "default": 42}
    schema = {"type": "object", "properties": {"value": {"const": value}}}
    sanitized = _sanitize_mcp_schema(schema)
    assert sanitized["properties"]["value"]["const"] == value
    assert jsonschema.Draft202012Validator(sanitized).is_valid({"value": value})


def test_old_sanitized_cache_is_rebuilt_without_discarding_raw_metadata(tmp_path):
    raw = tmp_path / "raw.json"
    sanitized = tmp_path / "sanitized.json"
    tools = [{"name": "example", "parameters": {"type": "object"}}]
    cache = MCPToolCache(raw, sanitized)
    cache.save({"server": tools})
    sanitized.write_text(json.dumps({"version": 1, "servers": {"server": tools}}), encoding="utf-8")
    assert not cache.has_sanitized_cache()
    assert cache.get_server_tools("server") == tools
    cache.save_sanitized({"server": tools})
    assert MCPToolCache(raw, sanitized).get_all_sanitized_tools() == {"server": tools}
