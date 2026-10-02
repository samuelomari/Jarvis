"""Permission Manager & Security Controller for JARVIS.

Enforces 4-tier security levels:
LEVEL 0 - INFORMATION: No confirmation required (read-only, status, inspection)
LEVEL 1 - SAFE AUTOMATION: No confirmation required (open apps, launch VS Code, safe file creation)
LEVEL 2 - SYSTEM CHANGES: Explain the action and request confirmation (install packages, modify configs, send email, kill user processes)
LEVEL 3 - DESTRUCTIVE OR SECURITY-SENSITIVE ACTIONS: Always require explicit confirmation (permanent delete, restart, shutdown, sudo)

Maintains a secure, sanitized audit trail.
"""

from datetime import datetime, timezone
from enum import IntEnum
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIT_LOG_FILE = PROJECT_ROOT / "data" / "audit_log.json"


class PermissionLevel(IntEnum):
    LEVEL_0_INFORMATION = 0
    LEVEL_1_SAFE_AUTOMATION = 1
    LEVEL_2_SYSTEM_CHANGES = 2
    LEVEL_3_DESTRUCTIVE_OR_SENSITIVE = 3


# Tool classification mapping
TOOL_PERMISSION_MAP: Dict[str, PermissionLevel] = {
    # LEVEL 0: Information / Read-Only
    "get_current_time": PermissionLevel.LEVEL_0_INFORMATION,
    "get_system_health": PermissionLevel.LEVEL_0_INFORMATION,
    "get_disk_usage": PermissionLevel.LEVEL_0_INFORMATION,
    "get_network_info": PermissionLevel.LEVEL_0_INFORMATION,
    "get_running_processes": PermissionLevel.LEVEL_0_INFORMATION,
    "check_port": PermissionLevel.LEVEL_0_INFORMATION,
    "check_proactive_alerts": PermissionLevel.LEVEL_0_INFORMATION,
    "list_directory": PermissionLevel.LEVEL_0_INFORMATION,
    "read_file": PermissionLevel.LEVEL_0_INFORMATION,
    "search_files": PermissionLevel.LEVEL_0_INFORMATION,
    "inspect_symbols": PermissionLevel.LEVEL_0_INFORMATION,
    "analyze_codebase": PermissionLevel.LEVEL_0_INFORMATION,
    "search_web": PermissionLevel.LEVEL_0_INFORMATION,
    "fetch_webpage": PermissionLevel.LEVEL_0_INFORMATION,
    "calendar_list_events": PermissionLevel.LEVEL_0_INFORMATION,
    "list_calendar_events": PermissionLevel.LEVEL_0_INFORMATION,
    "list_tasks": PermissionLevel.LEVEL_0_INFORMATION,
    "list_reminders": PermissionLevel.LEVEL_0_INFORMATION,
    "list_user_notifications": PermissionLevel.LEVEL_0_INFORMATION,
    "list_scheduled_tasks": PermissionLevel.LEVEL_0_INFORMATION,
    "list_available_agents": PermissionLevel.LEVEL_0_INFORMATION,
    "list_installed_packages": PermissionLevel.LEVEL_0_INFORMATION,
    "list_pomodoro_sessions": PermissionLevel.LEVEL_0_INFORMATION,
    "check_pomodoro": PermissionLevel.LEVEL_0_INFORMATION,
    "daily_agenda": PermissionLevel.LEVEL_0_INFORMATION,
    "explain_developer_failure": PermissionLevel.LEVEL_0_INFORMATION,
    "get_command_audit_log": PermissionLevel.LEVEL_0_INFORMATION,
    "github_list_repos": PermissionLevel.LEVEL_0_INFORMATION,
    "gmail_search_messages": PermissionLevel.LEVEL_0_INFORMATION,
    "search_emails": PermissionLevel.LEVEL_0_INFORMATION,
    "read_email": PermissionLevel.LEVEL_0_INFORMATION,
    "git_status": PermissionLevel.LEVEL_0_INFORMATION,
    "git_diff": PermissionLevel.LEVEL_0_INFORMATION,
    "git_log": PermissionLevel.LEVEL_0_INFORMATION,
    "read_clipboard": PermissionLevel.LEVEL_0_INFORMATION,
    "recall": PermissionLevel.LEVEL_0_INFORMATION,
    "take_screenshot": PermissionLevel.LEVEL_0_INFORMATION,
    "analyze_screenshot": PermissionLevel.LEVEL_0_INFORMATION,
    "analyze_image_file": PermissionLevel.LEVEL_0_INFORMATION,
    "read_screen_text": PermissionLevel.LEVEL_0_INFORMATION,

    # LEVEL 1: Safe Automation
    "open_application": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "open_browser_url": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "write_file": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "append_file": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "edit_file": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "create_directory": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "copy_file": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "move_file": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "trash_file": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "find_large_files": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "find_duplicate_files": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "organize_folder": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "speak_text": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "voice_speak": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "voice_listen": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "copy_to_clipboard": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "clear_clipboard": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "set_volume": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "set_brightness": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "minimize_window": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "maximize_window": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "switch_application": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "lock_computer": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "remember": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "forget": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "add_task": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "complete_task": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "set_reminder": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "dismiss_reminder": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "notify_user": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "start_pomodoro": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "generate_code": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "scaffold_project": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "run_tests": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "git_commit": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "git_create_branch": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "serious_mode_research": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "delegate_task": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,
    "draft_email": PermissionLevel.LEVEL_1_SAFE_AUTOMATION,

    # LEVEL 2: System Changes (Requires confirmation / explanation)
    "install_package": PermissionLevel.LEVEL_2_SYSTEM_CHANGES,
    "close_application": PermissionLevel.LEVEL_2_SYSTEM_CHANGES,
    "kill_process": PermissionLevel.LEVEL_2_SYSTEM_CHANGES,
    "git_push": PermissionLevel.LEVEL_2_SYSTEM_CHANGES,
    "schedule_autonomous_task": PermissionLevel.LEVEL_2_SYSTEM_CHANGES,
    "cancel_scheduled_task": PermissionLevel.LEVEL_2_SYSTEM_CHANGES,
    "run_autonomous_mission": PermissionLevel.LEVEL_2_SYSTEM_CHANGES,
    "run_multi_agent_workflow": PermissionLevel.LEVEL_2_SYSTEM_CHANGES,
    "create_calendar_event": PermissionLevel.LEVEL_2_SYSTEM_CHANGES,
    "send_email": PermissionLevel.LEVEL_2_SYSTEM_CHANGES,

    # LEVEL 3: Destructive or Security-Sensitive (Explicit confirmation required)
    "delete_file": PermissionLevel.LEVEL_3_DESTRUCTIVE_OR_SENSITIVE,
    "restart_computer": PermissionLevel.LEVEL_3_DESTRUCTIVE_OR_SENSITIVE,
    "shutdown_computer": PermissionLevel.LEVEL_3_DESTRUCTIVE_OR_SENSITIVE,
}

# Dangerous terminal command patterns
HIGH_RISK_TERMINAL_PATTERNS = [
    r"\brm\s+(-[rfRF]+\s+|--recursive)",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r"\bchmod\s+(-R\s+)?777\b",
    r"\bchown\s+-R\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bpoweroff\b",
    r"\bhalt\b",
    r"\biptables\b",
    r"\bufw\b",
    r"\buseradd\b",
    r"\buserdel\b",
    r"\busermod\b",
    r"\bpasswd\b",
    r"\bsudo\b",
    r">\s*/dev/sd[a-z]",
    r">\s*/dev/nvme",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",  # Fork bomb
]

MEDIUM_RISK_TERMINAL_PATTERNS = [
    r"\bpip\s+install\b",
    r"\bnpm\s+install\b",
    r"\bapt(-get)?\s+install\b",
    r"\bgit\s+push\b",
    r"\bkill\b",
    r"\bpkill\b",
    r"\bsystemctl\s+(start|stop|restart)\b",
    r"\bservice\s+\w+\s+(start|stop|restart)\b",
]

# Sensitive credentials redaction regexes
SECRET_PATTERNS = [
    (r"(?i)(api[_-]?key|secret|password|passwd|auth[_-]?token|bearer|access[_-]?token)[\"']?\s*[:=]\s*[\"']?([^\"'\s,;&]+)", r"\1=***REDACTED***"),
    (r"sk-[a-zA-Z0-9_\-]{20,}", "***REDACTED_API_KEY***"),
    (r"ghp_[a-zA-Z0-9]{36}", "***REDACTED_GITHUB_TOKEN***"),
    (r"-----BEGIN (?:RSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA )?PRIVATE KEY-----", "***REDACTED_PRIVATE_KEY***"),
]


def sanitize_secrets(text: Any) -> Any:
    """Sanitize sensitive keys, tokens, or passwords from logs or display."""
    if isinstance(text, dict):
        return {k: sanitize_secrets(v) for k, v in text.items()}
    if isinstance(text, list):
        return [sanitize_secrets(i) for i in text]
    if not isinstance(text, str):
        return text

    sanitized = text
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized


class PermissionManager:
    """Evaluates security levels, handles previews, confirmations, and audit logging."""

    def __init__(self, audit_file: Optional[Path] = None):
        self.audit_file = audit_file or AUDIT_LOG_FILE

    def classify_terminal_command(self, command: str) -> Tuple[PermissionLevel, str]:
        """Classify a shell command into LOW (Level 0/1), MEDIUM (Level 2), or HIGH (Level 3) risk."""
        cmd_clean = command.strip()
        for pattern in HIGH_RISK_TERMINAL_PATTERNS:
            if re.search(pattern, cmd_clean, re.IGNORECASE):
                return PermissionLevel.LEVEL_3_DESTRUCTIVE_OR_SENSITIVE, f"High-risk pattern matched: {pattern}"

        for pattern in MEDIUM_RISK_TERMINAL_PATTERNS:
            if re.search(pattern, cmd_clean, re.IGNORECASE):
                return PermissionLevel.LEVEL_2_SYSTEM_CHANGES, f"System change pattern matched: {pattern}"

        return PermissionLevel.LEVEL_1_SAFE_AUTOMATION, "Low-risk command"

    def classify_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Tuple[PermissionLevel, str]:
        """Classify a tool call into its permission level."""
        if tool_name == "run_terminal_command":
            cmd = tool_args.get("command", "")
            return self.classify_terminal_command(cmd)

        level = TOOL_PERMISSION_MAP.get(tool_name, PermissionLevel.LEVEL_2_SYSTEM_CHANGES)
        reason = f"Standard classification for '{tool_name}'"
        return level, reason

    def build_command_preview(
        self,
        task: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        level: PermissionLevel,
    ) -> str:
        """
        Format standard command preview required by JARVIS specification:
        Task:
        Risk level:
        Command or action:
        Files/services affected:
        Proceed? yes/no
        """
        clean_args = sanitize_secrets(tool_args)
        level_name = {
            PermissionLevel.LEVEL_0_INFORMATION: "LEVEL 0 — INFORMATION",
            PermissionLevel.LEVEL_1_SAFE_AUTOMATION: "LEVEL 1 — SAFE AUTOMATION",
            PermissionLevel.LEVEL_2_SYSTEM_CHANGES: "LEVEL 2 — SYSTEM CHANGES",
            PermissionLevel.LEVEL_3_DESTRUCTIVE_OR_SENSITIVE: "LEVEL 3 — DESTRUCTIVE OR SECURITY-SENSITIVE",
        }.get(level, str(level))

        target = (
            clean_args.get("path")
            or clean_args.get("command")
            or clean_args.get("app_name")
            or clean_args.get("to")
            or clean_args.get("pid")
            or "Local system"
        )

        return (
            f"\n[bold yellow]── SECURITY COMMAND PREVIEW ─────────────────────[/bold yellow]\n"
            f"Task:                    {task}\n"
            f"Risk level:              {level_name}\n"
            f"Command or action:       {tool_name}({json.dumps(clean_args)})\n"
            f"Files/services affected: {target}\n"
            f"─────────────────────────────────────────────────\n"
            f"Proceed? yes/no"
        )

    def is_allowed_automatically(self, level: PermissionLevel) -> bool:
        """Level 0 and 1 execute automatically; Level 2 and 3 require confirmation."""
        return level in (PermissionLevel.LEVEL_0_INFORMATION, PermissionLevel.LEVEL_1_SAFE_AUTOMATION)

    def log_action(
        self,
        request_text: str,
        actions_performed: str,
        commands_executed: str,
        result: Any,
        level: PermissionLevel,
        status: str = "COMPLETED",
    ) -> None:
        """Record an entry in the structured audit log with secret redaction."""
        try:
            self.audit_file.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request": sanitize_secrets(request_text)[:500],
                "actions_performed": sanitize_secrets(actions_performed),
                "commands_executed": sanitize_secrets(commands_executed)[:500],
                "result": sanitize_secrets(str(result))[:1000],
                "risk_level": int(level),
                "level_name": level.name,
                "status": status,
            }

            entries = []
            if self.audit_file.exists():
                try:
                    with open(self.audit_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            entries = data
                except Exception:
                    entries = []

            entries.append(entry)
            # Keep the last 500 audit entries
            if len(entries) > 500:
                entries = entries[-500:]

            with open(self.audit_file, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)

        except Exception as exc:
            logger.error("Failed to write audit log: %s", exc)

    def get_recent_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent audit log items."""
        if not self.audit_file.exists():
            return []
        try:
            with open(self.audit_file, "r", encoding="utf-8") as f:
                entries = json.load(f)
            return entries[-limit:] if isinstance(entries, list) else []
        except Exception:
            return []


_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """Get the global PermissionManager singleton."""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager
