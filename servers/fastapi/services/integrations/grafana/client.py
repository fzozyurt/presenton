from __future__ import annotations

import logging
from collections.abc import Mapping

from services.integrations.dto import TimeRangeForFetch
from services.integrations.http_client import HttpxHttpClient

LOGGER = logging.getLogger(__name__)


class GrafanaQueryClient:
    def __init__(self, http_client: HttpxHttpClient | None = None):
        self._http = http_client or HttpxHttpClient()

    async def query_datasource(
        self,
        *,
        base_url: str,
        headers: Mapping[str, str] | None = None,
        datasource_uid: str | None = None,
        queries: list[Mapping[str, object]],
        time_range: TimeRangeForFetch,
        interval_ms: int | None = None,
        max_data_points: int | None = None,
        auth: tuple[str, str] | None = None,
    ) -> Mapping[str, object]:
        url = f"{base_url.rstrip('/')}/api/ds/query"

        from datetime import UTC, datetime

        def _to_epoch_ms(dt: datetime) -> int:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return int(dt.timestamp() * 1000)

        payload: dict[str, object] = {
            "queries": [dict(q) for q in queries],
            "from": str(_to_epoch_ms(time_range.start) if time_range.start else _to_epoch_ms(datetime.now(UTC))),
            "to": str(_to_epoch_ms(time_range.end) if time_range.end else _to_epoch_ms(datetime.now(UTC))),
        }
        if interval_ms is not None:
            payload["intervalMs"] = interval_ms
        if max_data_points is not None:
            payload["maxDataPoints"] = max_data_points

        return await self._http.post_json(
            url,
            headers=dict(headers) if headers else None,
            body=payload,
            auth=auth,
        )

    async def get_dashboard(
        self,
        *,
        base_url: str,
        headers: Mapping[str, str] | None = None,
        dashboard_uid: str,
        auth: tuple[str, str] | None = None,
    ) -> Mapping[str, object]:
        url = f"{base_url.rstrip('/')}/api/dashboards/uid/{dashboard_uid}"
        return await self._http.get_json(
            url,
            headers=dict(headers) if headers else None,
            auth=auth,
        )

    async def close(self) -> None:
        await self._http.close()
