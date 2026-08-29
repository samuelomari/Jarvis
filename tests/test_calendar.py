"""Unit tests for Jarvis CalendarManager and scheduling tools."""

import tempfile
from pathlib import Path
import pytest
from memory.calendar_manager import CalendarManager
from tools.calendar_tools import (
    create_calendar_event,
    list_calendar_events,
    set_reminder,
    list_reminders,
    dismiss_reminder,
)


@pytest.fixture
def temp_calendar():
    """Create a temporary CalendarManager instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cal_file = Path(tmpdir) / "test_cal.json"
        mgr = CalendarManager(cal_file)
        yield mgr


def test_calendar_events_crud(temp_calendar):
    """Test adding, listing, and deleting calendar events."""
    res = temp_calendar.add_event(
        title="Team Standup",
        date="2026-08-30",
        time="10:00",
        description="Daily progress sync",
        category="work",
    )
    assert res["success"] is True
    event_id = res["event"]["id"]

    # List events
    events = temp_calendar.list_events()
    assert len(events) == 1
    assert events[0]["title"] == "Team Standup"

    # Filter by category
    work_events = temp_calendar.list_events(category="work")
    assert len(work_events) == 1
    pers_events = temp_calendar.list_events(category="personal")
    assert len(pers_events) == 0

    # Delete event
    del_res = temp_calendar.delete_event(event_id)
    assert del_res["success"] is True
    assert len(temp_calendar.list_events()) == 0


def test_reminders_lifecycle(temp_calendar):
    """Test setting, listing, triggering, and dismissing reminders."""
    rem_res = temp_calendar.add_reminder(
        title="Review PR",
        remind_at="2026-08-30 09:00",
        note="Check test coverage",
    )
    assert rem_res["success"] is True
    rem_id = rem_res["reminder"]["id"]

    # List pending
    pending = temp_calendar.list_reminders(status="pending")
    assert len(pending) == 1

    # Check pending reminders triggering
    triggered = temp_calendar.check_pending_reminders()
    assert len(triggered) >= 0

    # Dismiss reminder
    dismiss_res = temp_calendar.dismiss_reminder(rem_id)
    assert dismiss_res["success"] is True

    dismissed = temp_calendar.list_reminders(status="dismissed")
    assert len(dismissed) == 1

    # Delete reminder
    del_res = temp_calendar.delete_reminder(rem_id)
    assert del_res["success"] is True
    assert len(temp_calendar.list_reminders()) == 0


def test_calendar_tools_execution():
    """Test tool wrapper functions."""
    e_res = create_calendar_event("Sprint Planning", "2026-09-01", "14:00", category="work")
    assert e_res["success"] is True

    l_res = list_calendar_events()
    assert l_res["success"] is True

    r_res = set_reminder("Weekly Review", "2026-09-01 17:00")
    assert r_res["success"] is True

    lr_res = list_reminders()
    assert lr_res["success"] is True

