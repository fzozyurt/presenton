from typing import Optional
import uuid

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: Optional[str] = Field(default=None, max_length=1024)


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1024)


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    created_by: str
    created_at: str
    updated_at: str


class WorkspaceMemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    user_email: str
    user_avatar: Optional[str] = None
    role: str
    joined_at: str


class MemberCreate(BaseModel):
    email: str
    role: str = "editor"


class MemberUpdate(BaseModel):
    role: str
