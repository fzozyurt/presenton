from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, String, ForeignKey, UniqueConstraint
from sqlmodel import Field, SQLModel

from utils.datetime_utils import get_current_utc_datetime


class WorkspaceMemberModel(SQLModel, table=True):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )

    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    workspace_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    )
    role: str = Field(sa_column=Column(String(64), nullable=False, default="viewer"))
    joined_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=get_current_utc_datetime)
    )
