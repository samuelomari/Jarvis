"""Unit tests for the Jarvis security layer (Permission Manager + Emergency Stop)."""

import pytest

import security.permission_manager as spm
from security import (
    PermissionLevel,
    get_emergency_stop,
    is_emergency_command,
)
from security.permission_manager import PermissionManager, redact_args
from tools.registry import execute_tool


@pytest.fixture(autouse=True)
def _fresh_security(tmp_path, monkeypatch):
    """Isolate each test with a temp audit log and a released emergency brake."""
    pm = PermissionManager(audit_log_path=tmp_path / "audit.log")
    monkeypatch.setattr(spm, "_PERMISSION_MANAGER", pm)
    emergency = get_emergency_stop()
    emergency.release()
    yield pm
    emergency.release()
    spm._PERMISSION_MANAGER = None


# ── Classification ─────────────────────────────────────────────────────────────

def test_tool_risk_levels():
    """Tools map to the expected permission levels."""
    pm = PermissionManager()
    assert pm.classify_tool("read_file")[0] == PermissionLevel.INFORMATION
    assert pm.classify_tool("write_file")[0] == PermissionLevel.SAFE_AUTOMATION
    assert pm.classify_tool("install_package")[0] == PermissionLevel.SYSTEM_CHANGE
    assert pm.classify_tool("delete_file")[0] == PermissionLevel.DESTRUCTIVE


def test_command_risk_levels():
    """Shell commands are graded LOW/MEDIUM/HIGH (mapped to levels 1/2/3)."""
    pm = PermissionManager()
    assert pm.classify_command("ls -la")[0] == PermissionLevel.SAFE_AUTOMATION
    assert pm.classify_command("git status")[0] == PermissionLevel.SAFE_AUTOMATION
    assert pm.classify_command("pip install requests")[0] == PermissionLevel.SYSTEM_CHANGE
    assert pm.classify_command("rm -rf /tmp/data")[0] == PermissionLevel.DESTRUCTIVE
    assert pm.classify_command("sudo rm /etc/hosts")[0] == PermissionLevel.DESTRUCTIVE


# ── Decisions ──────────────────────────────────────────────────────────────────

def test_check_requires_confirmation_for_destructive(tmp_path):
    """Destructive actions are blocked until explicitly confirmed."""
    pm = PermissionManager(audit_log_path=tmp_path / "a.log")
    decision = pm.check("delete_file", {"path": "data/x.txt"})
    assert decision.blocked is False
    assert decision.allowed is False
    assert decision.requires_confirmation is True
    assert decision.preview()["Risk level"] == "DESTRUCTIVE"

    confirmed = pm.check("delete_file", {"path": "data/x.txt"}, confirmed=True)
    assert confirmed.allowed is True


def test_check_allows_information_and_safe():
    """Level 0/1 actions run without confirmation."""
    pm = PermissionManager()
    assert pm.check("read_file", {"path": "config.py"}).allowed is True
    assert pm.check("write_file", {"path": "data/x.txt", "content": "hi"}).allowed is True


def test_serious_mode_escalates_confirmations():
    """Serious mode makes every state-changing action require confirmation."""
    pm = PermissionManager()
    pm.set_serious_mode(True)
    assert pm.auto_confirm_level == PermissionLevel.INFORMATION
    assert pm.check("write_file", {"path": "data/x.txt", "content": "hi"}).requires_confirmation is True
    assert pm.check("read_file", {"path": "config.py"}).allowed is True
    pm.set_serious_mode(False)
    assert pm.check("write_file", {"path": "data/x.txt", "content": "hi"}).allowed is True


def test_redact_args_hides_secrets():
    """Secrets are redacted before auditing."""
    clean = redact_args({"api_key": "sk-123", "password": "hunter2", "path": "main.py"})
    assert clean["api_key"] == "***REDACTED***"
    assert clean["password"] == "***REDACTED***"
    assert clean["path"] == "main.py"


def test_audit_log_records_and_redacts(tmp_path):
    """Audit entries are written and sensitive values never stored."""
    pm = PermissionManager(audit_log_path=tmp_path / "audit.log")
    pm.log("set_clipboard", {"text": "hello", "token": "secret-token"}, {"success": True}, 1, "ALLOWED")
    result = pm.read_audit_log()
    assert result["success"] is True
    assert result["total_entries"] == 1
    blob = "\n".join(result["log"])
    assert "set_clipboard" in blob
    assert "secret-token" not in blob


# ── Emergency Stop ─────────────────────────────────────────────────────────────

def test_emergency_phrases():
    """Emergency triggers are recognised case/whitespace insensitively."""
    assert is_emergency_command("Jarvis stop!")
    assert is_emergency_command("  emergency stop  ")
    assert is_emergency_command("jarvis cancel")
    assert not is_emergency_command("what time is it")


def test_emergency_blocks_tool_execution():
    """While engaged, ordinary tools are blocked but control tools still work."""
    emergency = get_emergency_stop()
    emergency.engage("test")

    blocked = execute_tool("get_current_time")
    assert blocked["success"] is False
    assert blocked["emergency_stop"] is True

    status = execute_tool("get_permission_status")
    assert status["success"] is True

    emergency.release()
    assert isinstance(execute_tool("get_current_time"), str)


# ── Registry Enforcement ───────────────────────────────────────────────────────

def test_execute_tool_gates_destructive_action():
    """The registry returns needs_confirmation for destructive tools."""
    result = execute_tool("delete_file", {"path": "data/does_not_matter.txt"})
    assert result["success"] is False
    assert result["needs_confirmation"] is True


def test_execute_tool_confirmation_callback_approves():
    """A confirming callback allows the action to proceed."""
    from tools.filesystem import PROJECT_ROOT, write_file

    rel = "data/security_confirm_test.txt"
    write_file(rel, "content", overwrite=True)
    target = PROJECT_ROOT / rel
    assert target.exists()

    result = execute_tool("delete_file", {"path": rel}, confirm_callback=lambda decision: True)
    assert result["success"] is True
    assert not target.exists()


def test_execute_tool_confirmation_callback_denies():
    """A denying callback cancels the action and the file survives."""
    from tools.filesystem import PROJECT_ROOT, write_file

    rel = "data/security_deny_test.txt"
    write_file(rel, "content", overwrite=True)
    target = PROJECT_ROOT / rel

    result = execute_tool("delete_file", {"path": rel}, confirm_callback=lambda decision: False)
    assert result["success"] is False
    assert target.exists()

    target.unlink(missing_ok=True)


def test_terminal_command_risk_gating():
    """Terminal commands are graded by the registry before execution."""
    low = execute_tool("run_terminal_command", {"command": "pwd"})
    assert low["success"] is True
    assert "returncode" in low

    high = execute_tool("run_terminal_command", {"command": "rm -rf ./data/nothing"})
    assert high["success"] is False
    assert high["needs_confirmation"] is True