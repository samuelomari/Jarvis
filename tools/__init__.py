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
from tools import agent_tools
from tools import autonomous_tools
from tools import notification_tools
from tools import integrations
from tools import computer_control
from tools import developer_tools
from tools import system_monitor
from tools import vision_tools
from tools import debugging

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
    "agent_tools",
    "autonomous_tools",
    "notification_tools",
    "integrations",
    "computer_control",
    "developer_tools",
    "system_monitor",
    "vision_tools",
    "debugging",
]
