#!/usr/bin/env python3
"""Complete the Google OAuth flow for Gmail and Calendar access.

Usage:
    python scripts/google_oauth_flow.py

Requirements:
- A Google OAuth client secret JSON file at .secrets/google_client_secret.json
- A browser on the local machine to complete sign-in
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
CLIENT_SECRET = Path(os.getenv("GMAIL_CLIENT_SECRET_FILE", ".secrets/google_client_secret.json"))
TOKEN_PATH = Path(os.getenv("GMAIL_TOKEN_FILE", ".secrets/google_token.json"))
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def main() -> None:
    CLIENT_SECRET = (ROOT / CLIENT_SECRET).resolve() if not CLIENT_SECRET.is_absolute() else CLIENT_SECRET
    TOKEN_PATH = (ROOT / TOKEN_PATH).resolve() if not TOKEN_PATH.is_absolute() else TOKEN_PATH

    if not CLIENT_SECRET.exists():
        raise FileNotFoundError(
            f"Google OAuth client secret not found at {CLIENT_SECRET}. "
            "Create one in Google Cloud Console and save it to .secrets/google_client_secret.json."
        )

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    credentials = flow.run_local_server(port=0)
    TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")

    print(f"Google OAuth token saved to: {TOKEN_PATH}")
    print("You can now use Gmail and Calendar tools in Jarvis.")


if __name__ == "__main__":
    main()
