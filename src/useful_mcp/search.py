"""Tavily web search integration."""

import httpx

from useful_mcp.config import settings
from useful_mcp.http import TIMEOUT, post_json

TAVILY_URL = "https://api.tavily.com/search"


async def search_web(query: str, max_results: int = 5) -> dict:
    """Search the web with Tavily and return provider titles, URLs, and snippets."""
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty.")
    if isinstance(max_results, bool) or not isinstance(max_results, int) or not 1 <= max_results <= 10:
        raise ValueError("max_results must be an integer from 1 to 10.")
    if not settings.tavily_api_key:
        raise ValueError("Web search is not configured. Set TAVILY_API_KEY in your environment or .env file.")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        data = await post_json(client, TAVILY_URL, json={"api_key": settings.tavily_api_key, "query": query, "max_results": max_results})
    results = data.get("results")
    if not isinstance(results, list):
        raise RuntimeError("Tavily returned an unexpected search response.")
    return {"query": query, "results": [
        {"title": row.get("title"), "url": row.get("url"), "snippet": row.get("content"), "score": row.get("score")}
        for row in results[:max_results] if isinstance(row, dict)
    ]}
