# TASK 08 — Create the Deep Agent factory

## Goal

Build the Deep Agent in one place with model, tools, backend, permissions, memory, and subagents.

## File

`services/deepagents/agent_factory.py`

## Implement

```python
async def create_deck_agent(settings):
    """
    Create and return a Deep Agent configured for presentation generation orchestration.
    """
```

## Required behavior

1. Load MCP tools using `load_presentation_mcp_tools`.
2. Build backend using `build_deepagents_backend`.
3. Build permissions using `build_filesystem_permissions`.
4. Use supervisor prompt from `prompts.py`.
5. Register three subagents:
   - `research-planner`
   - `slide-architect`
   - `quality-reviewer`
6. Configure memory files:
   - `/memories/presentation_preferences.md`
   - `/memories/design_patterns.md`
   - `/memories/failure_lessons.md`
7. Do not enable preview async subagents in the first implementation.
8. The returned agent must support `await agent.ainvoke(...)`.

## Suggested skeleton

```python
from deepagents import create_deep_agent

from .backend import build_deepagents_backend
from .permissions import build_filesystem_permissions
from .mcp import load_presentation_mcp_tools
from .prompts import (
    SUPERVISOR_SYSTEM_PROMPT,
    RESEARCH_PLANNER_PROMPT,
    SLIDE_ARCHITECT_PROMPT,
    QUALITY_REVIEWER_PROMPT,
)


async def create_deck_agent(settings):
    tools = await load_presentation_mcp_tools(settings)

    subagents = [
        {
            "name": "research-planner",
            "description": "Builds a deck brief and evidence map from user request, uploaded files, context, and memory.",
            "system_prompt": RESEARCH_PLANNER_PROMPT,
            "tools": [],
        },
        {
            "name": "slide-architect",
            "description": "Creates a slide-by-slide DeckPlan with purpose, main message, layout tags, and evidence ids.",
            "system_prompt": SLIDE_ARCHITECT_PROMPT,
            "tools": [],
        },
        {
            "name": "quality-reviewer",
            "description": "Reviews the deck plan and generated output using a strict presentation quality rubric.",
            "system_prompt": QUALITY_REVIEWER_PROMPT,
            "tools": [],
        },
    ]

    agent = create_deep_agent(
        model=settings.deepagents_model,
        tools=tools,
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        subagents=subagents,
        backend=build_deepagents_backend(),
        permissions=build_filesystem_permissions(settings.deepagents_memory_mode),
        memory=[
            "/memories/presentation_preferences.md",
            "/memories/design_patterns.md",
            "/memories/failure_lessons.md",
        ],
    )

    return agent
```

Adapt field names to the local settings object.

## Acceptance criteria

- Agent factory is async.
- Agent creation does not run in legacy mode.
- MCP tool load failures are readable.
- Memory paths are configured.
- Subagents are registered with clear descriptions.
- No branch or repository metadata is included.
