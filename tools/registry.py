"""Tool registry for registering and executing Jarvis tools.

Execution is gated by the Permission Manager so the AI reasoning layer never
talks to the operating system directly:

    AI Assistant -> Permission Manager -> Approved Tool/API -> Operating System
"""

import functools
import inspect
import json
from typing import Any, Callable, Dict, List, Optional

from security import get_emergency_stop, get_permission_manager


_TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}

#: Signature of an optional interactive confirmation callback.
ConfirmCallback = Callable[[Any], bool]

#: Tools that stay available even while the emergency brake is engaged so the
#: user can always inspect status and return control to themselves.
EMERGENCY_CONTROL_TOOLS = {
    "resume_operations",
    "get_emergency_status",
    "get_permission_status",
    "get_audit_log",
    "system_status",
}


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


def _invoke(func: Callable, args: Dict[str, Any]) -> Any:
    """Call a tool function, filtering arguments to those it accepts."""
    sig = inspect.signature(func)
    has_kwargs = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )
    if has_kwargs:
        return func(**args)
    valid_args = {k: v for k, v in args.items() if k in sig.parameters}
    return func(**valid_args)


def execute_tool(
    name: str,
    tool_input: Optional[Dict[str, Any]] = None,
    confirm_callback: Optional[ConfirmCallback] = None,
    request: str = "",
) -> Any:
    """Execute a registered tool after passing the Permission Manager gate.

    Args:
        name: Registered tool name.
        tool_input: Arguments for the tool.
        confirm_callback: Optional interactive callback invoked for LEVEL 2/3
            actions. It receives the :class:`security.Decision` and must return
            ``True`` to proceed. Without a callback, sensitive actions return a
            ``needs_confirmation`` payload instead of executing.
        request: Optional originating user request, stored in the audit log.
    """
    if name not in _TOOL_REGISTRY:
        return {
            "success": False,
            "error": f"Tool '{name}' is not recognized. Available tools: {list(_TOOL_REGISTRY.keys())}",
        }

    func = _TOOL_REGISTRY[name]["func"]
    args = dict(tool_input or {})

    permission_manager = get_permission_manager()
    emergency = get_emergency_stop()

    # 0. Emergency brake: nothing runs while engaged (control tools excepted).
    if emergency.is_engaged and name not in EMERGENCY_CONTROL_TOOLS:
        permission_manager.log(name, args, "Emergency stop engaged", 3, "EMERGENCY_STOP", request)
        return {
            "success": False,
            "blocked": True,
            "emergency_stop": True,
            "error": "Emergency stop is engaged. Say 'release emergency stop' to resume.",
        }

    # 1. Permission Manager decides: allow, confirm, or block.
    decision = permission_manager.check(name, args)

    if not decision.allowed:
        if confirm_callback is not None:
            try:
                approved = bool(confirm_callback(decision))
            except Exception as exc:
                approved = False
                decision.reason = f"{decision.reason} (confirmation callback error: {exc})"
            if approved:
                decision.allowed = True
                decision.requires_confirmation = False
                args["confirmed"] = True
            else:
                permission_manager.log(name, args, decision.reason, decision.level, "DENIED", request)
                result = decision.to_tool_result()
                result["error"] = f"Action cancelled by user. {decision.reason}"
                return result
        else:
            permission_manager.log(name, args, decision.reason, decision.level, "NEEDS_CONFIRMATION", request)
            return decision.to_tool_result()

    # 2. Approved: execute the tool.
    status = "CONFIRMED" if args.get("confirmed") else "ALLOWED"
    try:
        result = _invoke(func, args)
    except Exception as exc:
        error_result = {
            "success": False,
            "error": f"Error executing tool '{name}': {type(exc).__name__}: {str(exc)}",
        }
        permission_manager.log(name, args, error_result, decision.level, "ERROR", request)
        return error_result

    succeeded = not (isinstance(result, dict) and result.get("success") is False)
    permission_manager.log(
        name, args, result, decision.level,
        status if succeeded else "FAILED", request,
    )
    return result

