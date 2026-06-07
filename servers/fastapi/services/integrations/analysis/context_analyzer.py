"""
Data-driven metric context analysis — no hardcoded metric names.

Principles:
1. Diurnal patterns: detected via autocorrelation on 24h lag, not assumed from names.
2. Rate vs absolute: inferred from value range (0-1/0-100 = likely rate) and column relationships.
3. Direction significance: learned from historical trend, not predefined "good/bad".
4. Column relationships: discovered via correlation + naming heuristics, not lookup tables.
5. Volume-weighted significance: small-sample anomalies are noise, large-sample ones are signal.
"""

from __future__ import annotations

import math
import statistics as _stats
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime


# ── Data-driven pattern detection ─────────────────────────────────────


@dataclass(slots=True)
class MetricProfile:
    """Statistical profile of a metric — purely from data, no naming assumptions."""

    name: str
    value_count: int
    value_range: tuple[float, float]
    mean: float
    std: float
    cv: float  # coefficient of variation = std/mean
    is_likely_rate: bool = False  # values in [0,1] or [0,100]
    is_likely_counter: bool = False  # monotonic increasing
    has_diurnal_pattern: bool = False  # 24h autocorrelation > threshold
    has_weekly_pattern: bool = False  # weekday/weekend distribution differs
    trend_direction: str = "stable"  # up/down/stable
    trend_strength: float = 0.0
    volatility: str = "stable"  # stable/moderate/volatile
    outlier_ratio: float = 0.0  # fraction of values beyond 2σ


def profile_metric(
    name: str,
    values: list[float],
    timestamps: list[str] | None = None,
) -> MetricProfile:
    """Build a statistical profile of a metric from raw data only."""
    if not values:
        return MetricProfile(name=name, value_count=0, value_range=(0, 0), mean=0, std=0, cv=0)

    vs = sorted(values)
    n = len(vs)
    mean = _stats.mean(vs)
    std = _stats.stdev(vs) if n >= 2 else 0.0
    cv = std / abs(mean) if mean != 0 else 0.0

    # Rate detection: values in typical percentage ranges
    in_0_1 = sum(1 for v in vs if 0 <= v <= 1)
    in_0_100 = sum(1 for v in vs if 0 <= v <= 100)
    is_likely_rate = (in_0_1 / n > 0.8) if n > 0 else False
    if not is_likely_rate and n > 0:
        is_likely_rate = (in_0_100 / n > 0.8) and any(v > 1 for v in vs)

    # Counter detection: monotonic increasing
    increasing_pairs = sum(1 for i in range(1, n) if vs[i] >= vs[i - 1])
    is_likely_counter = (increasing_pairs / (n - 1) > 0.9) if n > 1 else False

    # Diurnal detection via hourly bucket variance
    has_diurnal = False
    if timestamps and n >= 24:
        has_diurnal = _detect_diurnal_pattern(values, timestamps)

    # Weekly detection via weekday/weekend split
    has_weekly = False
    if timestamps and n >= 14:
        has_weekly = _detect_weekly_pattern(values, timestamps)

    # Trend
    direction, strength = _compute_trend(values)
    trend_direction = direction
    trend_strength = strength

    # Volatility
    volatility = "stable" if cv < 0.2 else ("volatile" if cv > 1.0 else "moderate")

    # Outlier ratio
    if std > 0:
        outlier_count = sum(1 for v in vs if abs(v - mean) > 2 * std)
        outlier_ratio = outlier_count / n
    else:
        outlier_ratio = 0.0

    return MetricProfile(
        name=name,
        value_count=n,
        value_range=(vs[0], vs[-1]),
        mean=mean,
        std=std,
        cv=cv,
        is_likely_rate=is_likely_rate,
        is_likely_counter=is_likely_counter,
        has_diurnal_pattern=has_diurnal,
        has_weekly_pattern=has_weekly,
        trend_direction=trend_direction,
        trend_strength=trend_strength,
        volatility=volatility,
        outlier_ratio=outlier_ratio,
    )


def _detect_diurnal_pattern(values: list[float], timestamps: list[str]) -> bool:
    """Detect 24h cyclical pattern using hourly bucket variance ratio."""
    try:
        hourly: dict[int, list[float]] = defaultdict(list)
        for v, ts in zip(values, timestamps):
            hour = _parse_hour(ts)
            if hour is not None:
                hourly[hour].append(v)

        if len(hourly) < 6:  # need at least 6 distinct hours
            return False

        # Between-hour variance vs within-hour variance
        hour_means = [_stats.mean(vs) for vs in hourly.values() if vs]
        if len(hour_means) < 6:
            return False

        between_var = _stats.variance(hour_means) if len(hour_means) >= 2 else 0
        within_vars = [_stats.variance(vs) for vs in hourly.values() if len(vs) >= 2]
        avg_within_var = _stats.mean(within_vars) if within_vars else 0

        if avg_within_var == 0:
            return between_var > 0

        # F-like ratio: between-group variance significantly exceeds within-group
        return between_var / avg_within_var > 2.0
    except Exception:
        return False


def _detect_weekly_pattern(values: list[float], timestamps: list[str]) -> bool:
    """Detect weekday/weekend difference using Welch's t-test approximation."""
    try:
        weekday_vals: list[float] = []
        weekend_vals: list[float] = []
        for v, ts in zip(values, timestamps):
            dow = _parse_day_of_week(ts)
            if dow is None:
                continue
            if dow < 5:
                weekday_vals.append(v)
            else:
                weekend_vals.append(v)

        if len(weekday_vals) < 5 or len(weekend_vals) < 2:
            return False

        wd_mean = _stats.mean(weekday_vals)
        we_mean = _stats.mean(weekend_vals)
        wd_std = _stats.stdev(weekday_vals) if len(weekday_vals) >= 2 else 0
        we_std = _stats.stdev(weekend_vals) if len(weekend_vals) >= 2 else 0

        pooled_se = math.sqrt(wd_std**2 / len(weekday_vals) + we_std**2 / len(weekend_vals))
        if pooled_se == 0:
            return False

        t_stat = abs(wd_mean - we_mean) / pooled_se
        return t_stat > 2.0  # roughly p < 0.05
    except Exception:
        return False


def _compute_trend(values: list[float]) -> tuple[str, float]:
    n = len(values)
    if n < 3:
        return "stable", 0.0
    x_mean = (n - 1) / 2.0
    y_mean = _stats.mean(values)
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    slope = num / den if den > 0 else 0.0
    if y_mean == 0:
        rel = float("inf") if slope != 0 else 0.0
    else:
        rel = abs(slope * n / y_mean)
    direction = "up" if rel > 0.02 and slope > 0 else ("down" if rel > 0.02 and slope < 0 else "stable")
    return direction, rel


def _parse_hour(ts: str) -> int | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).hour
    except (ValueError, TypeError):
        return None


def _parse_day_of_week(ts: str) -> int | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).weekday()
    except (ValueError, TypeError):
        return None


# ── Volume-weighted anomaly significance ──────────────────────────────


def assess_anomaly_significance(
    value: float,
    zscore: float,
    *,
    metric_profile: MetricProfile,
    row_context: dict[str, object] | None = None,
    time_of_day: int | None = None,
    day_of_week: int | None = None,
) -> dict[str, object]:
    """Assess whether a statistical anomaly is practically significant.

    Returns a dict with:
    - genuine: bool — is this worth investigating?
    - adjusted_severity: critical/warning/watch/info
    - reasons: list of reasons for adjustment
    - recommendation: what to do
    """
    genuine = True
    adjusted = "critical" if abs(zscore) > 3.5 else ("warning" if abs(zscore) > 2.5 else "watch")
    reasons: list[str] = []
    recs: list[str] = []

    # ── 1. Sample size check ──
    if metric_profile.value_count < 10:
        genuine = False
        adjusted = "info"
        reasons.append(f"Only {metric_profile.value_count} data points — statistically unreliable.")
        recs.append("Collect more data before drawing conclusions.")
    elif metric_profile.value_count < 30:
        if abs(zscore) < 3.5:
            adjusted = "watch"
            reasons.append(f"Small sample ({metric_profile.value_count} points) — elevated false positive risk.")
            recs.append("Verify with additional data before escalating.")

    # ── 2. Rate metric volume check ──
    if metric_profile.is_likely_rate and row_context:
        denominator = _find_denominator_in_row(row_context, metric_profile.name)
        if denominator is not None and denominator < 100:
            genuine = False
            adjusted = "info"
            reasons.append(f"Rate metric with tiny denominator ({denominizer:.0f} total events). Statistically meaningless.")
            recs.append("Increase sample before flagging. A 50%% error rate on 2 requests is noise.")
        elif denominator is not None and denominator < 1000:
            adjusted = "watch"
            reasons.append(f"Rate metric with moderate sample ({denominizer:.0f} events). Interpret cautiously.")

    # ── 3. Diurnal pattern — low values in off-hours are expected ──
    if metric_profile.has_diurnal_pattern and time_of_day is not None:
        if 0 <= time_of_day <= 5:
            genuine = False
            adjusted = "info"
            reasons.append(f"Value at {time_of_day:02d}:00 — metric shows 24h cycle. Off-hour lows are expected.")
            recs.append("Compare against same-hour historical average, not global average.")
        elif 22 <= time_of_day <= 23 or time_of_day <= 6:
            adjusted = "watch" if adjusted == "critical" else adjusted
            reasons.append(f"Value at {time_of_day:02d}:00 — near off-peak. Verify this is truly anomalous vs. historical same-hour values.")

    # ── 4. Weekly pattern — weekend changes may be normal ──
    if metric_profile.has_weekly_pattern and day_of_week is not None and day_of_week >= 5:
        genuine = False
        adjusted = "info"
        reasons.append(f"Weekend ({['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][day_of_week]}) — metric has known weekday/weekend divergence.")
        recs.append("Compare against same-day-last-week, not weekday average.")

    # ── 5. Volatility context ──
    if metric_profile.volatility == "volatile" and abs(zscore) < 3.0:
        adjusted = "watch"
        reasons.append(f"Metric is inherently volatile (CV={metric_profile.cv:.1%}). Moderate z-scores are normal for this metric.")
        recs.append("Use IQR-based detection for volatile metrics — Z-score over-alerts on high-variance data.")

    # ── 6. Trend-aware: if metric is trending, what looks like an anomaly may be trend continuation ──
    if metric_profile.trend_direction != "stable" and metric_profile.trend_strength > 0.1:
        if (metric_profile.trend_direction == "up" and zscore > 0) or (metric_profile.trend_direction == "down" and zscore < 0):
            adjusted = "watch" if adjusted == "critical" else adjusted
            reasons.append(f"Value follows existing {metric_profile.trend_direction}ward trend ({metric_profile.trend_strength:.1%}). May be trend continuation, not anomaly.")
            recs.append("Check if this is within the trend's confidence band before alerting.")

    # ── 7. Counter metrics: rate-of-change matters more than absolute ──
    if metric_profile.is_likely_counter:
        reasons.append("This appears to be a counter (monotonically increasing). Analyze rate-of-change, not absolute value.")
        recs.append("Compute delta from previous period — a counter always growing is normal.")

    return {
        "genuine": genuine,
        "adjusted_severity": adjusted,
        "reasons": reasons,
        "recommendation": " | ".join(recs) if recs else "Standard investigation protocol.",
        "metric_profile": {
            "cv": round(metric_profile.cv, 3),
            "volatility": metric_profile.volatility,
            "trend": metric_profile.trend_direction,
            "is_rate": metric_profile.is_likely_rate,
            "is_counter": metric_profile.is_likely_counter,
            "has_diurnal": metric_profile.has_diurnal_pattern,
            "has_weekly": metric_profile.has_weekly_pattern,
            "sample_size": metric_profile.value_count,
        },
    }


def _find_denominator_in_row(row: dict[str, object], metric_name: str) -> float | None:
    """Heuristically find a denominator column for a rate metric."""
    name_lower = metric_name.lower()
    # Look for total/count/all variants of the same base name
    base_candidates = [
        name_lower.replace("error_rate", "").replace("fail_rate", "").replace("_rate", "").replace("_pct", "").replace("_percent", ""),
    ]
    for base in base_candidates:
        if not base:
            continue
        for key, val in row.items():
            key_lower = key.lower()
            if key == metric_name:
                continue
            if base in key_lower and any(kw in key_lower for kw in ("total", "count", "all", "request", "sample")):
                if isinstance(val, (int, float)):
                    return float(val)
    return None


# ── Column relationship discovery via correlation ─────────────────────


@dataclass(slots=True)
class ColumnRelationship:
    col_a: str
    col_b: str
    relationship: str  # "strong_correlation", "moderate_correlation", "likely_ratio", "inverse"
    correlation: float
    description: str


def discover_relationships(
    field_names: list[str],
    rows: list[dict[str, object]],
) -> list[ColumnRelationship]:
    """Discover relationships between columns using Pearson correlation."""
    if len(field_names) < 2 or len(rows) < 3:
        return []

    numeric_cols = []
    for name in field_names:
        vals = [row.get(name) for row in rows]
        if all(isinstance(v, (int, float)) or v is None for v in vals):
            numeric_vals = [float(v) for v in vals if isinstance(v, (int, float))]
            if len(numeric_vals) >= 3:
                numeric_cols.append((name, numeric_vals))

    relationships: list[ColumnRelationship] = []
    for i in range(len(numeric_cols)):
        for j in range(i + 1, len(numeric_cols)):
            name_a, vals_a = numeric_cols[i]
            name_b, vals_b = numeric_cols[j]
            min_len = min(len(vals_a), len(vals_b))
            r = _pearson_correlation(vals_a[:min_len], vals_b[:min_len])
            if abs(r) < 0.5:
                continue

            rel_type = "strong_correlation" if abs(r) > 0.8 else "moderate_correlation"
            if r < -0.5:
                rel_type = "inverse"

            # Heuristic: if one is in [0,1] range and the other is larger, likely ratio
            a_in_unit = all(0 <= v <= 1 for v in vals_a[:min_len])
            b_larger = any(v > 1 for v in vals_b[:min_len])
            if a_in_unit and b_larger and r > 0.3:
                rel_type = "likely_ratio"
                relationships.append(ColumnRelationship(
                    col_a=name_a, col_b=name_b, relationship=rel_type,
                    correlation=round(r, 3),
                    description=f"{name_a} appears to be a rate derived from {name_b} (r={r:.2f}).",
                ))
                continue

            relationships.append(ColumnRelationship(
                col_a=name_a, col_b=name_b, relationship=rel_type,
                correlation=round(r, 3),
                description=f"{'Strong' if abs(r)>0.8 else 'Moderate'} {'positive' if r>0 else 'negative'} correlation (r={r:.2f}) between {name_a} and {name_b}.",
            ))

    return relationships


def _pearson_correlation(x: list[float], y: list[float]) -> float:
    n = min(len(x), len(y))
    if n < 3:
        return 0.0
    mx = _stats.mean(x)
    my = _stats.mean(y)
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    dx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    dy = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


# ── LLM context builder ──────────────────────────────────────────────


def build_context_report(
    field_names: list[str],
    rows: list[dict[str, object]],
    *,
    timestamps: list[str] | None = None,
    slo_targets: dict[str, float] | None = None,
) -> str:
    """Build a comprehensive, data-driven context report for LLM consumption."""
    if not rows:
        return "No data to analyze."

    lines = ["DATA PROFILE (purely statistical — no naming assumptions)", "=" * 55]

    # Profile every numeric field
    profiles: dict[str, MetricProfile] = {}
    for name in field_names:
        vals = []
        for row in rows:
            v = row.get(name)
            if isinstance(v, (int, float)) and math.isfinite(float(v)):
                vals.append(float(v))
        if vals:
            profiles[name] = profile_metric(name, vals, timestamps)

    # ── Metric profiles ──
    lines.append("\nMETRIC PROFILES:")
    for name, p in profiles.items():
        flags = []
        if p.is_likely_rate:
            flags.append("RATE")
        if p.is_likely_counter:
            flags.append("COUNTER")
        if p.has_diurnal_pattern:
            flags.append("24h-CYCLE")
        if p.has_weekly_pattern:
            flags.append("WEEKLY-PATTERN")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        lines.append(
            f"  {name}: n={p.value_count}, range=[{p.value_range[0]:.2f}, {p.value_range[1]:.2f}], "
            f"mean={p.mean:.2f}, cv={p.cv:.1%}, trend={p.trend_direction}({p.trend_strength:.1%}), "
            f"volatility={p.volatility}{flag_str}"
        )

    # ── Relationships ──
    rels = discover_relationships(field_names, rows)
    if rels:
        lines.append("\nCOLUMN RELATIONSHIPS (Pearson correlation):")
        for rel in rels:
            lines.append(f"  {rel.col_a} ↔ {rel.col_b}: {rel.relationship} (r={rel.correlation}) — {rel.description}")

    # ── Interpretation guide ──
    lines.append("\nINTERPRETATION RULES (apply to anomaly evaluation):")
    for name, p in profiles.items():
        rules = []
        if p.has_diurnal_pattern:
            rules.append("expect lows at 00:00-06:00 — do NOT alert on off-hour dips")
        if p.has_weekly_pattern:
            rules.append("expect weekday/weekend divergence — compare same-day-last-week")
        if p.is_likely_rate:
            rules.append("rate metric — significance depends on denominator volume (< 100 events = noise)")
        if p.is_likely_counter:
            rules.append("monotonically increasing — rate-of-change matters, not absolute value")
        if p.volatility == "volatile":
            rules.append("high variance — use IQR instead of Z-score for anomaly detection")
        if p.trend_direction != "stable" and p.trend_strength > 0.1:
            rules.append(f"existing {p.trend_direction}ward trend ({p.trend_strength:.1%}) — values in trend direction may be continuation, not anomaly")
        if p.outlier_ratio > 0.1:
            rules.append(f"heavy-tailed distribution ({p.outlier_ratio:.0%} outliers) — expect frequent 'anomalies' that may be normal tail behavior")
        if rules:
            lines.append(f"  [{name}]")
            for rule in rules:
                lines.append(f"    - {rule}")

    # ── SLO / Error budget analysis ──
    if slo_targets:
        lines.append("\nSLO / ERROR BUDGET ANALYSIS:")
        for metric_name, slo_value in slo_targets.items():
            profile = profiles.get(metric_name)
            if profile is None:
                continue
            total_requests = profile.value_count
            allowed_errors = total_requests * (1 - slo_value) if slo_value < 1 else 0
            actual_values = [
                float(row.get(metric_name, 0))
                for row in rows
                if isinstance(row.get(metric_name), (int, float))
            ]
            breaches = sum(1 for v in actual_values if v > slo_value) if slo_value < 1 else sum(1 for v in actual_values if v > slo_value)
            breach_rate = breaches / total_requests if total_requests > 0 else 0
            budget_consumed_pct = (breaches / allowed_errors * 100) if allowed_errors > 0 else (100 if breaches > 0 else 0)
            lines.append(f"  [{metric_name}] SLO: {slo_value}")
            lines.append(f"    Breaches: {breaches}/{total_requests} ({breach_rate:.2%})")
            if allowed_errors > 0:
                lines.append(f"    Error budget: {allowed_errors:.0f} allowed | {breaches} consumed ({budget_consumed_pct:.1f}%)")
                if budget_consumed_pct > 80:
                    lines.append(f"    [!] CRITICAL: > 80% error budget consumed. Freeze non-emergency deployments.")
                elif budget_consumed_pct > 50:
                    lines.append(f"    [!] WARNING: > 50% error budget consumed. Investigate burn rate.")
            elif breaches > 0:
                lines.append(f"    [!] SLO breach detected — every occurrence is a violation.")

    # ── Chart suggestions ──
    lines.append("\nCHART SUGGESTIONS (data-driven):")
    has_time = any("time" in n.lower() or "timestamp" in n.lower() or "date" in n.lower() for n in field_names)
    rate_fields = [n for n, p in profiles.items() if p.is_likely_rate]
    counter_fields = [n for n, p in profiles.items() if p.is_likely_counter]
    other_numeric = [n for n in profiles if n not in rate_fields and n not in counter_fields and not (has_time and ("time" in n.lower() or "timestamp" in n.lower()))]

    if has_time and other_numeric:
        lines.append(f"  -> LINE chart: {other_numeric[0]} over time (time-series with LTTB downsampling)")
    if rate_fields and other_numeric:
        lines.append(f"  -> BAR chart: {rate_fields[0]} vs {other_numeric[0]} (rate comparison)")
    if rels:
        for rel in rels[:2]:
            if rel.relationship == "likely_ratio" or rel.relationship == "inverse":
                lines.append(f"  -> SCATTER chart: {rel.col_a} vs {rel.col_b} (r={rel.correlation})")
    if counter_fields:
        lines.append(f"  -> LINE chart: {counter_fields[0]} growth rate (delta from previous period)")

    lines.append(f"\n  Total fields: {len(field_names)} | Numeric: {len(profiles)} | Relationships: {len(rels)} | Diurnal: {sum(1 for p in profiles.values() if p.has_diurnal_pattern)} | Weekly: {sum(1 for p in profiles.values() if p.has_weekly_pattern)}")

    return "\n".join(lines)

__all__ = [
    "MetricProfile",
    "ColumnRelationship",
    "profile_metric",
    "assess_anomaly_significance",
    "discover_relationships",
    "build_context_report",
]
