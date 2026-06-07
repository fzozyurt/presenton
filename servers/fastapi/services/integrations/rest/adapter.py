from __future__ import annotations

import logging
from collections.abc import Mapping

from services.integrations.dto import NormalizedDataSetDTO, ResolvedAdapterConfig
from services.integrations.http_client import HttpxHttpClient

LOGGER = logging.getLogger(__name__)


class RestDataAdapter:
    def __init__(self, http_client: HttpxHttpClient | None = None) -> None:
        self._http_client = http_client or HttpxHttpClient()

    @property
    def adapter_type(self) -> str:
        return "rest"

    async def fetch_normalized(self, request: ResolvedAdapterConfig) -> NormalizedDataSetDTO:
        config = request.config
        source_id = request.datasource_id

        raw_response = config.get("raw_response")
        if raw_response is not None and isinstance(raw_response, dict):
            return self._normalize_json(raw_response, request)

        url = str(config.get("url", "")).strip()
        if not url:
            raise ValueError("REST adapter requires 'url' in config or 'raw_response' for fixture mode.")

        method = str(config.get("method", "GET")).upper()
        headers_raw = config.get("headers")
        headers: dict[str, str] = {}
        if isinstance(headers_raw, dict):
            headers = {str(k): str(v) for k, v in headers_raw.items()}

        body = config.get("body")
        if isinstance(body, dict):
            body = {str(k): v for k, v in body.items()}

        if method == "POST":
            raw = await self._http_client.post_json(url, headers=headers, body=body)
        else:
            raw = await self._http_client.get_json(url, headers=headers)

        return self._normalize_json(raw, request)

    def _normalize_json(
        self,
        raw: dict[str, object],
        request: ResolvedAdapterConfig,
    ) -> NormalizedDataSetDTO:
        from services.integrations.builder import NormalizedDataSetBuilder, ParsedDataFrame, ParsedField
        from services.integrations.grafana.parser import _infer_fields_from_rows as infer

        rows: list[dict[str, object]] = []

        for list_key in ("data", "items", "results", "rows"):
            candidate = raw.get(list_key)
            if isinstance(candidate, list):
                for item in candidate:
                    if isinstance(item, dict):
                        rows.append({k: _flatten_value(v) for k, v in item.items()})
                break

        if not rows:
            rows = [{k: _flatten_value(v) for k, v in raw.items()}]

        if not rows:
            return NormalizedDataSetDTO(
                source_id=request.datasource_id,
                source_type=request.datasource_type,
                binding_id=request.binding_id,
                data_kind="table",
                metadata={"error": "No rows found in REST response"},
            )

        fields = infer(rows)
        frame = ParsedDataFrame(
            source_type=request.datasource_type,
            source_id=request.datasource_id,
            name="rest_response",
            fields=fields,
            rows=rows,
        )

        config = request.config
        return NormalizedDataSetBuilder().build(
            [frame],
            preferred_data_kind=_optional_str(config, "data_kind_hint"),
            visualization_hint=_optional_str(config, "visualization_hint"),
            row_limit=_optional_int(config, "row_limit"),
        )

    async def close(self) -> None:
        await self._http_client.close()


def _flatten_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, (int, float, bool, str)):
        return value
    if isinstance(value, (dict, list)):
        return None
    return str(value)


def _optional_str(config: Mapping[str, object], key: str) -> str | None:
    value = config.get(key)
    if isinstance(value, str):
        return value
    return None


def _optional_int(config: Mapping[str, object], key: str) -> int | None:
    value = config.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None

__all__ = ["RestDataAdapter"]
