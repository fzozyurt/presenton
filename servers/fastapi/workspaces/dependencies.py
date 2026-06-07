import uuid

from fastapi import Depends, HTTPException, Request

from identity.tokens import get_oidc_session_token_from_request, validate_oidc_session_token
from identity.provider import is_oidc_enabled
from services.database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession


async def get_current_user_id_from_request(request: Request) -> uuid.UUID:
    if not is_oidc_enabled():
        raise HTTPException(status_code=400, detail="OIDC not enabled")

    token = get_oidc_session_token_from_request(request)
    payload = validate_oidc_session_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return uuid.UUID(payload["uid"])
