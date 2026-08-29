"""Memory tools for Jarvis - remember, recall, and forget information."""

from typing import Any, Dict, Optional, Union
from memory.manager import MemoryManager
from tools.registry import register_tool

_memory_manager = MemoryManager()


def get_memory_manager() -> MemoryManager:
    """Return the global MemoryManager instance."""
    return _memory_manager


@register_tool({
    "name": "remember",
    "description": "Store a new fact, project detail, preference, goal, or piece of information in persistent long-term memory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Category for the memory (e.g., 'user_preferences', 'projects', 'goals', 'important_facts', or custom).",
            },
            "content": {
                "type": "string",
                "description": "The exact fact, note, or information to remember.",
            },
        },
        "required": ["category", "content"],
    },
})
def remember(category: str, content: str) -> Dict[str, Any]:
    """Store information in persistent memory."""
    return _memory_manager.remember(category=category, item=content)


@register_tool({
    "name": "recall",
    "description": "Retrieve memories from persistent storage. Can search across all categories or within a specific category, with optional keyword filtering.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Optional category to filter memories (e.g., 'user_preferences', 'projects', 'goals', 'important_facts').",
            },
            "query": {
                "type": "string",
                "description": "Optional search term to find relevant memories by keyword.",
            },
        },
        "required": [],
    },
})
def recall(
    category: Optional[str] = None, query: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve memories matching the given category and query."""
    return _memory_manager.recall(category=category, query=query)


@register_tool({
    "name": "forget",
    "description": "Remove a specific memory item from a category in persistent storage by index (1-based) or by matching text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Category containing the memory to remove.",
            },
            "item_or_index": {
                "type": "string",
                "description": "The memory item index (e.g. '1', '2') or exact/partial text to remove.",
            },
        },
        "required": ["category", "item_or_index"],
    },
})
def forget(category: str, item_or_index: Union[str, int]) -> Dict[str, Any]:
    """Remove a specific memory item."""
    return _memory_manager.forget(category=category, item_or_index=item_or_index)

