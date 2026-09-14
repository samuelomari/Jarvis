"""Autonomous Task Scheduler for Jarvis - cron/interval scheduling and background dispatch."""

import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SCHEDULED_TASKS_FILE = DATA_DIR / "scheduled_tasks.json"


class TaskScheduler:
    """Manages scheduled background missions and autonomous task execution."""

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or SCHEDULED_TASKS_FILE
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensure tasks file exists."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists() or self.file_path.stat().st_size == 0:
            self._save_raw([])

    def _load_raw(self) -> List[Dict[str, Any]]:
        """Load scheduled tasks from file."""
        self._ensure_file_exists()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_raw(self, tasks: List[Dict[str, Any]]) -> None:
        """Atomically persist scheduled tasks."""
        dir_name = self.file_path.parent
        dir_name.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tmp:
            json.dump(tasks, tmp, indent=2, ensure_ascii=False)
            tmp.flush()
            tmp_name = tmp.name
        os.replace(tmp_name, self.file_path)

    def _calculate_initial_next_run(
        self, schedule_type: str, interval_minutes: int, run_at: Optional[str]
    ) -> str:
        """Determine next run timestamp."""
        now = datetime.now()
        if schedule_type == "interval":
            minutes = max(1, interval_minutes)
            return (now + timedelta(minutes=minutes)).isoformat()
        elif schedule_type == "daily" and run_at:
            try:
                # Expecting HH:MM
                target_hour, target_min = map(int, run_at.split(":"))
                target_time = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
                if target_time <= now:
                    target_time += timedelta(days=1)
                return target_time.isoformat()
            except Exception:
                return (now + timedelta(hours=24)).isoformat()
        elif schedule_type == "once" and run_at:
            try:
                # Expecting YYYY-MM-DD HH:MM
                dt = datetime.fromisoformat(run_at.replace(" ", "T"))
                return dt.isoformat()
            except Exception:
                return (now + timedelta(minutes=5)).isoformat()
        else:
            return (now + timedelta(minutes=30)).isoformat()

    def add_task(
        self,
        name: str,
        goal: str,
        schedule_type: str = "interval",
        interval_minutes: int = 60,
        run_at: Optional[str] = None,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        """Add a new scheduled autonomous task."""
        clean_name = name.strip() or "Unnamed Mission"
        clean_goal = goal.strip()
        if not clean_goal:
            return {"success": False, "error": "Goal cannot be empty."}

        task_id = f"job_{uuid.uuid4().hex[:8]}"
        next_run = self._calculate_initial_next_run(schedule_type, interval_minutes, run_at)

        task = {
            "id": task_id,
            "name": clean_name,
            "goal": clean_goal,
            "schedule_type": schedule_type,
            "interval_minutes": interval_minutes,
            "run_at": run_at,
            "enabled": enabled,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "next_run": next_run,
            "run_count": 0,
        }

        tasks = self._load_raw()
        tasks.append(task)
        self._save_raw(tasks)

        return {
            "success": True,
            "message": f"Scheduled task '{clean_name}' created.",
            "task": task,
        }

    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all scheduled tasks."""
        tasks = self._load_raw()
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        return tasks

    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel/delete a scheduled task."""
        tasks = self._load_raw()
        found = False
        remaining = []
        for t in tasks:
            if t.get("id") == task_id:
                found = True
            else:
                remaining.append(t)

        if found:
            self._save_raw(remaining)
            return {"success": True, "message": f"Task '{task_id}' removed."}
        return {"success": False, "error": f"Task '{task_id}' not found."}

    def check_and_run_due_tasks(self) -> List[Dict[str, Any]]:
        """Check all tasks, execute any that are due, and schedule their next run."""
        tasks = self._load_raw()
        now = datetime.now()
        executed_results = []
        updated = False

        from autonomous.engine import get_mission_runner
        runner = get_mission_runner()

        for task in tasks:
            if not task.get("enabled", True) or task.get("status") != "active":
                continue

            next_run_str = task.get("next_run")
            if not next_run_str:
                continue

            try:
                next_run_dt = datetime.fromisoformat(next_run_str)
            except Exception:
                continue

            if now >= next_run_dt:
                # Run mission
                updated = True
                task_name = task.get("name", "Autonomous Task")
                task_goal = task.get("goal", "")

                try:
                    result = runner.run_mission(goal=task_goal, notify_on_complete=True)
                    task["run_count"] = task.get("run_count", 0) + 1
                    task["last_run"] = now.isoformat()
                    task["last_result"] = "success"

                    executed_results.append({
                        "task_id": task.get("id"),
                        "name": task_name,
                        "result": result,
                    })
                except Exception as exc:
                    task["last_run"] = now.isoformat()
                    task["last_result"] = f"error: {str(exc)}"

                # Calculate next run
                stype = task.get("schedule_type", "interval")
                if stype == "once":
                    task["status"] = "completed"
                    task["enabled"] = False
                elif stype == "interval":
                    mins = max(1, task.get("interval_minutes", 60))
                    task["next_run"] = (now + timedelta(minutes=mins)).isoformat()
                elif stype == "daily":
                    run_at = task.get("run_at", "09:00")
                    try:
                        h, m = map(int, run_at.split(":"))
                        nxt = now.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(days=1)
                        task["next_run"] = nxt.isoformat()
                    except Exception:
                        task["next_run"] = (now + timedelta(days=1)).isoformat()

        if updated:
            self._save_raw(tasks)

        return executed_results


# Global singleton
_scheduler = TaskScheduler()


def get_scheduler() -> TaskScheduler:
    """Return global TaskScheduler instance."""
    return _scheduler
