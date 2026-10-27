"""Compatibility entry point for running the useful MCP server."""

from useful_mcp.server import main, mcp

__all__ = ["mcp", "main"]

if __name__ == "__main__":
    main()
