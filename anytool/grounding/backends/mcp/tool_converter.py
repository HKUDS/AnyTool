"""
Tool converter for MCP.

This module provides utilities to convert MCP tools to BaseTool instances.
"""

import copy
from typing import Any, Dict
from mcp.types import Tool as MCPTool

from anytool.grounding.core.tool import BaseTool, RemoteTool
from anytool.grounding.core.types import BackendType, ToolSchema
from anytool.grounding.core.transport.connectors import BaseConnector
from anytool.utils.logging import Logger

logger = Logger.get_logger(__name__)


def _sanitize_mcp_schema(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize MCP tool schema to ensure Claude API compatibility (JSON Schema draft 2020-12).
    
    Fixes:
    - Empty schemas -> valid object schema
    - Removes display annotations from schema nodes
    - Preserves references, boolean schemas and validation constraints
    - Ensures top-level type is 'object' (Anthropic API requirement)
    """
    if not params:
        return {"type": "object", "properties": {}, "required": []}
    
    sanitized = copy.deepcopy(params)
    sanitized = _deep_sanitize(sanitized)
    
    # Anthropic API requires top-level type to be 'object'
    # If it's not an object, wrap the schema as a property of an object
    top_level_type = sanitized.get("type")
    if top_level_type is None:
        sanitized["type"] = "object"
    if top_level_type and top_level_type != "object":
        logger.debug(f"[MCP_SCHEMA_SANITIZE] Wrapping non-object schema (type={top_level_type}) into object")
        wrapped = {
            "type": "object",
            "properties": {
                "value": sanitized  # The original schema becomes a property
            },
            "required": ["value"]  # Make it required
        }
        sanitized = wrapped
    
    return sanitized


def _deep_sanitize(schema):
    """Remove display annotations without changing JSON Schema validation."""
    if isinstance(schema, bool):
        return schema

    for annotation in ("title", "examples", "nullable", "default"):
        schema.pop(annotation, None)

    # Only traverse schema-valued keywords, never literal enum/const values.
    for keyword in ("properties", "patternProperties", "$defs", "definitions", "dependentSchemas"):
        if isinstance(schema.get(keyword), dict):
            schema[keyword] = {name: _deep_sanitize(value) for name, value in schema[keyword].items()}
    for keyword in ("items", "additionalProperties", "additionalItems", "contains", "propertyNames",
                    "unevaluatedProperties", "unevaluatedItems", "not", "if", "then", "else"):
        if keyword in schema:
            value = schema[keyword]
            schema[keyword] = ([_deep_sanitize(item) for item in value]
                               if isinstance(value, list) else _deep_sanitize(value))
    for keyword in ("anyOf", "oneOf", "allOf", "prefixItems"):
        if isinstance(schema.get(keyword), list):
            schema[keyword] = [_deep_sanitize(value) for value in schema[keyword]]
    return schema


def convert_mcp_tool_to_base_tool(
    mcp_tool: MCPTool, 
    connector: BaseConnector
) -> BaseTool:
    """
    Convert an MCP Tool to a BaseTool (RemoteTool) instance.
    
    This function extracts the tool schema from an MCP tool object and creates
    a RemoteTool that can be used within the grounding framework.
    
    Args:
        mcp_tool: MCP Tool object from the MCP SDK
        connector: Connector instance for communicating with the MCP server
        
    Returns:
        RemoteTool instance wrapping the MCP tool
    """
    # Extract tool metadata
    tool_name = mcp_tool.name
    tool_description = getattr(mcp_tool, 'description', None) or ""
    
    # Convert MCP input schema to our parameter schema format (with sanitization)
    input_schema: Dict[str, Any] = {}
    if hasattr(mcp_tool, 'inputSchema') and mcp_tool.inputSchema:
        input_schema = _sanitize_mcp_schema(mcp_tool.inputSchema)
    else:
        input_schema = {"type": "object", "properties": {}, "required": []}
    
    # Create ToolSchema
    schema = ToolSchema(
        name=tool_name,
        description=tool_description,
        parameters=input_schema,
        backend_type=BackendType.MCP,
    )
    
    # Create and return RemoteTool
    remote_tool = RemoteTool(
        connector=connector,
        remote_name=tool_name,
        schema=schema,
        backend=BackendType.MCP,
    )
    
    logger.debug(f"Converted MCP tool '{tool_name}' to RemoteTool")
    return remote_tool
