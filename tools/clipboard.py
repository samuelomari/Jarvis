"""Clipboard manager - read, write, and clear the system clipboard on request.

The clipboard is only ever touched when the user explicitly asks for it; Jarvis
never monitors it continuously.
"""

import shutil
import subprocess
from typing import Any, Dict, List, Optional

from tools.registry import register_tool


def _run(command: List[str], input_text: Optional[str] = None, timeout: int = 5):
    """Run a clipboard helper command and return (ok, stdout, stderr)."""
    try:
        proc = subprocess.run(
            command,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode == 0, proc.stdout, proc.stderr
    except Exception as exc:
        return False, "", str(exc)


def _read_commands() -> List[List[str]]:
    commands = []
    if shutil.which("wl-paste"):
        commands.append(["wl-paste", "--no-newline"])
    if shutil.which("xclip"):
        commands.append(["xclip", "-selection", "clipboard", "-o"])
    if shutil.which("xsel"):
        commands.append(["xsel", "--clipboard", "--output"])
    return commands


def _write_commands() -> List[List[str]]:
    commands = []
    if shutil.which("wl-copy"):
        commands.append(["wl-copy"])
    if shutil.which("xclip"):
        commands.append(["xclip", "-selection", "clipboard"])
    if shutil.which("xsel"):
        commands.append(["xsel", "--clipboard", "--input"])
    return commands


@register_tool({
    "name": "get_clipboard",
    "description": "Read the current contents of the system clipboard (only when explicitly requested).",
    "input_schema": {"type": "object", "properties": {}, "required": []},
})
def get_clipboard() -> Dict[str, Any]:
    """Return the clipboard text."""
    try:
        import pyperclip  # type: ignore

        text = pyperclip.paste()
        if text is not None:
            return {"success": True, "content": text, "length": len(text), "backend": "pyperclip"}
    except Exception:
        pass

    for command in _read_commands():
        ok, out, err = _run(command)
        if ok:
            return {"success": True, "content": out, "length": len(out), "backend": command[0]}

    return {
        "success": False,
        "error": "No clipboard tool available (install wl-clipboard, xclip, or xsel).",
    }


@register_tool({
    "name": "set_clipboard",
    "description": "Copy the provided text to the system clipboard.",
    "input_schema": {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Text to place on the clipboard."}},
        "required": ["text"],
    },
})
def set_clipboard(text: str) -> Dict[str, Any]:
    """Write text to the clipboard."""
    try:
        import pyperclip  # type: ignore

        pyperclip.copy(text)
        return {"success": True, "message": f"Copied {len(text)} characters to the clipboard.", "backend": "pyperclip"}
    except Exception:
        pass

    for command in _write_commands():
        ok, _, err = _run(command, input_text=text)
        if ok:
            return {"success": True, "message": f"Copied {len(text)} characters to the clipboard.", "backend": command[0]}

    return {
        "success": False,
        "error": "No clipboard tool available (install wl-clipboard, xclip, or xsel).",
    }


@register_tool({
    "name": "clear_clipboard",
    "description": "Clear the system clipboard.",
    "input_schema": {
        "type": "object",
        "properties": {
            "confirm": {"type": "boolean", "description": "Must be true to clear the clipboard."},
        },
        "required": [],
    },
})
def clear_clipboard(confirm: bool = False) -> Dict[str, Any]:
    """Clear the clipboard after confirmation."""
    if not confirm:
        return {
            "success": False,
            "needs_confirmation": True,
            "error": "Clearing the clipboard requires confirmation (confirm=true).",
        }
    result = set_clipboard("")
    if result.get("success"):
        result["message"] = "Clipboard cleared."
    return result
