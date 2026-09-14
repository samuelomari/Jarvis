#!/usr/bin/env python3
"""Check whether configured environment variables and credential files are ready for live integrations."""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent


def status(label: str, ok: bool, message: str) -> None:
    print(f"[{ 'OK' if ok else 'MISSING' }] {label}: {message}")


def main() -> None:
    print("Jarvis integration readiness check\n")

    google_secret = Path(os.getenv("GMAIL_CLIENT_SECRET_FILE", ".secrets/google_client_secret.json"))
    google_token = Path(os.getenv("GMAIL_TOKEN_FILE", ".secrets/google_token.json"))
    github_token = os.getenv("GITHUB_TOKEN")

    secret_path = (ROOT / google_secret).resolve() if not google_secret.is_absolute() else google_secret
    token_path = (ROOT / google_token).resolve() if not google_token.is_absolute() else google_token

    status("Local Ollama", os.getenv("JARVIS_USE_LOCAL_MODEL", "true").lower() in {"1", "true", "yes"}, "Free local model route enabled")
    status("Google secret file", secret_path.exists(), str(secret_path))
    status("Google token file", token_path.exists(), str(token_path))
    status("GitHub token", bool(github_token), "GITHUB_TOKEN is set" if github_token else "Set GITHUB_TOKEN to enable GitHub repo access")

    if token_path.exists():
        try:
            payload = json.loads(token_path.read_text(encoding="utf-8"))
            status("Google token JSON", "refresh_token" in payload or "token" in payload, "Token file is valid JSON")
        except Exception as exc:
            status("Google token JSON", False, f"Could not parse token JSON: {exc}")

    print("\nNext steps:")
    print("1. Add your Google client secret to .secrets/google_client_secret.json")
    print("2. Run: python scripts/google_oauth_flow.py")
    print("3. Add your GitHub personal access token to GITHUB_TOKEN in .env")
    print("4. Start Jarvis and ask for Gmail, Calendar, or repo access")


if __name__ == "__main__":
    main()
