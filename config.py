import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_WORKSPACE_ID = os.getenv("ANTHROPIC_WORKSPACE_ID")

# Model Configuration
MODEL = "claude-3-5-sonnet-20241022"
MAX_TOKENS = 2048

# Tool Definitions for Claude
TOOLS = [
    {
        "name": "get_current_time",
        "description": "Get the current local date and time.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]
