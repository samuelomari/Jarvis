"""Notification Hub for Jarvis - desktop notifications, persistent JSON storage, and alert management."""

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
NOTIFICATIONS_FILE = DATA_DIR / "notifications.json"


class NotificationManager:
    """Manages system, autonomous agent, and task notifications."""

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or NOTIFICATIONS_FILE
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensure the notifications directory and file exist."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists() or self.file_path.stat().st_size == 0:
            self._save_raw([])

    def _load_raw(self) -> List[Dict[str, Any]]:
        """Load raw notifications list from disk."""
        self._ensure_file_exists()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_raw(self, items: List[Dict[str, Any]]) -> None:
        """Atomically persist notifications."""
        dir_name = self.file_path.parent
        dir_name.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tmp:
            json.dump(items, tmp, indent=2, ensure_ascii=False)
            tmp.flush()
            tmp_name = tmp.name
        os.replace(tmp_name, self.file_path)

    def _send_desktop_notification(self, title: str, message: str, level: str) -> bool:
        """Send native Linux desktop notification using notify-send."""
        notify_send_bin = shutil.which("notify-send")
        if not notify_send_bin:
            return False

        urgency_map = {
            "info": "low",
            "success": "normal",
            "warning": "normal",
            "error": "critical",
            "alert": "critical",
        }
        urgency = urgency_map.get(level.lower(), "normal")

        try:
            cmd = [
                notify_send_bin,
                "-a", "JARVIS AI",
                "-u", urgency,
                title,
                message[:300],
            ]
            subprocess.run(
                cmd,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2.0,
            )
            return True
        except Exception:
            return False

    def notify(
        self,
        title: str,
        message: str,
        level: str = "info",
        source: str = "system",
        desktop_alert: bool = True,
    ) -> Dict[str, Any]:
        """Dispatch a notification across all channels."""
        clean_title = title.strip() or "Jarvis Notification"
        clean_message = message.strip() or ""
        clean_level = level.lower().strip()
        if clean_level not in ("info", "success", "warning", "error", "alert"):
            clean_level = "info"

        notification_id = f"notif_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().isoformat()

        item = {
            "id": notification_id,
            "title": clean_title,
            "message": clean_message,
            "level": clean_level,
            "source": source,
            "timestamp": timestamp,
            "read": False,
        }

        # Persist notification
        items = self._load_raw()
        items.insert(0, item)
        # Keep maximum 200 notifications
        if len(items) > 200:
            items = items[:200]
        self._save_raw(items)

        # Trigger desktop alert
        desktop_sent = False
        if desktop_alert:
            desktop_sent = self._send_desktop_notification(clean_title, clean_message, clean_level)

        return {
            "success": True,
            "notification": item,
            "desktop_sent": desktop_sent,
        }

    def list_notifications(
        self, unread_only: bool = False, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List recent notifications."""
        items = self._load_raw()
        if unread_only:
            items = [item for item in items if not item.get("read", False)]
        return items[:limit]

    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        items = self._load_raw()
        found = False
        for item in items:
            if item.get("id") == notification_id:
                item["read"] = True
                found = True
                break
        if found:
            self._save_raw(items)
        return found

    def mark_all_as_read(self) -> int:
        """Mark all notifications as read."""
        items = self._load_raw()
        count = 0
        for item in items:
            if not item.get("read", False):
                item["read"] = True
                count += 1
        self._save_raw(items)
        return count

    def clear_notifications(self) -> bool:
        """Clear all stored notifications."""
        self._save_raw([])
        return True

    def get_unread_count(self) -> int:
        """Count unread notifications."""
        items = self._load_raw()
        return sum(1 for item in items if not item.get("read", False))


# Global singleton instance
_notification_manager = NotificationManager()


def get_notification_manager() -> NotificationManager:
    """Return the global NotificationManager singleton."""
    return _notification_manager
