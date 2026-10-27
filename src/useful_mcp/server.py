"""FastMCP server exposing weather, web search, and news tools."""

from fastmcp import FastMCP

from useful_mcp import __version__
from useful_mcp.config import settings
from useful_mcp.news import search_news
from useful_mcp.search import search_web
from useful_mcp.weather import get_current_weather, get_weather_forecast, search_city

mcp = FastMCP("useful-mcp-server")

mcp.tool(search_city)
mcp.tool(get_current_weather)
mcp.tool(get_weather_forecast)
mcp.tool(search_web)
mcp.tool(search_news)


@mcp.tool
def service_status() -> dict[str, object]:
    """Report this server's identity, configured transport, and credential presence."""
    return {
        "server": "useful-mcp-server",
        "version": __version__,
        "transport": settings.transport,
        "configuration": {
            "open_meteo": "public API; no key required",
            "web_search_configured": bool(settings.tavily_api_key),
            "news_search_configured": bool(settings.newsapi_api_key),
        },
    }


def main() -> None:
    if settings.transport == "stdio":
        mcp.run(transport="stdio")
    elif settings.transport == "http":
        mcp.run(transport="http", host=settings.host, port=settings.port)
    else:
        raise ValueError("MCP_TRANSPORT must be either 'stdio' or 'http'.")


if __name__ == "__main__":
    main()
