"""Calendar and reminders manager for Jarvis."""

import json
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class CalendarManager:
    """Manages events, reminders, and scheduling with persistent JSON storage."""

    def __init__(self, file_path: Optional[Union[str, Path]] = None):
        if file_path is None:
            self.file_path = DATA_DIR / "calendar.json"
        else:
            self.file_path = Path(file_path)

        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensure calendar file and directory exist."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists() or self.file_path.stat().st_size == 0:
            initial = {
                "events": [],
                "reminders": [],
            }
            self._save_raw(initial)

    def load(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load events and reminders from JSON file."""
        self._ensure_file_exists()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
        except (json.JSONDecodeError, OSError):
            data = {}

        if "events" not in data or not isinstance(data["events"], list):
            data["events"] = []
        if "reminders" not in data or not isinstance(data["reminders"], list):
            data["reminders"] = []

        return data

    def _save_raw(self, data: Dict[str, List[Dict[str, Any]]]) -> None:
        """Atomically persist calendar data."""
        dir_name = self.file_path.parent
        dir_name.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tmp:
            json.dump(data, tmp, indent=4, ensure_ascii=False)
            tmp.flush()
            temp_name = tmp.name

        os.replace(temp_name, self.file_path)

    # --- Events ---

    def add_event(
        self,
        title: str,
        date: str,
        time: str = "09:00",
        description: str = "",
        category: str = "general",
    ) -> Dict[str, Any]:
        """Add a calendar event."""
        data = self.load()
        event_id = f"evt_{uuid.uuid4().hex[:8]}"

        event = {
            "id": event_id,
            "title": title.strip(),
            "date": date.strip(),
            "time": time.strip(),
            "description": description.strip(),
            "category": category.strip().lower(),
            "created_at": datetime.now().isoformat(),
        }

        data["events"].append(event)
        # Sort events by date and time
        data["events"].sort(key=lambda x: (x.get("date", ""), x.get("time", "")))
        self._save_raw(data)

        return {"success": True, "message": f"Event '{title}' scheduled for {date} at {time}.", "event": event}

    def list_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List calendar events with optional filtering."""
        data = self.load()
        events = data.get("events", [])

        filtered = []
        for e in events:
            if category and e.get("category") != category.lower():
                continue
            if start_date and e.get("date", "") < start_date:
                continue
            if end_date and e.get("date", "") > end_date:
                continue
            filtered.append(e)

        return filtered

    def delete_event(self, event_id: str) -> Dict[str, Any]:
        """Delete an event by ID or title match."""
        data = self.load()
        events = data.get("events", [])
        original_count = len(events)

        events = [e for e in events if e.get("id") != event_id and e.get("title", "").lower() != event_id.lower()]
        if len(events) < original_count:
            data["events"] = events
            self._save_raw(data)
            return {"success": True, "message": f"Deleted event '{event_id}'."}

        return {"success": False, "error": f"Event '{event_id}' not found."}

    # --- Reminders ---

    def add_reminder(
        self,
        title: str,
        remind_at: str,
        note: str = "",
    ) -> Dict[str, Any]:
        """Add a timed reminder."""
        data = self.load()
        rem_id = f"rem_{uuid.uuid4().hex[:8]}"

        reminder = {
            "id": rem_id,
            "title": title.strip(),
            "remind_at": remind_at.strip(),
            "note": note.strip(),
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }

        data["reminders"].append(reminder)
        data["reminders"].sort(key=lambda x: x.get("remind_at", ""))
        self._save_raw(data)

        return {"success": True, "message": f"Reminder set for '{title}' at {remind_at}.", "reminder": reminder}

    def list_reminders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List reminders, optionally filtered by status ('pending', 'triggered', 'dismissed')."""
        data = self.load()
        reminders = data.get("reminders", [])

        if status:
            return [r for r in reminders if r.get("status") == status]
        return reminders

    def dismiss_reminder(self, reminder_id: str) -> Dict[str, Any]:
        """Mark a reminder as dismissed."""
        data = self.load()
        reminders = data.get("reminders", [])

        found = False
        for r in reminders:
            if r.get("id") == reminder_id or r.get("title", "").lower() == reminder_id.lower():
                r["status"] = "dismissed"
                r["dismissed_at"] = datetime.now().isoformat()
                found = True
                break

        if found:
            self._save_raw(data)
            return {"success": True, "message": f"Reminder '{reminder_id}' marked as dismissed."}

        return {"success": False, "error": f"Reminder '{reminder_id}' not found."}

    def delete_reminder(self, reminder_id: str) -> Dict[str, Any]:
        """Delete a reminder permanently."""
        data = self.load()
        reminders = data.get("reminders", [])
        original_count = len(reminders)

        reminders = [r for r in reminders if r.get("id") != reminder_id and r.get("title", "").lower() != reminder_id.lower()]
        if len(reminders) < original_count:
            data["reminders"] = reminders
            self._save_raw(data)
            return {"success": True, "message": f"Reminder '{reminder_id}' deleted."}

        return {"success": False, "error": f"Reminder '{reminder_id}' not found."}

    def check_pending_reminders(self) -> List[Dict[str, Any]]:
        """Check for due reminders and update their status to 'triggered'."""
        data = self.load()
        reminders = data.get("reminders", [])
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        now_iso = datetime.now().isoformat()

        triggered = []
        updated = False

        for r in reminders:
            if r.get("status") == "pending":
                target_time = r.get("remind_at", "")
                if target_time <= now_str or target_time <= now_iso:
                    r["status"] = "triggered"
                    r["triggered_at"] = now_iso
                    triggered.append(r)
                    updated = True

        if updated:
            self._save_raw(data)

        return triggered

