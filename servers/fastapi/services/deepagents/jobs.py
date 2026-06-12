from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from models.sql.deepagent_presentation_run import DeepAgentPresentationRunModel
from services.database import async_session_maker
from utils.datetime_utils import get_current_utc_datetime

from .config import DeepAgentsSettings, load_deepagents_settings
from .errors import RunStateError
from .runner import run_deepagents_presentation_generation
from .schemas import DeepAgentRunResult

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

RUN_STATUS_PENDING = "pending"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_PARTIAL = "partial"
RUN_STATUS_CANCELLED = "cancelled"

_VALID_STATUSES = {
    RUN_STATUS_PENDING,
    RUN_STATUS_RUNNING,
    RUN_STATUS_COMPLETED,
    RUN_STATUS_FAILED,
    RUN_STATUS_PARTIAL,
    RUN_STATUS_CANCELLED,
}


def _sanitize_input_snapshot(request: Any) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for key in (
        "content",
        "instructions",
        "template",
        "export_as",
        "web_search",
        "language",
    ):
        snapshot[key] = _safe_getattr(request, key, None)

    tone = _safe_getattr(request, "tone", None)
    snapshot["tone"] = (
        tone.value if hasattr(tone, "value") else str(tone) if tone else None
    )

    verbosity = _safe_getattr(request, "verbosity", None)
    snapshot["verbosity"] = (
        verbosity.value
        if hasattr(verbosity, "value")
        else str(verbosity)
        if verbosity
        else None
    )

    n_slides = _safe_getattr(request, "n_slides", None)
    snapshot["n_slides"] = n_slides

    slides_markdown = _safe_getattr(request, "slides_markdown", None)
    snapshot["has_slides_markdown"] = slides_markdown is not None

    raw_files = _safe_getattr(request, "files", None)
    snapshot["file_count"] = len(raw_files) if raw_files else 0
    if raw_files:
        from .tools import build_agent_file_context

        file_dicts = []
        for f in raw_files:
            if isinstance(f, str):
                from pathlib import Path

                p = Path(f)
                file_dicts.append(
                    {
                        "filename": p.name,
                        "file_id": p.name,
                        "mime_type": "application/octet-stream",
                    }
                )
            else:
                file_dicts.append(f)
        snapshot["files"] = build_agent_file_context(file_dicts)
    else:
        snapshot["files"] = []

    return snapshot


def _safe_getattr(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default)


def _validate_status(status: str) -> str:
    if status not in _VALID_STATUSES:
        raise RunStateError(f"Invalid run status: {status}")
    return status


async def create_deepagent_run(
    session: AsyncSession,
    presentation_id: uuid.UUID,
    thread_id: str,
    user_id: Optional[str] = None,
    auto_mode: bool = False,
    memory_mode: str = "review",
    input_snapshot: Optional[dict] = None,
) -> DeepAgentPresentationRunModel:
    run = DeepAgentPresentationRunModel(
        id=uuid.uuid4(),
        presentation_id=presentation_id,
        thread_id=thread_id,
        user_id=user_id,
        status=RUN_STATUS_PENDING,
        auto_mode=auto_mode,
        memory_mode=memory_mode
        if memory_mode in ("off", "review", "auto")
        else "review",
        input_snapshot=input_snapshot,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    logger.info(
        "Created Deep Agent run: id=%s presentation_id=%s", run.id, presentation_id
    )
    return run


async def mark_run_started(
    session: AsyncSession,
    run_id: uuid.UUID,
) -> DeepAgentPresentationRunModel:
    run = await session.get(DeepAgentPresentationRunModel, run_id)
    if run is None:
        raise RunStateError(f"Run not found: {run_id}")
    run.status = RUN_STATUS_RUNNING
    run.started_at = get_current_utc_datetime()
    run.updated_at = get_current_utc_datetime()
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def mark_run_step(
    session: AsyncSession,
    run_id: uuid.UUID,
    step: str,
    message: Optional[str] = None,
) -> DeepAgentPresentationRunModel:
    run = await session.get(DeepAgentPresentationRunModel, run_id)
    if run is None:
        raise RunStateError(f"Run not found: {run_id}")
    run.step = step
    run.updated_at = get_current_utc_datetime()
    if message is not None:
        run.message = message
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def mark_run_completed(
    session: AsyncSession,
    run_id: uuid.UUID,
    output_snapshot: dict,
    status: str = RUN_STATUS_COMPLETED,
) -> DeepAgentPresentationRunModel:
    run = await session.get(DeepAgentPresentationRunModel, run_id)
    if run is None:
        raise RunStateError(f"Run not found: {run_id}")
    run.status = _validate_status(status)
    run.step = "completed"
    run.updated_at = get_current_utc_datetime()
    run.completed_at = get_current_utc_datetime()
    run.output_snapshot = output_snapshot
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def mark_run_failed(
    session: AsyncSession,
    run_id: uuid.UUID,
    error: dict,
    step: Optional[str] = None,
) -> DeepAgentPresentationRunModel:
    run = await session.get(DeepAgentPresentationRunModel, run_id)
    if run is None:
        raise RunStateError(f"Run not found: {run_id}")
    run.status = RUN_STATUS_FAILED
    run.step = step or "failed"
    run.updated_at = get_current_utc_datetime()
    run.completed_at = get_current_utc_datetime()
    run.error = error
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def get_run_status(
    session: AsyncSession,
    run_id: uuid.UUID,
) -> Optional[DeepAgentPresentationRunModel]:
    run = await session.get(DeepAgentPresentationRunModel, run_id)
    return run


async def run_deepagents_generation_job(
    *,
    run_id: str,
    presentation_id: str,
    request_snapshot: dict,
    export_cookie_header: Optional[str] = None,
    settings: Optional[DeepAgentsSettings] = None,
) -> None:
    if settings is None:
        settings = load_deepagents_settings()

    run_uuid = uuid.UUID(run_id)
    pres_uuid = uuid.UUID(presentation_id)
    thread_id = request_snapshot.get("thread_id", str(uuid.uuid4()))

    async with async_session_maker() as session:
        try:
            await mark_run_started(session, run_uuid)
            await mark_run_step(session, run_uuid, "creating_agent")

            class _SnapshotRequest:
                pass

            snap_request = _SnapshotRequest()
            for key, value in request_snapshot.items():
                if key == "tone":
                    from enums.tone import Tone

                    setattr(snap_request, key, Tone(value) if value else Tone.DEFAULT)
                elif key == "verbosity":
                    from enums.verbosity import Verbosity

                    setattr(
                        snap_request,
                        key,
                        Verbosity(value) if value else Verbosity.STANDARD,
                    )
                else:
                    setattr(snap_request, key, value)

            async def step_callback(step: str) -> None:
                async with async_session_maker() as cb_session:
                    try:
                        await mark_run_step(cb_session, run_uuid, step)
                    except Exception:
                        logger.warning(
                            "Failed to update step for run %s: %s",
                            run_id,
                            step,
                        )
                    finally:
                        await cb_session.close()

            result = await run_deepagents_presentation_generation(
                request=snap_request,
                presentation_id=presentation_id,
                thread_id=thread_id,
                user_id=request_snapshot.get("user_id"),
                auto_mode=request_snapshot.get("auto_mode", False),
                memory_mode=request_snapshot.get("memory_mode", "review"),
                export_cookie_header=export_cookie_header,
                settings=settings,
                step_callback=step_callback,
            )

            output = result.model_dump(mode="json")
            if result.status in ("completed", "partial"):
                final_status = (
                    "completed" if result.status == "completed" else "partial"
                )
                await mark_run_completed(session, run_uuid, output, status=final_status)
            else:
                await mark_run_failed(
                    session,
                    run_uuid,
                    {"message": result.error or "Unknown error"},
                    step="failed",
                )

        except Exception as exc:
            logger.exception("Background job failed for run %s", run_id)
            try:
                await mark_run_failed(
                    session,
                    run_uuid,
                    {
                        "message": str(exc),
                        "type": type(exc).__name__,
                    },
                    step="failed",
                )
            except Exception:
                logger.exception("Failed to mark run %s as failed", run_id)
