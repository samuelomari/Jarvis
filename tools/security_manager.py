"""Security manager tools - permission introspection, audit log, emergency control.

These tools expose the Permission Manager and Emergency Stop to the assistant and
the user without granting the language model unrestricted access. They are always
read-only or control-plane only, so they remain available even when the emergency
brake is engaged.
"""

from datetime import datetime
from typing import Any, Dict

from security import PermissionLevel, get_emergency_stop, get_permission_manager
from security.permission_manager import _classify_command
from tools.registry import register_tool

PERMISSION_LEVEL_DESCRIPTIONS = {
    0: "LEVEL 0 - INFORMATION: read-only, no confirmation required.",
    1: "LEVEL 1 - SAFE AUTOMATION: reversible local actions, no confirmation.",
    2: "LEVEL 2 - SYSTEM CHANGES: explain + request confirmation.",
    3: "LEVEL 3 - DESTRUCTIVE: always require explicit confirmation.",
}


def get_permission_manager_status() -> Dict[str, Any]:
    """Internal helper returning the current permission posture."""
    pm = get_permission_manager()
    emergency = get_emergency_stop()
    return {
        "auto_confirm_level": pm.auto_confirm_level,
        "auto_confirm_label": PermissionLevel.NAMES.get(pm.auto_confirm_level, "UNKNOWN"),
        "serious_mode": pm.serious_mode,
        "confirmation_threshold": PermissionLevel.CONFIRMATION_THRESHOLD,
        "emergency": emergency.status(),
    }


@register_tool({
    "name": "system_status",
    "description": "Return a combined system and security status report (CPU, RAM, disk, battery, permission mode, emergency state).",
    "input_schema": {"type": "object", "properties": {}, "required": []},
})
def system_status() -> Dict[str, Any]:
    """Comprehensive status combining host telemetry and the security posture."""
    from tools.system_monitor import get_system_health

    try:
        health = get_system_health()
    except Exception as exc:  # pragma: no cover - defensive
        health = {"success": False, "error": str(exc)}

    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "system": health,
        "security": get_permission_manager_status(),
    }


@register_tool({
    "name": "get_permission_status",
    "description": "Report the active permission model: auto-confirm level, serious mode, and emergency stop state.",
    "input_schema": {"type": "object", "properties": {}, "required": []},
})
def get_permission_status() -> Dict[str, Any]:
    """Return the current permission posture."""
    return {"success": True, **get_permission_manager_status(),
            "levels": PERMISSION_LEVEL_DESCRIPTIONS}


@register_tool({
    "name": "get_emergency_status",
    "description": "Check whether the global emergency stop is currently engaged.",
    "input_schema": {"type": "object", "properties": {}, "required": []},
})
def get_emergency_status() -> Dict[str, Any]:
    """Return the emergency stop state."""
    return {"success": True, **get_emergency_stop().status()}


@register_tool({
    "name": "emergency_stop",
    "description": "Engage the global emergency stop: halt running commands, cancel pending automations, and block further tool execution.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {"type": "string", "description": "Optional reason recorded in the audit log."},
        },
        "required": [],
    },
})
def emergency_stop(reason: str = "Emergency stop requested.") -> Dict[str, Any]:
    """Engage the emergency brake."""
    pm = get_permission_manager()
    result = get_emergency_stop().engage(reason)
    pm.log("emergency_stop", {"reason": reason}, result, PermissionLevel.DESTRUCTIVE, "EMERGENCY_STOP")
    return result


@register_tool({
    "name": "resume_operations",
    "description": "Release the emergency stop and return control to the user so normal tool execution resumes.",
    "input_schema": {
        "type": "object",
        "properties": {
            "confirm": {"type": "boolean", "description": "Must be true to confirm resuming operations."},
        },
        "required": [],
    },
})
def resume_operations(confirm: bool = False) -> Dict[str, Any]:
    """Release the emergency brake after explicit confirmation."""
    if not confirm:
        return {
            "success": False,
            "needs_confirmation": True,
            "error": "Resuming operations requires explicit confirmation (confirm=true).",
        }
    pm = get_permission_manager()
    result = get_emergency_stop().release()
    pm.log("resume_operations", {"confirm": confirm}, result, PermissionLevel.SYSTEM_CHANGE, "ALLOWED")
    return result


@register_tool({
    "name": "get_audit_log",
    "description": "Retrieve recent audit log entries (timestamp, tool, risk level, status, result). Secrets are never recorded.",
    "input_schema": {
        "type": "object",
        "properties": {
            "lines": {"type": "integer", "description": "Number of recent entries to return (default: 50)."},
        },
        "required": [],
    },
})
def get_audit_log(lines: int = 50) -> Dict[str, Any]:
    """Return recent audit log entries."""
    return get_permission_manager().read_audit_log(lines=lines)


@register_tool({
    "name": "classify_action_risk",
    "description": "Preview the risk classification for a proposed tool or shell command without executing it.",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to classify."},
            "tool_name": {"type": "string", "description": "Alternatively, a tool name to classify."},
            "tool_args": {"type": "object", "description": "Optional arguments for the tool."},
        },
        "required": [],
    },
})
def classify_action_risk(
    command: str = "",
    tool_name: str = "",
    tool_args: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Return the permission level a proposed action would receive."""
    pm = get_permission_manager()

    if command:
        level, reason, matched = _classify_command(command)
        target = command
        kind = "command"
    elif tool_name:
        level, reason = pm.classify_tool(tool_name, tool_args or {})
        matched = None
        target = tool_name
        kind = "tool"
    else:
        return {"success": False, "error": "Provide either 'command' or 'tool_name'."}

    return {
        "success": True,
        "kind": kind,
        "target": target,
        "risk_level": PermissionLevel.NAMES.get(level, "UNKNOWN"),
        "permission_level": level,
        "requires_confirmation": level > pm.auto_confirm_level,
        "matched_pattern": matched,
        "reason": reason,
        "description": PERMISSION_LEVEL_DESCRIPTIONS.get(level, ""),
    }