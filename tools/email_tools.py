"""Email and Gmail tools for Jarvis - drafting, sending, reading, and searching emails."""

import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import register_tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DRAFTS_FILE = DATA_DIR / "email_drafts.json"


def _ensure_drafts_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DRAFTS_FILE.exists():
        DRAFTS_FILE.write_text("[]", encoding="utf-8")


def _load_drafts() -> List[Dict[str, Any]]:
    _ensure_drafts_file()
    try:
        return json.loads(DRAFTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_drafts(drafts: List[Dict[str, Any]]):
    _ensure_drafts_file()
    DRAFTS_FILE.write_text(json.dumps(drafts, indent=2), encoding="utf-8")


@register_tool({
    "name": "send_email",
    "description": "Send an email message to a specified recipient via configured SMTP/Gmail credentials.",
    "input_schema": {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address."},
            "subject": {"type": "string", "description": "Subject line of the email."},
            "body": {"type": "string", "description": "Plain text body of the email."},
        },
        "required": ["to", "subject", "body"],
    },
})
def send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Send an email."""
    if not to or "@" not in to:
        return {"success": False, "error": f"Invalid email recipient: {to}"}

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if smtp_host and smtp_user and smtp_password:
        try:
            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

            return {"success": True, "recipient": to, "subject": subject, "sent": True}
        except Exception as exc:
            return {"success": False, "error": f"SMTP transmission failed: {str(exc)}"}

    # Fallback to saving in sent/outbox queue if credentials not configured
    drafts = _load_drafts()
    outbox_item = {
        "id": f"outbox_{len(drafts) + 1}",
        "to": to,
        "subject": subject,
        "body": body,
        "status": "queued_outbox",
        "notice": "SMTP not configured in .env; email queued in outbox.",
    }
    drafts.append(outbox_item)
    _save_drafts(drafts)

    return {
        "success": True,
        "simulated": True,
        "recipient": to,
        "subject": subject,
        "message": "Email queued in outbox. Configure SMTP_HOST/SMTP_USER in .env for direct live transmission.",
    }


@register_tool({
    "name": "draft_email",
    "description": "Create and save an email draft for later review and sending.",
    "input_schema": {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address."},
            "subject": {"type": "string", "description": "Subject line of the email."},
            "body": {"type": "string", "description": "Body text of the draft."},
        },
        "required": ["to", "subject", "body"],
    },
})
def draft_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Save an email draft."""
    drafts = _load_drafts()
    draft = {
        "id": f"draft_{len(drafts) + 1}",
        "to": to,
        "subject": subject,
        "body": body,
        "status": "draft",
    }
    drafts.append(draft)
    _save_drafts(drafts)

    return {
        "success": True,
        "draft_id": draft["id"],
        "recipient": to,
        "subject": subject,
        "message": "Draft created successfully.",
    }


@register_tool({
    "name": "list_email_drafts",
    "description": "List all saved email drafts and queued outgoing messages.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
})
def list_email_drafts() -> Dict[str, Any]:
    """Retrieve saved drafts."""
    drafts = _load_drafts()
    return {"success": True, "count": len(drafts), "drafts": drafts}

