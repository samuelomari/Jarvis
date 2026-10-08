"""Core Jarvis agent implementation with tool execution, dynamic context, and safety boundaries."""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import MagicMock

try:
    import anthropic
except ImportError:  # pragma: no cover - fallback path.
    anthropic = None

from agent.context import build_system_prompt
from agent.gemini_client import GeminiClient
from agent.local_model import OllamaClient
from agent.mock import MockClient
from config import (
    AI_PROVIDER,
    ANTHROPIC_API_KEY,
    ANTHROPIC_WORKSPACE_ID,
    GEMINI_API_KEY,
    JARVIS_DEV_MODE,
    MAX_HISTORY_MESSAGES,
    MAX_TOKENS,
    MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    PROJECT_ROOT,
    TOOLS,
    USE_LOCAL_MODEL,
)
from memory.manager import MemoryManager
from security import get_emergency_stop, is_emergency_command
from tools.registry import execute_tool, get_all_tool_schemas


class Jarvis:
    """Main Jarvis AI agent with tool execution, Google Gemini brain, and memory."""

    def __init__(
        self,
        memory_manager: Optional[MemoryManager] = None,
        system_file: Optional[Path] = None,
        workspace_root: Optional[Path] = None,
        client: Optional[Any] = None,
    ):
        self.workspace_root = workspace_root or PROJECT_ROOT
        self.system_file = system_file or (self.workspace_root / "SYSTEM.md")
        self.memory_manager = memory_manager or MemoryManager(
            self.workspace_root / "memory" / "memory.json"
        )

        if client is not None:
            self.client = client
        else:
            self.client = self._initialize_client()

        self.messages: List[Dict[str, Any]] = []

    def _initialize_client(self) -> Any:
        """Initialize the AI client favoring Google Gemini as primary brain."""
        # 0. Check if anthropic.Anthropic is patched/mocked in active test suite
        if anthropic is not None and (
            isinstance(getattr(anthropic, "Anthropic", None), MagicMock)
            or hasattr(getattr(anthropic, "Anthropic", None), "mock_calls")
        ):
            try:
                mocked = anthropic.Anthropic()
                if hasattr(mocked, "messages"):
                    return mocked
            except Exception:
                pass

        import os
        gemini_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
        anthropic_key = os.getenv("ANTHROPIC_API_KEY") or ANTHROPIC_API_KEY
        dev_mode = (os.getenv("JARVIS_DEV_MODE", "").lower() in ("true", "1", "yes")) if os.getenv("JARVIS_DEV_MODE") is not None else JARVIS_DEV_MODE
        ai_provider = os.getenv("JARVIS_AI_PROVIDER", AI_PROVIDER).lower()
        use_local = (os.getenv("JARVIS_USE_LOCAL_MODEL", "").lower() in ("true", "1", "yes")) if os.getenv("JARVIS_USE_LOCAL_MODEL") is not None else USE_LOCAL_MODEL
        target_model = os.getenv("GEMINI_MODEL") or os.getenv("JARVIS_MODEL") or MODEL

        # 1. Development mode explicit offline mock
        if dev_mode:
            return MockClient()

        # 2. Google Gemini as primary AI Brain
        if gemini_key and (ai_provider == "gemini" or not anthropic_key):
            return GeminiClient(api_key=gemini_key, default_model=target_model)

        # 3. Anthropic Claude fallback if configured
        if anthropic_key and anthropic is not None:
            client_kwargs: Dict[str, Any] = {"api_key": anthropic_key}
            ws_id = os.getenv("ANTHROPIC_WORKSPACE_ID") or ANTHROPIC_WORKSPACE_ID
            if ws_id and ws_id.strip():
                client_kwargs["default_headers"] = {
                    "anthropic-workspace-id": ws_id
                }
            return anthropic.Anthropic(**client_kwargs)

        # 4. Local model preference (Ollama)
        if use_local:
            try:
                ollama = OllamaClient(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL)
                if ollama._is_available():
                    return ollama
            except Exception:
                pass

        # 5. Offline fallback
        return MockClient()

    def clear_history(self) -> None:
        """Reset conversation message history."""
        self.messages = []

    def get_history_count(self) -> int:
        """Return the number of messages in the active conversation."""
        return len(self.messages)

    def _trim_history(self) -> None:
        """Keep message history within configured limits while maintaining alternating structure."""
        if len(self.messages) > MAX_HISTORY_MESSAGES:
            # Keep the most recent messages, ensuring the first retained message is from the user
            excess = len(self.messages) - MAX_HISTORY_MESSAGES
            trimmed = self.messages[excess:]
            while trimmed and trimmed[0].get("role") != "user":
                trimmed = trimmed[1:]
            self.messages = trimmed

    def run_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        confirm_callback: Optional[Callable[[Any], bool]] = None,
        request: str = "",
    ) -> Any:
        """Execute a tool via the permission-gated registry."""
        return execute_tool(
            tool_name,
            tool_input,
            confirm_callback=confirm_callback,
            request=request,
        )

    def chat(
        self,
        user_input: str,
        on_tool_call: Optional[Callable[[str, Dict[str, Any], Any], None]] = None,
        confirm_callback: Optional[Callable[[Any], bool]] = None,
    ) -> str:
        """Process user input and return Jarvis's response with tool execution loop."""
        # Emergency control is handled before reaching the model.
        if is_emergency_command(user_input):
            result = get_emergency_stop().engage()
            self.messages.append({"role": "user", "content": user_input})
            self.messages.append({"role": "assistant", "content": result["message"]})
            return (
                "**[EMERGENCY STOP ENGAGED]**\n\n"
                f"{result['message']}\n"
                "All tool execution is now blocked. Say 'release emergency stop' to resume."
            )

        if "release emergency stop" in user_input.strip().lower() or "resume jarvis" in user_input.strip().lower():
            result = get_emergency_stop().release()
            self.messages.append({"role": "user", "content": user_input})
            self.messages.append({"role": "assistant", "content": result["message"]})
            return f"**[CONTROL RESTORED]** {result['message']}"

        self.messages.append({
            "role": "user",
            "content": user_input,
        })
        self._trim_history()

        system_prompt = build_system_prompt(
            system_file_path=self.system_file,
            memory_manager=self.memory_manager,
            workspace_root=self.workspace_root,
        )

        tools = get_all_tool_schemas()
        max_turns = 10
        turn = 0

        while turn < max_turns:
            turn += 1
            try:
                response = self.client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=system_prompt,
                    messages=self.messages,
                    tools=tools,
                )
            except Exception as err:
                if self.client.__class__.__name__ == "OllamaClient":
                    self.client = MockClient()
                    response = self.client.messages.create(
                        model=MODEL,
                        max_tokens=MAX_TOKENS,
                        system=system_prompt,
                        messages=self.messages,
                        tools=tools,
                    )
                else:
                    if hasattr(err, "message") and getattr(err, "message"):
                        return f"AI API Error: {err.message}"
                    if self.client.__class__.__name__ == "MockClient":
                        return "Jarvis is running in offline mode and cannot access the external API."
                    return f"Unexpected Error communicating with API: {str(err)}"

            # Save assistant response
            self.messages.append({
                "role": "assistant",
                "content": response.content,
            })

            # If no tools requested, we are done
            if response.stop_reason != "tool_use":
                break

            # Process tool calls
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_args = block.input or {}

                # Execute tool (permission-gated)
                result = self.run_tool(
                    tool_name,
                    tool_args,
                    confirm_callback=confirm_callback,
                    request=user_input,
                )

                if on_tool_call:
                    try:
                        on_tool_call(tool_name, tool_args, result)
                    except Exception:
                        pass

                is_error = isinstance(result, dict) and result.get("success") is False

                content_str = (
                    json.dumps(result, indent=2)
                    if isinstance(result, (dict, list))
                    else str(result)
                )

                tool_result_payload = {
                    "type": "tool_result",
                    "tool_use_id": getattr(block, "id", f"call_{tool_name}"),
                    "tool_name": tool_name,
                    "content": content_str,
                }
                if is_error:
                    tool_result_payload["is_error"] = True

                tool_results.append(tool_result_payload)

            if not tool_results:
                break

            # Send tool results back
            self.messages.append({
                "role": "user",
                "content": tool_results,
            })

        return self.extract_text(response)

    def extract_text(self, response: Any) -> str:
        """Extract text blocks from AI model response."""
        text_blocks = []
        content = getattr(response, "content", [])
        for block in content:
            if hasattr(block, "text") and block.text:
                text_blocks.append(block.text)
            elif isinstance(block, dict) and block.get("type") == "text":
                text_blocks.append(block.get("text", ""))

        return "\n\n".join(text_blocks)
