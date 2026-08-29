"""Core Jarvis agent implementation with tool execution, dynamic context, and safety boundaries."""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import anthropic

from agent.context import build_system_prompt
from config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_WORKSPACE_ID,
    MAX_HISTORY_MESSAGES,
    MAX_TOKENS,
    MODEL,
    PROJECT_ROOT,
    TOOLS,
)
from memory.manager import MemoryManager
from tools.registry import execute_tool, get_all_tool_schemas


class Jarvis:
    """Main Jarvis AI agent with tool execution and memory."""

    def __init__(
        self,
        memory_manager: Optional[MemoryManager] = None,
        system_file: Optional[Path] = None,
        workspace_root: Optional[Path] = None,
    ):
        self.workspace_root = workspace_root or PROJECT_ROOT
        self.system_file = system_file or (self.workspace_root / "SYSTEM.md")
        self.memory_manager = memory_manager or MemoryManager(
            self.workspace_root / "memory" / "memory.json"
        )

        client_kwargs = {"api_key": ANTHROPIC_API_KEY}
        if ANTHROPIC_WORKSPACE_ID and ANTHROPIC_WORKSPACE_ID.strip():
            client_kwargs["default_headers"] = {
                "anthropic-workspace-id": ANTHROPIC_WORKSPACE_ID
            }

        self.client = anthropic.Anthropic(**client_kwargs)
        self.messages: List[Dict[str, Any]] = []

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

    def run_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Execute a tool via the tool registry."""
        return execute_tool(tool_name, tool_input)

    def chat(
        self,
        user_input: str,
        on_tool_call: Optional[Callable[[str, Dict[str, Any], Any], None]] = None,
    ) -> str:
        """Process user input and return Jarvis's response with tool execution loop."""
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
            except anthropic.APIError as err:
                return f"Anthropic API Error: {err.message}"
            except Exception as err:
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

                # Execute tool
                result = self.run_tool(tool_name, tool_args)

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
                    "tool_use_id": block.id,
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
        """Extract text blocks from Claude's response."""
        text_blocks = []
        for block in response.content:
            if hasattr(block, "text") and block.text:
                text_blocks.append(block.text)
            elif isinstance(block, dict) and block.get("type") == "text":
                text_blocks.append(block.get("text", ""))

        return "\n\n".join(text_blocks)
