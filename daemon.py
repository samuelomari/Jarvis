"""Jarvis Always-On Daemon runner."""

import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from memory.calendar_manager import CalendarManager

calendar_manager = CalendarManager()
RUNNING = True


def handle_shutdown(signum, frame):
    """Graceful shutdown handler."""
    global RUNNING
    print("\n[DAEMON] Received shutdown signal. Terminating Jarvis Daemon...")
    RUNNING = False


def run_daemon():
    """Main daemon loop checking reminders and system status."""
    print("=" * 60)
    print(" JARVIS ALWAYS-ON DAEMON STARTED")
    print(f"Monitoring active reminders and tasks...")
    print("Press Ctrl+C to terminate.")
    print("=" * 60)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    while RUNNING:
        try:
            triggered = calendar_manager.check_pending_reminders()
            for r in triggered:
                now_str = datetime.now().strftime("%H:%M:%S")
                print(f"[{now_str}] [ALERT] REMINDER TRIGGERED: {r.get('title')} (Note: {r.get('note', 'None')})")

            time.sleep(5)
        except Exception as exc:
            print(f"[DAEMON ERROR] {exc}", file=sys.stderr)
            time.sleep(5)

    print("[DAEMON] Stopped cleanly.")


if __name__ == "__main__":
    run_daemon()

