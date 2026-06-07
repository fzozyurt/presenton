from __future__ import annotations

import logging
from typing import Any

import httpx

from services.integrations.ports import HttpClientPort

LOGGER = logging.getLogger(__name__)


class HttpxHttpClient:
    def __init__(self, timeout: float = 30.0):
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: dict[str, object] | None = None,
        auth: tuple[str, str] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, object]:
        client = await self._ensure_client()
        LOGGER.debug("POST %s", url)
        response = await client.post(
            url,
            headers=headers,
            json=body,
            auth=auth,
            timeout=timeout,
        )
        response.raise_for_status()
        data: Any = response.json()
        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object, got {type(data).__name__}")
        return data

    async def get_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        auth: tuple[str, str] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, object]:
        client = await self._ensure_client()
        LOGGER.debug("GET %s", url)
        response = await client.get(
            url,
            headers=headers,
            auth=auth,
            timeout=timeout,
        )
        response.raise_for_status()
        data: Any = response.json()
        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object, got {type(data).__name__}")
        return data

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
