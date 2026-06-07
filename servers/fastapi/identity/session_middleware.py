from fastapi import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from identity.provider import is_oidc_enabled
from identity.tokens import get_oidc_session_token_from_request, validate_oidc_session_token
from utils.get_env import is_disable_auth_enabled


class OIDCSessionMiddleware(BaseHTTPMiddleware):
    _EXEMPT_PREFIXES = (
        "/api/v1/auth/",
        "/api/v1/oidc/",
        "/docs",
        "/openapi.json",
        "/redoc",
    )
    _PROTECTED_NON_API_PATHS = {
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    def _is_exempt(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self._EXEMPT_PREFIXES)

    def _requires_auth(self, path: str) -> bool:
        if path.startswith("/api/"):
            return True
        if path.startswith("/app_data/images/"):
            return False
        if path.startswith("/app_data/"):
            return True
        return path in self._PROTECTED_NON_API_PATHS

    async def dispatch(self, request: Request, call_next):
        if not is_oidc_enabled() or is_disable_auth_enabled():
            return await call_next(request)

        path = request.url.path

        if (
            request.method == "OPTIONS"
            or not self._requires_auth(path)
            or self._is_exempt(path)
        ):
            return await call_next(request)

        token = get_oidc_session_token_from_request(request)
        payload = validate_oidc_session_token(token)

        if payload is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated"},
            )

        request.state.user = payload
        return await call_next(request)
