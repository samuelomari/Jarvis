"""Jarvis Always-On Autonomous Daemon runner."""

import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from autonomous.scheduler import get_scheduler
from memory.calendar_manager import CalendarManager
from notifications.manager import get_notification_manager

calendar_manager = CalendarManager()
task_scheduler = get_scheduler()
notification_manager = get_notification_manager()

RUNNING = True


def handle_shutdown(signum, frame):
    """Graceful shutdown handler."""
    global RUNNING
    print("\n[DAEMON] Received shutdown signal. Terminating Jarvis Daemon...")
    RUNNING = False


def run_daemon(poll_interval: int = 5):
    """Main daemon loop checking reminders, executing due autonomous missions, and dispatching alerts."""
    print("=" * 65)
    print(" JARVIS ALWAYS-ON AUTONOMOUS DAEMON ONLINE")
    print(" Subsystems: Calendar Reminders | Autonomous Task Scheduler | Desktop Alert Hub")
    print(f" Polling cycle: every {poll_interval}s | Press Ctrl+C to terminate.")
    print("=" * 65)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Initial notification
    notification_manager.notify(
        title="Jarvis Daemon Online",
        message="Background daemon initialized. Monitoring agenda reminders and autonomous missions.",
        level="info",
        source="daemon",
        desktop_alert=True,
    )

    loop_count = 0
    while RUNNING:
        loop_count += 1
        now_str = datetime.now().strftime("%H:%M:%S")

        # 1. Check reminders
        try:
            triggered = calendar_manager.check_pending_reminders()
            for r in triggered:
                title = r.get("title", "Scheduled Reminder")
                note = r.get("note", "")
                print(f"[{now_str}] [ALERT] REMINDER TRIGGERED: {title} (Note: {note or 'None'})")
                notification_manager.notify(
                    title=f"Reminder: {title}",
                    message=note or f"Scheduled alert for {title}",
                    level="alert",
                    source="calendar_reminder",
                    desktop_alert=True,
                )
        except Exception as exc:
            print(f"[{now_str}] [DAEMON REMINDER ERROR] {exc}", file=sys.stderr)

        # 2. Check scheduled autonomous missions
        try:
            executed_jobs = task_scheduler.check_and_run_due_tasks()
            for job in executed_jobs:
                print(f"[{now_str}] [AUTONOMOUS MISSION] Executed: {job.get('name')}")
        except Exception as exc:
            print(f"[{now_str}] [DAEMON SCHEDULER ERROR] {exc}", file=sys.stderr)

        time.sleep(poll_interval)

    print("[DAEMON] Jarvis Daemon stopped cleanly.")


if __name__ == "__main__":
    run_daemon()
