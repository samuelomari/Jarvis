"""Permission Manager - the central guard between the AI reasoning layer and the OS.

Architecture enforced by this module:

    AI Assistant
        |
    Permission Manager   <-- this file
        |
    Approved Tool / API
        |
    Operating System

Every tool execution flows through :meth:`PermissionManager.check`. The manager
classifies the request into one of four permission levels, decides whether the
action is allowed automatically, requires an explicit confirmation, or must be
blocked outright, and records an audit entry (never storing secrets).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIT_LOG_FILE = PROJECT_ROOT / "data" / "command_audit.log"


# ── Permission Levels ──────────────────────────────────────────────────────────

class PermissionLevel:
    """Four-tier permission model described in the Jarvis system contract."""

    INFORMATION = 0        # Read-only. No confirmation required.
    SAFE_AUTOMATION = 1    # Reversible automation. No confirmation required.
    SYSTEM_CHANGE = 2      # Explain action + request confirmation.
    DESTRUCTIVE = 3        # Always require explicit confirmation.

    NAMES = {
        0: "INFORMATION",
        1: "SAFE_AUTOMATION",
        2: "SYSTEM_CHANGE",
        3: "DESTRUCTIVE",
    }

    #: Any action at or above this level requires explicit confirmation.
    CONFIRMATION_THRESHOLD = SYSTEM_CHANGE


# ── Risk Classification ────────────────────────────────────────────────────────

# Level 0 - INFORMATION: never mutates state, no confirmation.
INFORMATION_TOOLS = {
    "get_current_time", "get_system_health", "get_disk_usage", "get_network_info",
    "get_running_processes", "check_proactive_alerts", "check_port", "read_file",
    "list_directory", "search_files", "inspect_symbols", "analyze_codebase",
    "explain_developer_failure", "git_status", "git_log", "git_diff", "recall",
    "list_tasks", "list_reminders", "list_calendar_events", "list_scheduled_tasks",
    "list_installed_packages", "list_available_agents", "list_user_notifications",
    "list_pomodoro_sessions", "daily_agenda", "search_web", "fetch_webpage",
    "github_list_repos", "gmail_search_messages", "calendar_list_events",
    "get_command_audit_log", "get_audit_log", "get_permission_status",
    "system_status", "classify_action_risk", "get_emergency_status",
    "emergency_stop", "resume_operations", "set_serious_mode",
    "get_serious_mode_status",
}

# Level 1 - SAFE_AUTOMATION: ordinary, reversible local automation.
SAFE_AUTOMATION_TOOLS = {
    "write_file", "append_file", "edit_file", "create_directory", "copy_file",
    "move_file", "open_application", "open_browser_url", "take_screenshot",
    "analyze_screenshot", "analyze_image_file", "read_screen_text", "set_volume",
    "set_brightness", "get_clipboard", "set_clipboard", "clear_clipboard",
    "list_windows", "focus_window", "minimize_window", "maximize_window",
    "speak_text", "remember", "forget", "notify_user", "create_calendar_event",
    "create_event", "set_reminder", "dismiss_reminder", "add_task", "complete_task",
    "git_create_branch", "git_commit", "generate_code", "scaffold_project",
    "start_pomodoro", "check_pomodoro", "find_large_files", "find_duplicate_files",
    "find_files", "organize_directory", "run_tests", "delegate_task",
}

# Level 2 - SYSTEM_CHANGE: mutates the host or moves data off-machine.
SYSTEM_CHANGE_TOOLS = {
    "install_package", "kill_process", "close_window", "git_push",
    "schedule_autonomous_task", "cancel_scheduled_task", "run_autonomous_mission",
    "run_multi_agent_workflow",
}

# Level 3 - DESTRUCTIVE: irreversible or security-sensitive.
DESTRUCTIVE_TOOLS = {
    "delete_file", "move_to_trash", "lock_screen", "restart_computer",
    "shutdown_computer",
}

# Shell command risk: LOW runs automatically, MEDIUM/HIGH need confirmation.
DANGEROUS_PATTERNS = [
    "rm -rf", "rm -fr", "mkfs", "dd if=", ":(){:|:&};:", "chmod 777 /",
    "sudo rm", "> /dev/sda", "shutdown", "reboot", "halt", "poweroff",
    "drop table", "delete from", "truncate table", "chown -r /", "iptables -f",
    "ufw disable", "passwd", "visudo", "> /dev/nvme",
]

MEDIUM_RISK_PATTERNS = [
    "pip install", "pip3 install", "npm install", "npm i ", "yarn add",
    "apt install", "apt-get install", "snap install", "cargo install",
    "npm run", "yarn run", "make install", "chmod ", "chown ", "systemctl ",
    "service ", "git push", "git reset", "git clean", "kill ", "pkill ",
    "docker run", "docker rm",
]

SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|private[_-]?key|access[_-]?key|"
    r"client[_-]?secret|credential|cookie|session|auth)",
    re.IGNORECASE,
)

REDACTED = "***REDACTED***"


# ── Decision Model ─────────────────────────────────────────────────────────────

@dataclass
class Decision:
    """Outcome of a permission check for a single action."""

    tool: str
    level: int
    allowed: bool
    requires_confirmation: bool
    blocked: bool
    reason: str
    risk_label: str = ""
    action: str = ""
    affected: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_tool_result(self) -> Dict[str, Any]:
        """Standard tool-shaped refusal/confirmation payload."""
        if self.blocked:
            return {
                "success": False,
                "blocked": True,
                "risk_level": self.risk_label,
                "error": self.reason,
            }
        return {
            "success": False,
            "needs_confirmation": True,
            "risk_level": self.risk_label,
            "error": self.reason,
            "preview": self.preview(),
        }

    def preview(self) -> Dict[str, Any]:
        """Command preview block shown to the user before sensitive actions."""
        return {
            "Task": self.action or f"Execute tool '{self.tool}'",
            "Risk level": self.risk_label or PermissionLevel.NAMES.get(self.level, "UNKNOWN"),
            "Command or action": self.action or self.tool,
            "Files/services affected": self.affected or ["(none detected)"],
        }

    def render_preview(self) -> str:
        """Human readable multi-line preview for the CLI."""
        lines = ["", "  ┌─ CONFIRMATION REQUIRED ──────────────────────────"]
        for key, value in self.preview().items():
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            lines.append(f"  │ {key}: {value}")
        lines.append("  └──────────────────────────────────────────────")
        return "\n".join(lines)


def _classify_command(command: str) -> Tuple[int, str, Optional[str]]:
    """Classify a shell command into a permission level.

    Returns ``(level, reason, matched_pattern)``.
    """
    cmd_lower = (command or "").lower()

    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in cmd_lower:
            return (
                PermissionLevel.DESTRUCTIVE,
                f"Command contains destructive pattern '{pattern}'.",
                pattern,
            )

    if cmd_lower.strip().startswith("sudo ") or " sudo " in f" {cmd_lower} ":
        return (
            PermissionLevel.DESTRUCTIVE,
            "Command requests elevated (sudo) privileges.",
            "sudo",
        )

    for pattern in MEDIUM_RISK_PATTERNS:
        if pattern.lower() in cmd_lower:
            return (
                PermissionLevel.SYSTEM_CHANGE,
                f"Command modifies the environment ('{pattern.strip()}').",
                pattern.strip(),
            )

    return (
        PermissionLevel.SAFE_AUTOMATION,
        "Read-only or low-impact command.",
        None,
    )


def redact_args(args: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a copy of tool arguments with sensitive values redacted."""
    if not args:
        return {}
    clean: Dict[str, Any] = {}
    for key, value in args.items():
        if SENSITIVE_KEY_PATTERN.search(str(key)):
            clean[key] = REDACTED
        elif isinstance(value, str) and len(value) > 300:
            clean[key] = value[:300] + "...(truncated)"
        else:
            clean[key] = value
    return clean


# ── Permission Manager ─────────────────────────────────────────────────────────

class PermissionManager:
    """Decides whether an action is allowed, confirmed, or blocked."""

    def __init__(
        self,
        audit_log_path: Optional[Path] = None,
        auto_confirm_level: int = PermissionLevel.SAFE_AUTOMATION,
    ):
        self.audit_log_path = Path(audit_log_path) if audit_log_path else AUDIT_LOG_FILE
        #: Actions at or below this level never prompt.
        self.auto_confirm_level = auto_confirm_level
        self._default_auto_confirm_level = auto_confirm_level
        self._serious_mode = False

    @property
    def serious_mode(self) -> bool:
        """When enabled, every mutating action (LEVEL 1+) requires confirmation."""
        return self._serious_mode

    def set_serious_mode(self, enabled: bool) -> Dict[str, Any]:
        """Toggle strict confirmation mode.

        In serious mode Jarvis prompts before *any* state-changing action, not
        just LEVEL 2/3 operations.
        """
        self._serious_mode = bool(enabled)
        self.auto_confirm_level = (
            PermissionLevel.INFORMATION if self._serious_mode
            else self._default_auto_confirm_level
        )
        return {
            "success": True,
            "serious_mode": self._serious_mode,
            "auto_confirm_level": self.auto_confirm_level,
            "message": (
                "Serious mode enabled: all state-changing actions require confirmation."
                if self._serious_mode
                else "Serious mode disabled: normal permissions restored."
            ),
        }

    # -- Classification --------------------------------------------------------

    def classify_command(self, command: str) -> Tuple[int, str]:
        """Public wrapper around shell command risk classification."""
        level, reason, _ = _classify_command(command)
        return level, reason

    def classify_tool(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> Tuple[int, str]:
        """Map a tool invocation to a permission level and explanation."""
        if tool_name == "run_terminal_command":
            return self.classify_command((args or {}).get("command", ""))

        if tool_name in DESTRUCTIVE_TOOLS:
            return PermissionLevel.DESTRUCTIVE, "Irreversible or security-sensitive action."
        if tool_name in SYSTEM_CHANGE_TOOLS:
            return PermissionLevel.SYSTEM_CHANGE, "Changes host state or pushes data externally."
        if tool_name in SAFE_AUTOMATION_TOOLS:
            return PermissionLevel.SAFE_AUTOMATION, "Reversible local automation."
        if tool_name in INFORMATION_TOOLS:
            return PermissionLevel.INFORMATION, "Read-only information request."

        # Unknown tools default to safe automation; they still surface in the audit log.
        return PermissionLevel.SAFE_AUTOMATION, "Unclassified tool (treated as reversible automation)."

    # -- Decision --------------------------------------------------------------

    def check(
        self,
        tool_name: str,
        args: Optional[Dict[str, Any]] = None,
        confirmed: bool = False,
    ) -> Decision:
        """Evaluate a tool invocation and return a :class:`Decision`."""
        args = args or {}
        if args.get("confirmed") is True:
            confirmed = True

        level, reason = self.classify_tool(tool_name, args)
        risk_label = PermissionLevel.NAMES.get(level, "UNKNOWN")

        action = tool_name
        if tool_name == "run_terminal_command":
            action = f"$ {args.get('command', '')}"
        elif tool_name == "open_application":
            action = f"Launch '{args.get('app_name', '')}'"
        elif tool_name == "install_package":
            action = f"Install package '{args.get('package', '')}'"
        elif tool_name in ("delete_file", "move_to_trash"):
            action = f"Delete '{args.get('path', '')}'"

        affected = [
            str(value) for key, value in args.items()
            if key in ("path", "file_path", "source_path", "destination_path",
                       "app_name", "package", "service")
        ]

        decision = Decision(
            tool=tool_name,
            level=level,
            allowed=True,
            requires_confirmation=False,
            blocked=False,
            reason=reason,
            risk_label=risk_label,
            action=action,
            affected=affected,
        )

        if level > self.auto_confirm_level and not confirmed:
            decision.allowed = False
            decision.requires_confirmation = True
            if level >= PermissionLevel.DESTRUCTIVE:
                decision.reason = f"{reason} Explicit confirmation required before proceeding."
            else:
                decision.reason = f"{reason} Please confirm before proceeding."
        elif level > self.auto_confirm_level and confirmed:
            decision.reason = f"{reason} Confirmation received."

        return decision

    # -- Audit Log -------------------------------------------------------------

    def log(
        self,
        tool_name: str,
        args: Optional[Dict[str, Any]],
        result: Any,
        level: int,
        status: str,
        request: str = "",
    ) -> None:
        """Append a single audit entry. Secrets are always redacted."""
        try:
            self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().isoformat()
            safe_args = redact_args(args)
            if isinstance(result, dict):
                summary = result.get("message") or result.get("error") or (
                    "ok" if result.get("success") else "failed"
                )
            else:
                summary = str(result)
            summary = str(summary)[:200]
            risk = PermissionLevel.NAMES.get(level, "UNKNOWN")

            with open(self.audit_log_path, "a", encoding="utf-8") as handle:
                handle.write(
                    f"[{timestamp}] [LEVEL={risk}] [{status}] TOOL: {tool_name} | "
                    f"ARGS: {json.dumps(safe_args, default=str)[:400]} | "
                    f"RESULT: {summary}\n"
                )
        except Exception:
            # Auditing must never break tool execution.
            pass

    def read_audit_log(self, lines: int = 50) -> Dict[str, Any]:
        """Return the most recent audit entries."""
        if not self.audit_log_path.exists():
            return {"success": True, "log": [], "message": "No audit log entries yet."}
        try:
            with open(self.audit_log_path, "r", encoding="utf-8") as handle:
                all_lines = handle.readlines()
            recent = all_lines[-lines:]
            return {
                "success": True,
                "total_entries": len(all_lines),
                "returned": len(recent),
                "log": [line.strip() for line in recent],
            }
        except Exception as exc:  # pragma: no cover - defensive
            return {"success": False, "error": str(exc)}


_PERMISSION_MANAGER: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """Return the process-wide Permission Manager singleton."""
    global _PERMISSION_MANAGER
    if _PERMISSION_MANAGER is None:
        _PERMISSION_MANAGER = PermissionManager()
    return _PERMISSION_MANAGER
