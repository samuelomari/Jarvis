"""Telegram integration for Jarvis - remote commands, push notifications, and live status reports."""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger("jarvis.telegram")


def is_telegram_configured() -> bool:
    """Check if Telegram bot credentials are configured."""
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def send_telegram_message(
    text: str,
    chat_id: Optional[str] = None,
    parse_mode: str = "Markdown",
    bot_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a message to a Telegram user or group chat."""
    token = bot_token or TELEGRAM_BOT_TOKEN
    target_chat = chat_id or TELEGRAM_CHAT_ID

    if not token or not target_chat:
        return {
            "success": False,
            "error": "Telegram is not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env",
            "simulated": True,
        }

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": target_chat,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return {"success": True, "message_id": data.get("result", {}).get("message_id")}
            else:
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "error": resp.text,
                }
    except Exception as exc:
        return {"success": False, "error": f"Failed to reach Telegram API: {str(exc)}"}


class TelegramBotRunner:
    """Handles polling for incoming commands from Telegram and routing to Jarvis."""

    def __init__(self, jarvis_instance=None):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.last_update_id = 0
        self._jarvis = jarvis_instance

    def get_jarvis(self):
        """Lazy load Jarvis agent instance."""
        if self._jarvis is None:
            from agent.core import Jarvis
            self._jarvis = Jarvis()
        return self._jarvis

    def fetch_updates(self, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch latest updates from Telegram getUpdates API."""
        if not self.bot_token:
            return []

        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {"timeout": 2}
        if offset is not None:
            params["offset"] = offset

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("result", [])
        except Exception as exc:
            logger.debug("Telegram polling failed: %s", exc)
        return []

    def process_pending_commands(self) -> List[Dict[str, Any]]:
        """Check for unhandled commands and execute them."""
        if not is_telegram_configured():
            return []

        updates = self.fetch_updates(offset=self.last_update_id + 1)
        responses = []

        for update in updates:
            up_id = update.get("update_id")
            if up_id:
                self.last_update_id = max(self.last_update_id, up_id)

            msg = update.get("message", {})
            sender_id = str(msg.get("chat", {}).get("id", ""))
            text = msg.get("text", "").strip()

            # Security check: only respond to the authorized user/chat
            if self.chat_id and sender_id != str(self.chat_id):
                continue

            if not text:
                continue

            reply_text = self._handle_incoming_text(text)
            send_telegram_message(reply_text, chat_id=sender_id)
            responses.append({"update_id": up_id, "query": text, "reply": reply_text})

        return responses

    def _handle_incoming_text(self, text: str) -> str:
        """Handle command routing or normal AI dialogue."""
        text_lower = text.lower().strip()

        if text_lower in ("/start", "/help"):
            return (
                "🤖 *Jarvis Telegram Bridge Online*\n\n"
                "Available commands:\n"
                "• `/status` - Check server and daemon health\n"
                "• `/tasks` - View scheduled missions & reminders\n"
                "• `/stop` - Emergency stop all autonomous tool operations\n"
                "• Any plain text question or command will be processed by your Gemini AI brain."
            )

        if text_lower == "/status":
            from tools.system_monitor import get_system_health
            health = get_system_health()
            cpu = health.get("cpu", {}).get("usage_percent", "N/A")
            mem = health.get("memory", {}).get("percent_used", "N/A")
            return f"📊 *Jarvis Status*\n• Brain: Gemini\n• CPU: {cpu}%\n• Memory: {mem}%\n• Status: Healthy & Online"

        if text_lower == "/tasks":
            from memory.calendar_manager import CalendarManager
            from autonomous.scheduler import get_scheduler
            cal = CalendarManager()
            sched = get_scheduler()
            reminders = cal.list_reminders()
            tasks = sched.list_tasks(status="active")
            return (
                f"📋 *Tasks Overview*\n"
                f"• Active Reminders: {len(reminders)}\n"
                f"• Scheduled Missions: {len(tasks)}"
            )

        if text_lower in ("/stop", "emergency stop", "jarvis stop"):
            from security import get_emergency_stop
            res = get_emergency_stop().engage()
            return f"🚨 *EMERGENCY STOP TRIGGERED*\n{res.get('message', 'All actions suspended.')}"

        # Route query through Jarvis
        jarvis = self.get_jarvis()
        try:
            return jarvis.chat(text)
        except Exception as exc:
            return f"⚠️ Error processing query: {str(exc)}"

