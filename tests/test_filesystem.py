"""Unit tests for Jarvis filesystem tools."""

from pathlib import Path
import pytest
from tools.filesystem import (
    _resolve_safe_path,
    read_file,
    write_file,
    list_directory,
    search_files,
    PROJECT_ROOT,
)


def test_safe_path_boundary():
    """Test that path resolution blocks access outside PROJECT_ROOT."""
    # Resolving within project root succeeds
    safe = _resolve_safe_path("config.py")
    assert safe == PROJECT_ROOT / "config.py"

    # Attempting to escape project root raises PermissionError
    with pytest.raises(PermissionError):
        _resolve_safe_path("../../etc/passwd")


def test_read_file():
    """Test reading existing file and line slice."""
    res = read_file("config.py", start_line=1, end_line=5)
    assert res["success"] is True
    assert "start_line" in res
    assert res["start_line"] == 1
    assert res["end_line"] == 5
    assert "MODEL" in res["content"] or "PROJECT_ROOT" in res["content"] or "load_dotenv" in res["content"]

    # Non-existent file
    missing = read_file("non_existent_file_12345.xyz")
    assert missing["success"] is False
    assert "not found" in missing["error"].lower()


def test_write_file_and_overwrite(tmp_path, monkeypatch):
    """Test writing and overwriting files safely."""
    test_rel_path = "data/test_sample.txt"

    # Write initial file
    res1 = write_file(test_rel_path, "Hello Jarvis!", overwrite=True)
    assert res1["success"] is True

    # Try to write without overwrite -> should fail
    res2 = write_file(test_rel_path, "New text", overwrite=False)
    assert res2["success"] is False
    assert "already exists" in res2["error"]

    # Overwrite = True
    res3 = write_file(test_rel_path, "New text updated", overwrite=True)
    assert res3["success"] is True

    # Verify content
    read_back = read_file(test_rel_path)
    assert "New text updated" in read_back["content"]

    # Clean up test file
    (PROJECT_ROOT / test_rel_path).unlink(missing_ok=True)


def test_list_directory():
    """Test listing directory tree structure."""
    res = list_directory("tools", max_depth=1)
    assert res["success"] is True
    assert "tree" in res
    assert "basic.py" in res["tree"]


def test_search_files():
    """Test searching for strings inside project workspace."""
    res = search_files(query="JARVIS", path=".")
    assert res["success"] is True
    assert res["match_count"] > 0
    assert any("README.md" in m["file"] or "SYSTEM.md" in m["file"] for m in res["matches"])

