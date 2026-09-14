"""Tests for task management support in Jarvis."""

from memory.calendar_manager import CalendarManager
from memory.manager import MemoryManager


def test_daily_agenda_summary(tmp_path):
    """A daily agenda should combine tasks, calendar events, and reminders."""
    memory = MemoryManager(tmp_path / "task_store.json")
    calendar = CalendarManager(tmp_path / "calendar.json")

    memory.add_task("Review launch notes", "Finalize the release announcement")
    calendar.add_event("Design sync", "2026-09-14", "09:30", category="work")
    calendar.add_reminder("Send client follow-up", "2026-09-14 16:00", "Check in on the proposal")

    agenda = memory.daily_agenda("2026-09-14", calendar_manager=calendar)
    assert agenda["success"] is True
    assert "Review launch notes" in agenda["summary"]
    assert "Design sync" in agenda["summary"]
    assert "Send client follow-up" in agenda["summary"]


def test_task_management_round_trip(tmp_path):
    """Store tasks, list them, and complete one."""
    mgr = MemoryManager(tmp_path / "tasks.json")

    created = mgr.add_task("Draft launch email", "Write the announcement note for the release")
    assert created["success"] is True
    assert created["task"]["title"] == "Draft launch email"
    assert created["task"]["status"] == "pending"

    all_tasks = mgr.list_tasks()
    assert all_tasks["count"] == 1
    assert all_tasks["tasks"][0]["title"] == "Draft launch email"

    task_id = created["task"]["id"]
    completed = mgr.complete_task(task_id)
    assert completed["success"] is True
    assert completed["task"]["status"] == "completed"

    remaining = mgr.list_tasks(status="pending")
    assert remaining["count"] == 0


def test_task_tool_registration_and_api_contract():
    """Ensure task tools are available in the global registry."""
    from tools.registry import get_all_tool_schemas

    tool_names = {tool["name"] for tool in get_all_tool_schemas()}
    assert "add_task" in tool_names
    assert "list_tasks" in tool_names
    assert "complete_task" in tool_names
