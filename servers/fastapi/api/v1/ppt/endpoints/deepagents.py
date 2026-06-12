from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from models.sql.deepagent_presentation_run import DeepAgentPresentationRunModel
from services.database import get_async_session
from services.deepagents.jobs import get_run_status

logger = logging.getLogger(__name__)

DEEPAGENTS_ROUTER = APIRouter(
    prefix="/presentation/deepagents",
    tags=["Deep Agents"],
)


class DeepAgentRunStatusResponse(BaseModel):
    run_id: str
    presentation_id: str
    thread_id: str
    status: str
    step: str | None = None
    message: str | None = None
    output_snapshot: dict | None = None
    error: dict | None = None


@DEEPAGENTS_ROUTER.get(
    "/status/{run_id}",
    response_model=DeepAgentRunStatusResponse,
)
async def get_deepagent_run_status(
    run_id: uuid.UUID,
    sql_session: AsyncSession = Depends(get_async_session),
):
    run = await get_run_status(sql_session, run_id)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail=f"Deep Agent run not found: {run_id}",
        )
    return DeepAgentRunStatusResponse(
        run_id=str(run.id),
        presentation_id=str(run.presentation_id),
        thread_id=run.thread_id,
        status=run.status,
        step=run.step,
        message=run.message,
        output_snapshot=run.output_snapshot,
        error=run.error,
    )
