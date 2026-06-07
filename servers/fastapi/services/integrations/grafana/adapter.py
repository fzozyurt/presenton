from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

from services.integrations.dto import (
    NormalizedDataSetDTO,
    ResolvedAdapterConfig,
    TimeRangeForFetch,
)
from services.integrations.grafana.client import GrafanaQueryClient
from services.integrations.grafana.normalizer import GrafanaResponseNormalizer
from services.integrations.http_client import HttpxHttpClient

LOGGER = logging.getLogger(__name__)

_MOCK_DATA: dict[str, list[dict[str, object]]] = {
    "cpu": [
        {"timestamp": "2026-06-07T10:00:00Z", "service": "api-gateway", "metric": "p99_latency_ms", "value": 342, "threshold": 200},
        {"timestamp": "2026-06-07T10:00:00Z", "service": "api-gateway", "metric": "p50_latency_ms", "value": 45, "threshold": 100},
        {"timestamp": "2026-06-07T10:00:00Z", "service": "api-gateway", "metric": "error_rate_pct", "value": 2.3, "threshold": 1.0},
        {"timestamp": "2026-06-07T10:00:00Z", "service": "api-gateway", "metric": "throughput_rps", "value": 1840, "threshold": 2000},
        {"timestamp": "2026-06-07T10:01:00Z", "service": "user-service", "metric": "p99_latency_ms", "value": 128, "threshold": 200},
        {"timestamp": "2026-06-07T10:01:00Z", "service": "user-service", "metric": "error_rate_pct", "value": 0.5, "threshold": 1.0},
        {"timestamp": "2026-06-07T10:01:00Z", "service": "user-service", "metric": "cpu_pct", "value": 73.1, "threshold": 80.0},
        {"timestamp": "2026-06-07T10:02:00Z", "service": "postgres-primary", "metric": "connection_count", "value": 142, "threshold": 200},
        {"timestamp": "2026-06-07T10:02:00Z", "service": "cache-redis", "metric": "hit_rate_pct", "value": 94.2, "threshold": 95.0},
        {"timestamp": "2026-06-07T10:03:00Z", "service": "api-gateway", "metric": "p99_latency_ms", "value": 491, "threshold": 200},
        {"timestamp": "2026-06-07T10:03:00Z", "service": "api-gateway", "metric": "error_rate_pct", "value": 4.1, "threshold": 1.0},
        {"timestamp": "2026-06-07T10:03:00Z", "service": "api-gateway", "metric": "throughput_rps", "value": 2150, "threshold": 2000},
        {"timestamp": "2026-06-07T10:03:00Z", "service": "api-gateway", "metric": "circuit_breaker", "value": 1, "threshold": 0},
    ],
    "memory": [
        {"timestamp": "2026-06-07T10:00:00Z", "pod": "web-7d4f", "metric": "heap_used_mb", "value": 512, "limit": 1024},
        {"timestamp": "2026-06-07T10:00:00Z", "pod": "worker-a1", "metric": "heap_used_mb", "value": 890, "limit": 1024},
        {"timestamp": "2026-06-07T10:00:00Z", "pod": "worker-b2", "metric": "heap_used_mb", "value": 1001, "limit": 1024},
        {"timestamp": "2026-06-07T10:00:00Z", "pod": "worker-b2", "metric": "oom_killed_last_h", "value": 2, "limit": 0},
    ],
    "revenue": [
        {"quarter": "Q1 2026", "region": "North America", "revenue": 4_200_000, "growth_pct": 12.4, "churn_pct": 3.1},
        {"quarter": "Q1 2026", "region": "EMEA", "revenue": 2_800_000, "growth_pct": 8.7},
        {"quarter": "Q2 2026", "region": "North America", "revenue": 4_720_000, "growth_pct": 12.4},
        {"quarter": "Q2 2026", "region": "EMEA", "revenue": 3_100_000, "growth_pct": 10.7},
    ],
    "default": [
        {"timestamp": "2026-06-07T10:00:00Z", "metric": "active_users", "value": 15_432},
        {"timestamp": "2026-06-07T10:01:00Z", "metric": "active_users", "value": 16_001},
        {"timestamp": "2026-06-07T10:00:00Z", "metric": "error_rate_pct", "value": 1.2},
        {"timestamp": "2026-06-07T10:01:00Z", "metric": "error_rate_pct", "value": 1.8},
    ],
}

_MOCK_PANEL_META: dict[str, dict[str, object]] = {
    "cpu": {"panel_title": "API Gateway — Four Golden Signals", "panel_description": "Latency (p50/p99), error rate, throughput, and circuit breaker status for api-gateway and downstream services. SLO: p99 < 200ms, error rate < 1%.", "slo_p99_ms": 200, "slo_error_pct": 1.0},
    "memory": {"panel_title": "Kubernetes Pods — Memory Saturation", "panel_description": "Heap usage per pod with OOM kill counter. Worker pods should stay under 80% of 1024MB limit. OOM kills indicate memory pressure requiring investigation.", "memory_limit_mb": 1024},
    "revenue": {"panel_title": "Quarterly Revenue by Region", "panel_description": "Revenue growth and churn rate by region. QoQ growth target: > 10%. Churn should trend below 3%.", "growth_target_pct": 10.0},
    "default": {"panel_title": "System Overview", "panel_description": "General system metrics. Active user count and error rate overview."},
}


class GrafanaDataAdapter:
    def __init__(
        self,
        query_client: GrafanaQueryClient | None = None,
        http_client: HttpxHttpClient | None = None,
        normalizer: GrafanaResponseNormalizer | None = None,
    ) -> None:
        self._query_client = query_client
        self._http_client = http_client or HttpxHttpClient()
        self._normalizer = normalizer or GrafanaResponseNormalizer()

    @property
    def adapter_type(self) -> str:
        return "grafana"

    async def fetch_normalized(self, request: ResolvedAdapterConfig) -> NormalizedDataSetDTO:
        config = request.config
        source_id = request.datasource_id

        # ── Fixture / mock mode ──
        raw_response = config.get("raw_response")
        if raw_response is not None and isinstance(raw_response, dict):
            return self._normalize_fixture(raw_response, request)

        # ── Mock data from query keywords ──
        query_str = str(config.get("query", "")).strip().lower()
        panel_meta = _extract_panel_metadata(config)

        # ── Mock data from query keywords ──
        mock_data = self._match_mock_data(query_str)
        if mock_data is not None:
            LOGGER.info("Grafana: using mock data for query=%r", query_str)
            return self._normalize_mock_rows(mock_data, request, panel_meta)

        # ── Real HTTP mode ──
        base_url = str(config.get("base_url", "")).strip()
        if not base_url:
            raise ValueError("Grafana base_url is required for HTTP mode. Provide it in config or use raw_response for fixture mode.")

        queries = self._resolve_queries(config)
        if not queries:
            queries = [{"refId": "A", "expr": query_str or "1+1"}]

        time_range = request.time_range or self._default_time_range()

        client = self._query_client or GrafanaQueryClient(self._http_client)
        raw = await client.query_datasource(
            base_url=base_url,
            datasource_uid=str(config.get("datasource_uid", "") or ""),
            queries=[dict(q) for q in queries],
            time_range=time_range,
            interval_ms=_optional_int(config, "interval_ms"),
            max_data_points=_optional_int(config, "max_data_points"),
        )

        row_limit = _optional_int(config, "row_limit")
        dataset = self._normalizer.normalize(
            raw,
            source_id=source_id,
            binding_id=request.binding_id,
            datasource_type=request.datasource_type,
            preferred_data_kind=_optional_str(config, "data_kind_hint"),
            visualization_hint=_optional_str(config, "visualization_hint"),
            row_limit=row_limit,
        )
        if panel_meta:
            dataset.metadata["panel"] = panel_meta
        return dataset

    @staticmethod
    def _match_mock_data(query: str) -> list[dict[str, object]] | None:
        if not query:
            return None
        for keyword, data in _MOCK_DATA.items():
            if keyword in query:
                return data
        if any(w in query for w in ("cpu", "latency", "response", "load")):
            return _MOCK_DATA["cpu"]
        if any(w in query for w in ("memory", "ram", "heap")):
            return _MOCK_DATA["memory"]
        if any(w in query for w in ("revenue", "sales", "profit", "growth")):
            return _MOCK_DATA["revenue"]
        return None

    @staticmethod
    def _match_mock_meta(query: str) -> dict[str, object] | None:
        if not query:
            return _MOCK_PANEL_META.get("default")
        for keyword, meta in _MOCK_PANEL_META.items():
            if keyword in query:
                return meta
        if any(w in query for w in ("cpu", "latency", "response", "load")):
            return _MOCK_PANEL_META["cpu"]
        if any(w in query for w in ("memory", "ram", "heap")):
            return _MOCK_PANEL_META["memory"]
        if any(w in query for w in ("revenue", "sales", "profit", "growth")):
            return _MOCK_PANEL_META["revenue"]
        return _MOCK_PANEL_META.get("default")

    def _normalize_mock_rows(
        self,
        rows: list[dict[str, object]],
        request: ResolvedAdapterConfig,
        panel_meta: dict[str, object] | None = None,
    ) -> NormalizedDataSetDTO:
        from services.integrations.builder import ParsedDataFrame, ParsedField
        from services.integrations.grafana.parser import _infer_fields_from_rows as infer

        fields = infer(rows)
        frame = ParsedDataFrame(
            source_type=request.datasource_type,
            source_id=request.datasource_id,
            name="mock",
            fields=fields,
            rows=rows,
        )
        row_limit = _optional_int(request.config, "row_limit")
        dataset = self._normalizer._builder.build(
            [frame],
            preferred_data_kind=_optional_str(request.config, "data_kind_hint"),
            visualization_hint=_optional_str(request.config, "visualization_hint"),
            row_limit=row_limit,
        )
        if panel_meta:
            dataset.metadata["panel"] = panel_meta
        return dataset

    def _normalize_fixture(
        self,
        raw: dict[str, object],
        request: ResolvedAdapterConfig,
    ) -> NormalizedDataSetDTO:
        row_limit = _optional_int(request.config, "row_limit")
        return self._normalizer.normalize(
            raw,
            source_id=request.datasource_id,
            binding_id=request.binding_id,
            datasource_type=request.datasource_type,
            preferred_data_kind=_optional_str(request.config, "data_kind_hint"),
            visualization_hint=_optional_str(request.config, "visualization_hint"),
            row_limit=row_limit,
        )

    @staticmethod
    def _resolve_queries(config: Mapping[str, object]) -> list[Mapping[str, object]]:
        queries = config.get("queries")
        if isinstance(queries, list) and queries and all(isinstance(q, dict) for q in queries):
            return queries
        panel_queries = config.get("panel_query_models")
        if isinstance(panel_queries, list) and panel_queries and all(isinstance(q, dict) for q in panel_queries):
            return panel_queries
        return []

    @staticmethod
    def _default_time_range() -> TimeRangeForFetch:
        now = datetime.now(UTC)
        return TimeRangeForFetch(start=now - timedelta(hours=1), end=now)


def _extract_panel_metadata(config: Mapping[str, object]) -> dict[str, object] | None:
    """Extract panel metadata from config (title, description, SLO thresholds)."""
    panel = dict(config.get("panel_meta", {}) or {})
    if not panel:
        query_str = str(config.get("query", "")).strip().lower()
        panel = GrafanaDataAdapter._match_mock_meta(query_str) or {}
    if not panel:
        return None

    return {
        "panel_title": str(panel.get("panel_title", "")),
        "panel_description": str(panel.get("panel_description", "")),
        "slo_targets": {
            k: v for k, v in panel.items()
            if k.startswith("slo_") or k.endswith("_target") or k.endswith("_limit")
        },
    }

    async def close(self) -> None:
        if self._query_client:
            await self._query_client.close()
        await self._http_client.close()


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

__all__ = ["GrafanaDataAdapter"]
