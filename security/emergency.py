"""Global emergency control for Jarvis.

Provides a single, thread-safe kill switch. When engaged it:

* blocks every subsequent tool execution (enforced by the Permission Manager),
* invokes registered cancel callbacks so running automations can stop,
* clears queued actions,
* reports control back to the user.

Recognised triggers: ``jarvis stop``, ``jarvis cancel``, ``emergency stop``.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List

EMERGENCY_TRIGGERS = (
    "jarvis stop",
    "jarvis cancel",
    "emergency stop",
    "jarvis emergency stop",
    "jarvis emergency halt",
)


@dataclass
class EmergencyStop:
    """Thread-safe emergency brake for the whole assistant."""

    _engaged: bool = False
    _lock: threading.RLock = field(default_factory=threading.RLock)
    engaged_at: str = ""
    reason: str = ""
    _cancel_hooks: List[Callable[[], None]] = field(default_factory=list)
    _queue: List[Dict[str, Any]] = field(default_factory=list)

    # -- State -----------------------------------------------------------------

    @property
    def is_engaged(self) -> bool:
        with self._lock:
            return self._engaged

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "engaged": self._engaged,
                "engaged_at": self.engaged_at,
                "reason": self.reason,
                "cancelled_hooks": len(self._cancel_hooks),
                "queued_actions": len(self._queue),
            }

    # -- Control ---------------------------------------------------------------

    def engage(self, reason: str = "User requested emergency stop.") -> Dict[str, Any]:
        """Engage the brake, run cancel hooks, and drop queued actions."""
        with self._lock:
            self._engaged = True
            self.engaged_at = datetime.now().isoformat()
            self.reason = reason
            hooks = list(self._cancel_hooks)
            queued = len(self._queue)
            self._queue.clear()

        cancelled = 0
        for hook in hooks:
            try:
                hook()
                cancelled += 1
            except Exception:
                continue

        return {
            "success": True,
            "engaged": True,
            "message": "Emergency stop engaged. All commands and queued actions cancelled.",
            "cancel_hooks_invoked": cancelled,
            "queued_actions_discarded": queued,
        }

    def release(self) -> Dict[str, Any]:
        """Return control to the user and allow tools to run again."""
        with self._lock:
            self._engaged = False
            self.reason = ""
            self.engaged_at = ""
        return {"success": True, "engaged": False, "message": "Emergency stop released. Normal operation resumed."}

    # -- Integration points ----------------------------------------------------

    def register_cancel_hook(self, hook: Callable[[], None]) -> None:
        """Register a callback invoked when the emergency brake is pulled."""
        with self._lock:
            if hook not in self._cancel_hooks:
                self._cancel_hooks.append(hook)

    def enqueue(self, action: Dict[str, Any]) -> bool:
        """Queue a pending action unless the brake is engaged."""
        with self._lock:
            if self._engaged:
                return False
            self._queue.append(action)
            return True

    def drain_queue(self) -> List[Dict[str, Any]]:
        """Return and clear the queued actions."""
        with self._lock:
            pending = list(self._queue)
            self._queue.clear()
            return pending


def is_emergency_command(text: str) -> bool:
    """Return True when user input is an emergency stop phrase."""
    if not text:
        return False
    normalized = " ".join(text.strip().lower().rstrip(".!").split())
    return normalized in EMERGENCY_TRIGGERS


_EMERGENCY_STOP: EmergencyStop = EmergencyStop()


def get_emergency_stop() -> EmergencyStop:
    """Return the process-wide emergency stop singleton."""
    return _EMERGENCY_STOP
