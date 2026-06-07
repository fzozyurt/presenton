from __future__ import annotations

import logging

from services.integrations.dto import (
    AnalysisResultDTO,
    AnomalyDTO,
    ChartDatumDTO,
    DataKind,
    NormalizedDataSetDTO,
    StatisticalSummaryDTO,
    VisualizationKind,
)
from services.integrations.analysis.statistical import (
    build_analysis_result,
    build_chart_data,
    compute_statistical_summary,
    detect_anomalies,
    infer_visualization_hint,
)

LOGGER = logging.getLogger(__name__)


class DataAnalyzer:
    def __init__(
        self,
        *,
        zscore_threshold: float = 2.5,
        delta_threshold: float = 0.4,
    ):
        self._zscore_threshold = zscore_threshold
        self._delta_threshold = delta_threshold

    async def analyze(
        self,
        dataset: NormalizedDataSetDTO,
        *,
        include_llm_prompt: bool = False,
    ) -> AnalysisResultDTO:
        anomalies = detect_anomalies(dataset, zscore_threshold=self._zscore_threshold, delta_threshold=self._delta_threshold)
        chart_data = build_chart_data(dataset)
        result = build_analysis_result(dataset, anomalies=anomalies, chart_data=chart_data)

        if include_llm_prompt and result.summary:
            result.summary = self._enrich_for_llm(result, dataset)

        return result

    @staticmethod
    def _enrich_for_llm(result: AnalysisResultDTO, dataset: NormalizedDataSetDTO) -> str:
        parts = [result.summary]

        if dataset.profile.processing_recommendation:
            parts.append(f"\nProcessing recommendation: {dataset.profile.processing_recommendation.value}.")

        if dataset.profile.visualization_recommendation:
            vr = dataset.profile.visualization_recommendation
            parts.append(f"Visualization: {vr.primary.value if vr.primary else 'auto'}.")
            if vr.alternatives:
                parts.append(f"Alternatives: {', '.join(a.value for a in vr.alternatives)}.")

        if result.anomalies:
            critical = [a for a in result.anomalies if a.severity.value == "critical"]
            if critical:
                parts.append(f"\nCRITICAL ANOMALIES: {len(critical)} detected.")
                for a in critical[:3]:
                    parts.append(f"  - {a.metric or '?'}={a.value} (factor x{a.factor})")

        if result.stats and result.stats.trend_direction:
            parts.append(
                f"\nTrend: {result.stats.trend_direction} "
                f"({result.stats.trend_strength:.1%} strength). "
                f"Consider {'investigating' if result.stats.trend_direction == 'down' else 'capitalizing on'} this trend."
            )

        return "\n".join(parts)


class LLMAnalysisBridge:
    @staticmethod
    def build_llm_context(analysis: AnalysisResultDTO) -> str:
        lines = [
            "DATA ANALYSIS SUMMARY",
            "=" * 40,
            analysis.summary,
            "",
        ]

        if analysis.stats and analysis.stats.value_avg is not None:
            lines.append("STATISTICAL DETAILS:")
            lines.append(f"  Row count: {analysis.stats.row_count}")
            lines.append(f"  Range: {analysis.stats.value_min:.2f} - {analysis.stats.value_max:.2f}")
            lines.append(f"  Average: {analysis.stats.value_avg:.2f}")
            lines.append(f"  P50: {analysis.stats.value_p50:.2f}")
            lines.append(f"  P95: {analysis.stats.value_p95:.2f}")
            lines.append(f"  Std Dev: {analysis.stats.value_std:.2f}")
            if analysis.stats.trend_direction:
                lines.append(f"  Trend: {analysis.stats.trend_direction} ({analysis.stats.trend_strength:.1%})")
            lines.append("")

        if analysis.anomalies:
            lines.append(f"ANOMALIES ({len(analysis.anomalies)}):")
            for a in analysis.anomalies[:8]:
                lines.append(f"  [{a.severity.value.upper()}] {a.metric or '?'}={a.value} (factor: x{a.factor})")
            lines.append("")

        if analysis.chart_data:
            lines.append(f"CHART DATA ({len(analysis.chart_data)} points, LTTB downsampled):")
            for c in analysis.chart_data[:6]:
                lines.append(f"  {c.label}: {c.value}")
            if len(analysis.chart_data) > 6:
                lines.append(f"  ... and {len(analysis.chart_data) - 6} more points")
            lines.append("")

        if analysis.visualization_hint:
            lines.append(f"RECOMMENDED CHART: {analysis.visualization_hint.value}")
            lines.append("")

        lines.append("Use this analysis to populate slide content. Chart data is in {label, value} format ready for ChartDatumSchema.")
        return "\n".join(lines)

    @staticmethod
    def _build_quick_summary(results: dict[str, object], dataset: NormalizedDataSetDTO) -> str:
        parts: list[str] = [f"Analysis of {dataset.source_type} data ({len(dataset.rows)} points, {dataset.data_kind.value})."]

        stats = results.get("statistics")
        if isinstance(stats, dict):
            avg = stats.get("value_avg")
            p95 = stats.get("value_p95")
            trend_dir = stats.get("trend_direction")
            if avg is not None and p95 is not None:
                parts.append(f"Stats: avg={float(avg):.2f}, p95={float(p95):.2f}.")
            if trend_dir and trend_dir != "stable":
                strength = stats.get("trend_strength", 0)
                parts.append(f"Trend: {trend_dir} ({float(strength):.1%} strength).")

        trend = results.get("trend")
        if isinstance(trend, dict):
            summary = trend.get("summary")
            if summary and isinstance(summary, str):
                parts.append(summary + ".")

        anomalies = results.get("anomalies")
        if isinstance(anomalies, list) and anomalies:
            critical = [a for a in anomalies if isinstance(a, dict) and a.get("severity") == "critical"]
            if critical:
                parts.append(f"CRITICAL: {len(critical)} anomalies detected. Investigate immediately.")
            else:
                parts.append(f"Anomalies: {len(anomalies)} detected (warning/watch level).")

        return " ".join(parts)

__all__ = ["DataAnalyzer", "LLMAnalysisBridge"]
