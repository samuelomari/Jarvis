"""Small persistent conversation index for recalling prior JARVIS exchanges."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from config import PROJECT_ROOT

CONVERSATIONS_FILE = PROJECT_ROOT / "data" / "conversations.json"


def _load() -> List[Dict[str, Any]]:
    if not CONVERSATIONS_FILE.exists():
        return []
    try:
        data = json.loads(CONVERSATIONS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _save(items: List[Dict[str, Any]]) -> None:
    CONVERSATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=CONVERSATIONS_FILE.parent, delete=False, encoding="utf-8") as tmp:
        json.dump(items[-500:], tmp, indent=2)
        tmp.flush()
        temp_name = tmp.name
    Path(temp_name).replace(CONVERSATIONS_FILE)


def record(user_message: str, assistant_reply: str) -> None:
    items = _load()
    items.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "user": user_message,
        "assistant": assistant_reply,
    })
    _save(items)


def search(query: str, limit: int = 20) -> Dict[str, Any]:
    term = query.strip().lower()
    if not term:
        return {"success": False, "error": "Search query cannot be empty."}
    matches = [
        item for item in reversed(_load())
        if term in item.get("user", "").lower() or term in item.get("assistant", "").lower()
    ]
    return {"success": True, "query": query, "count": min(len(matches), limit), "results": matches[:limit]}
