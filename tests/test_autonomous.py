"""Unit tests for Jarvis Autonomous Engine, TaskScheduler, and autonomous tools."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import pytest
from autonomous.engine import AutonomousMissionRunner
from autonomous.scheduler import TaskScheduler
from tools.autonomous_tools import (
    schedule_autonomous_task,
    list_scheduled_tasks,
    cancel_scheduled_task,
    run_autonomous_mission,
)


@pytest.fixture
def temp_scheduler():
    """Create a temporary TaskScheduler instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sched_file = Path(tmpdir) / "test_tasks.json"
        sched = TaskScheduler(sched_file)
        yield sched


def test_scheduler_task_lifecycle(temp_scheduler):
    """Test adding, listing, and canceling scheduled tasks."""
    res = temp_scheduler.add_task(
        name="Daily Git Backup",
        goal="Commit working directory changes and push to remote",
        schedule_type="interval",
        interval_minutes=120,
    )
    assert res["success"] is True
    task = res["task"]
    assert task["name"] == "Daily Git Backup"
    task_id = task["id"]

    # List tasks
    all_tasks = temp_scheduler.list_tasks()
    assert len(all_tasks) == 1
    assert all_tasks[0]["id"] == task_id

    # Cancel task
    cancel_res = temp_scheduler.cancel_task(task_id)
    assert cancel_res["success"] is True
    assert len(temp_scheduler.list_tasks()) == 0


def test_scheduler_due_task_execution(temp_scheduler, monkeypatch):
    """Test executing tasks that are due."""
    # Add task with next_run in the past
    past_time = (datetime.now() - timedelta(minutes=5)).isoformat()
    res = temp_scheduler.add_task(
        name="Security Audit",
        goal="Audit dependencies and check permissions",
        schedule_type="interval",
        interval_minutes=60,
    )
    task_id = res["task"]["id"]

    # Force next_run to past
    raw_tasks = temp_scheduler._load_raw()
    raw_tasks[0]["next_run"] = past_time
    temp_scheduler._save_raw(raw_tasks)

    executed = temp_scheduler.check_and_run_due_tasks()
    assert len(executed) == 1
    assert executed[0]["task_id"] == task_id

    # Verify task updated
    updated_tasks = temp_scheduler.list_tasks()
    assert updated_tasks[0]["run_count"] == 1
    assert updated_tasks[0]["last_run"] is not None


def test_autonomous_mission_runner():
    """Test autonomous mission execution loop."""
    runner = AutonomousMissionRunner()
    res = runner.run_mission("Analyze repository health and check LOC", max_steps=3, notify_on_complete=False)
    assert res["success"] is True
    assert len(res["steps"]) >= 3
    assert "Autonomous Mission Completed" in res["summary"]


def test_autonomous_tools_execution():
    """Test tool wrappers for autonomous management."""
    s_res = schedule_autonomous_task(
        name="Tool Test Mission",
        goal="Inspect pending reminders",
        schedule_type="interval",
        interval_minutes=30,
    )
    assert s_res["success"] is True
    task_id = s_res["task"]["id"]

    l_res = list_scheduled_tasks()
    assert l_res["success"] is True
    assert any(t["id"] == task_id for t in l_res["tasks"])

    c_res = cancel_scheduled_task(task_id)
    assert c_res["success"] is True
