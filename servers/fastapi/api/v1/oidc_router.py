from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, RedirectResponse

from identity.provider import get_oidc_provider, is_oidc_enabled
from identity.schemas import OIDCAuthStatus, UserProfile
from identity.service import get_or_create_user_by_oidc, get_user_by_id, user_to_profile
from identity.tokens import (
    OIDC_SESSION_COOKIE,
    OIDC_SESSION_TTL,
    clear_oidc_session_cookie,
    create_oidc_session_token,
    get_oidc_session_token_from_request,
    set_oidc_session_cookie,
    validate_oidc_session_token,
)
from services.database import get_async_session

OIDC_ROUTER = APIRouter(prefix="/api/v1/oidc", tags=["OIDC"])

_STATE_STORE: dict[str, str] = {}


@OIDC_ROUTER.get("/status")
async def get_oidc_status(request: Request, session: AsyncSession = Depends(get_async_session)):
    if not is_oidc_enabled():
        return {"provider": "oidc", "configured": False, "authenticated": False, "user": None}

    token = get_oidc_session_token_from_request(request)
    payload = validate_oidc_session_token(token)

    if payload is not None:
        user = await get_user_by_id(session, payload["uid"])
        profile = user_to_profile(user) if user else None
        return {
            "provider": "oidc",
            "configured": True,
            "authenticated": True,
            "user": profile.model_dump() if profile else None,
        }

    return {"provider": "oidc", "configured": True, "authenticated": False, "user": None}


@OIDC_ROUTER.get("/login")
async def oidc_login():
    if not is_oidc_enabled():
        raise HTTPException(status_code=400, detail="OIDC is not enabled")

    provider = get_oidc_provider()
    auth_url, state, verifier = await provider.get_authorization_url()
    _STATE_STORE[state] = verifier

    return RedirectResponse(url=auth_url, status_code=302)


@OIDC_ROUTER.get("/callback")
async def oidc_callback(
    request: Request,
    code: str,
    state: str,
    session: AsyncSession = Depends(get_async_session),
):
    if not is_oidc_enabled():
        raise HTTPException(status_code=400, detail="OIDC is not enabled")

    verifier = _STATE_STORE.pop(state, None)
    if verifier is None:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    provider = get_oidc_provider()

    try:
        token_response = await provider.exchange_code(code, verifier)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}")

    access_token = token_response.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token in response")

    try:
        userinfo = await provider.get_userinfo(access_token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Userinfo fetch failed: {str(e)}")

    provider_user_id = userinfo.get("sub")
    if not provider_user_id:
        raise HTTPException(status_code=400, detail="No sub claim in userinfo")

    email = userinfo.get("email")
    name = userinfo.get("name") or userinfo.get("preferred_username") or email or provider_user_id
    avatar_url = userinfo.get("picture")
    id_token = token_response.get("id_token")
    refresh_token = token_response.get("refresh_token")
    expires_in = token_response.get("expires_in")

    try:
        user, created = await get_or_create_user_by_oidc(
            session=session,
            provider="oidc",
            provider_user_id=provider_user_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
            access_token=access_token,
            refresh_token=refresh_token,
            id_token=id_token,
            expires_in=expires_in,
        )
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"User creation failed: {str(e)}")

    session_token = create_oidc_session_token(
        user_id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_admin=user.is_admin,
    )

    response = RedirectResponse(url="/upload", status_code=302)
    set_oidc_session_cookie(response, session_token, request)
    return response


@OIDC_ROUTER.post("/logout")
async def oidc_logout(request: Request):
    token = get_oidc_session_token_from_request(request)
    payload = validate_oidc_session_token(token)

    logout_url = None
    if payload:
        provider = get_oidc_provider()
        if is_oidc_enabled():
            try:
                await provider._discover()
                logout_url = provider.get_logout_url()
            except Exception:
                pass

    response = JSONResponse({"success": True})
    clear_oidc_session_cookie(response, request)

    if logout_url:
        return RedirectResponse(url=logout_url, status_code=302)

    return response
