"""Emergency Stop Controller for JARVIS.

Provides a global, immediate stop mechanism when the user signals:
- "Jarvis stop"
- "Jarvis cancel"
- "Emergency stop"
"""

import logging
import subprocess
import threading
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

EMERGENCY_PHRASES = [
    "jarvis stop",
    "jarvis cancel",
    "emergency stop",
    "stop jarvis",
    "cancel jarvis",
    "jarvis halt",
    "stop immediately",
]


class EmergencyStopController:
    """Singleton emergency stop controller for JARVIS."""

    _instance: Optional["EmergencyStopController"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "EmergencyStopController":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._stopped_event = threading.Event()
        self._active_processes: Dict[int, subprocess.Popen] = {}
        self._callbacks: List[Callable[[], None]] = []
        self._process_lock = threading.Lock()
        self._initialized = True

    @property
    def is_stopped(self) -> bool:
        """Check if an emergency stop is active."""
        return self._stopped_event.is_set()

    def check_phrase(self, text: str) -> bool:
        """Check if text contains an emergency stop command."""
        if not text:
            return False
        clean = text.strip().lower()
        for phrase in EMERGENCY_PHRASES:
            if phrase in clean:
                return True
        return False

    def register_process(self, proc: subprocess.Popen) -> None:
        """Register a subprocess to be killed on emergency stop."""
        with self._process_lock:
            if proc.pid:
                self._active_processes[proc.pid] = proc

    def unregister_process(self, pid: int) -> None:
        """Unregister a completed subprocess."""
        with self._process_lock:
            self._active_processes.pop(pid, None)

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register a cleanup/cancellation callback."""
        with self._process_lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def trigger(self, reason: str = "User initiated emergency stop") -> Dict[str, Any]:
        """
        Immediately:
        1. Stop running commands
        2. Stop pending automations
        3. Cancel queued actions
        4. Kill running registered processes
        5. Return control to the user
        """
        self._stopped_event.set()
        killed_pids = []

        with self._process_lock:
            for pid, proc in list(self._active_processes.items()):
                try:
                    proc.terminate()
                    try:
                        proc.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    killed_pids.append(pid)
                except Exception as exc:
                    logger.warning("Error terminating process %s: %s", pid, exc)
            self._active_processes.clear()

            for cb in self._callbacks:
                try:
                    cb()
                except Exception as exc:
                    logger.warning("Error in emergency callback: %s", exc)

        return {
            "status": "STOPPED",
            "reason": reason,
            "killed_processes": killed_pids,
            "message": "Global emergency stop activated. All active operations halted.",
        }

    def reset(self) -> None:
        """Reset the emergency stop state to resume normal operations."""
        self._stopped_event.clear()


_controller: Optional[EmergencyStopController] = None


def get_emergency_controller() -> EmergencyStopController:
    """Get the global EmergencyStopController instance."""
    global _controller
    if _controller is None:
        _controller = EmergencyStopController()
    return _controller
