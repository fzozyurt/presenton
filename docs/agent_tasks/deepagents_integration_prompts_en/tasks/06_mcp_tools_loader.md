# TASK 06 — Add MCP tools loader

## Goal

Load the existing presentation API tools through MCP so the Deep Agent can use the current generation and export engine.

## File

`services/deepagents/mcp.py`

## Requirements

1. Use `langchain_mcp_adapters.client.MultiServerMCPClient`.
2. Use the configured MCP URL.
3. The loader must be async.
4. If the MCP server is unavailable, raise a readable error.
5. If no tools are returned, fail fast.
6. Log tool names in debug mode.

## Implement

```python
async def load_presentation_mcp_tools() -> list:
    """
    Load presentation-engine MCP tools for the Deep Agent.
    """
```

Suggested shape:

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

async def load_presentation_mcp_tools(settings) -> list:
    client = MultiServerMCPClient({
        "presentation_engine": {
            "transport": "http",
            "url": settings.deepagents_mcp_url,
        }
    })

    async with client:
        tools = await client.get_tools()

    if not tools:
        raise RuntimeError("Presentation MCP server returned zero tools")

    return tools
```

Adapt the exact client usage to the installed adapter version.

## Acceptance criteria

- The function is async.
- MCP unavailable produces a clear exception.
- Empty tool list produces a clear exception.
- No blocking network call is used.
- No tool execution happens in this loader.
