"""Calendar and reminder agent tools for Jarvis."""

from typing import Any, Dict, List, Optional
from memory.calendar_manager import CalendarManager
from tools.registry import register_tool

_calendar_manager = CalendarManager()


def get_calendar_manager() -> CalendarManager:
    """Get the global CalendarManager instance."""
    return _calendar_manager


@register_tool({
    "name": "create_calendar_event",
    "description": "Schedule a new event or meeting on the user's calendar.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title or summary of the event.",
            },
            "date": {
                "type": "string",
                "description": "Date of the event in YYYY-MM-DD format (e.g. 2026-08-30).",
            },
            "time": {
                "type": "string",
                "description": "Time of the event in HH:MM format (e.g. 14:30). Defaults to 09:00.",
            },
            "description": {
                "type": "string",
                "description": "Optional notes or details about the event.",
            },
            "category": {
                "type": "string",
                "description": "Category for the event (e.g. 'work', 'personal', 'meeting', 'learning').",
            },
        },
        "required": ["title", "date"],
    },
})
def create_calendar_event(
    title: str,
    date: str,
    time: str = "09:00",
    description: str = "",
    category: str = "general",
) -> Dict[str, Any]:
    """Create a calendar event."""
    return _calendar_manager.add_event(
        title=title,
        date=date,
        time=time,
        description=description,
        category=category,
    )


@register_tool({
    "name": "list_calendar_events",
    "description": "List scheduled calendar events within an optional date range or category.",
    "input_schema": {
        "type": "object",
        "properties": {
            "start_date": {
                "type": "string",
                "description": "Optional start date filter in YYYY-MM-DD format.",
            },
            "end_date": {
                "type": "string",
                "description": "Optional end date filter in YYYY-MM-DD format.",
            },
            "category": {
                "type": "string",
                "description": "Optional category filter.",
            },
        },
        "required": [],
    },
})
def list_calendar_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """List calendar events."""
    events = _calendar_manager.list_events(start_date=start_date, end_date=end_date, category=category)
    return {
        "success": True,
        "count": len(events),
        "events": events,
    }


@register_tool({
    "name": "set_reminder",
    "description": "Create a timed reminder or alert for a task or deadline.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Summary of the reminder.",
            },
            "remind_at": {
                "type": "string",
                "description": "Target date and time (e.g. '2026-08-30 18:00' or '2026-08-30T18:00:00').",
            },
            "note": {
                "type": "string",
                "description": "Optional additional context or instructions.",
            },
        },
        "required": ["title", "remind_at"],
    },
})
def set_reminder(title: str, remind_at: str, note: str = "") -> Dict[str, Any]:
    """Set a new reminder."""
    return _calendar_manager.add_reminder(title=title, remind_at=remind_at, note=note)


@register_tool({
    "name": "list_reminders",
    "description": "Retrieve reminders filtered by status ('pending', 'triggered', 'dismissed').",
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Optional status filter ('pending', 'triggered', 'dismissed'). Defaults to 'pending'.",
            },
        },
        "required": [],
    },
})
def list_reminders(status: Optional[str] = "pending") -> Dict[str, Any]:
    """List reminders."""
    reminders = _calendar_manager.list_reminders(status=status)
    return {
        "success": True,
        "count": len(reminders),
        "reminders": reminders,
    }


@register_tool({
    "name": "dismiss_reminder",
    "description": "Mark an active or triggered reminder as acknowledged/dismissed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reminder_id": {
                "type": "string",
                "description": "The ID or title of the reminder to dismiss.",
            },
        },
        "required": ["reminder_id"],
    },
})
def dismiss_reminder(reminder_id: str) -> Dict[str, Any]:
    """Dismiss a reminder."""
    return _calendar_manager.dismiss_reminder(reminder_id=reminder_id)

