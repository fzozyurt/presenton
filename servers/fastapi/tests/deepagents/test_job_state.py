from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.deepagents.jobs import (
    RUN_STATUS_CANCELLED,
    RUN_STATUS_COMPLETED,
    RUN_STATUS_FAILED,
    RUN_STATUS_PARTIAL,
    RUN_STATUS_PENDING,
    RUN_STATUS_RUNNING,
    _sanitize_input_snapshot,
    _validate_status,
    create_deepagent_run,
    get_run_status,
    mark_run_completed,
    mark_run_failed,
    mark_run_started,
    mark_run_step,
    run_deepagents_generation_job,
)
from services.deepagents.errors import RunStateError
from services.deepagents.schemas import DeepAgentRunResult


class _FakeRun:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid.uuid4())
        self.presentation_id = kwargs.get("presentation_id", uuid.uuid4())
        self.thread_id = kwargs.get("thread_id", "t1")
        self.status = kwargs.get("status", RUN_STATUS_PENDING)
        self.step = kwargs.get("step")
        self.message = kwargs.get("message")
        self.output_snapshot = kwargs.get("output_snapshot")
        self.error = kwargs.get("error")
        self.updated_at = None
        self.completed_at = None
        self.started_at = None
        self.auto_mode = kwargs.get("auto_mode", False)
        self.memory_mode = kwargs.get("memory_mode", "review")
        self.input_snapshot = kwargs.get("input_snapshot")
        self.created_at = None


def test_validate_status_valid() -> None:
    assert _validate_status(RUN_STATUS_PENDING) == RUN_STATUS_PENDING
    assert _validate_status(RUN_STATUS_RUNNING) == RUN_STATUS_RUNNING
    assert _validate_status(RUN_STATUS_COMPLETED) == RUN_STATUS_COMPLETED
    assert _validate_status(RUN_STATUS_FAILED) == RUN_STATUS_FAILED
    assert _validate_status(RUN_STATUS_PARTIAL) == RUN_STATUS_PARTIAL
    assert _validate_status(RUN_STATUS_CANCELLED) == RUN_STATUS_CANCELLED


def test_validate_status_invalid() -> None:
    with pytest.raises(RunStateError):
        _validate_status("unknown_status")


def test_sanitize_input_snapshot() -> None:
    class _FakeRequest:
        content = "Test content"
        instructions = "Be creative"
        template = "general"
        export_as = "pptx"
        web_search = True
        language = "English"
        tone = None
        verbosity = None
        n_slides = 5
        slides_markdown = ["# Hello"]
        files = ["file1.pdf", "file2.docx"]

    snapshot = _sanitize_input_snapshot(_FakeRequest())
    assert snapshot["content"] == "Test content"
    assert snapshot["file_count"] == 2
    assert snapshot["has_slides_markdown"] is True
    assert snapshot["n_slides"] == 5


def test_create_deepagent_run() -> None:
    async def _run():
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        return await create_deepagent_run(
            session=session,
            presentation_id=uuid.uuid4(),
            thread_id="t1",
        )

    run = asyncio.run(_run())
    assert run.status == RUN_STATUS_PENDING
    assert run.thread_id == "t1"


def test_mark_run_started() -> None:
    async def _run():
        run_id = uuid.uuid4()
        fake_run = _FakeRun(id=run_id, status=RUN_STATUS_PENDING)
        session = AsyncMock()
        session.get = AsyncMock(return_value=fake_run)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        return await mark_run_started(session, run_id)

    updated = asyncio.run(_run())
    assert updated.status == RUN_STATUS_RUNNING
    assert updated.started_at is not None


def test_mark_run_step() -> None:
    async def _run():
        run_id = uuid.uuid4()
        fake_run = _FakeRun(id=run_id)
        session = AsyncMock()
        session.get = AsyncMock(return_value=fake_run)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        return await mark_run_step(session, run_id, "planning", "Planning started")

    updated = asyncio.run(_run())
    assert updated.step == "planning"
    assert updated.message == "Planning started"


def test_run_lifecycle_pending_to_completed() -> None:
    async def _run():
        run_id = uuid.uuid4()
        fake_run = _FakeRun(id=run_id, status=RUN_STATUS_PENDING)
        session = AsyncMock()
        session.get = AsyncMock(return_value=fake_run)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        started = await mark_run_started(session, run_id)
        assert started.status == RUN_STATUS_RUNNING

        fake_run.status = RUN_STATUS_RUNNING
        completed = await mark_run_completed(
            session, run_id, {"status": "completed"}, status=RUN_STATUS_COMPLETED
        )
        assert completed.status == RUN_STATUS_COMPLETED
        assert completed.step == "completed"

    asyncio.run(_run())


def test_failed_run_stores_error_snapshot() -> None:
    async def _run():
        run_id = uuid.uuid4()
        fake_run = _FakeRun(id=run_id)
        session = AsyncMock()
        session.get = AsyncMock(return_value=fake_run)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        return await mark_run_failed(
            session,
            run_id,
            {"message": "Something broke", "type": "ValueError"},
            step="generating",
        )

    failed = asyncio.run(_run())
    assert failed.status == RUN_STATUS_FAILED
    assert failed.error == {"message": "Something broke", "type": "ValueError"}
    assert failed.step == "generating"


def test_get_run_status() -> None:
    expected_id = uuid.uuid4()

    async def _run():
        fake_run = _FakeRun(id=expected_id)
        session = AsyncMock()
        session.get = AsyncMock(return_value=fake_run)

        return await get_run_status(session, expected_id)

    run = asyncio.run(_run())
    assert run is not None
    assert run.id == expected_id
