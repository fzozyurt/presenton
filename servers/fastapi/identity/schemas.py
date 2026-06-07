from typing import Optional
import uuid

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    avatar_url: Optional[str] = None


class UserProfile(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    avatar_url: Optional[str] = None
    is_admin: bool = False
    is_active: bool = True


class OIDCAuthStatus(BaseModel):
    configured: bool = True
    authenticated: bool
    provider: str = "oidc"
    user: Optional[UserProfile] = None


class OIDCLoginResponse(BaseModel):
    auth_url: str


class OIDCTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None


class WorkspaceInfo(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    role: str
