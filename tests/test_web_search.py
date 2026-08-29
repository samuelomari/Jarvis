"""Unit tests for Jarvis web search and fetch tools."""

from tools.web_search import search_web, fetch_webpage


def test_search_web_empty_query():
    """Test search_web rejects empty query."""
    res = search_web("")
    assert res["success"] is False
    assert "cannot be empty" in res["error"].lower()


def test_fetch_webpage_invalid_url():
    """Test fetch_webpage rejects invalid URL schemas."""
    res = fetch_webpage("ftp://invalid.url")
    assert res["success"] is False
    assert "invalid url" in res["error"].lower()

    res2 = fetch_webpage("file:///etc/passwd")
    assert res2["success"] is False

