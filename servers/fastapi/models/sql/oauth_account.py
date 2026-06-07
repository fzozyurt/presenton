from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Column, DateTime, String, UniqueConstraint, ForeignKey
from sqlmodel import Field, SQLModel

from utils.datetime_utils import get_current_utc_datetime


class OAuthAccountModel(SQLModel, table=True):
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
    )

    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    user_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    )
    provider: str = Field(sa_column=Column(String(64), nullable=False))
    provider_user_id: str = Field(sa_column=Column(String(256), nullable=False))
    access_token: Optional[str] = Field(sa_column=Column(String(4096), nullable=True))
    refresh_token: Optional[str] = Field(sa_column=Column(String(4096), nullable=True))
    expires_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    id_token: Optional[str] = Field(sa_column=Column(String(8192), nullable=True))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=get_current_utc_datetime)
    )
