"""Clipboard manager tools for JARVIS.

Allows reading, copying, and clearing clipboard on explicit request.
Never continuously monitors clipboard.
"""

import shutil
import subprocess
from typing import Any, Dict

from tools.registry import register_tool

# Internal fallback buffer when GUI clipboard utilities are not present
_FALLBACK_CLIPBOARD = ""


def _get_system_clipboard() -> str:
    """Retrieve text from OS clipboard using available tools."""
    global _FALLBACK_CLIPBOARD

    # 1. Wayland
    if shutil.which("wl-paste"):
        try:
            res = subprocess.run(["wl-paste", "--no-newline"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                return res.stdout
        except Exception:
            pass

    # 2. X11 xclip
    if shutil.which("xclip"):
        try:
            res = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                return res.stdout
        except Exception:
            pass

    # 3. X11 xsel
    if shutil.which("xsel"):
        try:
            res = subprocess.run(["xsel", "--clipboard", "--output"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                return res.stdout
        except Exception:
            pass

    # 4. macOS pbpaste
    if shutil.which("pbpaste"):
        try:
            res = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                return res.stdout
        except Exception:
            pass

    return _FALLBACK_CLIPBOARD


def _set_system_clipboard(text: str) -> bool:
    """Write text to OS clipboard using available tools."""
    global _FALLBACK_CLIPBOARD
    _FALLBACK_CLIPBOARD = text
    success = False

    # 1. Wayland
    if shutil.which("wl-copy"):
        try:
            res = subprocess.run(["wl-copy"], input=text, text=True, timeout=2)
            if res.returncode == 0:
                success = True
        except Exception:
            pass

    # 2. X11 xclip
    if shutil.which("xclip"):
        try:
            res = subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, timeout=2)
            if res.returncode == 0:
                success = True
        except Exception:
            pass

    # 3. X11 xsel
    if shutil.which("xsel"):
        try:
            res = subprocess.run(["xsel", "--clipboard", "--input"], input=text, text=True, timeout=2)
            if res.returncode == 0:
                success = True
        except Exception:
            pass

    # 4. macOS pbcopy
    if shutil.which("pbcopy"):
        try:
            res = subprocess.run(["pbcopy"], input=text, text=True, timeout=2)
            if res.returncode == 0:
                success = True
        except Exception:
            pass

    return True


@register_tool({
    "name": "read_clipboard",
    "description": "Read the current contents of the system clipboard. Only called upon explicit user request.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
})
def read_clipboard() -> Dict[str, Any]:
    """Read clipboard content upon user request."""
    content = _get_system_clipboard()
    return {
        "success": True,
        "content": content,
        "length": len(content),
        "message": f"Clipboard content read ({len(content)} characters)." if content else "Clipboard is empty.",
    }


@register_tool({
    "name": "copy_to_clipboard",
    "description": "Copy specified text to the system clipboard.",
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text content to copy to clipboard."},
        },
        "required": ["text"],
    },
})
def copy_to_clipboard(text: str) -> Dict[str, Any]:
    """Copy text to clipboard."""
    _set_system_clipboard(text)
    return {
        "success": True,
        "length": len(text),
        "message": f"Copied {len(text)} characters to clipboard.",
    }


@register_tool({
    "name": "clear_clipboard",
    "description": "Clear the system clipboard contents.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
})
def clear_clipboard() -> Dict[str, Any]:
    """Clear clipboard."""
    _set_system_clipboard("")
    return {
        "success": True,
        "message": "Clipboard cleared successfully.",
    }
