"""External integration tools for speech, Gmail, Google Calendar, GitHub, and browser access."""

import json
import os
import shlex
import subprocess
import webbrowser
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib import error, request

from tools.registry import register_tool


def _google_credentials_available() -> bool:
    """Return whether Google auth environment is configured for Gmail/Calendar access."""
    return bool(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        or os.getenv("GMAIL_CREDENTIALS_FILE")
        or os.getenv("GMAIL_TOKEN_FILE")
    )


def _build_google_service(service_name: str, version: str):
    """Construct a Google API service if the client libraries and credentials are available."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Google API client libraries are not installed. Install google-api-python-client and google-auth-oauthlib."
        ) from exc

    creds_path = os.getenv("GMAIL_CREDENTIALS_FILE") or os.getenv("GMAIL_TOKEN_FILE")
    if not creds_path:
        raise RuntimeError(
            "Google integration is not configured. Set GMAIL_CREDENTIALS_FILE or GOOGLE_APPLICATION_CREDENTIALS."
        )

    if service_name == "gmail" and os.path.exists(creds_path):
        # Credentials file may be a token or JSON credentials file, so keep it simple and let the API layer decide.
        pass

    # Prefer application credentials from env if available.
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        creds = None
        return build(service_name, version, credentials=creds)

    # For locally stored token JSON, build the service using the file as credentials if it is a token file.
    try:
        with open(creds_path, "r", encoding="utf-8") as handle:
            token_data = json.load(handle)
        creds = Credentials.from_authorized_user_info(token_data)
        return build(service_name, version, credentials=creds)
    except Exception:
        # If the credential file is a standard client secret file, the user can run the OAuth flow separately.
        raise RuntimeError(
            "Google token or credentials file is missing or invalid. Generate a valid OAuth token for Gmail/Calendar access."
        )


@register_tool({
    "name": "speak_text",
    "description": "Speak a provided text message aloud using the local operating system speech engine when available.",
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to speak aloud."},
            "voice": {"type": "string", "description": "Optional voice name or preference."},
        },
        "required": ["text"],
    },
})
def speak_text(text: str, voice: str = "default") -> Dict[str, Any]:
    """Attempt to speak a message using a local TTS engine."""
    if not text or not text.strip():
        return {"success": False, "error": "Text is empty."}

    command_candidates = []
    for cmd in [
        ["espeak", text],
        ["spd-say", text],
        ["say", text],
    ]:
        command_candidates.append(cmd)

    if voice and voice != "default":
        command_candidates = [
            ["espeak", f"-v {voice}", text],
            ["spd-say", "-v", voice, text],
        ] + command_candidates

    for cmd in command_candidates:
        try:
            subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"success": True, "message": f"Spoken successfully via: {' '.join(cmd[:2]) if len(cmd) > 1 else cmd[0]}"}
        except Exception:
            continue

    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return {"success": True, "message": "Spoken successfully using pyttsx3."}
    except Exception:
        return {
            "success": False,
            "error": "No speech engine is available on this system. Install espeak, speech-dispatcher, or pyttsx3.",
        }


@register_tool({
    "name": "open_browser_url",
    "description": "Open a URL in the user’s default browser.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Full URL to open in the browser."},
            "new": {"type": "integer", "description": "Browser tab mode: 0 same window, 1 new window, 2 new tab."},
        },
        "required": ["url"],
    },
})
def open_browser_url(url: str, new: int = 2) -> Dict[str, Any]:
    """Open a URL in the default browser."""
    if not url or not url.startswith(("http://", "https://")):
        return {"success": False, "error": "URL must start with http:// or https://"}

    try:
        opened = webbrowser.open(url, new=new)
        return {"success": bool(opened), "url": url, "opened": opened}
    except Exception as exc:
        return {"success": False, "error": f"Failed to open browser: {str(exc)}"}


@register_tool({
    "name": "gmail_search_messages",
    "description": "Search the user’s Gmail inbox for messages matching a query and optionally return a preview of matching results.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Gmail search query such as 'from:me is:unread'."},
            "max_results": {"type": "integer", "description": "Maximum number of messages to return."},
        },
        "required": ["query"],
    },
})
def gmail_search_messages(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Search Gmail using a configured Google OAuth token."""
    if not query or not query.strip():
        return {"success": False, "error": "Query cannot be empty."}
    if not _google_credentials_available():
        return {
            "success": False,
            "error": "Gmail access is not configured. Set GMAIL_CREDENTIALS_FILE or GOOGLE_APPLICATION_CREDENTIALS with a valid Google OAuth token.",
        }

    try:
        from googleapiclient.discovery import build
    except ImportError:
        return {
            "success": False,
            "error": "google-api-python-client is not installed. Add it to requirements.txt and configure a Gmail OAuth credential.",
        }

    try:
        service = build("gmail", "v1", credentials=None)
        results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        messages = results.get("messages", [])
        preview = []
        for item in messages[:max_results]:
            msg = service.users().messages().get(userId="me", id=item["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"]).execute()
            headers = {header["name"]: header["value"] for header in msg.get("payload", {}).get("headers", [])}
            preview.append({
                "id": item["id"],
                "subject": headers.get("Subject", ""),
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
            })
        return {"success": True, "query": query, "count": len(preview), "messages": preview}
    except Exception as exc:
        return {"success": False, "error": f"Failed to access Gmail: {str(exc)}"}


@register_tool({
    "name": "calendar_list_events",
    "description": "List upcoming calendar events for the user from their Google Calendar.",
    "input_schema": {
        "type": "object",
        "properties": {
            "start_date": {"type": "string", "description": "Start date in ISO format (YYYY-MM-DD)."},
            "end_date": {"type": "string", "description": "End date in ISO format (YYYY-MM-DD)."},
            "max_results": {"type": "integer", "description": "Maximum number of events to return."},
        },
        "required": [],
    },
})
def calendar_list_events(start_date: Optional[str] = None, end_date: Optional[str] = None, max_results: int = 10) -> Dict[str, Any]:
    """Return upcoming events from the user's Google Calendar."""
    if not _google_credentials_available():
        return {
            "success": False,
            "error": "Google Calendar access is not configured. Set GMAIL_CREDENTIALS_FILE or GOOGLE_APPLICATION_CREDENTIALS with a valid OAuth token.",
        }

    try:
        from googleapiclient.discovery import build
    except ImportError:
        return {"success": False, "error": "google-api-python-client is not installed."}

    try:
        service = build("calendar", "v3", credentials=None)
        now = datetime.utcnow().isoformat() + "Z"
        start = start_date or now
        end = end_date or (datetime.utcnow().replace(hour=23, minute=59, second=59).isoformat() + "Z")
        events = service.events().list(calendarId="primary", timeMin=start, timeMax=end, maxResults=max_results, singleEvents=True, orderBy="startTime").execute()
        items = events.get("items", [])
        formatted = []
        for item in items:
            start_value = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
            end_value = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
            formatted.append({
                "id": item.get("id"),
                "summary": item.get("summary", "(No title)"),
                "start": start_value,
                "end": end_value,
                "location": item.get("location"),
                "status": item.get("status"),
            })
        return {"success": True, "count": len(formatted), "events": formatted}
    except Exception as exc:
        return {"success": False, "error": f"Failed to access Google Calendar: {str(exc)}"}


@register_tool({
    "name": "github_list_repos",
    "description": "List repositories for a GitHub user or the authenticated user using a personal access token.",
    "input_schema": {
        "type": "object",
        "properties": {
            "username": {"type": "string", "description": "GitHub username to inspect. Defaults to the authenticated user when a token is configured."},
            "limit": {"type": "integer", "description": "Maximum number of repositories to return."},
        },
        "required": [],
    },
})
def github_list_repos(username: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """List repos from GitHub via the REST API."""
    token = os.getenv("GITHUB_TOKEN")
    if not token and not username:
        return {
            "success": False,
            "error": "GitHub access is not configured. Set GITHUB_TOKEN or provide a username to list public repositories.",
        }

    endpoint = "https://api.github.com/user/repos" if token and not username else f"https://api.github.com/users/{username}/repos"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Jarvis-Agent"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        req = request.Request(endpoint, headers=headers, method="GET")
        with request.urlopen(req, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        repos = payload[:limit] if isinstance(payload, list) else []
        normalized = [{
            "name": repo.get("name"),
            "full_name": repo.get("full_name"),
            "private": repo.get("private"),
            "html_url": repo.get("html_url"),
            "description": repo.get("description"),
        } for repo in repos]
        return {"success": True, "count": len(normalized), "repositories": normalized}
    except error.HTTPError as exc:
        return {"success": False, "error": f"GitHub API request failed: {exc.read().decode('utf-8', 'ignore')}"}
    except Exception as exc:
        return {"success": False, "error": f"Failed to access GitHub: {str(exc)}"}
