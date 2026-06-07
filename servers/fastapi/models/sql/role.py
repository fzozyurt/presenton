from typing import Optional
import uuid

from sqlalchemy import JSON, Column, String
from sqlmodel import Field, SQLModel


class RoleModel(SQLModel, table=True):
    __tablename__ = "roles"

    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    name: str = Field(sa_column=Column(String(64), unique=True, index=True, nullable=False))
    description: Optional[str] = Field(sa_column=Column(String(512), nullable=True))
    permissions: list[str] = Field(sa_column=Column(JSON, nullable=False, default=list))
