"""Tools for notifying the user via desktop alerts and checking notifications."""

from typing import Any, Dict, List, Optional
from tools.registry import register_tool


def _get_mgr():
    from notifications.manager import get_notification_manager
    return get_notification_manager()


@register_tool({
    "name": "notify_user",
    "description": "Send a notification to the user with a title, message, level (info, success, warning, error, alert), and optional desktop alert popup.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Short heading or title for the notification.",
            },
            "message": {
                "type": "string",
                "description": "Details of what has been accomplished or requires attention.",
            },
            "level": {
                "type": "string",
                "description": "Severity/category: 'info', 'success', 'warning', 'error', or 'alert'. Defaults to 'info'.",
            },
            "desktop_alert": {
                "type": "boolean",
                "description": "Whether to trigger an OS desktop notification popup (default: true).",
            },
        },
        "required": ["title", "message"],
    },
})
def notify_user(
    title: str,
    message: str,
    level: str = "info",
    desktop_alert: bool = True,
) -> Dict[str, Any]:
    """Send notification to the user."""
    mgr = _get_mgr()
    return mgr.notify(
        title=title,
        message=message,
        level=level,
        source="jarvis_agent",
        desktop_alert=desktop_alert,
    )


@register_tool({
    "name": "list_user_notifications",
    "description": "List recent notifications sent to the user, with option to filter for unread alerts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "unread_only": {
                "type": "boolean",
                "description": "Whether to return only unread notifications (default: false).",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of notifications to return (default: 20).",
            },
        },
        "required": [],
    },
})
def list_user_notifications(
    unread_only: bool = False, limit: int = 20
) -> Dict[str, Any]:
    """Retrieve notifications."""
    mgr = _get_mgr()
    items = mgr.list_notifications(unread_only=unread_only, limit=limit)
    return {
        "success": True,
        "count": len(items),
        "unread_count": mgr.get_unread_count(),
        "notifications": items,
    }
