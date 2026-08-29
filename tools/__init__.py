"""Jarvis tools package with auto-registration of all tool modules."""

from tools.registry import (
    register_tool,
    execute_tool,
    get_all_tool_schemas,
    get_registered_tools,
)

# Import all tool modules to register their tools
from tools import basic
from tools import memory_tools
from tools import filesystem
from tools import analysis
from tools import web_search
from tools import calendar_tools

__all__ = [
    "register_tool",
    "execute_tool",
    "get_all_tool_schemas",
    "get_registered_tools",
    "basic",
    "memory_tools",
    "filesystem",
    "analysis",
    "web_search",
    "calendar_tools",
]
