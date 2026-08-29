"""Tool registry for registering and executing Jarvis tools."""

import functools
import inspect
import json
from typing import Any, Callable, Dict, List, Optional


_TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_tool(schema: Dict[str, Any]):
    """Decorator to register a function as an agent tool with its Claude schema.

    Example:
        @register_tool({
            "name": "get_current_time",
            "description": "Get current time",
            "input_schema": {"type": "object", "properties": {}}
        })
        def get_current_time(): ...
    """
    def decorator(func: Callable) -> Callable:
        name = schema.get("name", func.__name__)
        _TOOL_REGISTRY[name] = {
            "name": name,
            "schema": schema,
            "func": func,
        }

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_all_tool_schemas() -> List[Dict[str, Any]]:
    """Return list of all registered tool schemas formatted for Claude."""
    return [entry["schema"] for entry in _TOOL_REGISTRY.values()]


def get_registered_tools() -> Dict[str, Dict[str, Any]]:
    """Return dictionary of all registered tool entries."""
    return dict(_TOOL_REGISTRY)


def execute_tool(name: str, tool_input: Optional[Dict[str, Any]] = None) -> Any:
    """Execute a registered tool by name with provided arguments."""
    if name not in _TOOL_REGISTRY:
        return {
            "success": False,
            "error": f"Tool '{name}' is not recognized. Available tools: {list(_TOOL_REGISTRY.keys())}",
        }

    func = _TOOL_REGISTRY[name]["func"]
    args = tool_input or {}

    try:
        sig = inspect.signature(func)
        # Check if function takes kwargs or accepts the passed arguments
        has_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        if has_kwargs:
            result = func(**args)
        else:
            # Filter only accepted parameters
            valid_args = {k: v for k, v in args.items() if k in sig.parameters}
            result = func(**valid_args)

        return result
    except Exception as exc:
        return {
            "success": False,
            "error": f"Error executing tool '{name}': {type(exc).__name__}: {str(exc)}",
        }

