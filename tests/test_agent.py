"""Unit tests for Jarvis Agent, Tool Registry, and Execution Loop."""

from unittest.mock import MagicMock, patch
import pytest

from agent.core import Jarvis
from agent.context import build_system_prompt
from tools.registry import (
    register_tool,
    execute_tool,
    get_all_tool_schemas,
    get_registered_tools,
)
from memory.manager import MemoryManager


def test_tool_registry_registration_and_execution():
    """Test registering and executing custom tool."""
    @register_tool({
        "name": "mock_calculator",
        "description": "Adds two numbers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
            },
            "required": ["a", "b"],
        },
    })
    def mock_calc(a: int, b: int):
        return a + b

    # Check schema
    tools = get_all_tool_schemas()
    names = [t["name"] for t in tools]
    assert "mock_calculator" in names

    # Execute
    res = execute_tool("mock_calculator", {"a": 10, "b": 25})
    assert res == 35

    # Unknown tool
    unknown_res = execute_tool("non_existent_tool_xyz", {})
    assert unknown_res["success"] is False
    assert "not recognized" in unknown_res["error"]


def test_system_prompt_builder(tmp_path):
    """Test dynamic context injection into system prompt."""
    sys_file = tmp_path / "SYSTEM.md"
    sys_file.write_text("# JARVIS IDENTITY\nYou are Jarvis.", encoding="utf-8")

    mem_file = tmp_path / "memory.json"
    mem_mgr = MemoryManager(mem_file)
    mem_mgr.remember("projects", "DevOS Project")

    prompt = build_system_prompt(sys_file, mem_mgr, tmp_path)
    assert "# JARVIS IDENTITY" in prompt
    assert "Dynamic Runtime Context" in prompt
    assert "Active Long-Term Memories" in prompt
    assert "DevOS Project" in prompt


def test_jarvis_history_trimming(tmp_path):
    """Test message history trimming logic."""
    with patch("anthropic.Anthropic"):
        jarvis = Jarvis(
            memory_manager=MemoryManager(tmp_path / "mem.json"),
            system_file=tmp_path / "SYS.md",
            workspace_root=tmp_path,
        )

        # Add mock messages
        for i in range(60):
            jarvis.messages.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}",
            })

        assert jarvis.get_history_count() == 60
        jarvis._trim_history()
        # Max history should keep it bounded and starting with a user message
        assert jarvis.get_history_count() <= 40
        assert jarvis.messages[0]["role"] == "user"

        jarvis.clear_history()
        assert jarvis.get_history_count() == 0


def test_jarvis_chat_tool_execution(tmp_path):
    """Test mock chat loop triggering tool call and returning response."""
    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        # Mock tool use response followed by final text response
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.id = "call_abc123"
        tool_block.name = "get_current_time"
        tool_block.input = {}

        response_1 = MagicMock()
        response_1.stop_reason = "tool_use"
        response_1.content = [tool_block]

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "The current time has been retrieved."

        response_2 = MagicMock()
        response_2.stop_reason = "end_turn"
        response_2.content = [text_block]

        mock_client.messages.create.side_effect = [response_1, response_2]

        jarvis = Jarvis(
            memory_manager=MemoryManager(tmp_path / "mem.json"),
            system_file=tmp_path / "SYS.md",
            workspace_root=tmp_path,
        )

        tool_calls = []
        def on_tool(name, args, result):
            tool_calls.append((name, args, result))

        reply = jarvis.chat("What time is it?", on_tool_call=on_tool)
        assert "The current time has been retrieved." in reply
        assert len(tool_calls) == 1
        assert tool_calls[0][0] == "get_current_time"

