from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Column, DateTime, String, ForeignKey
from sqlmodel import Field, SQLModel

from utils.datetime_utils import get_current_utc_datetime


class WorkspaceModel(SQLModel, table=True):
    __tablename__ = "workspaces"

    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    name: str = Field(sa_column=Column(String(255), nullable=False))
    slug: str = Field(sa_column=Column(String(255), unique=True, index=True, nullable=False))
    description: Optional[str] = Field(sa_column=Column(String(1024), nullable=True))
    created_by: uuid.UUID = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=get_current_utc_datetime)
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=get_current_utc_datetime,
            onupdate=get_current_utc_datetime,
        )
    )
