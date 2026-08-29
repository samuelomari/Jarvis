"""Mock Claude client for development/testing without API key."""

import json
from typing import Any, Dict, List


class MockMessage:
    """Mock response from Claude."""
    
    def __init__(self, content: str, stop_reason: str = "end_turn"):
        self.content = [MockTextBlock(content)]
        self.stop_reason = stop_reason


class MockTextBlock:
    """Mock text response block."""
    
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class MockToolBlock:
    """Mock tool use block."""
    
    def __init__(self, tool_name: str, tool_input: Dict[str, Any]):
        self.type = "tool_use"
        self.name = tool_name
        self.input = tool_input
        self.id = f"tool_{tool_name}_{hash(str(tool_input)) % 100000}"


class MockClient:
    """Mock Anthropic client for dev mode."""
    
    def __init__(self):
        self.messages_sent = []
        self.call_count = 0
    
    def messages(self):
        """Return mock message creation interface."""
        return self
    
    def create(self, **kwargs) -> MockMessage:
        """Create a mock response based on user input."""
        self.call_count += 1
        self.messages_sent.append(kwargs)
        
        # Extract user's last message
        messages = kwargs.get("messages", [])
        user_message = ""
        
        if messages:
            last_msg = messages[-1]
            if isinstance(last_msg.get("content"), str):
                user_message = last_msg["content"]
            elif isinstance(last_msg.get("content"), list):
                for block in last_msg["content"]:
                    if isinstance(block, dict) and block.get("type") == "text":
                        user_message = block.get("text", "")
        
        user_message = user_message.lower()
        
        # Smart mock responses based on user input
        if "time" in user_message or "current" in user_message:
            # Request the time tool
            return MockMessage(
                json.dumps({
                    "type": "tool_use",
                    "id": "tool_time_1",
                    "name": "get_current_time",
                    "input": {}
                }),
                stop_reason="tool_use"
            )
        
        elif "memory" in user_message or "remember" in user_message:
            return MockMessage(
                "I can help you remember things. What would you like me to remember?",
                stop_reason="end_turn"
            )
        
        elif "search" in user_message or "find" in user_message:
            return MockMessage(
                "I can search for information. What would you like me to search for?",
                stop_reason="end_turn"
            )
        
        elif "file" in user_message or "read" in user_message or "project" in user_message:
            return MockMessage(
                "I can analyze project files and read documents. What file would you like me to examine?",
                stop_reason="end_turn"
            )
        
        elif "calendar" in user_message or "remind" in user_message or "event" in user_message:
            return MockMessage(
                "I can manage your calendar and reminders. What would you like to schedule?",
                stop_reason="end_turn"
            )
        
        elif "about" in user_message or "who" in user_message or "what are you" in user_message:
            return MockMessage(
                "I'm Jarvis, your personal AI assistant. I can help with:\n"
                "- Answering questions\n"
                "- Managing your time and reminders\n"
                "- Analyzing your projects and files\n"
                "- Searching for information\n"
                "- Remembering important details\n\n"
                "What can I help you with?",
                stop_reason="end_turn"
            )
        
        elif "help" in user_message or "can you" in user_message:
            return MockMessage(
                "I can assist with many tasks! Try asking me:\n"
                "- 'What time is it?'\n"
                "- 'Remember that I'm working on Jarvis'\n"
                "- 'What files are in my project?'\n"
                "- 'Search for React documentation'\n"
                "- 'Create a reminder for tomorrow'\n\n"
                "What would you like?",
                stop_reason="end_turn"
            )
        
        else:
            # Generic helpful response
            return MockMessage(
                f"I understand you're asking about: '{user_message}'. "
                "I'm in development mode with mock responses. "
                "To enable real Claude API responses, configure ANTHROPIC_API_KEY and JARVIS_DEV_MODE=false in .env",
                stop_reason="end_turn"
            )
