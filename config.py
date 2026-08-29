"""Configuration settings for Jarvis."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Workspace paths
PROJECT_ROOT = Path(__file__).resolve().parent

# API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_WORKSPACE_ID = os.getenv("ANTHROPIC_WORKSPACE_ID")

# Model Configuration
MODEL = os.getenv("JARVIS_MODEL", "claude-3-5-sonnet-20241022")
MAX_TOKENS = int(os.getenv("JARVIS_MAX_TOKENS", "2048"))
MAX_HISTORY_MESSAGES = int(os.getenv("JARVIS_MAX_HISTORY", "40"))

# Tool Definitions dynamically loaded from registry
from tools import get_all_tool_schemas

TOOLS = get_all_tool_schemas()
