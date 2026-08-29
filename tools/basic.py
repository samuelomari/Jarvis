"""Basic tools for Jarvis - time and system information."""

from datetime import datetime
from tools.registry import register_tool


@register_tool({
    "name": "get_current_time",
    "description": "Get the current local date and time in human-readable format.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
})
def get_current_time() -> str:
    """Return the current local date and time."""
    return datetime.now().strftime("%A, %d %B %Y at %H:%M:%S")
