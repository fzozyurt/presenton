import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional

from fastapi import Request

OIDC_SESSION_COOKIE = "presenton_oidc_session"
OIDC_SESSION_TTL = 60 * 60 * 24 * 30  # 30 days


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8"))


def _get_oidc_session_secret() -> str:
    secret = _get_or_create_session_secret()
    return secret


_SESSION_SECRET = None


def _get_or_create_session_secret() -> str:
    global _SESSION_SECRET
    if _SESSION_SECRET is not None:
        return _SESSION_SECRET

    import os
    secret = os.getenv("OIDC_SESSION_SECRET")
    if not secret:
        # Fall back to AUTH_SECRET_KEY from user config, or generate a random one
        from utils.get_env import get_user_config_path_env
        from utils.user_config_store import read_user_config_file

        config_path = get_user_config_path_env()
        config = read_user_config_file(config_path) if config_path else {}
        secret = config.get("AUTH_SECRET_KEY")

        if not secret:
            secret = _base64url_encode(secrets.token_bytes(32))

        os.environ["OIDC_SESSION_SECRET"] = secret

    _SESSION_SECRET = secret
    return secret


def _sign_payload(payload_encoded: str, secret: str) -> str:
    signature = hmac.new(
        secret.encode("utf-8"), payload_encoded.encode("utf-8"), hashlib.sha256
    ).digest()
    return _base64url_encode(signature)


def create_oidc_session_token(
    user_id: str,
    email: str,
    name: str,
    avatar_url: Optional[str] = None,
    is_admin: bool = False,
) -> str:
    secret = _get_oidc_session_secret()
    issued_at = int(time.time())

    payload = {
        "v": 1,
        "uid": user_id,
        "email": email,
        "name": name,
        "avatar": avatar_url,
        "admin": is_admin,
        "iat": issued_at,
        "exp": issued_at + OIDC_SESSION_TTL,
    }

    payload_encoded = _base64url_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signature_encoded = _sign_payload(payload_encoded, secret)
    return f"{payload_encoded}.{signature_encoded}"


def validate_oidc_session_token(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None

    secret = _get_oidc_session_secret()
    if not secret:
        return None

    try:
        payload_encoded, signature_encoded = token.split(".", 1)
    except ValueError:
        return None

    expected_signature = _sign_payload(payload_encoded, secret)
    if not hmac.compare_digest(signature_encoded, expected_signature):
        return None

    try:
        payload_raw = _base64url_decode(payload_encoded)
        payload = json.loads(payload_raw)
    except Exception:
        return None

    if payload.get("v") != 1:
        return None

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(time.time()):
        return None

    return payload


def get_oidc_session_token_from_request(request: Request) -> Optional[str]:
    cookie_token = request.cookies.get(OIDC_SESSION_COOKIE)
    if cookie_token:
        return cookie_token

    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip() or None

    return None


def set_oidc_session_cookie(response, token: str, request: Request) -> None:
    from starlette.responses import Response

    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    secure = forwarded_proto.lower() == "https" or request.url.scheme == "https"

    response.set_cookie(
        key=OIDC_SESSION_COOKIE,
        value=token,
        max_age=OIDC_SESSION_TTL,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )


def clear_oidc_session_cookie(response, request: Request) -> None:
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    secure = forwarded_proto.lower() == "https" or request.url.scheme == "https"

    response.delete_cookie(
        key=OIDC_SESSION_COOKIE,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
