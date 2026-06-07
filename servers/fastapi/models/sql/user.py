from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Column, DateTime, String, Boolean as SaBoolean
from sqlmodel import Field, SQLModel

from utils.datetime_utils import get_current_utc_datetime


class UserModel(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    email: str = Field(sa_column=Column(String(320), unique=True, index=True, nullable=False))
    name: str = Field(sa_column=Column(String(255), nullable=False))
    hashed_password: Optional[str] = Field(sa_column=Column(String(256), nullable=True))
    is_active: bool = Field(sa_column=Column(SaBoolean, nullable=False, default=True))
    is_admin: bool = Field(sa_column=Column(SaBoolean, nullable=False, default=False))
    avatar_url: Optional[str] = Field(sa_column=Column(String(2048), nullable=True))
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
