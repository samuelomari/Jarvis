"""Unit tests for Jarvis NotificationManager and notification tools."""

import tempfile
from pathlib import Path
import pytest
from notifications.manager import NotificationManager
from tools.notification_tools import notify_user, list_user_notifications


@pytest.fixture
def temp_notifications():
    """Create a temporary NotificationManager instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        notif_file = Path(tmpdir) / "test_notifications.json"
        mgr = NotificationManager(notif_file)
        yield mgr


def test_notification_dispatch_and_storage(temp_notifications):
    """Test creating and retrieving notifications."""
    res = temp_notifications.notify(
        title="Build Success",
        message="All unit tests passed successfully.",
        level="success",
        source="ci_pipeline",
        desktop_alert=False,
    )
    assert res["success"] is True
    notif = res["notification"]
    assert notif["title"] == "Build Success"
    assert notif["read"] is False

    # List notifications
    items = temp_notifications.list_notifications()
    assert len(items) == 1
    assert items[0]["title"] == "Build Success"

    # Mark as read
    assert temp_notifications.get_unread_count() == 1
    temp_notifications.mark_as_read(notif["id"])
    assert temp_notifications.get_unread_count() == 0

    # Filter unread
    unread = temp_notifications.list_notifications(unread_only=True)
    assert len(unread) == 0


def test_notification_clear(temp_notifications):
    """Test clearing all notifications."""
    temp_notifications.notify("Alert 1", "Message 1", desktop_alert=False)
    temp_notifications.notify("Alert 2", "Message 2", desktop_alert=False)
    assert len(temp_notifications.list_notifications()) == 2

    temp_notifications.clear_notifications()
    assert len(temp_notifications.list_notifications()) == 0


def test_notification_tools_execution():
    """Test tool wrapper functions."""
    res = notify_user("System Check", "Tool test alert", level="info", desktop_alert=False)
    assert res["success"] is True

    list_res = list_user_notifications(limit=5)
    assert list_res["success"] is True
    assert list_res["count"] > 0
