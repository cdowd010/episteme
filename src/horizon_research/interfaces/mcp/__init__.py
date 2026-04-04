"""MCP server adapter — primary external interface for AI agents.

Exposes all gateway operations as typed MCP tools with structured
status-first result envelopes.

Dependency: requires the `fastmcp` optional extra.
Install: pip install "horizon-research[mcp]"

All tool handlers are thin wrappers. Business logic lives in
core/gateway.py, never here.
"""
