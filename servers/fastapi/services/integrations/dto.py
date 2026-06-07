from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ── Data shape classification ──────────────────────────────────────────


class DataKind(str, Enum):
    TIME_SERIES = "time_series"
    CATEGORICAL = "categorical"
    TABLE = "table"
    SINGLE_VALUE = "single_value"
    MULTI_VALUE = "multi_value"
    MATRIX = "matrix"
    HISTOGRAM = "histogram"
    DISTRIBUTION = "distribution"
    RELATIONSHIP = "relationship"
    TEXT = "text"


class VisualizationKind(str, Enum):
    LINE = "line"
    AREA = "area"
    BAR = "bar"
    COLUMN = "column"
    STACKED_BAR = "stacked_bar"
    STACKED_COLUMN = "stacked_column"
    PIE = "pie"
    DONUT = "donut"
    SCATTER = "scatter"
    BUBBLE = "bubble"
    COMBO = "combo"
    HISTOGRAM = "histogram"
    HEATMAP = "heatmap"
    GAUGE = "gauge"
    SCORECARD = "scorecard"
    TABLE_RENDER = "table"
    PIVOT_TABLE = "pivot_table"
    TREEMAP = "treemap"
    WATERFALL = "waterfall"
    RADAR = "radar"
    SPARKLINE = "sparkline"


class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATETIME = "datetime"


class FieldRole(str, Enum):
    TIMESTAMP = "timestamp"
    VALUE = "value"
    LABEL = "label"
    SERIES = "series"
    DIMENSION = "dimension"
    METADATA = "metadata"
    UNKNOWN = "unknown"


class ProcessingRecommendation(str, Enum):
    ML_TIME_SERIES = "ml_time_series"
    ML_TABLE = "ml_table"
    KPI = "kpi"
    LLM_SUMMARY_ONLY = "llm_summary_only"
    NONE = "none"


class SourceType(str, Enum):
    GRAFANA = "grafana"
    PROMETHEUS = "prometheus"
    D_DATABASE = "d_database"
    REST = "rest"
    CUSTOM_HTTP = "custom_http"


# ── Data structures ────────────────────────────────────────────────────


class NormalizedFieldDTO(BaseModel):
    name: str = Field(..., description="Field name as it appears in row dicts")
    type: FieldType = Field(..., description="Data type of this field")
    unit: str | None = Field(None, description="Optional unit of measurement")
    role: FieldRole = Field(FieldRole.UNKNOWN, description="Semantic role")


class VisualizationRecommendationDTO(BaseModel):
    primary: VisualizationKind | None = Field(None)
    alternatives: list[VisualizationKind] = Field(default_factory=list)
    reason: str | None = Field(None)


class NormalizedDataProfileDTO(BaseModel):
    has_timestamp: bool = False
    has_numeric_value: bool = False
    time_field: str | None = None
    value_fields: list[str] = Field(default_factory=list)
    label_fields: list[str] = Field(default_factory=list)
    series_field: str | None = None
    processing_recommendation: ProcessingRecommendation = ProcessingRecommendation.NONE
    visualization_recommendation: VisualizationRecommendationDTO | None = None


class NormalizedDataSetDTO(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    source_id: str = Field(..., description="Identifier of the source system")
    source_type: str = Field(..., description="Type of source (grafana, rest, etc.)")
    binding_id: str | None = Field(None, description="Binding ID if applicable")
    data_kind: DataKind = Field(..., description="Shape of the data")
    data_schema: list[NormalizedFieldDTO] = Field(default_factory=list, alias="schema")
    rows: list[dict[str, object]] = Field(default_factory=list)
    profile: NormalizedDataProfileDTO = Field(default_factory=NormalizedDataProfileDTO)
    stats: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)


# ── Adapter configuration ──────────────────────────────────────────────


class TimeRangeForFetch(BaseModel):
    start: datetime | None = None
    end: datetime | None = None
    timezone: str = "UTC"


class ResolvedAdapterConfig(BaseModel):
    datasource_id: str
    datasource_type: str
    binding_id: str | None = None
    credential_ref: str | None = None
    config: dict[str, object] = Field(default_factory=dict)
    time_range: TimeRangeForFetch | None = None


# ── ML analysis DTOs ───────────────────────────────────────────────────


class AnomalySeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    WATCH = "watch"
    INFO = "info"


class AnomalyDTO(BaseModel):
    severity: AnomalySeverity
    factor: float
    service: str | None = None
    pod: str | None = None
    region: str | None = None
    metric: str | None = None
    timestamp: str | None = None
    value: float | None = None
    threshold: float | None = None
    description: str | None = None


class StatisticalSummaryDTO(BaseModel):
    row_count: int = 0
    value_min: float | None = None
    value_max: float | None = None
    value_avg: float | None = None
    value_p50: float | None = None
    value_p95: float | None = None
    value_std: float | None = None
    trend_direction: str | None = None
    trend_strength: float | None = None


class ChartDatumDTO(BaseModel):
    label: str
    value: float
    series: str | None = None


class AnalysisResultDTO(BaseModel):
    summary: str
    stats: StatisticalSummaryDTO | None = None
    anomalies: list[AnomalyDTO] = Field(default_factory=list)
    chart_data: list[ChartDatumDTO] = Field(default_factory=list)
    recommendation: ProcessingRecommendation = ProcessingRecommendation.NONE
    visualization_hint: VisualizationKind | None = None
    raw_sample: list[dict[str, object]] = Field(default_factory=list)
    raw_total_count: int = 0
