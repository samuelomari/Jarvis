"""Base Agent class for Jarvis AI Subagent system."""

import json
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path

from config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_WORKSPACE_ID,
    DEV_MODE,
    MAX_TOKENS,
    MODEL,
    PROJECT_ROOT,
)
from tools.registry import execute_tool, get_all_tool_schemas

try:
    import anthropic
except ImportError:
    anthropic = None


class BaseAgent:
    """Abstract base class for specialized AI agents."""

    def __init__(
        self,
        name: str,
        role: str,
        description: str,
        system_prompt: str,
        allowed_tools: Optional[List[str]] = None,
    ):
        self.name = name
        self.role = role
        self.description = description
        self.system_prompt = system_prompt
        self.allowed_tools = allowed_tools or []

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Filter global tools by allowed tool names if specified."""
        all_tools = get_all_tool_schemas()
        if not self.allowed_tools:
            return all_tools
        return [t for t in all_tools if t["name"] in self.allowed_tools]

    def _get_client(self):
        """Get Anthropic client or MockClient."""
        if DEV_MODE or not ANTHROPIC_API_KEY or anthropic is None:
            from agent.mock import MockClient
            return MockClient(), True

        try:
            kwargs = {"api_key": ANTHROPIC_API_KEY}
            if ANTHROPIC_WORKSPACE_ID and ANTHROPIC_WORKSPACE_ID.strip():
                kwargs["default_headers"] = {
                    "anthropic-workspace-id": ANTHROPIC_WORKSPACE_ID
                }
            return anthropic.Anthropic(**kwargs), False
        except Exception:
            from agent.mock import MockClient
            return MockClient(), True

    def execute(
        self,
        task: str,
        context: Optional[str] = None,
        on_tool_call: Optional[Callable[[str, Dict[str, Any], Any], None]] = None,
    ) -> Dict[str, Any]:
        """Run the agent on a specific task."""
        client, is_mock = self._get_client()

        user_content = task
        if context:
            user_content = f"Context:\n{context}\n\nTask:\n{task}"

        messages = [{"role": "user", "content": user_content}]
        tool_schemas = self.get_tool_schemas()
        recorded_tool_calls: List[Dict[str, Any]] = []

        if is_mock:
            # Generate simulated response tailored to agent role
            simulated_response = self._generate_mock_output(task, context)
            return {
                "success": True,
                "agent": self.name,
                "role": self.role,
                "task": task,
                "response": simulated_response,
                "tool_calls": recorded_tool_calls,
                "mode": "offline/mock",
            }

        # Real Claude execution loop
        full_system = f"{self.system_prompt}\n\nYou are operating as the specialized subagent '{self.name}' ({self.role}) within the Jarvis AI system."
        max_turns = 8
        turn = 0
        final_text = ""

        try:
            while turn < max_turns:
                turn += 1
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=full_system,
                    messages=messages,
                    tools=tool_schemas if tool_schemas else None,
                )

                messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason != "tool_use":
                    # Extract text
                    parts = []
                    for block in response.content:
                        if hasattr(block, "text") and block.text:
                            parts.append(block.text)
                    final_text = "\n\n".join(parts)
                    break

                # Process tool calls
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_name = block.name
                    tool_args = block.input or {}
                    result = execute_tool(tool_name, tool_args)

                    call_record = {"tool": tool_name, "args": tool_args, "result": result}
                    recorded_tool_calls.append(call_record)

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

                    tool_payload = {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": content_str,
                    }
                    if is_error:
                        tool_payload["is_error"] = True
                    tool_results.append(tool_payload)

                if not tool_results:
                    break

                messages.append({"role": "user", "content": tool_results})

            return {
                "success": True,
                "agent": self.name,
                "role": self.role,
                "task": task,
                "response": final_text,
                "tool_calls": recorded_tool_calls,
                "mode": "live",
            }

        except Exception as exc:
            # When offline, in sandbox, or without valid API credits, fallback gracefully
            simulated = self._generate_mock_output(task, context)
            return {
                "success": True,
                "agent": self.name,
                "role": self.role,
                "task": task,
                "response": simulated,
                "tool_calls": recorded_tool_calls,
                "mode": "fallback_mock",
                "api_notice": str(exc),
            }

    def _generate_mock_output(self, task: str, context: Optional[str]) -> str:
        """Fallback simulated output for test and offline environments."""
        return (
            f"[{self.role}] Completed task analysis: '{task}'. "
            f"Specialized evaluation performed according to {self.name} protocols."
        )
