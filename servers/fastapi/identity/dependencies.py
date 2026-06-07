from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from identity.provider import is_oidc_enabled
from identity.service import get_user_by_id, user_to_profile
from identity.tokens import validate_oidc_session_token, get_oidc_session_token_from_request
from services.database import get_async_session


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> Optional[dict]:
    """Extract and validate the current OIDC-authenticated user.

    Returns user dict or raises 401 if not authenticated.
    Only activates when OIDC is enabled.
    """
    if not is_oidc_enabled():
        return None

    token = get_oidc_session_token_from_request(request)
    payload = validate_oidc_session_token(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return payload


async def get_optional_user(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> Optional[dict]:
    """Extract current user without raising on missing auth."""
    if not is_oidc_enabled():
        return None

    token = get_oidc_session_token_from_request(request)
    return validate_oidc_session_token(token)


async def require_user(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Get current authenticated user or raise 401."""
    user = await get_current_user(request, session)
    if user is None and is_oidc_enabled():
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user or {}
