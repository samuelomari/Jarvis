"""Unit tests for the desktop/system plugin modules.

Covers the security manager tools, serious mode, clipboard, window manager, and
file manager. Hardware-dependent operations (clipboard backends, X11 windows) are
asserted to return well-formed results rather than to succeed.
"""

import pytest

import security.permission_manager as spm
from security.permission_manager import PermissionManager
from tools.clipboard import clear_clipboard, get_clipboard
from tools.file_manager import (
    _resolve_scan_root,
    find_duplicate_files,
    find_files,
    find_large_files,
    move_to_trash,
    organize_directory,
)
from tools.security_manager import (
    classify_action_risk,
    get_audit_log,
    get_emergency_status,
    get_permission_status,
    system_status,
)
from tools.serious_mode import get_serious_mode_status, set_serious_mode
from tools.window_manager import close_window, list_windows

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    """Use a temp audit log so tests never touch the real one."""
    monkeypatch.setattr(spm, "_PERMISSION_MANAGER", PermissionManager(audit_log_path=tmp_path / "audit.log"))
    yield
    spm._PERMISSION_MANAGER = None


@pytest.fixture
def fm_dir():
    """A disposable directory inside the workspace for file-manager tests."""
    import shutil

    folder = PROJECT_ROOT / "data" / "fm_test"
    folder.mkdir(parents=True, exist_ok=True)
    yield folder
    shutil.rmtree(folder, ignore_errors=True)


# ── Security manager tools ─────────────────────────────────────────────────────

def test_security_status_tools():
    """Status/introspection tools return successful payloads."""
    assert get_permission_status()["success"] is True
    assert get_emergency_status()["success"] is True
    assert system_status()["success"] is True
    assert get_audit_log()["success"] is True


def test_classify_action_risk_tool():
    """Risk preview reflects the command classification."""
    risky = classify_action_risk(command="rm -rf /tmp/x")
    assert risky["risk_level"] == "DESTRUCTIVE"

    safe = classify_action_risk(tool_name="read_file")
    assert safe["permission_level"] == 0

    missing = classify_action_risk()
    assert missing["success"] is False


def test_serious_mode_tool():
    """Serious mode can be toggled and reported through tools."""
    assert set_serious_mode(True)["serious_mode"] is True
    assert get_serious_mode_status()["serious_mode"] is True
    assert set_serious_mode(False)["serious_mode"] is False


# ── Clipboard ──────────────────────────────────────────────────────────────────

def test_clear_clipboard_requires_confirmation():
    """Clearing the clipboard must be explicitly confirmed."""
    result = clear_clipboard()
    assert result["success"] is False
    assert result["needs_confirmation"] is True


def test_get_clipboard_returns_wellformed_result():
    """Clipboard reads return a structured result whether or not a backend exists."""
    result = get_clipboard()
    assert isinstance(result, dict)
    assert "success" in result


# ── Window manager ─────────────────────────────────────────────────────────────

def test_close_window_requires_confirmation():
    """Closing a window must be explicitly confirmed."""
    result = close_window("Some Window")
    assert result["success"] is False
    assert result["needs_confirmation"] is True


def test_list_windows_returns_wellformed_result():
    """Window enumeration returns a structured result (or an informative error)."""
    result = list_windows()
    assert isinstance(result, dict)
    assert "success" in result


# ── File manager ───────────────────────────────────────────────────────────────

def test_scan_root_blocks_system_directories():
    """System directories can never be scanned."""
    with pytest.raises(PermissionError):
        _resolve_scan_root("/etc")
    with pytest.raises(PermissionError):
        _resolve_scan_root("/usr")


def test_find_files(fm_dir):
    """find_files matches glob patterns within the workspace."""
    (fm_dir / "alpha.py").write_text("print('a')", encoding="utf-8")
    (fm_dir / "beta.txt").write_text("b", encoding="utf-8")

    result = find_files(name_pattern="*.py", path="data/fm_test")
    assert result["success"] is True
    names = [m["path"] for m in result["matches"]]
    assert any(name.endswith("alpha.py") for name in names)
    assert not any(name.endswith("beta.txt") for name in names)


def test_find_large_files(fm_dir):
    """find_large_files isolates files above the threshold."""
    (fm_dir / "small.txt").write_text("x" * 10, encoding="utf-8")
    (fm_dir / "big.bin").write_bytes(b"0" * (2 * 1024 * 1024))

    result = find_large_files(min_size_mb=1, path="data/fm_test")
    assert result["success"] is True
    files = [item["path"] for item in result["files"]]
    assert any(name.endswith("big.bin") for name in files)
    assert not any(name.endswith("small.txt") for name in files)


def test_find_duplicate_files(fm_dir):
    """find_duplicate_files groups identical content."""
    payload = "duplicate content here"
    (fm_dir / "one.txt").write_text(payload, encoding="utf-8")
    (fm_dir / "two.txt").write_text(payload, encoding="utf-8")
    (fm_dir / "unique.txt").write_text("something else entirely", encoding="utf-8")

    result = find_duplicate_files(path="data/fm_test", min_size_kb=0.001)
    assert result["success"] is True
    assert result["duplicate_groups"] >= 1
    flat = [f for group in result["groups"] for f in group["files"]]
    assert any(name.endswith("one.txt") for name in flat)
    assert any(name.endswith("two.txt") for name in flat)


def test_organize_directory_dry_run(fm_dir):
    """Dry-run organization returns a plan without moving anything."""
    (fm_dir / "note.md").write_text("hello", encoding="utf-8")
    result = organize_directory(path="data/fm_test", dry_run=True)
    assert result["success"] is True
    assert result["dry_run"] is True
    assert (fm_dir / "note.md").exists()
    assert any(item["destination"].startswith("md/") for item in result["plan"])


def test_move_to_trash_requires_confirmation(fm_dir):
    """Trash moves are refused without explicit confirmation."""
    target = fm_dir / "to_delete.txt"
    target.write_text("bye", encoding="utf-8")
    result = move_to_trash(path="data/fm_test/to_delete.txt")
    assert result["success"] is False
    assert result["needs_confirmation"] is True
    assert target.exists()
