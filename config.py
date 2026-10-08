"""Configuration settings for Jarvis."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Workspace paths
PROJECT_ROOT = Path(__file__).resolve().parent

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_WORKSPACE_ID = os.getenv("ANTHROPIC_WORKSPACE_ID")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Development mode
DEV_MODE = os.getenv("JARVIS_DEV_MODE", "false").strip().lower() in ("true", "1", "yes")
JARVIS_DEV_MODE = DEV_MODE

# Local model preference: prefer Ollama when enabled and no paid API key is configured
USE_LOCAL_MODEL = os.getenv("JARVIS_USE_LOCAL_MODEL", "true").strip().lower() in ("true", "1", "yes")

# AI Provider: "gemini" (default), "anthropic", "ollama", "mock"
AI_PROVIDER = os.getenv("JARVIS_AI_PROVIDER", "gemini").strip().lower()

# Model Configuration (Gemini as default primary brain)
raw_model = (os.getenv("JARVIS_MODEL") or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")).strip()
if not raw_model or raw_model.startswith("claude-") or raw_model.startswith("sk-"):
    MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
else:
    MODEL = raw_model

MAX_TOKENS = int(os.getenv("JARVIS_MAX_TOKENS", "2048"))
MAX_HISTORY_MESSAGES = int(os.getenv("JARVIS_MAX_HISTORY", "40"))

# Tool Definitions dynamically loaded from registry
from tools import get_all_tool_schemas

TOOLS = get_all_tool_schemas()
