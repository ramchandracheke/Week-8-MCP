"""NewsAPI integration."""

import httpx

from useful_mcp.config import settings
from useful_mcp.http import TIMEOUT, get_json

NEWS_URL = "https://newsapi.org/v2/everything"


async def search_news(query: str, max_results: int = 5) -> dict:
    """Search current articles through NewsAPI; credentials are optional until called."""
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty.")
    if isinstance(max_results, bool) or not isinstance(max_results, int) or not 1 <= max_results <= 10:
        raise ValueError("max_results must be an integer from 1 to 10.")
    if not settings.newsapi_api_key:
        raise ValueError("News search is not configured. Set NEWSAPI_API_KEY in your environment or .env file.")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        data = await get_json(client, NEWS_URL, params={"q": query, "pageSize": max_results, "sortBy": "publishedAt"}, headers={"X-Api-Key": settings.newsapi_api_key})
    articles = data.get("articles")
    if data.get("status") != "ok" or not isinstance(articles, list):
        raise RuntimeError("NewsAPI returned an unexpected response.")
    return {"query": query, "articles": [
        {"title": row.get("title"), "source": (row.get("source") or {}).get("name"), "published_at": row.get("publishedAt"),
         "description": row.get("description"), "url": row.get("url")}
        for row in articles[:max_results] if isinstance(row, dict)
    ]}
