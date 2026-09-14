"""Persistent memory manager for Jarvis."""

import json
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


DEFAULT_CATEGORIES = [
    "user_preferences",
    "projects",
    "goals",
    "important_facts",
]


class MemoryManager:
    """Manages reading, updating, searching, and persisting memory in JSON format."""

    def __init__(self, file_path: Optional[Union[str, Path]] = None):
        if file_path is None:
            # Default to memory/memory.json relative to repository root
            base_dir = Path(__file__).resolve().parent
            self.file_path = base_dir / "memory.json"
        else:
            self.file_path = Path(file_path)

        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensure that the memory directory and file exist with standard structure."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists() or self.file_path.stat().st_size == 0:
            initial_data = {category: [] for category in DEFAULT_CATEGORIES}
            initial_data["tasks"] = []
            self._save_raw(initial_data)

    def load(self) -> Dict[str, List[Any]]:
        """Load and return memories from the JSON file."""
        self._ensure_file_exists()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
        except (json.JSONDecodeError, OSError):
            data = {}

        # Ensure default categories exist
        for cat in DEFAULT_CATEGORIES:
            if cat not in data or not isinstance(data[cat], list):
                data[cat] = []
        if "tasks" not in data or not isinstance(data["tasks"], list):
            data["tasks"] = []

        return data

    def _save_raw(self, data: Dict[str, List[Any]]) -> None:
        """Atomically write data to the memory file."""
        dir_name = self.file_path.parent
        dir_name.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            "w", dir=dir_name, delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(data, tmp, indent=4, ensure_ascii=False)
            tmp.flush()
            temp_name = tmp.name

        os.replace(temp_name, self.file_path)

    def remember(self, category: str, item: str) -> Dict[str, Any]:
        """Store a new piece of information under the specified category."""
        category = category.strip().lower().replace(" ", "_")
        item = item.strip()

        if not item:
            return {"success": False, "error": "Item content cannot be empty."}

        data = self.load()
        if category not in data:
            data[category] = []

        if item in data[category]:
            return {
                "success": True,
                "message": f"Memory already exists in category '{category}'.",
                "category": category,
                "item": item,
            }

        data[category].append(item)
        self._save_raw(data)

        return {
            "success": True,
            "message": f"Successfully stored memory in category '{category}'.",
            "category": category,
            "item": item,
        }

    def recall(
        self, category: Optional[str] = None, query: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve memories, optionally filtered by category and search keyword."""
        data = self.load()
        results: Dict[str, List[str]] = {}

        if category:
            category_key = category.strip().lower().replace(" ", "_")
            categories_to_check = [category_key] if category_key in data else []
        else:
            categories_to_check = list(data.keys())

        query_str = query.lower().strip() if query else None

        for cat in categories_to_check:
            items = data.get(cat, [])
            if not isinstance(items, list):
                continue

            if query_str:
                matched = [
                    str(it) for it in items if query_str in str(it).lower()
                ]
            else:
                matched = [str(it) for it in items]

            if matched:
                results[cat] = matched

        return {
            "success": True,
            "count": sum(len(items) for items in results.values()),
            "memories": results,
        }

    def forget(
        self, category: str, item_or_index: Union[str, int]
    ) -> Dict[str, Any]:
        """Remove a memory item by index (1-based or 0-based) or by exact/substring match."""
        category = category.strip().lower().replace(" ", "_")
        data = self.load()

        if category not in data or not data[category]:
            return {
                "success": False,
                "error": f"No memories found in category '{category}'.",
            }

        target_items = data[category]
        removed_item = None

        # Check if item_or_index is integer or string representing integer
        try:
            idx = int(item_or_index)
            # Try 1-based index first if idx > 0, otherwise 0-based
            if 1 <= idx <= len(target_items):
                removed_item = target_items.pop(idx - 1)
            elif 0 <= idx < len(target_items):
                removed_item = target_items.pop(idx)
        except (ValueError, TypeError):
            pass

        if removed_item is None and isinstance(item_or_index, str):
            match_str = item_or_index.strip().lower()
            for i, it in enumerate(target_items):
                if str(it).lower() == match_str:
                    removed_item = target_items.pop(i)
                    break
            # If not exact match, check substring
            if removed_item is None:
                for i, it in enumerate(target_items):
                    if match_str in str(it).lower():
                        removed_item = target_items.pop(i)
                        break

        if removed_item is not None:
            self._save_raw(data)
            return {
                "success": True,
                "message": f"Removed memory from '{category}': {removed_item}",
                "removed": removed_item,
            }

        return {
            "success": False,
            "error": f"Could not find matching memory '{item_or_index}' in category '{category}'.",
        }

    def add_task(self, title: str, description: str = "") -> Dict[str, Any]:
        """Create a new pending task and persist it in the JSON store."""
        task_title = (title or "").strip()
        if not task_title:
            return {"success": False, "error": "Task title cannot be empty."}

        data = self.load()
        task = {
            "id": uuid.uuid4().hex[:12],
            "title": task_title,
            "description": description.strip(),
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "completed_at": None,
        }
        data.setdefault("tasks", []).append(task)
        self._save_raw(data)
        return {"success": True, "message": "Task created successfully.", "task": task}

    def list_tasks(self, status: Optional[str] = None) -> Dict[str, Any]:
        """Return all tasks, optionally filtered by status."""
        data = self.load()
        tasks = data.get("tasks", [])
        if status:
            tasks = [task for task in tasks if task.get("status") == status.lower()]
        return {"success": True, "count": len(tasks), "tasks": tasks}

    def complete_task(self, task_id: str) -> Dict[str, Any]:
        """Mark a task as complete by its ID."""
        data = self.load()
        tasks = data.get("tasks", [])
        for task in tasks:
            if task.get("id") == task_id:
                task["status"] = "completed"
                task["completed_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
                self._save_raw(data)
                return {"success": True, "message": "Task marked as completed.", "task": task}
        return {"success": False, "error": f"No task found with id '{task_id}'."}

    def daily_agenda(self, day: Optional[str] = None, calendar_manager: Optional[Any] = None) -> Dict[str, Any]:
        """Build a summary for the day from tasks, events, and due reminders."""
        target_day = day or datetime.utcnow().strftime("%Y-%m-%d")
        data = self.load()
        tasks = data.get("tasks", [])
        matching_tasks = [
            task for task in tasks if task.get("status") != "completed"
        ]

        summary_parts = [f"Agenda for {target_day}:"]
        if matching_tasks:
            summary_parts.append("Tasks:")
            for task in matching_tasks:
                summary_parts.append(f"- {task.get('title')} [{task.get('status', 'pending')}]")
        else:
            summary_parts.append("Tasks: none")

        cal_data = {"events": [], "reminders": []}
        if calendar_manager is None:
            try:
                from memory.calendar_manager import CalendarManager
                calendar_manager = CalendarManager()
            except ImportError:
                calendar_manager = None

        if calendar_manager is not None:
            cal_data = calendar_manager.load()

        events = cal_data.get("events", [])
        day_events = [
            event for event in events if str(event.get("date", "")) == target_day
        ]
        if day_events:
            summary_parts.append("Events:")
            for event in day_events:
                when = f"{event.get('date')} {event.get('time', '09:00')}".strip()
                summary_parts.append(f"- {event.get('title')} ({when})")
        else:
            summary_parts.append("Events: none")

        reminders = cal_data.get("reminders", [])
        pending_reminders = [
            reminder for reminder in reminders
            if reminder.get("status") in (None, "pending")
            and str(reminder.get("remind_at", "")).startswith(target_day)
        ]
        if pending_reminders:
            summary_parts.append("Reminders:")
            for reminder in pending_reminders:
                summary_parts.append(f"- {reminder.get('title')} ({reminder.get('remind_at')})")
        else:
            summary_parts.append("Reminders: none")

        summary = "\n".join(summary_parts)
        return {
            "success": True,
            "day": target_day,
            "summary": summary,
            "task_count": len(matching_tasks),
            "event_count": len(day_events),
            "reminder_count": len(pending_reminders),
        }

    def get_summary(self) -> str:
        """Return a formatted string of non-empty memories for system prompt injection."""
        data = self.load()
        lines = []
        for cat, items in data.items():
            if cat == "tasks":
                continue
            if items:
                formatted_cat = cat.replace("_", " ").title()
                lines.append(f"### {formatted_cat}")
                for idx, item in enumerate(items, 1):
                    lines.append(f"- {item}")
        tasks = data.get("tasks", [])
        if tasks:
            lines.append("### Tasks")
            for task in tasks:
                status = task.get("status", "pending")
                lines.append(f"- [{status}] {task.get('title')}" )
        return "\n".join(lines) if lines else "No active long-term memories."

