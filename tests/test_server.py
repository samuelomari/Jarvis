"""Unit tests for Jarvis FastAPI backend server."""

import pytest
from fastapi.testclient import TestClient
from server import app


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


def test_health_check(client):
    """Test /api/health endpoint."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert "version" in data


def test_dashboard_html_serve(client):
    """Test root dashboard serves HTML."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "JARVIS" in resp.text
    assert "Neural Interface" in resp.text or "hud-header" in resp.text


def test_memory_endpoints(client):
    """Test memory REST endpoints."""
    # Add memory
    add_resp = client.post(
        "/api/memory",
        json={"category": "test_cat", "content": "Server API memory test"},
    )
    assert add_resp.status_code == 200
    assert add_resp.json()["success"] is True

    # Get memory
    get_resp = client.get("/api/memory")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert "test_cat" in data["data"]

    # Delete memory
    del_resp = client.request(
        "DELETE",
        "/api/memory",
        json={"category": "test_cat", "item_or_index": "Server API memory test"},
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True


def test_calendar_and_reminders_endpoints(client):
    """Test calendar and reminder API endpoints."""
    # Add event
    ev_resp = client.post(
        "/api/calendar/events",
        json={
            "title": "API Test Event",
            "date": "2026-09-01",
            "time": "11:00",
            "category": "work",
        },
    )
    assert ev_resp.status_code == 200
    ev_data = ev_resp.json()
    assert ev_data["success"] is True
    event_id = ev_data["event"]["id"]

    # Get events
    list_ev = client.get("/api/calendar/events")
    assert list_ev.status_code == 200
    assert any(e["id"] == event_id for e in list_ev.json()["events"])

    # Delete event
    del_ev = client.delete(f"/api/calendar/events/{event_id}")
    assert del_ev.status_code == 200

    # Add reminder
    rem_resp = client.post(
        "/api/calendar/reminders",
        json={
            "title": "API Reminder Test",
            "remind_at": "2026-09-01 12:00",
            "note": "Testing",
        },
    )
    assert rem_resp.status_code == 200
    rem_id = rem_resp.json()["reminder"]["id"]

    # Dismiss reminder
    dismiss_resp = client.post(f"/api/calendar/reminders/{rem_id}/dismiss")
    assert dismiss_resp.status_code == 200

    # Delete reminder
    del_rem = client.delete(f"/api/calendar/reminders/{rem_id}")
    assert del_rem.status_code == 200


def test_project_stats_and_tree_endpoints(client):
    """Test project stats and directory tree endpoints."""
    stats_resp = client.get("/api/project/stats")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["success"] is True

    tree_resp = client.get("/api/project/tree")
    assert tree_resp.status_code == 200
    assert tree_resp.json()["success"] is True


def test_system_stats_and_tools_endpoints(client):
    """Test system telemetry and tool list endpoints."""
    sys_resp = client.get("/api/system/stats")
    assert sys_resp.status_code == 200
    assert sys_resp.json()["success"] is True
    assert "cpu_percent" in sys_resp.json()

    tools_resp = client.get("/api/tools")
    assert tools_resp.status_code == 200
    assert tools_resp.json()["count"] >= 10


def test_file_operations_endpoints(client):
    """Test REST endpoints for writing, editing, and deleting files."""
    test_path = "data/test_server_file.txt"

    # Write file
    w_resp = client.post(
        "/api/project/write",
        json={"path": test_path, "content": "Initial Line\nSecond Line\n", "overwrite": True},
    )
    assert w_resp.status_code == 200
    assert w_resp.json()["success"] is True

    # Read file
    r_resp = client.post("/api/project/read", json={"path": test_path})
    assert r_resp.status_code == 200
    assert "Initial Line" in r_resp.json()["content"]

    # Edit file
    e_resp = client.post(
        "/api/project/edit",
        json={
            "path": test_path,
            "target_content": "Second Line",
            "replacement_content": "Modified Second Line",
        },
    )
    assert e_resp.status_code == 200
    assert e_resp.json()["success"] is True

    # Delete file
    d_resp = client.request("DELETE", "/api/project/delete", json={"path": test_path})
    assert d_resp.status_code == 200
    assert d_resp.json()["success"] is True


def test_agents_endpoints(client):
    """Test AI Subagents REST endpoints."""
    # List agents
    list_resp = client.get("/api/agents")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["success"] is True
    assert len(data["agents"]) >= 4

    # Delegate task
    del_resp = client.post(
        "/api/agents/delegate",
        json={"agent_name": "coder", "task": "Review API endpoints"},
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Multi-agent workflow
    flow_resp = client.post(
        "/api/agents/workflow",
        json={"goal": "Verify database schema migration"},
    )
    assert flow_resp.status_code == 200
    assert flow_resp.json()["success"] is True


def test_autonomous_and_notifications_endpoints(client):
    """Test autonomous tasks and notifications REST endpoints."""
    # Create notification
    n_resp = client.post(
        "/api/notifications",
        json={
            "title": "Server Test Notification",
            "message": "Testing notification endpoint",
            "level": "info",
            "desktop_alert": False,
        },
    )
    assert n_resp.status_code == 200
    assert n_resp.json()["success"] is True

    # Get notifications
    get_n = client.get("/api/notifications")
    assert get_n.status_code == 200
    assert get_n.json()["success"] is True
    assert len(get_n.json()["notifications"]) > 0

    # Mark all read
    read_all = client.post("/api/notifications/read-all")
    assert read_all.status_code == 200
    assert read_all.json()["success"] is True

    # Create autonomous task
    task_resp = client.post(
        "/api/autonomous/tasks",
        json={
            "name": "API Scheduled Mission",
            "goal": "Check system metrics every hour",
            "schedule_type": "interval",
            "interval_minutes": 60,
        },
    )
    assert task_resp.status_code == 200
    assert task_resp.json()["success"] is True
    task_id = task_resp.json()["task"]["id"]

    # List tasks
    list_tasks = client.get("/api/autonomous/tasks")
    assert list_tasks.status_code == 200
    assert any(t["id"] == task_id for t in list_tasks.json()["tasks"])

    # Run autonomous now
    run_now = client.post(
        "/api/autonomous/run",
        json={"goal": "Run brief diagnostic check", "max_steps": 2},
    )
    assert run_now.status_code == 200
    assert run_now.json()["success"] is True

    # Cancel task
    del_task = client.delete(f"/api/autonomous/tasks/{task_id}")
    assert del_task.status_code == 200
    assert del_task.json()["success"] is True


