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
        anomalies = await detect_anomalies(dataset, zscore_threshold=self._zscore_threshold)
        chart_data = await build_chart_data(dataset)
        result = await build_analysis_result(dataset, anomalies=anomalies, chart_data=chart_data)

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
            "DATA ANALYSIS — SRE REVIEW FORMAT",
            "=" * 50,
            "",
            "EXECUTIVE SUMMARY",
            "-" * 20,
            analysis.summary,
            "",
        ]

        if analysis.stats and analysis.stats.value_avg is not None:
            lines.append("FOUR GOLDEN SIGNALS ANALYSIS")
            lines.append("-" * 20)
            lines.append(f"  Row count: {analysis.stats.row_count} data points")
            lines.append(f"  Value range: {analysis.stats.value_min:.2f} — {analysis.stats.value_max:.2f}")
            lines.append(f"  Mean: {analysis.stats.value_avg:.2f}")
            lines.append(f"  P50 (median/typical): {analysis.stats.value_p50:.2f}")
            lines.append(f"  P95 (tail): {analysis.stats.value_p95:.2f}")
            if analysis.stats.value_std is not None and analysis.stats.value_avg:
                cv = (analysis.stats.value_std / abs(analysis.stats.value_avg)) if analysis.stats.value_avg != 0 else 0
                lines.append(f"  Std Dev: {analysis.stats.value_std:.2f} (CV: {cv:.1%} — {'high variance' if cv > 1 else 'moderate' if cv > 0.5 else 'stable'})")
            if analysis.stats.trend_direction:
                direction_word = analysis.stats.trend_direction.upper()
                lines.append(f"  Trend: {direction_word} ({analysis.stats.trend_strength:.1%} strength)")
                if analysis.stats.trend_direction == "down" and analysis.stats.trend_strength > 0.1:
                    lines.append("  [!] Negative trend detected — investigate root cause.")
                elif analysis.stats.trend_direction == "up" and analysis.stats.trend_strength > 0.2:
                    lines.append("  [!] Rapid growth detected — check capacity headroom.")
            lines.append("")
            p50 = analysis.stats.value_p50 or 0
            p95 = analysis.stats.value_p95 or 0
            if p50 > 0 and p95 / p50 > 3:
                lines.append(f"  [!!] HEAVY TAIL: p95 is {p95/p50:.1f}x p50. Users in the tail are having a significantly worse experience. Investigate tail latency causes.")
            lines.append("")

        if analysis.anomalies:
            by_sev: dict[str, list[AnomalyDTO]] = {"critical": [], "warning": [], "watch": []}
            for a in analysis.anomalies:
                sev = a.severity.value
                if sev in by_sev:
                    by_sev[sev].append(a)
            lines.append("ANOMALY REPORT (ML-detected: Z-score + IQR)")
            lines.append("-" * 20)

            if by_sev["critical"]:
                lines.append(f"  CRITICAL ({len(by_sev['critical'])}): Immediate action required")
                for a in by_sev["critical"][:5]:
                    lines.append(f"    -> {a.metric or '?'} = {a.value} (factor: x{a.factor:.1f}) | {a.description or ''}")
            if by_sev["warning"]:
                lines.append(f"  WARNING ({len(by_sev['warning'])}): Review this week")
                for a in by_sev["warning"][:3]:
                    lines.append(f"    -> {a.metric or '?'} = {a.value} (factor: x{a.factor:.1f})")
            if by_sev["watch"]:
                lines.append(f"  WATCH ({len(by_sev['watch'])}): Monitor for escalation")
            lines.append("")

        if analysis.chart_data:
            lines.append(f"CHART DATA ({len(analysis.chart_data)} points, LTTB downsampled — preserves peaks/valleys)")
            lines.append("-" * 20)
            for c in analysis.chart_data[:8]:
                series_suffix = f" [{c.series}]" if c.series else ""
                lines.append(f"  {c.label}: {c.value}{series_suffix}")
            if len(analysis.chart_data) > 8:
                lines.append(f"  ... and {len(analysis.chart_data) - 8} more points")
            lines.append("")

        if analysis.visualization_hint:
            lines.append(f"RECOMMENDED CHART: {analysis.visualization_hint.value}")
            lines.append(f"DATA KIND: {analysis.recommendation.value if analysis.recommendation else 'auto'}")
            lines.append("")

        lines.append(
            "SLIDE GUIDANCE: Use 'chart_data' directly in slide's chart.data field (matches ChartDatumSchema). "
            "Put critical anomalies in bold with severity markers. "
            "Include trend arrows (up/down/stable) in stat cards. "
            "When past_analysis_context is available, compute WoW (week-over-week) deltas for every key metric."
        )
        return "\n".join(lines)

    @staticmethod
    def build_full_sre_report(
        analysis: AnalysisResultDTO,
        *,
        dataset: NormalizedDataSetDTO | None = None,
        past_context: str = "",
    ) -> str:
        """Build a complete SRE review report with data-driven context."""
        parts = [LLMAnalysisBridge.build_llm_context(analysis)]

        if dataset and dataset.rows:
            from services.integrations.analysis.context_analyzer import build_context_report
            field_names = [f.name for f in dataset.data_schema] if dataset.data_schema else list(dataset.rows[0].keys()) if dataset.rows else []
            timestamps = None
            if dataset.profile.time_field:
                timestamps = [
                    str(row.get(dataset.profile.time_field, ""))
                    for row in dataset.rows
                ]
            ctx_report = build_context_report(field_names, dataset.rows, timestamps=timestamps)
            parts.append("\n" + ctx_report)

        if past_context:
            parts.append("\n\nHISTORICAL CONTEXT (previous analysis):")
            parts.append("-" * 30)
            parts.append(past_context[:2000])
            parts.append("\nCompare current values against this baseline. Highlight Week-over-Week deltas.")

        return "\n".join(parts)

    @staticmethod
    def _build_quick_summary(results: dict[str, object], dataset: NormalizedDataSetDTO) -> str:
        parts: list[str] = [
            f"SRE Analysis: {dataset.source_type} | {len(dataset.rows)} points | {dataset.data_kind.value}."
        ]

        stats = results.get("statistics")
        if isinstance(stats, dict):
            avg = stats.get("value_avg")
            p50 = stats.get("value_p50")
            p95 = stats.get("value_p95")
            trend_dir = stats.get("trend_direction")
            if avg is not None and p95 is not None:
                parts.append(f"avg={float(avg):.1f}, p50={float(p50):.1f}, p95={float(p95):.1f}.")
            if trend_dir and trend_dir != "stable":
                strength = stats.get("trend_strength", 0)
                direction_word = trend_dir.upper()
                parts.append(f"Trend: {direction_word} ({float(strength):.1%}).")

        trend = results.get("trend")
        if isinstance(trend, dict):
            summary = trend.get("summary")
            if summary and isinstance(summary, str):
                parts.append(summary + ".")

        anomalies = results.get("anomalies")
        if isinstance(anomalies, list) and anomalies:
            critical = [a for a in anomalies if isinstance(a, dict) and a.get("severity") == "critical"]
            warning = [a for a in anomalies if isinstance(a, dict) and a.get("severity") == "warning"]
            if critical:
                parts.append(f"[!!] {len(critical)} CRITICAL — immediate attention needed.")
            elif warning:
                parts.append(f"[!] {len(warning)} warnings — review this week.")
            else:
                parts.append(f"{len(anomalies)} watch items — monitor.")

        return " ".join(parts)

__all__ = ["DataAnalyzer", "LLMAnalysisBridge"]
