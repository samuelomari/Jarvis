"""Serious Mode - strict confirmation posture for high-stakes sessions.

When serious mode is enabled the Permission Manager requires an explicit
confirmation for *every* state-changing action (LEVEL 1 and above), instead of
only LEVEL 2/3. Read-only information requests stay automatic.
"""

from typing import Any, Dict

from security import get_permission_manager
from tools.registry import register_tool


@register_tool({
    "name": "set_serious_mode",
    "description": "Enable or disable serious mode. When enabled, every state-changing action requires explicit confirmation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "enabled": {"type": "boolean", "description": "True enables strict confirmations; False restores normal permissions."},
        },
        "required": ["enabled"],
    },
})
def set_serious_mode(enabled: bool) -> Dict[str, Any]:
    """Toggle serious mode on the Permission Manager."""
    result = get_permission_manager().set_serious_mode(enabled)
    get_permission_manager().log(
        "set_serious_mode", {"enabled": enabled}, result, 1, "ALLOWED"
    )
    return result


@register_tool({
    "name": "get_serious_mode_status",
    "description": "Report whether serious mode (strict confirmation) is currently enabled.",
    "input_schema": {"type": "object", "properties": {}, "required": []},
})
def get_serious_mode_status() -> Dict[str, Any]:
    """Return the serious mode state."""
    pm = get_permission_manager()
    return {
        "success": True,
        "serious_mode": pm.serious_mode,
        "auto_confirm_level": pm.auto_confirm_level,
        "message": (
            "Serious mode is ON - all state-changing actions require confirmation."
            if pm.serious_mode
            else "Serious mode is OFF - normal permissions apply."
        ),
    }
