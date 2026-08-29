"""Stage 4: Web search and external information tools."""

from tools.registry import register_tool


@register_tool({
    "name": "search_web",
    "description": "Search the web for information. Returns relevant results.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default: 5)"
            }
        },
        "required": ["query"],
    },
})
def search_web(query: str, max_results: int = 5) -> str:
    """
    Search the web for information.
    
    Note: In production, this would use a search API like Google, Bing, or DuckDuckGo.
    For now, returns mock results.
    """
    # In production, integrate with:
    # - Google Custom Search API
    # - Bing Search API
    # - DuckDuckGo API
    # - Tavily Search API (AI-focused)
    
    return f"""
**Search Results for: "{query}"**

This feature requires integration with a search API.

To enable web search, add one of:
- GOOGLE_SEARCH_API_KEY (Google Custom Search)
- BING_SEARCH_KEY (Microsoft Bing)
- TAVILY_API_KEY (AI-optimized search)

Once configured, you'll get real search results here.

**Recommended Setup:**
1. Get a free API key from [Tavily Search](https://tavily.com)
2. Add to .env: TAVILY_API_KEY=your_key
3. We'll integrate it in the next iteration
"""


@register_tool({
    "name": "get_documentation",
    "description": "Get documentation or reference material for a topic.",
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Topic to get documentation for (e.g., 'Python', 'React', 'Docker')"
            }
        },
        "required": ["topic"],
    },
})
def get_documentation(topic: str) -> str:
    """Get documentation links for a topic."""
    docs = {
        "python": {
            "Official Docs": "https://docs.python.org/3/",
            "Python Tutorial": "https://docs.python.org/3/tutorial/",
            "Python Library Reference": "https://docs.python.org/3/library/",
            "PEP Index": "https://peps.python.org/",
        },
        "react": {
            "React Docs": "https://react.dev",
            "React Hook Reference": "https://react.dev/reference/react",
            "React API Reference": "https://react.dev/reference/react",
        },
        "javascript": {
            "MDN Web Docs": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/",
            "JavaScript.info": "https://javascript.info/",
            "ES6+ Cheatsheet": "https://devhints.io/es6",
        },
        "docker": {
            "Docker Docs": "https://docs.docker.com/",
            "Dockerfile Reference": "https://docs.docker.com/engine/reference/builder/",
            "Docker Compose": "https://docs.docker.com/compose/",
        },
        "git": {
            "Git Book": "https://git-scm.com/book/en/v2",
            "Git Documentation": "https://git-scm.com/doc",
        },
        "anthropic": {
            "Claude Documentation": "https://docs.anthropic.com/",
            "Claude API Reference": "https://docs.anthropic.com/en/api/overview",
            "Prompt Engineering": "https://docs.anthropic.com/en/docs/build-a-chatbot",
        },
        "node": {
            "Node.js Docs": "https://nodejs.org/docs/",
            "Node.js API": "https://nodejs.org/api/",
            "npm Docs": "https://docs.npmjs.com/",
        }
    }
    
    topic_lower = topic.lower()
    
    if topic_lower in docs:
        result = f"**Documentation for {topic}:**\n"
        for title, url in docs[topic_lower].items():
            result += f"- [{title}]({url})\n"
        return result
    
    return f"Documentation for '{topic}' not in quick reference. Try searching for it with search_web()."


@register_tool({
    "name": "get_trends",
    "description": "Get information about current trends in tech/dev.",
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Topic area (e.g., 'AI', 'Web Development', 'Python')"
            }
        },
        "required": ["topic"],
    },
})
def get_trends(topic: str) -> str:
    """Get information about current trends."""
    return f"""
**Current Trends in {topic}**

To get real trend data, this feature requires integration with:
- Hacker News API
- Dev.to API
- GitHub Trending
- Reddit API
- Twitter/X API

**Popular resources:**
- Hacker News: https://news.ycombinator.com
- Dev.to: https://dev.to
- GitHub Trends: https://github.com/trending
- Lobsters: https://lobste.rs

Would you like me to search the web for latest trends in {topic}?
"""
