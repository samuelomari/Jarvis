"""Unified email management tools for JARVIS.

Supports searching inbox, reading emails, drafting emails, and sending emails
(with mandatory user confirmation). Supports both configured Gmail API and local
inbox repository.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from tools.registry import register_tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EMAIL_DIR = PROJECT_ROOT / "data" / "emails"
INBOX_FILE = EMAIL_DIR / "inbox.json"
SENT_FILE = EMAIL_DIR / "sent.json"
DRAFTS_FILE = EMAIL_DIR / "drafts.json"


def _ensure_local_mailbox() -> None:
    """Initialize local mailbox files with sample developer emails if empty."""
    EMAIL_DIR.mkdir(parents=True, exist_ok=True)
    if not INBOX_FILE.exists():
        sample_inbox = [
            {
                "id": "msg_001",
                "from": "team@devos.org",
                "to": "samuel@jarvis.local",
                "subject": "DevOS Architecture Review Meeting",
                "date": "2026-10-02T10:00:00Z",
                "snippet": "Hi Samuel, please review the latest specifications for the kernel bridge...",
                "body": "Hi Samuel,\n\nPlease review the latest specifications for the kernel bridge and plugin pipeline before our sync tomorrow.\n\nBest,\nDevOS Team",
                "read": False,
            },
            {
                "id": "msg_002",
                "from": "notifications@github.com",
                "to": "samuel@jarvis.local",
                "subject": "[GitHub] Security update for your repository",
                "date": "2026-10-01T15:30:00Z",
                "snippet": "Dependabot detected 0 vulnerabilities in your latest commit...",
                "body": "Dependabot analysis complete. All dependencies in Jarvis and DevOS are healthy and up to date.",
                "read": True,
            },
            {
                "id": "msg_003",
                "from": "professor@university.edu",
                "to": "samuel@jarvis.local",
                "subject": "Advanced AI Systems - Project Submission",
                "date": "2026-09-30T09:15:00Z",
                "snippet": "Reminder: The autonomous agent implementation project is due next week...",
                "body": "Samuel,\n\nReminder: The autonomous agent implementation project is due next week. Please ensure your submission includes comprehensive test results and architectural documentation.\n\nRegards,\nProf. Davis",
                "read": True,
            },
        ]
        with open(INBOX_FILE, "w", encoding="utf-8") as f:
            json.dump(sample_inbox, f, indent=2)

    if not SENT_FILE.exists():
        with open(SENT_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

    if not DRAFTS_FILE.exists():
        with open(DRAFTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)


@register_tool({
    "name": "search_emails",
    "description": "Search inbox messages by keyword, sender, or subject across local mailbox and configured Gmail.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search term (e.g. 'DevOS', 'from:github', 'project')."},
            "max_results": {"type": "integer", "description": "Maximum number of messages to return (default: 5)."},
        },
        "required": ["query"],
    },
})
def search_emails(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Search for emails matching a query."""
    _ensure_local_mailbox()
    query_lower = query.lower().strip()

    # Try Gmail API if configured
    try:
        from tools.integrations import _google_credentials_available, gmail_search_messages
        if _google_credentials_available():
            gmail_res = gmail_search_messages(query=query, max_results=max_results)
            if gmail_res.get("success"):
                return gmail_res
    except Exception:
        pass

    # Search local inbox
    try:
        with open(INBOX_FILE, "r", encoding="utf-8") as f:
            messages = json.load(f)

        matches = []
        for msg in messages:
            haystack = f"{msg.get('subject', '')} {msg.get('from', '')} {msg.get('snippet', '')} {msg.get('body', '')}".lower()
            if query_lower in haystack or not query_lower:
                matches.append({
                    "id": msg.get("id"),
                    "from": msg.get("from"),
                    "subject": msg.get("subject"),
                    "date": msg.get("date"),
                    "snippet": msg.get("snippet", ""),
                    "read": msg.get("read", False),
                })
                if len(matches) >= max_results:
                    break

        return {
            "success": True,
            "source": "local_mailbox",
            "query": query,
            "count": len(matches),
            "messages": matches,
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed searching emails: {str(exc)}"}


@register_tool({
    "name": "read_email",
    "description": "Read the full contents of an email by its ID.",
    "input_schema": {
        "type": "object",
        "properties": {
            "email_id": {"type": "string", "description": "The unique ID of the email to read."},
        },
        "required": ["email_id"],
    },
})
def read_email(email_id: str) -> Dict[str, Any]:
    """Read a specific email by ID."""
    _ensure_local_mailbox()

    try:
        with open(INBOX_FILE, "r", encoding="utf-8") as f:
            messages = json.load(f)

        for msg in messages:
            if msg.get("id") == email_id:
                msg["read"] = True
                with open(INBOX_FILE, "w", encoding="utf-8") as fw:
                    json.dump(messages, fw, indent=2)
                return {
                    "success": True,
                    "email": msg,
                }

        # Check drafts or sent as well
        for filepath in (DRAFTS_FILE, SENT_FILE):
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    extra = json.load(f)
                for msg in extra:
                    if msg.get("id") == email_id:
                        return {"success": True, "email": msg}

        return {"success": False, "error": f"Email with ID '{email_id}' not found."}
    except Exception as exc:
        return {"success": False, "error": f"Failed reading email: {str(exc)}"}


@register_tool({
    "name": "draft_email",
    "description": "Save an email draft without sending it. Level 1 action.",
    "input_schema": {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address."},
            "subject": {"type": "string", "description": "Email subject line."},
            "body": {"type": "string", "description": "Email body content."},
        },
        "required": ["to", "subject", "body"],
    },
})
def draft_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Draft an email and save to drafts folder."""
    _ensure_local_mailbox()
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    draft_obj = {
        "id": draft_id,
        "to": to.strip(),
        "subject": subject.strip(),
        "body": body.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        drafts = []
        if DRAFTS_FILE.exists():
            with open(DRAFTS_FILE, "r", encoding="utf-8") as f:
                drafts = json.load(f)

        drafts.append(draft_obj)
        with open(DRAFTS_FILE, "w", encoding="utf-8") as f:
            json.dump(drafts, f, indent=2)

        return {
            "success": True,
            "draft_id": draft_id,
            "message": f"Draft saved successfully for {to}.",
            "draft": draft_obj,
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed saving draft: {str(exc)}"}


@register_tool({
    "name": "send_email",
    "description": "Send an email. LEVEL 2 sensitive action requiring explicit user confirmation (confirmed=True).",
    "input_schema": {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address."},
            "subject": {"type": "string", "description": "Subject line of the email."},
            "body": {"type": "string", "description": "Body message text."},
            "confirmed": {"type": "boolean", "description": "Explicit confirmation from the user to send the email."},
        },
        "required": ["to", "subject", "body"],
    },
})
def send_email(to: str, subject: str, body: str, confirmed: bool = False) -> Dict[str, Any]:
    """Send an email after explicit user confirmation."""
    if not confirmed:
        return {
            "success": False,
            "needs_confirmation": True,
            "risk_level": "LEVEL 2 — SYSTEM CHANGES",
            "task": f"Send email to {to}",
            "details": {
                "to": to,
                "subject": subject,
                "body_preview": body[:120] + ("..." if len(body) > 120 else ""),
            },
            "error": "Sending email blocked: Requires explicit user confirmation. Please confirm with confirmed=True.",
        }

    _ensure_local_mailbox()
    msg_id = f"sent_{uuid.uuid4().hex[:8]}"
    sent_record = {
        "id": msg_id,
        "to": to.strip(),
        "subject": subject.strip(),
        "body": body.strip(),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "status": "DELIVERED",
    }

    try:
        sent_items = []
        if SENT_FILE.exists():
            with open(SENT_FILE, "r", encoding="utf-8") as f:
                sent_items = json.load(f)

        sent_items.append(sent_record)
        with open(SENT_FILE, "w", encoding="utf-8") as f:
            json.dump(sent_items, f, indent=2)

        return {
            "success": True,
            "message_id": msg_id,
            "message": f"Email successfully sent to {to}.",
            "record": sent_record,
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed sending email: {str(exc)}"}
