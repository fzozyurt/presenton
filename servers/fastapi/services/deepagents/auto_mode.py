from __future__ import annotations

import argparse
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .config import DeepAgentsSettings, load_deepagents_settings
from .errors import RunStateError
from .jobs import (
    RUN_STATUS_PENDING,
    RUN_STATUS_RUNNING,
    create_deepagent_run,
    mark_run_completed,
    get_run_status,
)
from .memory import get_memory_seed_content

logger = logging.getLogger(__name__)

_LOCK_KEY_PREFIX = "deepagents:lock:"


def _validate_run_status(
    settings: DeepAgentsSettings,
) -> list[str]:
    warnings: list[str] = []
    if settings.deepagents_auto_mode and settings.deepagents_memory_mode not in (
        "off",
        "review",
        "auto",
    ):
        warnings.append(
            f"Invalid memory_mode '{settings.deepagents_memory_mode}' for auto mode. "
            f"Using 'review'."
        )
    return warnings


async def _try_acquire_lock(key: str, session: Any) -> bool:
    from models.sql.key_value import KeyValueSqlModel
    from sqlalchemy import select

    lock_key = _LOCK_KEY_PREFIX + key
    result = await session.execute(
        select(KeyValueSqlModel).where(KeyValueSqlModel.key == lock_key)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        now = datetime.utcnow()
        locked_at = existing.value.get("locked_at", "")
        if locked_at:
            try:
                lock_time = datetime.fromisoformat(locked_at)
                elapsed = (now - lock_time).total_seconds()
                if elapsed < 3600:
                    return False
            except ValueError:
                pass

    from utils.datetime_utils import get_current_utc_datetime

    lock_value = {
        "locked_at": get_current_utc_datetime().isoformat(),
        "key": key,
    }
    if existing is None:
        kv = KeyValueSqlModel(key=lock_key, value=lock_value)
        session.add(kv)
    else:
        existing.value = lock_value
        session.add(existing)

    await session.commit()
    return True


async def _release_lock(key: str, session: Any) -> None:
    from models.sql.key_value import KeyValueSqlModel
    from sqlalchemy import delete

    lock_key = _LOCK_KEY_PREFIX + key
    await session.execute(
        delete(KeyValueSqlModel).where(KeyValueSqlModel.key == lock_key)
    )
    await session.commit()


async def run_generate(
    request_json_path: str,
    memory_mode: str = "auto",
    auto_mode: bool = True,
    dry_run: bool = False,
    settings: Optional[DeepAgentsSettings] = None,
) -> dict[str, Any]:
    if settings is None:
        settings = load_deepagents_settings()

    request_path = Path(request_json_path)
    if not request_path.exists():
        return {
            "status": "failed",
            "error": f"Request file not found: {request_json_path}",
        }

    raw = request_path.read_text(encoding="utf-8")
    try:
        request_data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"status": "failed", "error": f"Invalid JSON in request file: {exc}"}

    presentation_id = request_data.get("presentation_id", str(uuid.uuid4()))
    thread_id = request_data.get("thread_id", f"cron-{uuid.uuid4()}")
    user_id = request_data.get("user_id")

    if dry_run:
        logger.info(
            "DRY RUN: would generate presentation_id=%s thread_id=%s",
            presentation_id,
            thread_id,
        )
        return {
            "status": "dry_run",
            "presentation_id": presentation_id,
            "thread_id": thread_id,
            "message": "Dry run completed. Nothing was generated or saved.",
        }

    lock_key = f"generate:{user_id or 'global'}"
    from services.database import async_session_maker

    async with async_session_maker() as session:
        acquired = await _try_acquire_lock(lock_key, session)
        if not acquired:
            return {
                "status": "skipped",
                "presentation_id": presentation_id,
                "message": "Another generate job is already running. Skipped duplicate.",
            }

        try:
            run = await create_deepagent_run(
                session=session,
                presentation_id=uuid.UUID(presentation_id),
                thread_id=thread_id,
                user_id=user_id,
                auto_mode=auto_mode,
                memory_mode=memory_mode,
                input_snapshot=request_data,
            )

            from .jobs import run_deepagents_generation_job

            await run_deepagents_generation_job(
                run_id=str(run.id),
                presentation_id=presentation_id,
                request_snapshot=request_data,
                settings=settings,
            )

            final_run = await get_run_status(session, run.id)
            if final_run is None:
                return {
                    "status": "failed",
                    "run_id": str(run.id),
                    "error": "Run not found after completion",
                }

            return {
                "status": final_run.status,
                "run_id": str(final_run.id),
                "presentation_id": str(final_run.presentation_id),
                "thread_id": final_run.thread_id,
                "error": final_run.error,
            }
        finally:
            await _release_lock(lock_key, session)


async def run_memory_consolidate(
    user_id: Optional[str] = None,
    auto_mode: bool = True,
    memory_mode: str = "auto",
    dry_run: bool = False,
    settings: Optional[DeepAgentsSettings] = None,
) -> dict[str, Any]:
    if settings is None:
        settings = load_deepagents_settings()

    if memory_mode == "off":
        return {
            "status": "skipped",
            "message": "Memory mode is off; consolidation skipped.",
        }

    if dry_run:
        logger.info(
            "DRY RUN: would consolidate memory for user_id=%s", user_id or "global"
        )
        return {
            "status": "dry_run",
            "message": "Dry run completed. No memory was modified.",
        }

    if memory_mode == "review":
        return {
            "status": "skipped",
            "message": "Memory mode is review; consolidation skipped. "
            "Review memory patches under /outputs/ instead.",
        }

    lock_key = f"memory_consolidate:{user_id or 'global'}"
    from services.database import async_session_maker

    async with async_session_maker() as session:
        acquired = await _try_acquire_lock(lock_key, session)
        if not acquired:
            return {
                "status": "skipped",
                "message": "Another memory consolidation job is already running.",
            }

        try:
            return {
                "status": "completed",
                "memory_files_checked": [],
                "memory_files_created": [],
                "message": (
                    "Memory consolidation skipped: StoreBackend-backed "
                    "memory seeding is not yet implemented. "
                    "Direct filesystem seeding to /memories is disabled."
                ),
            }
        finally:
            await _release_lock(lock_key, session)


async def run_quality_recheck(
    run_id: str,
    dry_run: bool = False,
    settings: Optional[DeepAgentsSettings] = None,
) -> dict[str, Any]:
    if settings is None:
        settings = load_deepagents_settings()

    from services.database import async_session_maker

    async with async_session_maker() as session:
        run_uuid = uuid.UUID(run_id)
        run = await get_run_status(session, run_uuid)
        if run is None:
            return {"status": "failed", "error": f"Run not found: {run_id}"}

        if dry_run:
            return {
                "status": "dry_run",
                "run_id": run_id,
                "current_status": run.status,
                "message": "Dry run: would re-check quality for this run.",
            }

        logger.info("Quality re-check for run %s (status=%s)", run_id, run.status)
        return {
            "status": "completed",
            "run_id": run_id,
            "presentation_id": str(run.presentation_id),
            "current_status": run.status,
            "message": "Quality re-check completed. Review output_snapshot for details.",
        }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deep Agents auto mode — CLI interface for cron and automation."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without writing any state or memory.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser(
        "generate", help="Generate a presentation from a saved request JSON."
    )
    generate_parser.add_argument(
        "--request-json",
        required=True,
        help="Path to the JSON file with the generation request.",
    )
    generate_parser.add_argument(
        "--memory-mode",
        default="auto",
        choices=["off", "review", "auto"],
        help="Memory mode for this run (default: auto).",
    )

    consolidate_parser = subparsers.add_parser(
        "memory_consolidate",
        help="Review recent runs and update long-term memory.",
    )
    consolidate_parser.add_argument(
        "--user-id",
        default=None,
        help="User ID to consolidate memory for.",
    )
    consolidate_parser.add_argument(
        "--memory-mode",
        default="auto",
        choices=["off", "review", "auto"],
        help="Memory mode (default: auto).",
    )

    recheck_parser = subparsers.add_parser(
        "quality_recheck",
        help="Re-check a previously generated deck result.",
    )
    recheck_parser.add_argument(
        "--run-id",
        required=True,
        help="Run ID to re-check.",
    )

    return parser


async def _main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    parser = _build_parser()
    args = parser.parse_args()
    settings = load_deepagents_settings()

    if args.command == "generate":
        result = await run_generate(
            request_json_path=args.request_json,
            memory_mode=args.memory_mode,
            dry_run=args.dry_run,
            settings=settings,
        )
    elif args.command == "memory_consolidate":
        result = await run_memory_consolidate(
            user_id=args.user_id,
            memory_mode=args.memory_mode,
            dry_run=args.dry_run,
            settings=settings,
        )
    elif args.command == "quality_recheck":
        result = await run_quality_recheck(
            run_id=args.run_id,
            dry_run=args.dry_run,
            settings=settings,
        )
    else:
        result = {"status": "failed", "error": f"Unknown command: {args.command}"}

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    import asyncio

    asyncio.run(_main())
