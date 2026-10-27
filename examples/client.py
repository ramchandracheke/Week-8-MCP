"""Protocol smoke client for stdio or Streamable HTTP (no LLM key required)."""

import argparse
import asyncio
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport


async def exercise(client: Client) -> None:
    async with client:
        tools = await client.list_tools()
        print("Available tools:", ", ".join(tool.name for tool in tools))
        status = await client.call_tool("service_status", {})
        print("Status:", status.data)
        city = await client.call_tool("get_current_weather", {"city": "London"})
        print("Current weather:", city.data)
        forecast = await client.call_tool("get_weather_forecast", {"city": "London", "days": 3})
        print("Forecast:", forecast.data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("transport", choices=("stdio", "http"), help="stdio launches the local server; http connects to a running server")
    parser.add_argument("--url", default="http://127.0.0.1:8000/mcp")
    args = parser.parse_args()
    if args.transport == "stdio":
        client = Client(PythonStdioTransport("server.py", cwd=Path(__file__).resolve().parents[1]))
    else:
        client = Client(args.url)
    asyncio.run(exercise(client))


if __name__ == "__main__":
    main()
