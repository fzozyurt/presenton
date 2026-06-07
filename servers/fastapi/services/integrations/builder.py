from __future__ import annotations

import statistics as _statistics
from dataclasses import dataclass, field

from services.integrations.dto import (
    DataKind,
    FieldRole,
    FieldType,
    NormalizedDataProfileDTO,
    NormalizedDataSetDTO,
    NormalizedFieldDTO,
    ProcessingRecommendation,
    VisualizationKind,
    VisualizationRecommendationDTO,
)

# ── Intermediate structures ────────────────────────────────────────────


@dataclass(slots=True)
class ParsedField:
    name: str
    data_type: str
    unit: str | None = None
    role: FieldRole | None = None


@dataclass(slots=True)
class ParsedDataFrame:
    source_type: str
    source_id: str
    name: str | None = None
    query_ref: str | None = None
    fields: list[ParsedField] = field(default_factory=list)
    rows: list[dict[str, object]] = field(default_factory=list)


# ── Type mapping ───────────────────────────────────────────────────────

_TYPE_MAP: dict[str, FieldType] = {
    "time": FieldType.DATETIME,
    "number": FieldType.NUMBER,
    "string": FieldType.STRING,
    "boolean": FieldType.BOOLEAN,
    "integer": FieldType.INTEGER,
}

_TIME_LIKE = frozenset({"time", "timestamp", "datetime", "date", "created_at", "updated_at"})
_SERIES_LIKE = frozenset({"metric", "series", "legend", "name", "label"})
_VALUE_LIKE = frozenset({"value", "count", "sum", "avg", "min", "max", "total", "amount"})


def _map_data_type(data_type: str) -> FieldType:
    return _TYPE_MAP.get(data_type.lower(), FieldType.STRING)


def _infer_role(name: str, data_type: str) -> FieldRole:
    name_lower = name.lower()
    if name_lower in _TIME_LIKE or data_type == "time":
        return FieldRole.TIMESTAMP
    if name_lower in _SERIES_LIKE:
        return FieldRole.SERIES
    if data_type in ("number", "integer"):
        return _value_role_for_numeric(name_lower)
    if name_lower == "query_ref":
        return FieldRole.DIMENSION
    return FieldRole.DIMENSION if data_type == "string" else FieldRole.UNKNOWN


def _value_role_for_numeric(name_lower: str) -> FieldRole:
    if name_lower in _VALUE_LIKE:
        return FieldRole.VALUE
    if any(kw in name_lower for kw in ("count", "rate", "pct", "percent", "latency", "error", "revenue", "growth")):
        return FieldRole.VALUE
    return FieldRole.VALUE


# ── Builder ────────────────────────────────────────────────────────────


class NormalizedDataSetBuilder:
    def build(
        self,
        frames: list[ParsedDataFrame],
        *,
        preferred_data_kind: str | None = None,
        visualization_hint: str | None = None,
        row_limit: int | None = None,
    ) -> NormalizedDataSetDTO:
        if not frames:
            raise ValueError("At least one ParsedDataFrame is required")

        all_fields = self._merge_fields(frames)
        all_rows = self._merge_rows(frames)

        if row_limit is not None and row_limit > 0 and len(all_rows) > row_limit:
            all_rows = all_rows[:row_limit]

        data_kind = self._infer_data_kind(all_fields, preferred_data_kind)
        schema = self._build_schema(all_fields)
        stats = self._compute_stats(all_rows, all_fields)
        profile = self._build_profile(all_fields, all_rows, data_kind, visualization_hint)
        metadata = self._build_metadata(frames, visualization_hint)

        source_id = frames[0].source_id
        source_type = frames[0].source_type

        return NormalizedDataSetDTO(
            source_id=source_id,
            source_type=source_type,
            data_kind=data_kind,
            schema=schema,
            rows=all_rows,
            profile=profile,
            stats=stats,
            metadata=metadata,
        )

    @staticmethod
    def _merge_fields(frames: list[ParsedDataFrame]) -> list[ParsedField]:
        seen: set[str] = set()
        merged: list[ParsedField] = []
        for frame in frames:
            for f in frame.fields:
                if f.name not in seen:
                    seen.add(f.name)
                    merged.append(f)
        return merged

    @staticmethod
    def _merge_rows(frames: list[ParsedDataFrame]) -> list[dict[str, object]]:
        all_rows: list[dict[str, object]] = []
        for frame in frames:
            qr = frame.query_ref
            for row in frame.rows:
                augmented = dict(row)
                if qr is not None and "query_ref" not in augmented:
                    augmented["query_ref"] = qr
                all_rows.append(augmented)
        return all_rows

    def _infer_data_kind(
        self, fields: list[ParsedField], preferred: str | None
    ) -> DataKind:
        if preferred:
            try:
                return DataKind(preferred)
            except ValueError:
                pass

        field_types = [f.data_type.lower() for f in fields]
        field_count = len(fields)
        has_time = any(ft == "time" for ft in field_types)
        num_count = sum(1 for ft in field_types if ft in ("number", "integer"))
        str_count = sum(1 for ft in field_types if ft == "string")

        if field_count == 1 and num_count == 1:
            return DataKind.SINGLE_VALUE
        if has_time and str_count == 1 and num_count == 1 and field_count <= 4:
            return DataKind.MATRIX
        if has_time and num_count >= 1:
            return DataKind.TIME_SERIES
        if num_count == 1 and str_count >= 1 and field_count <= 3:
            return DataKind.CATEGORICAL
        if num_count >= 2 and str_count == 0 and not has_time:
            return DataKind.MULTI_VALUE
        return DataKind.TABLE

    @staticmethod
    def _build_schema(fields: list[ParsedField]) -> list[NormalizedFieldDTO]:
        schema: list[NormalizedFieldDTO] = []
        for f in fields:
            role = f.role or _infer_role(f.name, f.data_type)
            schema.append(
                NormalizedFieldDTO(
                    name=f.name,
                    type=_map_data_type(f.data_type),
                    unit=f.unit,
                    role=role,
                )
            )
        return schema

    @staticmethod
    def _compute_stats(
        rows: list[dict[str, object]], fields: list[ParsedField]
    ) -> dict[str, object]:
        stats: dict[str, object] = {"row_count": len(rows)}
        numeric_fields = [f for f in fields if f.data_type in ("number", "integer")]
        if numeric_fields:
            primary = numeric_fields[0]
            values: list[float] = []
            for row in rows:
                v = row.get(primary.name)
                if isinstance(v, (int, float)):
                    values.append(float(v))
            if values:
                stats["value_min"] = min(values)
                stats["value_max"] = max(values)
                stats["value_avg"] = round(_statistics.mean(values), 4)
                stats["value_count"] = len(values)
        return stats

    @staticmethod
    def _build_profile(
        fields: list[ParsedField],
        rows: list[dict[str, object]],
        data_kind: DataKind,
        visualization_hint: str | None,
    ) -> NormalizedDataProfileDTO:
        _ = rows
        flat_schema = NormalizedDataSetBuilder._build_schema(fields)
        has_timestamp = any(f.role == FieldRole.TIMESTAMP for f in flat_schema)
        has_numeric_value = any(f.role == FieldRole.VALUE for f in flat_schema)
        time_field = next((f.name for f in flat_schema if f.role == FieldRole.TIMESTAMP), None)
        value_fields = [f.name for f in flat_schema if f.role == FieldRole.VALUE]
        label_fields = [
            f.name for f in flat_schema if f.role in (FieldRole.LABEL, FieldRole.DIMENSION)
        ]
        series_field = next((f.name for f in flat_schema if f.role == FieldRole.SERIES), None)

        proc_rec = _infer_processing_recommendation(data_kind)
        vis_rec = _build_visualization_recommendation(data_kind, visualization_hint)

        return NormalizedDataProfileDTO(
            has_timestamp=has_timestamp,
            has_numeric_value=has_numeric_value,
            time_field=time_field,
            value_fields=value_fields,
            label_fields=label_fields,
            series_field=series_field,
            processing_recommendation=proc_rec,
            visualization_recommendation=vis_rec,
        )

    @staticmethod
    def _build_metadata(
        frames: list[ParsedDataFrame], visualization_hint: str | None
    ) -> dict[str, object]:
        query_refs: list[str] = []
        for frame in frames:
            if frame.query_ref and frame.query_ref not in query_refs:
                query_refs.append(frame.query_ref)
        result: dict[str, object] = {
            "provider": frames[0].source_type,
            "source_id": frames[0].source_id,
            "frame_count": len(frames),
        }
        if query_refs:
            result["query_refs"] = query_refs
        if visualization_hint:
            result["visualization_hint"] = visualization_hint
        return result


def _infer_processing_recommendation(data_kind: DataKind) -> ProcessingRecommendation:
    _map: dict[DataKind, ProcessingRecommendation] = {
        DataKind.TIME_SERIES: ProcessingRecommendation.ML_TIME_SERIES,
        DataKind.CATEGORICAL: ProcessingRecommendation.KPI,
        DataKind.TABLE: ProcessingRecommendation.ML_TABLE,
        DataKind.SINGLE_VALUE: ProcessingRecommendation.KPI,
        DataKind.MULTI_VALUE: ProcessingRecommendation.KPI,
        DataKind.MATRIX: ProcessingRecommendation.ML_TABLE,
        DataKind.HISTOGRAM: ProcessingRecommendation.ML_TABLE,
        DataKind.DISTRIBUTION: ProcessingRecommendation.ML_TABLE,
        DataKind.RELATIONSHIP: ProcessingRecommendation.ML_TABLE,
        DataKind.TEXT: ProcessingRecommendation.LLM_SUMMARY_ONLY,
    }
    return _map.get(data_kind, ProcessingRecommendation.NONE)


def _build_visualization_recommendation(
    data_kind: DataKind, visualization_hint: str | None
) -> VisualizationRecommendationDTO | None:
    primary: VisualizationKind | None = None
    alternatives: list[VisualizationKind] = []

    if visualization_hint:
        try:
            primary = VisualizationKind(visualization_hint)
        except ValueError:
            pass

    if data_kind == DataKind.TIME_SERIES:
        primary = primary or VisualizationKind.LINE
        alternatives = [VisualizationKind.AREA, VisualizationKind.COLUMN]
    elif data_kind == DataKind.CATEGORICAL:
        primary = primary or VisualizationKind.BAR
        alternatives = [VisualizationKind.COLUMN, VisualizationKind.PIE, VisualizationKind.DONUT]
    elif data_kind == DataKind.TABLE:
        primary = primary or VisualizationKind.TABLE_RENDER
    elif data_kind == DataKind.SINGLE_VALUE:
        primary = primary or VisualizationKind.SCORECARD
        alternatives = [VisualizationKind.GAUGE]
    elif data_kind == DataKind.MULTI_VALUE:
        primary = primary or VisualizationKind.BAR
    elif data_kind == DataKind.MATRIX:
        primary = primary or VisualizationKind.HEATMAP
    elif data_kind == DataKind.HISTOGRAM:
        primary = primary or VisualizationKind.HISTOGRAM
    elif data_kind == DataKind.TEXT:
        return None

    return VisualizationRecommendationDTO(
        primary=primary,
        alternatives=alternatives,
        reason=f"Inferred from DataKind={data_kind.value}",
    )
