"""MCP server entry point and tool registration.

Builds the FastMCP server, registers all tool handlers from tools.py,
and exposes a run() function as the entry point.

Usage:
    ds-mcp                                # installed console script
    python -m desitter.interfaces.mcp.server
"""
from __future__ import annotations

try:
    import fastmcp
except ImportError as exc:
    raise ImportError(
        "MCP server requires the 'mcp' extra: "
        "pip install 'desitter[mcp]'"
    ) from exc

from pathlib import Path

from ...config import build_context, load_config
from .tools import register_tools


def create_server(workspace: Path | None = None) -> fastmcp.FastMCP:
    """Build and return a configured FastMCP server instance.

    Loads configuration from ``workspace`` (or cwd), constructs a
    ``ProjectContext``, and registers all MCP tool handlers.

    Args:
        workspace: Path to the project workspace. Defaults to cwd.

    Returns:
        fastmcp.FastMCP: A fully configured server ready to run.
    """
    ws = workspace or Path.cwd()
    config = load_config(ws)
    context = build_context(ws, config)

    server = fastmcp.FastMCP(
        name="desitter",
        description="Epistemic web data system for research projects",
    )
    register_tools(server, context)
    return server


def run(workspace: Path | None = None) -> None:
    """Create and run the MCP server (blocking).

    This is the main entry point for the ``ds-mcp`` console script.
    Blocks until the server is shut down.

    Args:
        workspace: Path to the project workspace. Defaults to cwd.
    """
    server = create_server(workspace)
    server.run()


if __name__ == "__main__":
    run()
