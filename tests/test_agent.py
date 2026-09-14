"""Unit tests for Jarvis Agent, Tool Registry, and Execution Loop."""

from unittest.mock import MagicMock, patch

from agent.core import Jarvis
from agent.context import build_system_prompt
from memory.manager import MemoryManager
from tools.registry import execute_tool, get_all_tool_schemas, register_tool


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

    tools = get_all_tool_schemas()
    names = [t["name"] for t in tools]
    assert "mock_calculator" in names

    res = execute_tool("mock_calculator", {"a": 10, "b": 25})
    assert res == 35

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


def test_jarvis_mock_fallback_without_api_key(monkeypatch, tmp_path):
    """Test that Jarvis works without a paid API key by using the local/offline option."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("JARVIS_DEV_MODE", "true")

    with patch("agent.core.anthropic", None):
        jarvis = Jarvis(
            memory_manager=MemoryManager(tmp_path / "mem.json"),
            system_file=tmp_path / "SYS.md",
            workspace_root=tmp_path,
        )
        assert jarvis.client.__class__.__name__ in {"MockClient", "OllamaClient"}
        reply = jarvis.chat("What time is it?")
        assert isinstance(reply, str)
        assert len(reply) > 0


def test_required_integration_tools_are_registered():
    """Ensure Jarvis exposes the speech and external-service access tools required for real usage."""
    tool_names = {tool["name"] for tool in get_all_tool_schemas()}
    for name in [
        "speak_text",
        "gmail_search_messages",
        "calendar_list_events",
        "github_list_repos",
        "open_browser_url",
    ]:
        assert name in tool_names


def test_jarvis_history_trimming(tmp_path):
    """Test message history trimming logic."""
    with patch("anthropic.Anthropic"):
        jarvis = Jarvis(
            memory_manager=MemoryManager(tmp_path / "mem.json"),
            system_file=tmp_path / "SYS.md",
            workspace_root=tmp_path,
        )

        for i in range(60):
            jarvis.messages.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}",
            })

        assert jarvis.get_history_count() == 60
        jarvis._trim_history()
        assert jarvis.get_history_count() <= 40
        assert jarvis.messages[0]["role"] == "user"

        jarvis.clear_history()
        assert jarvis.get_history_count() == 0


def test_jarvis_chat_tool_execution(tmp_path):
    """Test mock chat loop triggering tool call and returning response."""
    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

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

