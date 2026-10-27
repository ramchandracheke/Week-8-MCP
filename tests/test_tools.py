import asyncio
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport

from useful_mcp.server import mcp


@pytest.mark.asyncio
async def test_tool_discovery_and_invocation():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools}
        assert {"search_city", "get_current_weather", "get_weather_forecast", "search_web", "search_news", "service_status"} <= names
        result = await client.call_tool("service_status", {})
        assert result.data["server"] == "useful-mcp-server"
        assert "web_search_configured" in result.data["configuration"]


@pytest.mark.asyncio
async def test_stdio_subprocess_transport():
    project = Path(__file__).resolve().parents[1]
    transport = PythonStdioTransport("server.py", cwd=str(project), python_cmd=sys.executable)
    async with Client(transport) as client:
        result = await client.call_tool("service_status", {})
        assert result.data["server"] == "useful-mcp-server"


@pytest.mark.asyncio
async def test_streamable_http_transport():
    project = Path(__file__).resolve().parents[1]
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = os.environ.copy()
    env.update({"MCP_TRANSPORT": "http", "MCP_HOST": "127.0.0.1", "MCP_PORT": str(port)})
    process = subprocess.Popen([sys.executable, "server.py"], cwd=project, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        last_error = None
        for _ in range(50):
            try:
                async with Client(f"http://127.0.0.1:{port}/mcp") as client:
                    result = await client.call_tool("service_status", {})
                    assert result.data["server"] == "useful-mcp-server"
                    assert result.data["transport"] == "http"
                    return
            except Exception as exc:
                last_error = exc
                if process.poll() is not None:
                    raise RuntimeError("HTTP MCP server exited before accepting a client") from exc
                await asyncio.sleep(0.1)
        raise TimeoutError("HTTP MCP server did not become ready") from last_error
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
