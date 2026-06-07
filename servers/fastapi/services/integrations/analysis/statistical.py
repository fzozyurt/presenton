from __future__ import annotations

import logging
from collections import defaultdict

from services.integrations.dto import (
    AnalysisResultDTO,
    AnomalyDTO,
    AnomalySeverity,
    ChartDatumDTO,
    DataKind,
    NormalizedDataSetDTO,
    ProcessingRecommendation,
    StatisticalSummaryDTO,
    VisualizationKind,
)
from services.integrations.analysis.downsampling import build_chart_data_intelligent
from services.integrations.ml.models import (
    StatisticalBaselineModel,
    ZScoreAnomalyModel,
    TrendDetectionModel,
    IQRAnomalyModel,
)

LOGGER = logging.getLogger(__name__)

_baseline = StatisticalBaselineModel()
_zscore = ZScoreAnomalyModel()
_iqr = IQRAnomalyModel()
_trend = TrendDetectionModel()


async def compute_statistical_summary(dataset: NormalizedDataSetDTO) -> StatisticalSummaryDTO:
    result = await _baseline.analyze(dataset)
    if "error" in result:
        return StatisticalSummaryDTO(row_count=len(dataset.rows))

    return StatisticalSummaryDTO(
        row_count=int(result.get("row_count", 0)),
        value_min=float(result.get("value_min", 0)) if result.get("value_min") is not None else None,
        value_max=float(result.get("value_max", 0)) if result.get("value_max") is not None else None,
        value_avg=float(result.get("value_avg", 0)) if result.get("value_avg") is not None else None,
        value_p50=float(result.get("value_p50", 0)) if result.get("value_p50") is not None else None,
        value_p95=float(result.get("value_p95", 0)) if result.get("value_p95") is not None else None,
        value_std=float(result.get("value_std", 0)) if result.get("value_std") is not None else None,
        trend_direction=str(result.get("trend_direction")) if result.get("trend_direction") else None,
        trend_strength=float(result.get("trend_strength", 0)) if result.get("trend_strength") is not None else None,
    )


async def detect_anomalies(
    dataset: NormalizedDataSetDTO,
    *,
    zscore_threshold: float = 2.5,
) -> list[AnomalyDTO]:
    anomalies: list[AnomalyDTO] = []

    if _zscore.supports(dataset):
        zscore_model = ZScoreAnomalyModel(threshold=zscore_threshold)
        result = await zscore_model.analyze(dataset)
        for a in result.get("anomalies", []):
            if isinstance(a, dict):
                try:
                    anomalies.append(AnomalyDTO(
                        severity=AnomalySeverity(str(a.get("severity", "watch"))),
                        factor=float(a.get("factor", 0)),
                        service=str(a.get("service")) if a.get("service") else None,
                        metric=str(a.get("metric")) if a.get("metric") else None,
                        timestamp=str(a.get("timestamp")) if a.get("timestamp") else None,
                        value=float(a.get("value", 0)) if a.get("value") is not None else None,
                        threshold=float(a.get("threshold", 0)) if a.get("threshold") is not None else None,
                        description=str(a.get("description")) if a.get("description") else None,
                    ))
                except (ValueError, TypeError):
                    pass

    if _iqr.supports(dataset):
        iqr_result = await _iqr.analyze(dataset)
        existing_vals = {(a.service, a.metric, a.timestamp) for a in anomalies}
        for a in iqr_result.get("anomalies", []):
            if isinstance(a, dict):
                key = (str(a.get("service")), str(a.get("metric")), str(a.get("timestamp")))
                if key not in existing_vals:
                    try:
                        anomalies.append(AnomalyDTO(
                            severity=AnomalySeverity(str(a.get("severity", "watch"))),
                            factor=float(a.get("factor", 0)),
                            service=str(a.get("service")) if a.get("service") else None,
                            metric=str(a.get("metric")) if a.get("metric") else None,
                            timestamp=str(a.get("timestamp")) if a.get("timestamp") else None,
                            value=float(a.get("value", 0)) if a.get("value") is not None else None,
                            description=str(a.get("description")) if a.get("description") else None,
                        ))
                    except (ValueError, TypeError):
                        pass
                    existing_vals.add(key)

    anomalies.sort(key=lambda a: a.factor, reverse=True)
    return anomalies[:12]


async def build_chart_data(
    dataset: NormalizedDataSetDTO,
    *,
    max_points: int = 12,
) -> list[ChartDatumDTO]:
    return build_chart_data_intelligent(dataset, max_points=max_points)


def infer_visualization_hint(dataset: NormalizedDataSetDTO) -> VisualizationKind | None:
    if dataset.profile.visualization_recommendation and dataset.profile.visualization_recommendation.primary:
        return dataset.profile.visualization_recommendation.primary

    _kind_map: dict[DataKind, VisualizationKind] = {
        DataKind.TIME_SERIES: VisualizationKind.LINE,
        DataKind.CATEGORICAL: VisualizationKind.BAR,
        DataKind.SINGLE_VALUE: VisualizationKind.SCORECARD,
        DataKind.MULTI_VALUE: VisualizationKind.BAR,
        DataKind.MATRIX: VisualizationKind.HEATMAP,
        DataKind.TABLE: VisualizationKind.TABLE_RENDER,
    }
    return _kind_map.get(dataset.data_kind)


async def build_analysis_result(
    dataset: NormalizedDataSetDTO,
    *,
    anomalies: list[AnomalyDTO] | None = None,
    chart_data: list[ChartDatumDTO] | None = None,
    max_chart_points: int = 12,
) -> AnalysisResultDTO:
    stats = await compute_statistical_summary(dataset)
    if anomalies is None:
        anomalies = await detect_anomalies(dataset)
    if chart_data is None:
        chart_data = await build_chart_data(dataset, max_points=max_chart_points)
    vis_hint = infer_visualization_hint(dataset)

    trend_info = ""
    if stats.trend_direction:
        trend_info = f"Trend: {stats.trend_direction} ({stats.trend_strength:.1%} strength). "

    summary_parts: list[str] = [
        f"Data: {len(dataset.rows)} points, {dataset.data_kind.value}, source={dataset.source_type}.",
    ]
    if stats.value_avg is not None:
        summary_parts.append(
            f"Stats: avg={stats.value_avg:.2f}, min={stats.value_min:.2f}, "
            f"max={stats.value_max:.2f}, p95={stats.value_p95:.2f}. {trend_info}"
        )
    if anomalies:
        by_sev: dict[str, int] = defaultdict(int)
        for a in anomalies:
            by_sev[a.severity.value] += 1
        sev_str = ", ".join(f"{k}: {v}" for k, v in sorted(by_sev.items()))
        summary_parts.append(f"Anomalies detected: {sev_str}.")
    if chart_data:
        summary_parts.append(f"Chart-ready: {len(chart_data)} data points (LTTB downsampled).")
    if vis_hint:
        summary_parts.append(f"Recommended viz: {vis_hint.value}.")

    return AnalysisResultDTO(
        summary="\n".join(summary_parts),
        stats=stats,
        anomalies=anomalies,
        chart_data=chart_data,
        recommendation=dataset.profile.processing_recommendation,
        visualization_hint=vis_hint,
        raw_sample=dataset.rows[:3],
        raw_total_count=len(dataset.rows),
    )

__all__ = [
    "compute_statistical_summary",
    "detect_anomalies",
    "build_chart_data",
    "infer_visualization_hint",
    "build_analysis_result",
]
