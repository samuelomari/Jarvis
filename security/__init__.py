"""Jarvis security package.

Exposes the two pillars of the safety architecture:

* :class:`~security.permission_manager.PermissionManager` - classifies every
  action into one of four permission levels and decides whether it is allowed,
  requires confirmation, or is blocked.
* :class:`~security.emergency.EmergencyStop` - a global kill switch that
  immediately halts commands, automations, and queued actions.
"""

from security.emergency import (
    EmergencyStop,
    get_emergency_stop,
    is_emergency_command,
    EMERGENCY_TRIGGERS,
)
from security.permission_manager import (
    Decision,
    PermissionLevel,
    PermissionManager,
    get_permission_manager,
    redact_args,
)

__all__ = [
    "PermissionLevel",
    "PermissionManager",
    "Decision",
    "get_permission_manager",
    "redact_args",
    "EmergencyStop",
    "get_emergency_stop",
    "is_emergency_command",
    "EMERGENCY_TRIGGERS",
]
