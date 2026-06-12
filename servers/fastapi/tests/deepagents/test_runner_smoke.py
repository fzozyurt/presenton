from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from services.deepagents.config import DeepAgentsSettings
from services.deepagents.errors import MCPUnavailableError
from services.deepagents.runner import (
    _normalize_output,
    run_deepagents_presentation_generation,
)
from services.deepagents.schemas import DeepAgentRunResult, DeckQualityReport


def test_missing_thread_id_fails_fast() -> None:
    settings = DeepAgentsSettings()

    async def runner() -> DeepAgentRunResult:
        return await run_deepagents_presentation_generation(
            request={},
            presentation_id=str(uuid.uuid4()),
            thread_id="",
            settings=settings,
        )

    result = _run_async(runner())
    assert result.status == "failed"
    assert "thread_id is required" in (result.error or "")


def test_mcp_unavailable_returns_readable_failure() -> None:
    settings = DeepAgentsSettings()
    pid = str(uuid.uuid4())

    async def runner() -> DeepAgentRunResult:
        return await run_deepagents_presentation_generation(
            request={},
            presentation_id=pid,
            thread_id="thread-abc",
            settings=settings,
        )

    with patch(
        "services.deepagents.runner.create_deck_agent",
        AsyncMock(
            side_effect=MCPUnavailableError("MCP server at http://x is unavailable")
        ),
    ):
        result = _run_async(runner())
    assert result.status == "failed"
    assert "MCP" in (result.error or "")


def test_normalize_output_none() -> None:
    result = _normalize_output(None)
    assert result.status == "failed"
    assert result.error == "Agent returned no output"


def test_normalize_output_dict() -> None:
    result = _normalize_output(
        {
            "presentation_id": "p1",
            "thread_id": "t1",
            "status": "completed",
            "warnings": ["test warning"],
        }
    )
    assert result.status == "completed"
    assert result.presentation_id == "p1"
    assert "test warning" in result.warnings


def test_normalize_output_partial() -> None:
    result = _normalize_output("unexpected string output")
    assert result.status == "partial"


def test_normalize_output_with_quality_report() -> None:
    result = _normalize_output(
        {
            "presentation_id": "p1",
            "thread_id": "t1",
            "status": "completed",
            "quality_report": {
                "score": 92,
                "passed": True,
                "issues": [],
                "summary": "Good deck",
            },
        }
    )
    assert result.status == "completed"
    assert result.quality_report is not None
    assert result.quality_report.score == 92
    assert result.quality_report.passed is True


def _run_async(coro):
    import asyncio

    return asyncio.run(coro)
