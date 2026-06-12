import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from utils.datetime_utils import get_current_utc_datetime


class DeepAgentPresentationRunModel(SQLModel, table=True):
    __tablename__ = "deepagent_presentation_runs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    presentation_id: uuid.UUID = Field(index=True)
    thread_id: str = Field(index=True)
    user_id: Optional[str] = Field(default=None, index=True)

    status: str = Field(default="pending", index=True)
    step: Optional[str] = None
    message: Optional[str] = None

    auto_mode: bool = False
    memory_mode: str = "review"

    input_snapshot: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    output_snapshot: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    error: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=get_current_utc_datetime)
    updated_at: datetime = Field(default_factory=get_current_utc_datetime)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
