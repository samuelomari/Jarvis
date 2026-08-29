"""Memory management tools for Jarvis."""

from memory.manager import MemoryManager
from tools.registry import register_tool

# Global memory manager instance
memory_manager = MemoryManager()


@register_tool({
    "name": "remember",
    "description": "Remember information and store it for future use.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Category to remember (e.g., 'projects', 'goals', 'important_facts', 'user_preferences')"
            },
            "information": {
                "type": "string",
                "description": "The information to remember"
            }
        },
        "required": ["category", "information"],
    },
})
def remember(category: str, information: str) -> str:
    """Remember information."""
    result = memory_manager.remember(category, information)
    return result.get("message", str(result))


@register_tool({
    "name": "recall",
    "description": "Recall information from memory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Optional: specific category to recall from"
            }
        },
        "required": [],
    },
})
def recall(category: str = None) -> str:
    """Recall information from memory."""
    result = memory_manager.recall(category=category)
    
    if isinstance(result, dict):
        if result.get("success"):
            memories = result.get("memories", {})
            if not memories:
                return f"No memories found{f' in {category}' if category else ''}."
            
            output = f"**Memories{f' in {category}' if category else ''}:**\n"
            for cat, items in memories.items():
                output += f"\n**{cat}:**\n"
                for item in items:
                    output += f"- {item}\n"
            return output
        else:
            return result.get("error", "Error recalling memories")
    
    return str(result)


@register_tool({
    "name": "forget",
    "description": "Remove information from memory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Category to forget from"
            },
            "item": {
                "type": "string",
                "description": "Optional: specific item to forget. If not provided, clears entire category"
            }
        },
        "required": ["category"],
    },
})
def forget(category: str, item: str = None) -> str:
    """Forget information from memory."""
    result = memory_manager.forget(category, item)
    return result.get("message", str(result)) if isinstance(result, dict) else str(result)


@register_tool({
    "name": "search_memory",
    "description": "Search memory for specific information.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            }
        },
        "required": ["query"],
    },
})
def search_memory(query: str) -> str:
    """Search memory."""
    result = memory_manager.recall(query=query)
    
    if isinstance(result, dict):
        if result.get("success") and result.get("count", 0) > 0:
            memories = result.get("memories", {})
            output = f"**Found {result.get('count', 0)} matches for '{query}':**\n"
            for cat, items in memories.items():
                output += f"\n**{cat}:**\n"
                for item in items:
                    output += f"- {item}\n"
            return output
        else:
            return f"No memories found matching '{query}'."
    
    return str(result)
