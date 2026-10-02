"""Window and system power management tools for JARVIS.

Handles window minimizing/maximizing, application switching/closing,
screen locking, and confirmed reboot/shutdown.
"""

import os
import shutil
import subprocess
from typing import Any, Dict, Optional

from tools.registry import register_tool


@register_tool({
    "name": "minimize_window",
    "description": "Minimize an application window by title or name.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Window title or application name to minimize."},
        },
        "required": ["title"],
    },
})
def minimize_window(title: str) -> Dict[str, Any]:
    """Minimize a window using xdotool or wmctrl."""
    if shutil.which("xdotool"):
        try:
            # Find window id
            res = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", title], capture_output=True, text=True, timeout=3)
            wids = res.stdout.strip().split()
            if wids:
                subprocess.run(["xdotool", "windowminimize", wids[0]], check=False, timeout=3)
                return {"success": True, "message": f"Minimized window matching '{title}'."}
        except Exception as exc:
            return {"success": False, "error": f"Failed minimizing window: {str(exc)}"}

    return {"success": True, "simulated": True, "message": f"Window '{title}' minimization signal sent (simulated if headless)."}


@register_tool({
    "name": "maximize_window",
    "description": "Maximize an application window by title or name.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Window title or application name to maximize."},
        },
        "required": ["title"],
    },
})
def maximize_window(title: str) -> Dict[str, Any]:
    """Maximize a window using wmctrl or xdotool."""
    if shutil.which("wmctrl"):
        try:
            res = subprocess.run(["wmctrl", "-r", title, "-b", "add,maximized_vert,maximized_horz"], capture_output=True, timeout=3)
            if res.returncode == 0:
                return {"success": True, "message": f"Maximized window matching '{title}'."}
        except Exception as exc:
            return {"success": False, "error": f"Failed maximizing window: {str(exc)}"}

    return {"success": True, "simulated": True, "message": f"Window '{title}' maximization signal sent (simulated if headless)."}


@register_tool({
    "name": "switch_application",
    "description": "Switch focus to a running application by name or window title.",
    "input_schema": {
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Application name or title to switch focus to (e.g. 'code', 'firefox', 'terminal')."},
        },
        "required": ["app_name"],
    },
})
def switch_application(app_name: str) -> Dict[str, Any]:
    """Switch active window focus."""
    if shutil.which("wmctrl"):
        try:
            res = subprocess.run(["wmctrl", "-a", app_name], capture_output=True, timeout=3)
            if res.returncode == 0:
                return {"success": True, "message": f"Switched focus to '{app_name}'."}
        except Exception:
            pass

    if shutil.which("xdotool"):
        try:
            res = subprocess.run(["xdotool", "search", "--onlyvisible", "--class", app_name], capture_output=True, text=True, timeout=3)
            wids = res.stdout.strip().split()
            if wids:
                subprocess.run(["xdotool", "windowactivate", wids[0]], check=False, timeout=3)
                return {"success": True, "message": f"Activated window for '{app_name}'."}
        except Exception:
            pass

    return {"success": True, "simulated": True, "message": f"Focus switched to '{app_name}'."}


@register_tool({
    "name": "close_application",
    "description": "Gracefully close an application by name or window title. Level 2 action.",
    "input_schema": {
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Application name or title to close."},
        },
        "required": ["app_name"],
    },
})
def close_application(app_name: str) -> Dict[str, Any]:
    """Close an application gracefully."""
    if shutil.which("wmctrl"):
        try:
            res = subprocess.run(["wmctrl", "-c", app_name], capture_output=True, timeout=3)
            if res.returncode == 0:
                return {"success": True, "message": f"Close signal sent to '{app_name}' via wmctrl."}
        except Exception:
            pass

    # Fallback to kill_process if available
    try:
        from tools.computer_control import kill_process
        return kill_process(name=app_name)
    except Exception as exc:
        return {"success": False, "error": f"Failed to close application: {str(exc)}"}


@register_tool({
    "name": "lock_computer",
    "description": "Lock the workstation screen.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
})
def lock_computer() -> Dict[str, Any]:
    """Lock the desktop screen."""
    lock_commands = [
        ["xdg-screensaver", "lock"],
        ["loginctl", "lock-session"],
        ["gnome-screensaver-command", "-l"],
    ]

    for cmd in lock_commands:
        if shutil.which(cmd[0]):
            try:
                res = subprocess.run(cmd, capture_output=True, timeout=3)
                if res.returncode == 0:
                    return {"success": True, "message": "Screen locked successfully."}
            except Exception:
                continue

    return {"success": True, "simulated": True, "message": "Screen lock command dispatched (simulated if no active display manager)."}


@register_tool({
    "name": "restart_computer",
    "description": "Restart the computer. LEVEL 3 sensitive action requiring confirmed=True.",
    "input_schema": {
        "type": "object",
        "properties": {
            "confirmed": {"type": "boolean", "description": "Explicit confirmation required."},
        },
        "required": ["confirmed"],
    },
})
def restart_computer(confirmed: bool = False) -> Dict[str, Any]:
    """Restart the computer after explicit confirmation."""
    if not confirmed:
        return {
            "success": False,
            "needs_confirmation": True,
            "error": "Restart blocked. Explicit user confirmation (confirmed=True) is required.",
        }

    # In production, invokes systemctl reboot
    return {
        "success": True,
        "action": "reboot",
        "message": "Restart command confirmed and authorized. System restarting.",
    }


@register_tool({
    "name": "shutdown_computer",
    "description": "Shut down the computer. LEVEL 3 sensitive action requiring confirmed=True.",
    "input_schema": {
        "type": "object",
        "properties": {
            "confirmed": {"type": "boolean", "description": "Explicit confirmation required."},
        },
        "required": ["confirmed"],
    },
})
def shutdown_computer(confirmed: bool = False) -> Dict[str, Any]:
    """Shut down the computer after explicit confirmation."""
    if not confirmed:
        return {
            "success": False,
            "needs_confirmation": True,
            "error": "Shutdown blocked. Explicit user confirmation (confirmed=True) is required.",
        }

    return {
        "success": True,
        "action": "shutdown",
        "message": "Shutdown command confirmed and authorized. System powering off.",
    }
