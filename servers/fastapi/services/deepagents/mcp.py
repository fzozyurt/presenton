from __future__ import annotations

import logging

from .config import DeepAgentsSettings
from .errors import MCPUnavailableError

logger = logging.getLogger(__name__)


async def load_presentation_mcp_tools(settings: DeepAgentsSettings) -> list:
    """
    Load presentation-engine MCP tools for the Deep Agent.

    Uses langchain_mcp_adapters to connect to the configured MCP server.
    """
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError as exc:
        raise MCPUnavailableError("langchain-mcp-adapters is not installed") from exc

    mcp_url = settings.deepagents_mcp_url

    try:
        client = MultiServerMCPClient(
            {
                "presentation_engine": {
                    "transport": "http",
                    "url": mcp_url,
                }
            }
        )

        async with client:
            tools = await client.get_tools()
    except Exception as exc:
        raise MCPUnavailableError(
            f"Presentation MCP server at {mcp_url} is unavailable: {exc}"
        ) from exc

    if not tools:
        raise MCPUnavailableError("Presentation MCP server returned zero tools")

    logger.debug("Loaded %d MCP tools from presentation engine", len(tools))
    for t in tools:
        logger.debug("  MCP tool: %s", getattr(t, "name", str(t)))

    return tools
