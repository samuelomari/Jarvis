"""Window manager - list, focus, minimize, maximize, and close desktop windows.

Uses the approved X11 automation interfaces ``wmctrl`` and ``xdotool``. On
Wayland sessions these helpers may report that they are unavailable.
"""

import shutil
import subprocess
from typing import Any, Dict, List

from tools.registry import register_tool


def _has(command: str) -> bool:
    return shutil.which(command) is not None


def _run(command: List[str], timeout: int = 5):
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return proc.returncode == 0, proc.stdout, proc.stderr
    except Exception as exc:
        return False, "", str(exc)


def _window_command_available() -> bool:
    return _has("wmctrl") or _has("xdotool")


@register_tool({
    "name": "list_windows",
    "description": "List currently open desktop windows with their IDs and titles.",
    "input_schema": {"type": "object", "properties": {}, "required": []},
})
def list_windows() -> Dict[str, Any]:
    """Enumerate open windows."""
    if not _window_command_available():
        return {
            "success": False,
            "error": "No window control tool found (install wmctrl or xdotool). Wayland sessions are not supported.",
        }

    windows: List[Dict[str, Any]] = []
    if _has("wmctrl"):
        ok, out, err = _run(["wmctrl", "-l"])
        if ok:
            for line in out.splitlines():
                parts = line.split(None, 3)
                if len(parts) >= 4:
                    windows.append({"id": parts[0], "desktop": parts[1], "host": parts[2], "title": parts[3]})
            return {"success": True, "count": len(windows), "windows": windows, "backend": "wmctrl"}
        return {"success": False, "error": err.strip() or "wmctrl failed."}

    ok, out, _ = _run(["xdotool", "search", "--onlyvisible", "--name", ""])
    if ok:
        for wid in out.split():
            title_ok, title, _ = _run(["xdotool", "getwindowname", wid])
            windows.append({"id": wid, "title": title.strip() if title_ok else ""})
    return {"success": True, "count": len(windows), "windows": windows, "backend": "xdotool"}


@register_tool({
    "name": "focus_window",
    "description": "Bring a window matching the given title to the foreground.",
    "input_schema": {
        "type": "object",
        "properties": {"title": {"type": "string", "description": "Substring of the window title to focus."}},
        "required": ["title"],
    },
})
def focus_window(title: str) -> Dict[str, Any]:
    """Focus a window by title substring."""
    if _has("wmctrl"):
        ok, _, err = _run(["wmctrl", "-a", title])
        if ok:
            return {"success": True, "message": f"Focused window '{title}'."}
        return {"success": False, "error": err.strip() or f"wmctrl could not focus '{title}'."}
    if _has("xdotool"):
        ok, out, _ = _run(["xdotool", "search", "--name", title])
        ids = out.split()
        if ok and ids:
            _run(["xdotool", "windowactivate", ids[0]])
            return {"success": True, "message": f"Focused window '{title}'."}
    return {"success": False, "error": "No window control tool found (install wmctrl or xdotool)."}


@register_tool({
    "name": "minimize_window",
    "description": "Minimize a window matching the given title.",
    "input_schema": {
        "type": "object",
        "properties": {"title": {"type": "string", "description": "Substring of the window title to minimize."}},
        "required": ["title"],
    },
})
def minimize_window(title: str) -> Dict[str, Any]:
    """Minimize a window."""
    if _has("wmctrl"):
        ok, _, err = _run(["wmctrl", "-r", title, "-b", "add,hidden"])
        if ok:
            return {"success": True, "message": f"Minimized window '{title}'."}
        return {"success": False, "error": err.strip() or "wmctrl failed."}
    if _has("xdotool"):
        ok, out, _ = _run(["xdotool", "search", "--name", title])
        ids = out.split()
        if ids:
            _run(["xdotool", "windowminimize", ids[0]])
            return {"success": True, "message": f"Minimized window '{title}'."}
    return {"success": False, "error": "No window control tool found (install wmctrl or xdotool)."}


@register_tool({
    "name": "maximize_window",
    "description": "Maximize a window matching the given title.",
    "input_schema": {
        "type": "object",
        "properties": {"title": {"type": "string", "description": "Substring of the window title to maximize."}},
        "required": ["title"],
    },
})
def maximize_window(title: str) -> Dict[str, Any]:
    """Maximize a window."""
    if _has("wmctrl"):
        ok, _, err = _run(["wmctrl", "-r", title, "-b", "add,maximized_vert,maximized_horz"])
        if ok:
            return {"success": True, "message": f"Maximized window '{title}'."}
        return {"success": False, "error": err.strip() or "wmctrl failed."}
    if _has("xdotool"):
        ok, out, _ = _run(["xdotool", "search", "--name", title])
        ids = out.split()
        if ids:
            _run(["xdotool", "windowsize", ids[0], "100%", "100%"])
            return {"success": True, "message": f"Maximized window '{title}'."}
    return {"success": False, "error": "No window control tool found (install wmctrl or xdotool)."}


@register_tool({
    "name": "close_window",
    "description": "Gracefully close a window matching the given title. Requires explicit confirmation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Substring of the window title to close."},
            "confirmed": {"type": "boolean", "description": "Must be true to confirm closing the window."},
        },
        "required": ["title"],
    },
})
def close_window(title: str, confirmed: bool = False) -> Dict[str, Any]:
    """Close a window after confirmation."""
    if not confirmed:
        return {
            "success": False,
            "needs_confirmation": True,
            "error": f"Closing window '{title}' requires explicit confirmation.",
        }
    if _has("wmctrl"):
        ok, _, err = _run(["wmctrl", "-c", title])
        if ok:
            return {"success": True, "message": f"Closed window '{title}'."}
        return {"success": False, "error": err.strip() or "wmctrl failed."}
    if _has("xdotool"):
        ok, out, _ = _run(["xdotool", "search", "--name", title])
        ids = out.split()
        if ids:
            _run(["xdotool", "windowkill", ids[0]])
            return {"success": True, "message": f"Closed window '{title}'."}
    return {"success": False, "error": "No window control tool found (install wmctrl or xdotool)."}
