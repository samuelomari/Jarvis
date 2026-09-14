"""Local Ollama-backed client for offline, no-cost model inference."""

import json
import os
from typing import Any, Dict, List, Optional
from urllib import error, request


class LocalTextBlock:
    """Response text block compatible with the existing agent loop."""

    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class LocalOllamaResponse:
    """Minimal response object with the same shape the app expects."""

    def __init__(self, text: str, stop_reason: str = "end_turn"):
        self.content = [LocalTextBlock(text)]
        self.stop_reason = stop_reason


class OllamaClient:
    """HTTP client for a local Ollama server."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.messages = self

    def _build_messages(self, messages: List[Dict[str, Any]], system: Optional[str] = None) -> List[Dict[str, str]]:
        chat_messages: List[Dict[str, str]] = []
        if system:
            chat_messages.append({"role": "system", "content": str(system)})

        for message in messages:
            role = str(message.get("role", "user"))
            content = message.get("content", "")
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(str(block.get("text", "")))
                        elif block.get("type") == "tool_result":
                            text_parts.append(str(block.get("content", "")))
                        elif block.get("type") == "tool_use":
                            text_parts.append(f"Tool call: {block.get('name', 'unknown')} {block.get('content', '')}")
                    elif isinstance(block, str):
                        text_parts.append(block)
                content = "\n".join(text_parts)
            chat_messages.append({"role": role, "content": str(content)})

        return chat_messages

    def _is_available(self) -> bool:
        try:
            req = request.Request(f"{self.base_url}/api/tags", method="GET")
            with request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except (error.URLError, TimeoutError, OSError):
            return False

    def create(self, **kwargs) -> LocalOllamaResponse:
        """Call the local Ollama /api/chat endpoint."""
        if not self._is_available():
            raise RuntimeError(
                "Ollama is not running locally. Start it with 'ollama serve' or disable local mode."
            )

        model_name = kwargs.get("model") or self.model
        messages = self._build_messages(kwargs.get("messages", []), kwargs.get("system"))
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.2,
            },
        }

        req = request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))

        text = ""
        if isinstance(data, dict):
            message = data.get("message", {})
            text = str(message.get("content", ""))
        if not text:
            text = "I’m running locally via Ollama and generated a blank response."

        return LocalOllamaResponse(text, stop_reason="end_turn")
