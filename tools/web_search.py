"""Web search and page content extraction tools for Jarvis."""

import re
from typing import Any, Dict, List, Optional
import httpx
from tools.registry import register_tool

try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


@register_tool({
    "name": "search_web",
    "description": "Search the live web for current information, documentation, news, or articles using DuckDuckGo.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query keywords.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of search results to return (default: 5).",
            },
        },
        "required": ["query"],
    },
})
def search_web(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Perform live web search and return structured result snippets."""
    query = query.strip()
    if not query:
        return {"success": False, "error": "Search query cannot be empty."}

    results = []

    if HAS_DDGS:
        try:
            with DDGS() as ddgs:
                ddgs_results = list(ddgs.text(query, max_results=max_results))
                for item in ddgs_results:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("href", item.get("link", "")),
                        "snippet": item.get("body", item.get("snippet", "")),
                    })
        except Exception as exc:
            # Fallback to direct HTTP search if DDGS throws rate limits or errors
            pass

    # Fallback to direct HTTP DuckDuckGo HTML parsing if DDGS did not return results
    if not results:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = httpx.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers=headers,
                timeout=10.0,
                follow_redirects=True,
            )
            if resp.status_code == 200 and HAS_BS4:
                soup = BeautifulSoup(resp.text, "html.parser")
                for r in soup.select(".result"):
                    title_elem = r.select_one(".result__title a")
                    snippet_elem = r.select_one(".result__snippet")
                    if title_elem:
                        href = title_elem.get("href", "")
                        # Unpack DuckDuckGo redirect url if present
                        if "uddg=" in href:
                            import urllib.parse
                            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                            href = parsed.get("uddg", [href])[0]

                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "url": href,
                            "snippet": snippet_elem.get_text(strip=True) if snippet_elem else "",
                        })
                        if len(results) >= max_results:
                            break
        except Exception as fallback_exc:
            return {"success": False, "error": f"Search failed: {str(fallback_exc)}"}

    return {
        "success": True,
        "query": query,
        "count": len(results),
        "results": results,
    }


@register_tool({
    "name": "fetch_webpage",
    "description": "Fetch the readable text content of a webpage given its URL.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Full HTTP or HTTPS URL to fetch.",
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum character length of returned text (default: 4000).",
            },
        },
        "required": ["url"],
    },
})
def fetch_webpage(url: str, max_chars: int = 4000) -> Dict[str, Any]:
    """Fetch and parse text from a web URL."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return {"success": False, "error": "Invalid URL. Must begin with http:// or https://"}

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)

        if resp.status_code != 200:
            return {"success": False, "error": f"HTTP request returned status {resp.status_code}"}

        html_text = resp.text
        if HAS_BS4:
            soup = BeautifulSoup(html_text, "html.parser")
            # Remove scripts, styles, navigations
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
        else:
            # Basic tag strip regex
            text = re.sub(r"<[^>]+>", " ", html_text)
            text = re.sub(r"\s+", " ", text).strip()

        # Clean multiple blank lines
        cleaned_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        trimmed = cleaned_text[:max_chars]

        return {
            "success": True,
            "url": url,
            "length": len(trimmed),
            "content": trimmed,
            "truncated": len(cleaned_text) > max_chars,
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed fetching webpage: {str(exc)}"}

