from __future__ import annotations

import logging
from collections.abc import Mapping

from services.integrations.builder import ParsedDataFrame, ParsedField

LOGGER = logging.getLogger(__name__)


class GrafanaFrameParser:
    def parse(
        self,
        raw: Mapping[str, object],
        *,
        source_id: str,
        source_type: str = "grafana",
    ) -> list[ParsedDataFrame]:
        result_key: str | None = None
        frames_raw: object = None

        for key in ("results", "data"):
            candidate = raw.get(key)
            if candidate is not None:
                result_key = key
                frames_raw = candidate
                break

        if frames_raw is None:
            frames = raw.get("frames")
            if isinstance(frames, list):
                return self._parse_frame_list(frames, source_id, source_type)
            return self._fallback_parse(raw, source_id, source_type)

        return self._parse_nested_response(frames_raw, source_id, source_type)

    def _parse_nested_response(
        self,
        data: object,
        source_id: str,
        source_type: str,
    ) -> list[ParsedDataFrame]:
        frames_raw: object = None

        if isinstance(data, dict):
            for key in ("frames", "results", "series"):
                candidate = data.get(key)
                if isinstance(candidate, list) and candidate:
                    frames_raw = candidate
                    break
            if frames_raw is None:
                for key, value in data.items():
                    if isinstance(value, list) and value:
                        if all(isinstance(v, dict) and ("schema" in v or "fields" in v) for v in value[:1]):
                            frames_raw = value
                            break

        if isinstance(data, list):
            if all(isinstance(v, dict) for v in data[:1]):
                first = data[0]
                if "schema" in first or "fields" in first:
                    frames_raw = data

        if frames_raw is None and isinstance(data, dict):
            return self._fallback_parse(data, source_id, source_type)

        if isinstance(frames_raw, list):
            return self._parse_frame_list(frames_raw, source_id, source_type)

        return []

    def _parse_frame_list(
        self,
        frames: list[object],
        source_id: str,
        source_type: str,
    ) -> list[ParsedDataFrame]:
        result: list[ParsedDataFrame] = []
        for i, frame in enumerate(frames):
            if not isinstance(frame, dict):
                continue

            parsed = self._parse_single_frame(frame, source_id, source_type, i)
            if parsed and parsed.rows:
                result.append(parsed)
        return result

    def _parse_single_frame(
        self,
        frame: dict[str, object],
        source_id: str,
        source_type: str,
        index: int,
    ) -> ParsedDataFrame | None:
        schema = frame.get("schema")
        if not isinstance(schema, dict):
            return None

        fields_raw = schema.get("fields")
        if not isinstance(fields_raw, list):
            return None

        parsed_fields: list[ParsedField] = []
        for f in fields_raw:
            if isinstance(f, dict):
                name = str(f.get("name", ""))
                data_type = str(f.get("type", "string"))
                unit = str(f["unit"]) if f.get("unit") and isinstance(f["unit"], str) else None
                if name:
                    parsed_fields.append(ParsedField(name=name, data_type=data_type, unit=unit))

        data_block = frame.get("data")
        if not isinstance(data_block, dict):
            return None

        values_block = data_block.get("values")
        if not isinstance(values_block, list) or not values_block:
            return None

        rows = self._columnar_to_rows(parsed_fields, values_block)

        return ParsedDataFrame(
            source_type=source_type,
            source_id=source_id,
            name=f"frame_{index}",
            query_ref=str(frame.get("refId", "")) or None,
            fields=parsed_fields,
            rows=rows,
        )

    @staticmethod
    def _columnar_to_rows(
        fields: list[ParsedField],
        values: list[list[object]],
    ) -> list[dict[str, object]]:
        if not fields or not values:
            return []

        col_count = len(fields)
        row_count = min(len(col) for col in values)

        rows: list[dict[str, object]] = []
        for ri in range(row_count):
            row: dict[str, object] = {}
            for ci in range(col_count):
                if ci < len(values) and ri < len(values[ci]):
                    raw_val = values[ci][ri]
                    field_name = fields[ci].name
                    field_type = fields[ci].data_type
                    row[field_name] = _normalize_value(raw_val, field_type)
            rows.append(row)
        return rows

    @staticmethod
    def _fallback_parse(
        raw: Mapping[str, object],
        source_id: str,
        source_type: str,
    ) -> list[ParsedDataFrame]:
        for list_key in ("data", "results", "rows", "values"):
            candidate = raw.get(list_key)
            if isinstance(candidate, list) and candidate:
                rows = []
                for item in candidate:
                    if isinstance(item, dict):
                        rows.append({k: _normalize_value(v) for k, v in item.items()})
                if rows:
                    fields = _infer_fields_from_rows(rows)
                    return [
                        ParsedDataFrame(
                            source_type=source_type,
                            source_id=source_id,
                            name="fallback",
                            fields=fields,
                            rows=rows,
                        )
                    ]
        return []


def _normalize_value(value: object, field_type: str = "") -> object:
    if value is None:
        return None
    if isinstance(value, (int, float, bool, str)):
        if field_type == "time" and isinstance(value, (int, float)):
            from datetime import UTC, datetime
            try:
                return datetime.fromtimestamp(float(value) / 1000, tz=UTC).isoformat()
            except (ValueError, OSError):
                return str(value)
        return value
    return str(value)


def _infer_fields_from_rows(rows: list[dict[str, object]]) -> list[ParsedField]:
    seen: dict[str, str] = {}
    for row in rows:
        for key, value in row.items():
            if key not in seen:
                if isinstance(value, bool):
                    seen[key] = "boolean"
                elif isinstance(value, int):
                    seen[key] = "integer"
                elif isinstance(value, float):
                    seen[key] = "number"
                else:
                    seen[key] = "string"
    return [ParsedField(name=k, data_type=v) for k, v in seen.items()]

__all__ = ["GrafanaFrameParser"]
