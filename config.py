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
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Development mode
DEV_MODE = os.getenv("JARVIS_DEV_MODE", "false").strip().lower() in ("true", "1", "yes")
JARVIS_DEV_MODE = DEV_MODE

# Local model preference: prefer Ollama when enabled and no paid API key is configured
USE_LOCAL_MODEL = os.getenv("JARVIS_USE_LOCAL_MODEL", "true").strip().lower() in ("true", "1", "yes")

# Model Configuration
raw_model = os.getenv("JARVIS_MODEL", "claude-3-5-sonnet-20241022").strip()
if raw_model.startswith("sk-") or not raw_model:
    MODEL = "claude-3-5-sonnet-20241022"
else:
    MODEL = raw_model

MAX_TOKENS = int(os.getenv("JARVIS_MAX_TOKENS", "2048"))
MAX_HISTORY_MESSAGES = int(os.getenv("JARVIS_MAX_HISTORY", "40"))

# Tool Definitions dynamically loaded from registry
from tools import get_all_tool_schemas

TOOLS = get_all_tool_schemas()

