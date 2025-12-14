from importlib import import_module as _imp
from typing import Dict as _Dict, Any as _Any, TYPE_CHECKING as _TYPE_CHECKING

if _TYPE_CHECKING:
    from anytool.tool_layer import AnyTool as AnyTool, AnyToolConfig as AnyToolConfig
    from anytool.agents import GroundingAgent as GroundingAgent
    from anytool.llm import LLMClient as LLMClient
    from anytool.recording import RecordingManager as RecordingManager

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    
    # Main API
    "AnyTool",
    "AnyToolConfig",

    # Core Components
    "GroundingAgent",
    "GroundingClient",
    "LLMClient",
    "BaseTool",
    "ToolResult",
    "BackendType",

    # Recording System
    "RecordingManager",
    "RecordingViewer",
]

# Map attribute → sub-module that provides it
_attr_to_module: _Dict[str, str] = {
    # Main API
    "AnyTool": "anytool.tool_layer",
    "AnyToolConfig": "anytool.tool_layer",

    # Core Components
    "GroundingAgent": "anytool.agents",
    "GroundingClient": "anytool.grounding.core.grounding_client",
    "LLMClient": "anytool.llm",
    "BaseTool": "anytool.grounding.core.tool.base",
    "ToolResult": "anytool.grounding.core.types",
    "BackendType": "anytool.grounding.core.types",

    # Recording System
    "RecordingManager": "anytool.recording",
    "RecordingViewer": "anytool.recording.viewer",
}


def __getattr__(name: str) -> _Any:
    """Dynamically import sub-modules on first attribute access.

    This keeps the *initial* package import lightweight and avoids raising
    `ModuleNotFoundError` for optional / heavy dependencies until the
    corresponding functionality is explicitly used.
    """
    if name not in _attr_to_module:
        raise AttributeError(f"module 'anytool' has no attribute '{name}'")

    module_name = _attr_to_module[name]
    module = _imp(module_name)
    value = getattr(module, name)
    globals()[name] = value 
    return value


def __dir__():
    return sorted(list(globals().keys()) + list(_attr_to_module.keys()))