from __future__ import annotations


class AdapterSchemaProvider:
    """Provides config schemas for each adapter type, consumable by LLM Agent."""

    _schemas: dict[str, dict[str, object]] = {
        "grafana": {
            "adapter_type": "grafana",
            "description": "Fetches time-series and panel data from Grafana dashboards via the Grafana HTTP API.",
            "required_config": ["base_url"],
            "optional_config": [
                "datasource_uid", "dashboard_uid", "panel_id",
                "queries", "interval_ms", "max_data_points",
                "data_kind_hint", "visualization_hint", "row_limit",
            ],
            "fixture_mode": "Pass raw_response in config to use mock data instead of real HTTP calls.",
            "query_formats": {
                "dashboard_uid": "string — Grafana dashboard UID",
                "panel_id": "integer — Panel ID within the dashboard",
                "queries": "list of dicts — Grafana query objects with refId, expr, etc.",
                "expr": "string — PromQL or Grafana query expression",
            },
            "supports": ["time_series", "categorical", "table", "single_value", "multi_value"],
        },
        "rest": {
            "adapter_type": "rest",
            "description": "Fetches structured data from any REST API endpoint returning JSON.",
            "required_config": ["url"],
            "optional_config": [
                "method", "headers", "body",
                "data_kind_hint", "visualization_hint", "row_limit",
            ],
            "fixture_mode": "Pass raw_response in config to use inline JSON instead of real HTTP calls.",
            "query_formats": {
                "url": "string — Full HTTP/HTTPS endpoint URL",
                "method": "string — HTTP method (GET or POST, default GET)",
                "headers": "dict — HTTP headers to send",
                "body": "dict — JSON body for POST requests",
            },
            "supports": ["table", "categorical", "single_value", "multi_value", "text"],
        },
        "prometheus": {
            "adapter_type": "prometheus",
            "description": "Fetches metrics from Prometheus via PromQL queries. Currently routes through REST adapter.",
            "required_config": ["url"],
            "optional_config": ["query", "time_range", "step", "row_limit"],
            "note": "Routes through REST adapter. Pass PromQL in query field.",
            "supports": ["time_series", "single_value"],
        },
        "d_database": {
            "adapter_type": "d_database",
            "description": "Fetches data from D database via SQL/qSQL queries. Routes through REST adapter.",
            "required_config": ["url"],
            "optional_config": ["query", "row_limit"],
            "note": "Routes through REST adapter. Pass SQL/qSQL in query field.",
            "supports": ["table", "categorical", "single_value"],
        },
    }

    @classmethod
    def get_schema(cls, adapter_type: str) -> dict[str, object] | None:
        return cls._schemas.get(adapter_type.lower())

    @classmethod
    def list_all(cls) -> list[dict[str, object]]:
        return list(cls._schemas.values())

    @classmethod
    def get_agent_catalog(cls) -> str:
        """Build a compact catalog of all adapters for LLM Agent consumption."""
        lines = ["AVAILABLE DATA SOURCE ADAPTERS:", "=" * 40]
        for atype, schema in cls._schemas.items():
            desc = schema.get("description", "")
            required = schema.get("required_config", [])
            optional = schema.get("optional_config", [])
            supports = schema.get("supports", [])
            lines.append(f"\n[{atype}]")
            lines.append(f"  {desc}")
            lines.append(f"  Required: {', '.join(required)}")
            if optional:
                lines.append(f"  Optional: {', '.join(optional)}")
            lines.append(f"  Data shapes: {', '.join(supports)}")

            note = schema.get("note")
            if note:
                lines.append(f"  Note: {note}")
            fixture = schema.get("fixture_mode")
            if fixture:
                lines.append(f"  Fixture: {fixture}")

        return "\n".join(lines)

__all__ = ["AdapterSchemaProvider"]
