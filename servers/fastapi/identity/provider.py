"""Generic OpenID Connect (OIDC) Provider.

Works with any OIDC-compliant Identity Provider:
- Keycloak, Authentik, Authelia, Dex
- Azure Entra ID, Okta, Auth0
- Company Access Manager (OIDC-compliant)
"""
import asyncio
import json
import os
import secrets
import time
import urllib.parse
from typing import Optional

import aiohttp

from utils.oauth.pkce import generate_pkce


class OIDCProvider:
    """Generic OIDC Relying Party."""

    def __init__(self):
        self.issuer = os.getenv("OIDC_ISSUER", "").strip().rstrip("/")
        self.client_id = os.getenv("OIDC_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("OIDC_CLIENT_SECRET", "").strip()
        self.redirect_uri = os.getenv("OIDC_REDIRECT_URI", "").strip()
        self.scopes = os.getenv("OIDC_SCOPES", "openid profile email").strip()

        self._discovery: Optional[dict] = None

    @property
    def enabled(self) -> bool:
        return os.getenv("OIDC_ENABLED", "").strip().lower() in ("true", "1", "yes", "on")

    async def _discover(self) -> dict:
        if self._discovery is not None:
            return self._discovery

        url = f"{self.issuer}/.well-known/openid-configuration"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise ValueError(f"OIDC discovery failed ({resp.status}): {text}")
                self._discovery = await resp.json()
        return self._discovery

    async def get_authorization_url(self, state: Optional[str] = None) -> tuple[str, str, str]:
        """Generate PKCE-backed authorization URL.

        Returns (auth_url, state, code_verifier).
        """
        discovery = await self._discover()
        auth_endpoint = discovery["authorization_endpoint"]
        verifier, challenge = generate_pkce()

        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scopes,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }

        auth_url = f"{auth_endpoint}?{urllib.parse.urlencode(params)}"
        return auth_url, state, verifier

    async def exchange_code(self, code: str, code_verifier: str) -> dict:
        """Exchange authorization code for tokens.

        Returns token response dict with access_token, id_token, refresh_token, expires_in.
        """
        discovery = await self._discover()
        token_endpoint = discovery["token_endpoint"]

        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "code_verifier": code_verifier,
        }

        if self.client_secret:
            payload["client_secret"] = self.client_secret

        async with aiohttp.ClientSession() as session:
            async with session.post(
                token_endpoint,
                data=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise ValueError(f"Token exchange failed ({resp.status}): {text}")
                return await resp.json()

    async def refresh_token(self, refresh_token: str) -> dict:
        """Refresh an access token.

        Returns new token response dict.
        """
        discovery = await self._discover()
        token_endpoint = discovery["token_endpoint"]

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }

        if self.client_secret:
            payload["client_secret"] = self.client_secret

        async with aiohttp.ClientSession() as session:
            async with session.post(
                token_endpoint,
                data=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise ValueError(f"Token refresh failed ({resp.status}): {text}")
                return await resp.json()

    async def get_userinfo(self, access_token: str) -> dict:
        """Fetch user info from the OIDC userinfo endpoint.

        Returns user claims dict (sub, email, name, picture, etc.).
        """
        discovery = await self._discover()
        userinfo_endpoint = discovery.get("userinfo_endpoint")

        if not userinfo_endpoint:
            raise ValueError("OIDC provider does not have a userinfo endpoint")

        headers = {"Authorization": f"Bearer {access_token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                userinfo_endpoint,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise ValueError(f"Userinfo fetch failed ({resp.status}): {text}")
                return await resp.json()

    def get_logout_url(self, id_token_hint: Optional[str] = None) -> Optional[str]:
        """Get the end session URL if supported by the provider."""
        discovery = self._discovery
        if discovery is None:
            return None

        end_session_endpoint = discovery.get("end_session_endpoint")
        if not end_session_endpoint:
            return None

        params = {}
        if id_token_hint:
            params["id_token_hint"] = id_token_hint
        params["post_logout_redirect_uri"] = self.redirect_uri.rsplit("/", 1)[0]

        return f"{end_session_endpoint}?{urllib.parse.urlencode(params)}"


_oidc_provider: Optional[OIDCProvider] = None


def get_oidc_provider() -> OIDCProvider:
    global _oidc_provider
    if _oidc_provider is None:
        _oidc_provider = OIDCProvider()
    return _oidc_provider


def is_oidc_enabled() -> bool:
    return get_oidc_provider().enabled
