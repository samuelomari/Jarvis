"""Computer control tools - app launching, terminal, screenshots, volume, brightness, screen reading."""

import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import register_tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIT_LOG_FILE = PROJECT_ROOT / "data" / "command_audit.log"

# Commands that require explicit confirmation (blocked in auto-execution)
DANGEROUS_PATTERNS = [
    "rm -rf", "mkfs", "dd if=", ":(){:|:&};:", "chmod 777 /",
    "sudo rm", "shutdown", "reboot", "halt", "poweroff",
    "DROP TABLE", "DELETE FROM", "> /dev/sda",
]


def _audit_log(command: str, result: str, allowed: bool) -> None:
    """Append command to audit log."""
    from datetime import datetime
    AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat()
    status = "ALLOWED" if allowed else "BLOCKED"
    with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] [{status}] CMD: {command[:200]} | RESULT: {result[:100]}\n")


def _is_dangerous(command: str) -> Optional[str]:
    """Return the matched dangerous pattern if found, else None."""
    cmd_lower = command.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in cmd_lower:
            return pattern
    return None


@register_tool({
    "name": "run_terminal_command",
    "description": "Execute a safe shell command in the project workspace and return stdout/stderr. Dangerous commands are blocked.",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute."},
            "cwd": {"type": "string", "description": "Working directory (defaults to project root)."},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)."},
        },
        "required": ["command"],
    },
})
def run_terminal_command(command: str, cwd: str = ".", timeout: int = 30) -> Dict[str, Any]:
    """Execute a shell command safely."""
    danger = _is_dangerous(command)
    if danger:
        _audit_log(command, "BLOCKED", False)
        return {
            "success": False,
            "error": f"Command blocked: contains dangerous pattern '{danger}'. Confirm manually if intentional.",
        }

    work_dir = PROJECT_ROOT / cwd if not Path(cwd).is_absolute() else Path(cwd)
    if not work_dir.exists():
        work_dir = PROJECT_ROOT

    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result_summary = proc.stdout[:500] if proc.stdout else proc.stderr[:200]
        _audit_log(command, result_summary, True)
        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[:3000],
            "stderr": proc.stderr[:1000],
            "command": command,
        }
    except subprocess.TimeoutExpired:
        _audit_log(command, "TIMEOUT", True)
        return {"success": False, "error": f"Command timed out after {timeout}s."}
    except Exception as exc:
        return {"success": False, "error": f"Failed to run command: {str(exc)}"}


@register_tool({
    "name": "open_application",
    "description": "Launch a desktop application or program by name (e.g. 'code', 'firefox', 'nautilus', 'gedit').",
    "input_schema": {
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Application name or command (e.g. 'code', 'firefox', 'vlc')."},
            "args": {"type": "string", "description": "Optional arguments to pass to the application."},
        },
        "required": ["app_name"],
    },
})
def open_application(app_name: str, args: str = "") -> Dict[str, Any]:
    """Launch a desktop application."""
    app = app_name.strip()
    if not app:
        return {"success": False, "error": "Application name cannot be empty."}

    danger = _is_dangerous(app)
    if danger:
        return {"success": False, "error": f"Blocked: '{danger}' is not allowed."}

    cmd_parts = [app] + shlex.split(args) if args.strip() else [app]

    try:
        subprocess.Popen(
            cmd_parts,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        _audit_log(f"open_application: {app} {args}", "launched", True)
        return {"success": True, "message": f"Launched '{app}' successfully."}
    except FileNotFoundError:
        return {"success": False, "error": f"Application '{app}' not found. Is it installed?"}
    except Exception as exc:
        return {"success": False, "error": f"Failed to launch '{app}': {str(exc)}"}


@register_tool({
    "name": "take_screenshot",
    "description": "Capture a screenshot of the current screen and save it to the workspace.",
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "Output filename (default: screenshot.png). Saved in data/screenshots/."},
        },
        "required": [],
    },
})
def take_screenshot(filename: str = "screenshot.png") -> Dict[str, Any]:
    """Take a screenshot using available system tools."""
    screenshots_dir = PROJECT_ROOT / "data" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(filename).name or "screenshot.png"
    if not safe_name.endswith((".png", ".jpg")):
        safe_name += ".png"

    output_path = screenshots_dir / safe_name

    # Try scrot, gnome-screenshot, import (ImageMagick), xwd in order
    for cmd in [
        ["scrot", str(output_path)],
        ["gnome-screenshot", "-f", str(output_path)],
        ["import", "-window", "root", str(output_path)],
    ]:
        if shutil.which(cmd[0]):
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                if result.returncode == 0 and output_path.exists():
                    return {
                        "success": True,
                        "path": str(output_path.relative_to(PROJECT_ROOT)),
                        "absolute_path": str(output_path),
                        "message": f"Screenshot saved to {output_path.relative_to(PROJECT_ROOT)}",
                    }
            except Exception:
                continue

    # Fallback: try Python PIL
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.save(str(output_path))
        return {
            "success": True,
            "path": str(output_path.relative_to(PROJECT_ROOT)),
            "absolute_path": str(output_path),
            "message": f"Screenshot saved via PIL to {output_path.relative_to(PROJECT_ROOT)}",
        }
    except Exception:
        pass

    return {
        "success": False,
        "error": "No screenshot tool available. Install scrot, gnome-screenshot, or Pillow.",
    }


@register_tool({
    "name": "get_running_processes",
    "description": "List currently running processes with CPU and memory usage.",
    "input_schema": {
        "type": "object",
        "properties": {
            "filter_name": {"type": "string", "description": "Optional process name filter (e.g. 'python', 'node')."},
            "limit": {"type": "integer", "description": "Maximum number of processes to return (default: 20)."},
        },
        "required": [],
    },
})
def get_running_processes(filter_name: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    """List running processes."""
    try:
        import psutil
        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status", "cmdline"]):
            try:
                info = proc.info
                name = info.get("name", "")
                if filter_name and filter_name.lower() not in name.lower():
                    continue
                cmdline = " ".join(info.get("cmdline") or [])[:80]
                procs.append({
                    "pid": info["pid"],
                    "name": name,
                    "cpu_percent": round(info.get("cpu_percent") or 0, 1),
                    "memory_percent": round(info.get("memory_percent") or 0, 2),
                    "status": info.get("status", ""),
                    "cmdline": cmdline,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        procs.sort(key=lambda x: x["cpu_percent"], reverse=True)
        return {"success": True, "count": len(procs[:limit]), "processes": procs[:limit]}
    except ImportError:
        return {"success": False, "error": "psutil not installed."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool({
    "name": "kill_process",
    "description": "Terminate a running process by PID or name. Requires confirmation for system processes.",
    "input_schema": {
        "type": "object",
        "properties": {
            "pid": {"type": "integer", "description": "Process ID to kill."},
            "name": {"type": "string", "description": "Process name to kill (kills first match)."},
        },
        "required": [],
    },
})
def kill_process(pid: Optional[int] = None, name: Optional[str] = None) -> Dict[str, Any]:
    """Kill a process by PID or name."""
    if not pid and not name:
        return {"success": False, "error": "Provide either pid or name."}

    protected = {"systemd", "init", "kernel", "kthreadd", "Xorg", "gdm", "lightdm"}

    try:
        import psutil
        target = None
        if pid:
            target = psutil.Process(pid)
        else:
            for proc in psutil.process_iter(["pid", "name"]):
                if name and name.lower() in proc.info["name"].lower():
                    if proc.info["name"] in protected:
                        return {"success": False, "error": f"Cannot kill protected system process '{proc.info['name']}'."}
                    target = proc
                    break

        if not target:
            return {"success": False, "error": f"Process not found: pid={pid}, name={name}"}

        proc_name = target.name()
        if proc_name in protected:
            return {"success": False, "error": f"Cannot kill protected system process '{proc_name}'."}

        target.terminate()
        _audit_log(f"kill_process pid={target.pid} name={proc_name}", "terminated", True)
        return {"success": True, "message": f"Process '{proc_name}' (PID {target.pid}) terminated."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool({
    "name": "set_volume",
    "description": "Set the system audio volume level (0-100).",
    "input_schema": {
        "type": "object",
        "properties": {
            "level": {"type": "integer", "description": "Volume level from 0 to 100."},
        },
        "required": ["level"],
    },
})
def set_volume(level: int) -> Dict[str, Any]:
    """Set system volume using amixer or pactl."""
    level = max(0, min(100, level))

    for cmd in [
        ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"],
        ["amixer", "-q", "sset", "Master", f"{level}%"],
    ]:
        if shutil.which(cmd[0]):
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=5)
                if result.returncode == 0:
                    return {"success": True, "message": f"Volume set to {level}%."}
            except Exception:
                continue

    return {"success": False, "error": "No volume control tool found (pactl/amixer)."}


@register_tool({
    "name": "set_brightness",
    "description": "Set the screen brightness level (0-100). Requires xrandr or brightnessctl.",
    "input_schema": {
        "type": "object",
        "properties": {
            "level": {"type": "integer", "description": "Brightness level from 0 to 100."},
        },
        "required": ["level"],
    },
})
def set_brightness(level: int) -> Dict[str, Any]:
    """Set screen brightness."""
    level = max(5, min(100, level))
    fraction = round(level / 100, 2)

    if shutil.which("brightnessctl"):
        try:
            result = subprocess.run(
                ["brightnessctl", "set", f"{level}%"],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return {"success": True, "message": f"Brightness set to {level}%."}
        except Exception:
            pass

    if shutil.which("xrandr"):
        try:
            # Get primary display
            out = subprocess.check_output(["xrandr", "--listmonitors"], text=True, timeout=5)
            display = "eDP-1"
            for line in out.splitlines():
                if "+" in line:
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        display = parts[-1]
                        break
            result = subprocess.run(
                ["xrandr", "--output", display, "--brightness", str(fraction)],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return {"success": True, "message": f"Brightness set to {level}% via xrandr."}
        except Exception:
            pass

    return {"success": False, "error": "No brightness control tool found (brightnessctl/xrandr)."}


@register_tool({
    "name": "read_screen_text",
    "description": "Take a screenshot and extract visible text from the screen using OCR.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
})
def read_screen_text() -> Dict[str, Any]:
    """Capture screen and extract text via OCR."""
    screenshot_result = take_screenshot("ocr_temp.png")
    if not screenshot_result.get("success"):
        return {"success": False, "error": f"Screenshot failed: {screenshot_result.get('error')}"}

    img_path = screenshot_result["absolute_path"]

    try:
        import pytesseract
        from PIL import Image
        img = Image.open(img_path)
        text = pytesseract.image_to_string(img)
        return {
            "success": True,
            "text": text.strip(),
            "char_count": len(text.strip()),
            "screenshot_path": screenshot_result["path"],
        }
    except ImportError:
        return {
            "success": False,
            "error": "pytesseract or Pillow not installed. Run: pip install pytesseract Pillow",
        }
    except Exception as exc:
        return {"success": False, "error": f"OCR failed: {str(exc)}"}


@register_tool({
    "name": "get_command_audit_log",
    "description": "Retrieve the recent command execution audit log for security review.",
    "input_schema": {
        "type": "object",
        "properties": {
            "lines": {"type": "integer", "description": "Number of recent log lines to return (default: 50)."},
        },
        "required": [],
    },
})
def get_command_audit_log(lines: int = 50) -> Dict[str, Any]:
    """Read the command audit log."""
    if not AUDIT_LOG_FILE.exists():
        return {"success": True, "log": [], "message": "No audit log entries yet."}

    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        recent = all_lines[-lines:]
        return {
            "success": True,
            "total_entries": len(all_lines),
            "returned": len(recent),
            "log": [line.strip() for line in recent],
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}
