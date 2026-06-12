from __future__ import annotations

from typing import Any

from .backend import build_deepagents_backend
from .config import DeepAgentsSettings
from .errors import AgentFactoryError
from .mcp import load_presentation_mcp_tools
from .permissions import build_filesystem_permissions
from .prompts import (
    QUALITY_REVIEWER_PROMPT,
    RESEARCH_PLANNER_PROMPT,
    SLIDE_ARCHITECT_PROMPT,
    SUPERVISOR_SYSTEM_PROMPT,
)


async def create_deck_agent(
    settings: DeepAgentsSettings,
    user_id: str | None = None,
) -> Any:
    """
    Create and return a Deep Agent configured for presentation generation orchestration.

    The agent is only created when Deep Agents mode is enabled.
    In legacy mode, this function raises AgentFactoryError.
    """
    if not settings.is_deepagents_mode:
        raise AgentFactoryError(
            "Deep Agents mode is not enabled. "
            "Set PRESENTATION_ORCHESTRATOR=deepagents or DEEPAGENTS_ENABLED=true."
        )

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

    try:
        from deepagents import create_deep_agent
    except ImportError as exc:
        raise AgentFactoryError("deepagents package is not installed") from exc

    try:
        agent = create_deep_agent(
            model=settings.deepagents_model,
            tools=tools,
            system_prompt=SUPERVISOR_SYSTEM_PROMPT,
            subagents=subagents,
            backend=build_deepagents_backend(settings=settings, user_id=user_id),
            permissions=build_filesystem_permissions(settings.deepagents_memory_mode),
            memory=[
                "/memories/presentation_preferences.md",
                "/memories/design_patterns.md",
                "/memories/failure_lessons.md",
            ],
        )
    except Exception as exc:
        raise AgentFactoryError(f"Failed to create Deep Agent: {exc}") from exc

    return agent
