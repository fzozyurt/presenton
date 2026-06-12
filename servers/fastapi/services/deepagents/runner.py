from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from .agent_factory import create_deck_agent
from .config import DeepAgentsSettings
from .errors import MCPUnavailableError, RunTimeoutError
from .memory import build_memory_update_instruction
from .schemas import (
    DeepAgentRunResult,
    DeckPlan,
    DeckQualityReport,
    SlideQualityIssue,
)

logger = logging.getLogger(__name__)

_RUNNER_STEPS = [
    "creating_agent",
    "planning",
    "generating",
    "quality_review",
    "exporting",
    "saving_memory",
    "completed",
    "failed",
]

DeepAgentStepCallback = Optional[callable]


def _build_user_message(
    presentation_id: str,
    thread_id: str,
    auto_mode: bool,
    memory_mode: str,
    request: Any,
) -> str:
    content = getattr(request, "content", "")
    n_slides = getattr(request, "n_slides", None)
    language = getattr(request, "language", None)
    tone = getattr(request, "tone", None)
    verbosity = getattr(request, "verbosity", None)
    instructions = getattr(request, "instructions", None)
    template = getattr(request, "template", "general")
    export_as = getattr(request, "export_as", "pptx")
    web_search = getattr(request, "web_search", False)
    files = getattr(request, "files", None)
    slides_markdown = getattr(request, "slides_markdown", None)

    tone_val = tone.value if hasattr(tone, "value") else str(tone or "default")
    verbosity_val = (
        verbosity.value if hasattr(verbosity, "value") else str(verbosity or "standard")
    )

    lines = [
        "Create a presentation using the existing presentation engine.",
        "",
        f"presentation_id: {presentation_id}",
        f"thread_id: {thread_id}",
        f"auto_mode: {auto_mode}",
        f"memory_mode: {memory_mode}",
        "",
        "Request:",
        f"- content: {content}",
        f"- number_of_slides: {n_slides}",
        f"- language: {language}",
        f"- tone: {tone_val}",
        f"- verbosity: {verbosity_val}",
        f"- instructions: {instructions}",
        f"- template: {template}",
        f"- export_as: {export_as}",
        f"- web_search: {web_search}",
        f"- files: {files}",
        f"- slides_markdown: {slides_markdown is not None}",
        "",
        "Important:",
        "1. Create DeckPlan before generating/exporting.",
        "2. Use available presentation-engine tools for actual generation and export.",
        "3. Validate the result before final response.",
        f"4. Save generated planning/report artifacts under /outputs/{presentation_id}/.",
        f"5. {build_memory_update_instruction(auto_mode, memory_mode, presentation_id)}",
    ]

    return "\n".join(lines)


def _build_agent_config(
    thread_id: str,
    presentation_id: str,
    user_id: str | None,
    auto_mode: bool,
    memory_mode: str,
) -> dict[str, Any]:
    return {
        "configurable": {
            "thread_id": thread_id,
        },
        "metadata": {
            "presentation_id": presentation_id,
            "user_id": user_id or "anonymous",
            "auto_mode": auto_mode,
            "memory_mode": memory_mode,
            "orchestrator": "deepagents",
        },
    }


def _normalize_output(output: Any) -> DeepAgentRunResult:
    if output is None:
        return DeepAgentRunResult(
            presentation_id="",
            thread_id="",
            status="failed",
            error="Agent returned no output",
        )

    if isinstance(output, dict):
        return DeepAgentRunResult(
            presentation_id=output.get("presentation_id", ""),
            thread_id=output.get("thread_id", ""),
            status=output.get("status", "partial"),
            deck_plan=_maybe_parse_model(output.get("deck_plan"), DeckPlan),
            quality_report=_maybe_parse_model(
                output.get("quality_report"), DeckQualityReport
            ),
            presentation_path=output.get("presentation_path"),
            edit_path=output.get("edit_path"),
            export_path=output.get("export_path"),
            memory_updates=output.get("memory_updates", []),
            warnings=output.get("warnings", []),
            error=output.get("error"),
        )

    if hasattr(output, "get") and callable(getattr(output, "get", None)):
        return _normalize_output(dict(output))

    try:
        raw = json.loads(str(output))
        if isinstance(raw, dict):
            return _normalize_output(raw)
    except (json.JSONDecodeError, TypeError):
        pass

    return DeepAgentRunResult(
        presentation_id="",
        thread_id="",
        status="partial",
        warnings=["Output not in expected format; returning partial result"],
    )


def _maybe_parse_model(data: Any, model_class: type) -> Any:
    if data is None:
        return None
    if isinstance(data, model_class):
        return data
    if isinstance(data, dict):
        try:
            return model_class(**data)
        except Exception:
            return None
    return None


def _build_quality_review_prompt(
    deck_plan: Optional[DeckPlan],
    max_qa_loops: int,
) -> str:
    prompt_parts = [
        "Review the following deck plan against the quality rubric.",
        "",
        f"Maximum QA loops remaining: {max_qa_loops}",
        "",
    ]
    if deck_plan is not None:
        prompt_parts.append("## Deck Plan")
        try:
            prompt_parts.append(json.dumps(deck_plan.model_dump(mode="json"), indent=2))
        except Exception:
            prompt_parts.append(str(deck_plan))

    return "\n".join(prompt_parts)


def _has_high_severity_issues(report: Optional[DeckQualityReport]) -> bool:
    if report is None or not report.issues:
        return False
    return any(issue.severity == "high" for issue in report.issues)


async def run_deepagents_presentation_generation(
    *,
    request: Any,
    presentation_id: str,
    thread_id: str,
    user_id: str | None = None,
    auto_mode: bool = False,
    memory_mode: str = "review",
    export_cookie_header: str | None = None,
    settings: Optional[DeepAgentsSettings] = None,
    step_callback: DeepAgentStepCallback = None,
) -> DeepAgentRunResult:
    from .config import load_deepagents_settings

    if settings is None:
        settings = load_deepagents_settings()

    if not thread_id:
        return DeepAgentRunResult(
            presentation_id=presentation_id,
            thread_id="",
            status="failed",
            error="thread_id is required",
        )

    agent = None
    try:
        if step_callback:
            await step_callback("creating_agent")

        agent = await create_deck_agent(settings=settings, user_id=user_id)

        user_message = _build_user_message(
            presentation_id=presentation_id,
            thread_id=thread_id,
            auto_mode=auto_mode,
            memory_mode=memory_mode,
            request=request,
        )

        config = _build_agent_config(
            thread_id=thread_id,
            presentation_id=presentation_id,
            user_id=user_id,
            auto_mode=auto_mode,
            memory_mode=memory_mode,
        )

        timeout = settings.deepagents_run_timeout_seconds
        max_qa_loops = settings.deepagents_max_qa_loops

        if step_callback:
            await step_callback("planning")

        try:
            raw_output = await asyncio.wait_for(
                agent.ainvoke(user_message, config=config),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise RunTimeoutError(
                f"Agent run timed out after {timeout} seconds"
            ) from None

        result = _normalize_output(raw_output)

        deck_plan = result.deck_plan
        quality_report = result.quality_report

        qa_loop_count = 0
        while max_qa_loops > 0 and qa_loop_count < max_qa_loops:
            if step_callback:
                await step_callback("quality_review")

            if quality_report is not None and quality_report.passed:
                break

            review_prompt = _build_quality_review_prompt(
                deck_plan=deck_plan,
                max_qa_loops=max_qa_loops - qa_loop_count - 1,
            )

            try:
                revised_output = await asyncio.wait_for(
                    agent.ainvoke(review_prompt, config=config),
                    timeout=timeout,
                )
                revised_result = _normalize_output(revised_output)
                if revised_result.deck_plan is not None:
                    deck_plan = revised_result.deck_plan
                if revised_result.quality_report is not None:
                    quality_report = revised_result.quality_report
                if revised_result.warnings:
                    result.warnings.extend(revised_result.warnings)
            except asyncio.TimeoutError:
                result.warnings.append(
                    f"Quality review loop {qa_loop_count + 1} timed out"
                )
                break

            if quality_report is not None and quality_report.passed:
                break

            qa_loop_count += 1

        result.deck_plan = deck_plan
        result.quality_report = quality_report

        if quality_report is not None:
            if _has_high_severity_issues(quality_report) and quality_report.score < 80:
                result.status = "partial"
                result.warnings.append(
                    f"Final quality score {quality_report.score} is below threshold "
                    f"with high-severity issues. Marked as partial."
                )
        elif max_qa_loops > 0:
            result.warnings.append(
                "No quality report produced despite QA loops being configured."
            )

        if step_callback:
            await step_callback("completed")

        return result

    except MCPUnavailableError as exc:
        logger.error("MCP unavailable: %s", exc)
        return DeepAgentRunResult(
            presentation_id=presentation_id,
            thread_id=thread_id,
            status="failed",
            error=str(exc),
        )
    except RunTimeoutError as exc:
        logger.error("Run timed out: %s", exc)
        return DeepAgentRunResult(
            presentation_id=presentation_id,
            thread_id=thread_id,
            status="failed",
            error=str(exc),
        )
    except Exception as exc:
        logger.exception("Deep Agents runner failed")
        return DeepAgentRunResult(
            presentation_id=presentation_id,
            thread_id=thread_id,
            status="failed",
            error=str(exc),
        )
