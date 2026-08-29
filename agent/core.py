"""Core Jarvis agent implementation with tool-use capability."""

import anthropic

from config import ANTHROPIC_API_KEY, ANTHROPIC_WORKSPACE_ID, MODEL, MAX_TOKENS, TOOLS
from tools.basic import get_current_time


class Jarvis:
    """Main Jarvis AI agent with tool execution."""

    def __init__(self):
        headers = {}
        if ANTHROPIC_WORKSPACE_ID:
            headers["anthropic-workspace-id"] = ANTHROPIC_WORKSPACE_ID
        
        self.client = anthropic.Anthropic(
            api_key=ANTHROPIC_API_KEY,
            default_headers=headers
        )
        self.messages = []

    def run_tool(self, tool_name, tool_input):
        """Execute a tool by name with given input."""
        if tool_name == "get_current_time":
            return get_current_time()

        raise ValueError(f"Unknown tool: {tool_name}")

    def chat(self, user_input):
        """Process user input and return Jarvis's response."""
        self.messages.append({
            "role": "user",
            "content": user_input
        })

        while True:
            # Call Claude with tools
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=self.load_system(),
                messages=self.messages,
                tools=TOOLS
            )

            # Add Claude's response to message history
            self.messages.append({
                "role": "assistant",
                "content": response.content
            })

            # Check if Claude wants to use a tool
            if response.stop_reason != "tool_use":
                break

            # Process tool requests
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                # Execute the tool
                result = self.run_tool(
                    block.name,
                    block.input
                )

                # Collect tool results
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                })

            # Send tool results back to Claude
            self.messages.append({
                "role": "user",
                "content": tool_results
            })

        # Extract and return final text response
        return self.extract_text(response)

    def load_system(self):
        """Load system prompt from SYSTEM.md."""
        with open("SYSTEM.md", "r", encoding="utf-8") as file:
            return file.read()

    def extract_text(self, response):
        """Extract text blocks from Claude's response."""
        text = []

        for block in response.content:
            if block.type == "text":
                text.append(block.text)

        return "\n".join(text)
