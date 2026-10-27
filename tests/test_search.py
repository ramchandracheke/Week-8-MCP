import pytest

from useful_mcp import search
from useful_mcp import news


@pytest.mark.asyncio
async def test_search_rejects_empty_query():
    with pytest.raises(ValueError, match="query must not be empty"):
        await search.search_web("  ")


@pytest.mark.asyncio
async def test_search_requires_credentials(monkeypatch):
    monkeypatch.setattr(search.settings, "tavily_api_key", None)
    with pytest.raises(ValueError, match="Set TAVILY_API_KEY"):
        await search.search_web("MCP")


@pytest.mark.asyncio
async def test_news_requires_credentials(monkeypatch):
    monkeypatch.setattr(news.settings, "newsapi_api_key", None)
    with pytest.raises(ValueError, match="Set NEWSAPI_API_KEY"):
        await news.search_news("MCP")


@pytest.mark.asyncio
async def test_search_maps_tavily_results(monkeypatch):
    monkeypatch.setattr(search.settings, "tavily_api_key", "test-secret")

    async def fake_post_json(client, url, **kwargs):
        assert kwargs["json"]["api_key"] == "test-secret"
        return {"results": [{"title": "MCP", "url": "https://example.test", "content": "A snippet", "score": 0.9}]}

    monkeypatch.setattr(search, "post_json", fake_post_json)
    assert await search.search_web("MCP") == {"query": "MCP", "results": [
        {"title": "MCP", "url": "https://example.test", "snippet": "A snippet", "score": 0.9}]}
