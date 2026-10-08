"""Telegram tools for Jarvis - send phone alerts, summaries, and check remote messages."""

from typing import Any, Dict, Optional

from notifications.telegram import (
    is_telegram_configured,
    send_telegram_message,
    TelegramBotRunner,
)
from tools.registry import register_tool


@register_tool({
    "name": "send_telegram_message",
    "description": "Send a text message or notification directly to the user's phone via Telegram.",
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Text message content to send (Markdown supported).",
            },
            "chat_id": {
                "type": "string",
                "description": "Optional specific Telegram chat ID. Defaults to configured owner ID.",
            },
        },
        "required": ["message"],
    },
})
def telegram_send(message: str, chat_id: Optional[str] = None) -> Dict[str, Any]:
    """Send a message to the user via Telegram."""
    if not message or not message.strip():
        return {"success": False, "error": "Message cannot be empty."}

    res = send_telegram_message(message, chat_id=chat_id)
    return res


@register_tool({
    "name": "check_telegram_messages",
    "description": "Check for incoming messages or remote commands sent to Jarvis via Telegram.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
})
def telegram_check_messages() -> Dict[str, Any]:
    """Check for pending messages received via Telegram bot."""
    if not is_telegram_configured():
        return {
            "success": False,
            "error": "Telegram is not configured. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env",
            "messages": [],
        }

    runner = TelegramBotRunner()
    updates = runner.fetch_updates()
    extracted = []
    for u in updates:
        msg = u.get("message", {})
        if msg:
            extracted.append({
                "from": msg.get("from", {}).get("username") or msg.get("from", {}).get("first_name"),
                "text": msg.get("text", ""),
                "date": msg.get("date"),
            })

    return {
        "success": True,
        "count": len(extracted),
        "messages": extracted,
    }

