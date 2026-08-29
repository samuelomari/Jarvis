"""Unit tests for Jarvis MemoryManager and memory tools."""

import tempfile
from pathlib import Path
import pytest
from memory.manager import MemoryManager


@pytest.fixture
def temp_memory():
    """Create a temporary MemoryManager instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mem_file = Path(tmpdir) / "test_memory.json"
        mgr = MemoryManager(mem_file)
        yield mgr


def test_memory_initialization(temp_memory):
    """Test that memory initializes with default categories."""
    data = temp_memory.load()
    assert "user_preferences" in data
    assert "projects" in data
    assert "goals" in data
    assert "important_facts" in data


def test_remember_and_recall(temp_memory):
    """Test storing items and recalling them."""
    res1 = temp_memory.remember("user_preferences", "Prefers clean code and Python")
    assert res1["success"] is True

    res2 = temp_memory.remember("projects", "Building DevOS framework")
    assert res2["success"] is True

    # Duplicate check
    res_dup = temp_memory.remember("projects", "Building DevOS framework")
    assert res_dup["success"] is True
    assert "already exists" in res_dup["message"]

    # Recall all
    all_mem = temp_memory.recall()
    assert all_mem["count"] == 2
    assert "user_preferences" in all_mem["memories"]
    assert "projects" in all_mem["memories"]

    # Recall by category
    proj_mem = temp_memory.recall(category="projects")
    assert proj_mem["count"] == 1
    assert "DevOS" in proj_mem["memories"]["projects"][0]

    # Recall with search query
    query_mem = temp_memory.recall(query="python")
    assert query_mem["count"] == 1
    assert "Python" in query_mem["memories"]["user_preferences"][0]


def test_forget_memory(temp_memory):
    """Test removing memory items by index and by text matching."""
    temp_memory.remember("goals", "Learn Rust")
    temp_memory.remember("goals", "Master TypeScript")

    # Forget by 1-based index (item 1 = "Learn Rust")
    res = temp_memory.forget("goals", 1)
    assert res["success"] is True
    assert res["removed"] == "Learn Rust"

    # Remaining item
    recalled = temp_memory.recall(category="goals")
    assert recalled["count"] == 1
    assert recalled["memories"]["goals"][0] == "Master TypeScript"

    # Forget by string match
    res2 = temp_memory.forget("goals", "TypeScript")
    assert res2["success"] is True

    recalled_after = temp_memory.recall(category="goals")
    assert recalled_after["count"] == 0


def test_memory_summary(temp_memory):
    """Test formatting memory summary for system prompt."""
    temp_memory.remember("projects", "Jarvis Assistant")
    summary = temp_memory.get_summary()
    assert "Projects" in summary
    assert "Jarvis Assistant" in summary

