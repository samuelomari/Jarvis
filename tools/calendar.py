"""Stage 5: Calendar and reminders management."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from tools.registry import register_tool


REMINDERS_FILE = Path(__file__).parent.parent / "data" / "reminders.json"


def _load_reminders():
    """Load reminders from file."""
    REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if REMINDERS_FILE.exists():
        with open(REMINDERS_FILE, "r") as f:
            return json.load(f)
    return []


def _save_reminders(reminders):
    """Save reminders to file."""
    REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f, indent=2)


@register_tool({
    "name": "create_reminder",
    "description": "Create a reminder for a specific date and time.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Reminder title"
            },
            "date": {
                "type": "string",
                "description": "Date in format YYYY-MM-DD"
            },
            "time": {
                "type": "string",
                "description": "Time in format HH:MM (24-hour)"
            },
            "description": {
                "type": "string",
                "description": "Optional: detailed description"
            }
        },
        "required": ["title", "date", "time"],
    },
})
def create_reminder(title: str, date: str, time: str, description: str = "") -> str:
    """Create a new reminder."""
    try:
        # Validate date format
        reminder_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        
        reminders = _load_reminders()
        
        reminder = {
            "id": len(reminders) + 1,
            "title": title,
            "date": date,
            "time": time,
            "datetime": reminder_datetime.isoformat(),
            "description": description,
            "created_at": datetime.now().isoformat(),
            "completed": False
        }
        
        reminders.append(reminder)
        _save_reminders(reminders)
        
        return f"✓ Reminder created: '{title}' on {date} at {time}"
    except ValueError as e:
        return f"Invalid date/time format. Use YYYY-MM-DD and HH:MM. Error: {str(e)}"


@register_tool({
    "name": "list_reminders",
    "description": "List upcoming reminders.",
    "input_schema": {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Show reminders for next N days (default: 7)"
            },
            "completed": {
                "type": "boolean",
                "description": "Show completed reminders? (default: false)"
            }
        },
        "required": [],
    },
})
def list_reminders(days: int = 7, completed: bool = False) -> str:
    """List reminders."""
    reminders = _load_reminders()
    
    now = datetime.now()
    cutoff = now + timedelta(days=days)
    
    upcoming = []
    for r in reminders:
        if r["completed"] == completed:
            try:
                rem_time = datetime.fromisoformat(r["datetime"])
                if now <= rem_time <= cutoff:
                    upcoming.append(r)
            except:
                pass
    
    if not upcoming:
        status = "completed" if completed else "upcoming"
        return f"No {status} reminders in the next {days} days."
    
    # Sort by datetime
    upcoming.sort(key=lambda x: x["datetime"])
    
    result = f"**{'Completed' if completed else 'Upcoming'} Reminders:**\n"
    for r in upcoming:
        result += f"\n🔔 **{r['title']}**\n"
        result += f"   📅 {r['date']} at {r['time']}\n"
        if r['description']:
            result += f"   📝 {r['description']}\n"
    
    return result


@register_tool({
    "name": "complete_reminder",
    "description": "Mark a reminder as completed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reminder_id": {
                "type": "integer",
                "description": "ID of the reminder to complete"
            }
        },
        "required": ["reminder_id"],
    },
})
def complete_reminder(reminder_id: int) -> str:
    """Mark reminder as completed."""
    reminders = _load_reminders()
    
    for r in reminders:
        if r["id"] == reminder_id:
            r["completed"] = True
            _save_reminders(reminders)
            return f"✓ Reminder completed: {r['title']}"
    
    return f"Reminder with ID {reminder_id} not found."


@register_tool({
    "name": "delete_reminder",
    "description": "Delete a reminder.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reminder_id": {
                "type": "integer",
                "description": "ID of the reminder to delete"
            }
        },
        "required": ["reminder_id"],
    },
})
def delete_reminder(reminder_id: int) -> str:
    """Delete a reminder."""
    reminders = _load_reminders()
    
    for i, r in enumerate(reminders):
        if r["id"] == reminder_id:
            deleted = reminders.pop(i)
            _save_reminders(reminders)
            return f"✓ Deleted reminder: {deleted['title']}"
    
    return f"Reminder with ID {reminder_id} not found."


@register_tool({
    "name": "get_calendar_summary",
    "description": "Get a summary of your calendar (reminders) for a given period.",
    "input_schema": {
        "type": "object",
        "properties": {
            "period": {
                "type": "string",
                "description": "Period: 'today', 'week', 'month' (default: 'week')"
            }
        },
        "required": [],
    },
})
def get_calendar_summary(period: str = "week") -> str:
    """Get calendar summary."""
    reminders = _load_reminders()
    
    now = datetime.now()
    
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        label = "Today"
    elif period == "week":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        label = "This Week"
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = start + timedelta(days=32)
        end = next_month.replace(day=1)
        label = "This Month"
    else:
        return f"Unknown period: {period}. Use 'today', 'week', or 'month'."
    
    events = []
    for r in reminders:
        if not r["completed"]:
            try:
                rem_time = datetime.fromisoformat(r["datetime"])
                if start <= rem_time < end:
                    events.append(r)
            except:
                pass
    
    if not events:
        return f"No reminders for {label}."
    
    events.sort(key=lambda x: x["datetime"])
    
    result = f"**Calendar Summary - {label}:**\n"
    current_date = None
    for e in events:
        if e["date"] != current_date:
            current_date = e["date"]
            result += f"\n📅 **{current_date}**\n"
        result += f"  - {e['time']}: {e['title']}\n"
    
    return result
