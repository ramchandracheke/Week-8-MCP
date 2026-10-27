"""Environment-backed application settings."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    transport: str = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
    host: str = os.getenv("MCP_HOST", "127.0.0.1")
    port: int = int(os.getenv("MCP_PORT", "8000"))
    tavily_api_key: str | None = os.getenv("TAVILY_API_KEY")
    newsapi_api_key: str | None = os.getenv("NEWSAPI_API_KEY")


settings = Settings()
