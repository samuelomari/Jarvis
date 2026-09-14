#!/usr/bin/env python3
"""Create the expected credential folders and example secrets for live integrations."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRETS_DIR = ROOT / ".secrets"


def main() -> None:
    SECRETS_DIR.mkdir(exist_ok=True)

    google_token = SECRETS_DIR / "google_token.json"
    google_client = SECRETS_DIR / "google_client_secret.json"

    if not google_token.exists():
        google_token.write_text(json.dumps({"token": "", "refresh_token": "", "token_uri": "https://oauth2.googleapis.com/token"}, indent=2))

    if not google_client.exists():
        google_client.write_text(json.dumps({
            "installed": {
                "client_id": "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com",
                "project_id": "your-project-id",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "YOUR_GOOGLE_CLIENT_SECRET",
                "redirect_uris": ["http://localhost"]
            }
        }, indent=2))

    print(f"Credential folders ready at: {SECRETS_DIR}")
    print("Next steps:")
    print("1. Fill in .env based on .env.example")
    print("2. Create Google OAuth credentials in Google Cloud Console")
    print("3. Generate a GitHub PAT and set GITHUB_TOKEN")


if __name__ == "__main__":
    main()
