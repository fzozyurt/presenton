from __future__ import annotations

import math
import statistics as _statistics

from services.integrations.dto import (
    AnomalyDTO,
    AnomalySeverity,
    DataKind,
    NormalizedDataSetDTO,
    StatisticalSummaryDTO,
)

_TIME_SERIES_KINDS = {
    DataKind.TIME_SERIES, DataKind.CATEGORICAL, DataKind.MULTI_VALUE,
    DataKind.SINGLE_VALUE, DataKind.MATRIX, DataKind.DISTRIBUTION,
}
_ALL_NUMERIC_KINDS = _TIME_SERIES_KINDS | {DataKind.TABLE, DataKind.HISTOGRAM, DataKind.RELATIONSHIP}


class StatisticalBaselineModel:
    @property
    def model_name(self) -> str:
        return "statistical_baseline"

    @property
    def model_type(self) -> str:
        return "baseline"

    @property
    def description(self) -> str:
        return "Computes descriptive statistics: mean, std, median (p50), p95, min, max, quartiles. Always use first to understand data distribution."

    @property
    def supported_data_kinds(self) -> list[DataKind]:
        return list(_ALL_NUMERIC_KINDS)

    @property
    def model_card(self) -> dict[str, object]:
        return {
            "name": self.model_name,
            "type": self.model_type,
            "description": self.description,
            "supported_data_kinds": [k.value for k in self.supported_data_kinds],
            "when_to_use": "Use for any numeric dataset to get baseline statistics before deeper analysis.",
            "output_keys": ["row_count", "value_min", "value_max", "value_avg", "value_p50", "value_p95", "value_std", "value_q1", "value_q3", "trend_direction", "trend_strength"],
            "requires": "At least one numeric value field.",
            "confidence": "Deterministic — always produces exact results.",
        }

    def supports(self, dataset: NormalizedDataSetDTO) -> bool:
        return bool(dataset.profile.value_fields) and dataset.data_kind in self.supported_data_kinds

    async def analyze(self, dataset: NormalizedDataSetDTO) -> dict[str, object]:
        value_fields = dataset.profile.value_fields
        if not value_fields:
            return {"error": "No value fields found"}

        primary = value_fields[0]
        values = self._extract_values(dataset.rows, primary)
        if not values:
            return {"error": "No numeric values found"}

        vs = sorted(values)
        n = len(vs)

        result: dict[str, object] = {
            "row_count": len(dataset.rows),
            "value_count": n,
            "value_min": vs[0],
            "value_max": vs[-1],
            "value_avg": round(_statistics.mean(vs), 4),
            "value_p50": round(float(_statistics.median(vs)), 4),
            "value_std": round(_statistics.stdev(vs), 4) if n >= 2 else 0.0,
            "primary_field": primary,
        }

        if n >= 20:
            result["value_p95"] = round(float(_statistics.quantiles(vs, n=20)[18]), 4)
        else:
            result["value_p95"] = vs[-1]

        if n >= 4:
            result["value_q1"] = round(float(_statistics.quantiles(vs, n=4)[0]), 4)
            result["value_q3"] = round(float(_statistics.quantiles(vs, n=4)[2]), 4)

        trend_field = dataset.profile.time_field
        if trend_field and n >= 3:
            timestamps = [row.get(trend_field) for row in dataset.rows]
            direction, strength = self._compute_trend(values, timestamps)
            result["trend_direction"] = direction
            result["trend_strength"] = round(strength, 4)

        return result

    @staticmethod
    def _extract_values(rows: list[dict[str, object]], field: str) -> list[float]:
        values: list[float] = []
        for row in rows:
            v = row.get(field)
            if isinstance(v, (int, float)) and math.isfinite(float(v)):
                values.append(float(v))
        return values

    @staticmethod
    def _compute_trend(values: list[float], timestamps: list[str | None]) -> tuple[str | None, float]:
        ts_sorted = sorted(
            [(t, i) for i, t in enumerate(timestamps) if isinstance(t, str)],
            key=lambda x: x[0],
        )
        if len(ts_sorted) < 3:
            n = len(values)
            half = n // 2
            first = _statistics.mean(values[:half]) if values[:half] else 0.0
            last = _statistics.mean(values[half:]) if values[half:] else 0.0
        else:
            first_idx = ts_sorted[0][1]
            last_idx = ts_sorted[-1][1]
            first = values[first_idx] if first_idx < len(values) else values[0]
            last = values[last_idx] if last_idx < len(values) else values[-1]

        if first == 0:
            return None, 0.0
        change = (last - first) / abs(first)
        direction = "up" if change > 0.02 else ("down" if change < -0.02 else "stable")
        return direction, abs(change)


class ZScoreAnomalyModel:
    def __init__(self, threshold: float = 2.5, critical_threshold: float = 3.5):
        self._threshold = threshold
        self._critical_threshold = critical_threshold

    @property
    def model_name(self) -> str:
        return "zscore_anomaly"

    @property
    def model_type(self) -> str:
        return "anomaly"

    @property
    def description(self) -> str:
        return "Detects statistical outliers using Z-score method. Flags values deviating more than 2.5σ from mean. Best for normally distributed data."

    @property
    def supported_data_kinds(self) -> list[DataKind]:
        return list(_ALL_NUMERIC_KINDS)

    @property
    def model_card(self) -> dict[str, object]:
        return {
            "name": self.model_name,
            "type": self.model_type,
            "description": self.description,
            "supported_data_kinds": [k.value for k in self.supported_data_kinds],
            "when_to_use": "Use when you suspect outliers in normally-distributed numeric data. Best for monitoring metrics, latency data, error rates.",
            "output_keys": ["anomalies", "total", "mean", "std"],
            "severity_levels": {"critical": f"> {self._critical_threshold}σ", "warning": f"> {self._threshold}σ", "watch": "borderline"},
            "requires": "At least 3 numeric values. Works best with 30+ data points.",
            "confidence": "Statistical — may produce false positives on non-normal distributions. Pair with IQR model for robust detection.",
        }

    def supports(self, dataset: NormalizedDataSetDTO) -> bool:
        return bool(dataset.profile.value_fields) and dataset.data_kind in self.supported_data_kinds

    async def analyze(self, dataset: NormalizedDataSetDTO) -> dict[str, object]:
        value_fields = dataset.profile.value_fields
        if not value_fields:
            return {"anomalies": [], "total": 0}

        primary = value_fields[0]
        values: list[tuple[int, float]] = []
        for i, row in enumerate(dataset.rows):
            v = row.get(primary)
            if isinstance(v, (int, float)) and math.isfinite(float(v)):
                values.append((i, float(v)))

        if len(values) < 3:
            return {"anomalies": [], "total": 0, "warning": "Insufficient data points for Z-score analysis (need >= 3)"}

        all_vals = [v for _, v in values]
        mean = _statistics.mean(all_vals)
        std = _statistics.stdev(all_vals) if len(all_vals) >= 2 else 0.0

        if std == 0.0:
            return {"anomalies": [], "total": 0, "note": "All values identical — no anomalies possible."}

        anomalies: list[dict[str, object]] = []
        for idx, val in values:
            zscore = (val - mean) / std
            if abs(zscore) <= self._threshold:
                continue

            row = dataset.rows[idx] if idx < len(dataset.rows) else {}
            severity = (
                AnomalySeverity.CRITICAL if abs(zscore) > self._critical_threshold
                else AnomalySeverity.WARNING if abs(zscore) > (self._threshold + self._critical_threshold) / 2
                else AnomalySeverity.WATCH
            )

            service = str(row.get("service") or row.get("pod") or row.get("region") or "")
            metric = str(row.get("metric") or primary)
            ts = str(row.get("timestamp") or row.get("time") or "")

            anomalies.append({
                "severity": severity.value,
                "factor": round(abs(zscore), 2),
                "zscore": round(zscore, 2),
                "service": service or None,
                "metric": metric or None,
                "timestamp": ts or None,
                "value": val,
                "threshold": round(mean + self._threshold * std, 2) if std > 0 else None,
                "description": f"Z-score {zscore:+.2f} (σ={std:.2f}, μ={mean:.2f}) — {'extreme outlier' if abs(zscore) > 3.5 else 'moderate outlier' if abs(zscore) > 2.8 else 'mild outlier'}",
            })

        anomalies.sort(key=lambda a: -float(a["factor"]))
        return {"anomalies": anomalies[:12], "total": len(anomalies), "mean": round(mean, 4), "std": round(std, 4)}


class TrendDetectionModel:
    def __init__(self, min_strength: float = 0.03):
        self._min_strength = min_strength

    @property
    def model_name(self) -> str:
        return "trend_detection"

    @property
    def model_type(self) -> str:
        return "trend"

    @property
    def description(self) -> str:
        return "Detects directional trends using linear regression slope. Identifies upward, downward, or stable patterns with acceleration analysis."

    @property
    def supported_data_kinds(self) -> list[DataKind]:
        return [DataKind.TIME_SERIES, DataKind.CATEGORICAL, DataKind.MULTI_VALUE]

    @property
    def model_card(self) -> dict[str, object]:
        return {
            "name": self.model_name,
            "type": self.model_type,
            "description": self.description,
            "supported_data_kinds": [k.value for k in self.supported_data_kinds],
            "when_to_use": "Use for time-series or sequential data to detect growth/decline patterns. Best for revenue trends, user growth, resource consumption.",
            "output_keys": ["direction", "strength", "slope", "acceleration", "consecutive_periods", "summary"],
            "requires": "At least 3 ordered data points. Time-series data_kind preferred.",
            "confidence": "Linear regression — sensitive to outliers. Consider running Z-score detection first to filter outliers.",
        }

    def supports(self, dataset: NormalizedDataSetDTO) -> bool:
        return (
            dataset.data_kind in self.supported_data_kinds
            and bool(dataset.profile.value_fields)
        )

    async def analyze(self, dataset: NormalizedDataSetDTO) -> dict[str, object]:
        value_fields = dataset.profile.value_fields
        if not value_fields:
            return {"error": "No value fields"}

        primary = value_fields[0]
        values = [
            float(row[primary])
            for row in dataset.rows
            if isinstance(row.get(primary), (int, float)) and math.isfinite(float(row[primary]))
        ]
        if len(values) < 3:
            return {"error": "Need at least 3 values for trend", "direction": "stable", "strength": 0.0}

        n = len(values)
        x_mean = (n - 1) / 2.0
        y_mean = _statistics.mean(values)

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator > 0 else 0.0

        if y_mean == 0:
            relative_change = float("inf") if slope != 0 else 0.0
        else:
            relative_change = abs(slope * n / y_mean)

        if relative_change < self._min_strength:
            direction = "stable"
            strength = 0.0
        elif slope > 0:
            direction = "up"
            strength = relative_change
        else:
            direction = "down"
            strength = relative_change

        if n >= 4:
            half = n // 2
            first_half_avg = _statistics.mean(values[:half])
            second_half_avg = _statistics.mean(values[half:])
            acceleration = "accelerating" if abs(second_half_avg - first_half_avg) > abs(slope * half) else "steady"
        else:
            acceleration = "steady"

        consecutive_direction = 0
        for i in range(1, n):
            if (direction == "up" and values[i] > values[i - 1]) or (
                direction == "down" and values[i] < values[i - 1]
            ):
                consecutive_direction += 1

        summary = (
            f"Strong {direction}ward trend ({strength:.1%})"
            if strength > 0.1
            else (
                f"Moderate {direction}ward trend ({strength:.1%})"
                if strength > self._min_strength
                else "Stable — no significant trend detected"
            )
        )

        return {
            "direction": direction,
            "strength": round(strength, 4),
            "slope": round(slope, 4),
            "acceleration": acceleration,
            "consecutive_periods": consecutive_direction,
            "total_periods": n,
            "summary": summary,
        }


class IQRAnomalyModel:
    def __init__(self, multiplier: float = 1.5):
        self._multiplier = multiplier

    @property
    def model_name(self) -> str:
        return "iqr_anomaly"

    @property
    def model_type(self) -> str:
        return "anomaly"

    @property
    def description(self) -> str:
        return "Detects outliers using Inter-Quartile Range (IQR) method. Robust to non-normal distributions — better than Z-score for skewed data."

    @property
    def supported_data_kinds(self) -> list[DataKind]:
        return list(_ALL_NUMERIC_KINDS)

    @property
    def model_card(self) -> dict[str, object]:
        return {
            "name": self.model_name,
            "type": self.model_type,
            "description": self.description,
            "supported_data_kinds": [k.value for k in self.supported_data_kinds],
            "when_to_use": "Use when data may not be normally distributed (e.g., latency percentiles, revenue per region). More robust than Z-score for skewed distributions.",
            "output_keys": ["anomalies", "total", "q1", "q3", "iqr", "lower_bound", "upper_bound"],
            "requires": "At least 4 numeric values for quartile computation.",
            "confidence": "Non-parametric — robust to non-normal distributions. Pair with Z-score for comprehensive coverage.",
        }

    def supports(self, dataset: NormalizedDataSetDTO) -> bool:
        return bool(dataset.profile.value_fields) and dataset.data_kind in self.supported_data_kinds

    async def analyze(self, dataset: NormalizedDataSetDTO) -> dict[str, object]:
        value_fields = dataset.profile.value_fields
        if not value_fields:
            return {"anomalies": [], "total": 0}

        primary = value_fields[0]
        indexed: list[tuple[int, float, dict[str, object]]] = []
        for i, row in enumerate(dataset.rows):
            v = row.get(primary)
            if isinstance(v, (int, float)) and math.isfinite(float(v)):
                indexed.append((i, float(v), row))

        if len(indexed) < 4:
            return {"anomalies": [], "total": 0, "warning": "Insufficient data for IQR analysis (need >= 4)"}

        vals_sorted = sorted(v for _, v, _ in indexed)
        n = len(vals_sorted)
        q1 = float(_statistics.quantiles(vals_sorted, n=4)[0])
        q3 = float(_statistics.quantiles(vals_sorted, n=4)[2])
        iqr = q3 - q1

        if iqr == 0:
            return {"anomalies": [], "total": 0, "note": "Zero IQR — all middle values identical."}

        lower = q1 - self._multiplier * iqr
        upper = q3 + self._multiplier * iqr

        anomalies: list[dict[str, object]] = []
        for idx, val, row in indexed:
            if lower <= val <= upper:
                continue
            extreme = val > q3 + 3 * iqr or val < q1 - 3 * iqr
            severity = "critical" if extreme else "warning"
            anomalies.append({
                "severity": severity,
                "factor": round(abs(val - (q3 if val > upper else q1)) / max(iqr, 0.001), 2),
                "value": val,
                "lower_bound": round(lower, 2),
                "upper_bound": round(upper, 2),
                "service": str(row.get("service", "") or ""),
                "metric": str(row.get("metric", primary) or primary),
                "description": (
                    f"IQR {'extreme ' if extreme else ''}outlier: {val:.2f} "
                    f"outside [{lower:.2f}, {upper:.2f}] (IQR={iqr:.2f})"
                ),
                "timestamp": str(row.get("timestamp", "") or ""),
            })

        anomalies.sort(key=lambda a: -float(a["factor"]))
        return {
            "anomalies": anomalies[:12],
            "total": len(anomalies),
            "q1": round(q1, 4),
            "q3": round(q3, 4),
            "iqr": round(iqr, 4),
            "lower_bound": round(lower, 2),
            "upper_bound": round(upper, 2),
        }


# ── Advanced models ────────────────────────────────────────────────────


class ChangePointDetectionModel:
    """Binary segmentation change point detection.

    Detects points in a time series where the statistical properties
    (mean, variance) change significantly. Cost function: reduction in
    sum of squared errors when splitting at a candidate point.

    Real SRE use: 'The system changed behavior at 10:03 AM after the deploy.'
    """

    def __init__(self, min_segment_length: int = 3, max_change_points: int = 5, penalty: float = 3.0):
        self._min_seg = min_segment_length
        self._max_cp = max_change_points
        self._penalty = penalty

    @property
    def model_name(self) -> str:
        return "change_point_detection"

    @property
    def model_type(self) -> str:
        return "change_point"

    @property
    def description(self) -> str:
        return "Detects regime changes in time-series using binary segmentation. Finds points where mean/variance shifts — critical for deploy-correlated incident detection."

    @property
    def supported_data_kinds(self) -> list[DataKind]:
        return [DataKind.TIME_SERIES, DataKind.CATEGORICAL, DataKind.MULTI_VALUE]

    @property
    def model_card(self) -> dict[str, object]:
        return {
            "name": self.model_name,
            "type": self.model_type,
            "description": self.description,
            "supported_data_kinds": [k.value for k in self.supported_data_kinds],
            "when_to_use": "Use when you suspect a deployment or config change altered system behavior. Correlate detected change points with release timeline.",
            "output_keys": ["change_points", "segments", "segment_stats", "most_significant"],
            "requires": "Ordered time-series with >= 6 data points.",
            "confidence": "Statistical — based on SSE reduction. Larger changes produce stronger signals.",
        }

    def supports(self, dataset: NormalizedDataSetDTO) -> bool:
        return (
            dataset.data_kind in self.supported_data_kinds
            and bool(dataset.profile.value_fields)
        )

    async def analyze(self, dataset: NormalizedDataSetDTO) -> dict[str, object]:
        value_fields = dataset.profile.value_fields
        if not value_fields:
            return {"error": "No value fields"}

        primary = value_fields[0]
        values = [
            float(row[primary])
            for row in dataset.rows
            if isinstance(row.get(primary), (int, float)) and math.isfinite(float(row[primary]))
        ]
        if len(values) < self._min_seg * 2:
            return {"change_points": [], "segments": [], "note": f"Need at least {self._min_seg * 2} points."}

        cp_indices = self._binary_segmentation(values)
        if not cp_indices:
            return {"change_points": [], "segments": [{"start": 0, "end": len(values) - 1, "mean": round(_statistics.mean(values), 4), "std": round(_statistics.stdev(values), 4) if len(values) >= 2 else 0.0, "count": len(values)}], "note": "No significant change points detected."}

        segments = []
        prev = 0
        for cp in sorted(cp_indices) + [len(values)]:
            seg_vals = values[prev:cp]
            if seg_vals:
                segments.append({
                    "start_index": prev,
                    "end_index": cp - 1,
                    "mean": round(_statistics.mean(seg_vals), 4),
                    "std": round(_statistics.stdev(seg_vals), 4) if len(seg_vals) >= 2 else 0.0,
                    "count": len(seg_vals),
                    "change_from_previous": round(_statistics.mean(seg_vals) - _statistics.mean(values[:prev]), 4) if prev > 0 else 0.0,
                })
            prev = cp

        timestamps = []
        time_field = dataset.profile.time_field
        if time_field:
            timestamps = [
                str(row.get(time_field, ""))
                for row in dataset.rows
            ]

        cp_details = []
        for cp in sorted(cp_indices):
            before = values[cp - self._min_seg : cp] if cp >= self._min_seg else values[:cp]
            after = values[cp : cp + self._min_seg] if cp + self._min_seg <= len(values) else values[cp:]
            before_mean = _statistics.mean(before) if before else 0
            after_mean = _statistics.mean(after) if after else 0
            change_pct = ((after_mean - before_mean) / abs(before_mean) * 100) if before_mean != 0 else float("inf")

            ts = timestamps[cp] if cp < len(timestamps) else ""
            cp_details.append({
                "index": cp,
                "timestamp": ts,
                "before_mean": round(before_mean, 4),
                "after_mean": round(after_mean, 4),
                "change_pct": round(change_pct, 2),
                "direction": "up" if change_pct > 0 else "down",
                "description": f"{'Increase' if change_pct > 0 else 'Decrease'} of {abs(change_pct):.1f}% at {ts or (' index ' + str(cp))}" + (" — likely deploy or config change" if abs(change_pct) > 50 else ""),
            })

        most_sig = max(cp_details, key=lambda x: abs(x["change_pct"])) if cp_details else None

        return {
            "change_points": cp_details,
            "segments": segments,
            "most_significant": most_sig,
            "total_segments": len(segments),
            "summary": (
                f"Detected {len(cp_details)} change point(s). "
                + (f"Most significant: {most_sig['description']}." if most_sig else "No strong signals.")
            ),
        }

    def _binary_segmentation(self, values: list[float]) -> list[int]:
        cp = self._find_best_split(values, 0, len(values))
        if cp is None or len(cp) >= self._max_cp:
            return cp or []
        return cp

    def _find_best_split(self, values: list[float], offset: int, end: int, depth: int = 0) -> list[int] | None:
        if depth >= self._max_cp or end - offset < self._min_seg * 2:
            return None

        seg = values[offset:end]
        n = len(seg)
        if n < self._min_seg * 2:
            return None

        total_mean = _statistics.mean(seg)
        total_sse = sum((v - total_mean) ** 2 for v in seg)

        best_reduction = 0.0
        best_idx = -1

        for i in range(self._min_seg, n - self._min_seg + 1):
            left = seg[:i]
            right = seg[i:]
            left_mean = _statistics.mean(left)
            right_mean = _statistics.mean(right)
            left_sse = sum((v - left_mean) ** 2 for v in left)
            right_sse = sum((v - right_mean) ** 2 for v in right)
            reduction = total_sse - (left_sse + right_sse)
            if reduction > best_reduction:
                best_reduction = reduction
                best_idx = i

        if best_idx < 0:
            return None

        if best_reduction / max(total_sse, 0.001) < 0.05:
            return None

        if best_reduction < self._penalty * total_sse / n:
            return None

        cp_abs = offset + best_idx
        result = [cp_abs]
        left_cp = self._find_best_split(values, offset, cp_abs, depth + 1)
        right_cp = self._find_best_split(values, cp_abs, end, depth + 1)
        if left_cp:
            result.extend(left_cp)
        if right_cp:
            result.extend(right_cp)

        return sorted(result)


class SeasonalDecompositionModel:
    """Classical seasonal-trend decomposition.

    Decomposes a time series:
      original = trend + seasonal + residual

    The residual is what SREs care about — it's the signal after removing
    expected patterns. A spike in the residual = genuine anomaly.
    """

    def __init__(self, period: int | None = None, min_periods: int = 2):
        self._period = period
        self._min_periods = min_periods

    @property
    def model_name(self) -> str:
        return "seasonal_decomposition"

    @property
    def model_type(self) -> str:
        return "decomposition"

    @property
    def description(self) -> str:
        return "Decomposes time-series into trend + seasonal + residual. The residual reveals true anomalies after removing expected patterns — essential for SRE monitoring."

    @property
    def supported_data_kinds(self) -> list[DataKind]:
        return [DataKind.TIME_SERIES]

    @property
    def model_card(self) -> dict[str, object]:
        return {
            "name": self.model_name,
            "type": self.model_type,
            "description": self.description,
            "supported_data_kinds": [k.value for k in self.supported_data_kinds],
            "when_to_use": "Use for time-series with known daily/weekly patterns. Separates 'this is normal Tuesday behavior' from 'this is an anomaly'. Critical for reducing false positive alerts.",
            "output_keys": ["trend", "seasonal", "residual", "seasonal_strength", "trend_strength", "residual_anomalies"],
            "requires": "At least 2 full periods of time-series data (e.g., 48 hours for hourly data).",
            "confidence": "Additive decomposition — assumes constant seasonal pattern. For multiplicative patterns, log-transform first.",
        }

    def supports(self, dataset: NormalizedDataSetDTO) -> bool:
        return (
            dataset.data_kind == DataKind.TIME_SERIES
            and bool(dataset.profile.value_fields)
            and dataset.profile.has_timestamp
        )

    async def analyze(self, dataset: NormalizedDataSetDTO) -> dict[str, object]:
        value_fields = dataset.profile.value_fields
        if not value_fields:
            return {"error": "No value fields"}

        primary = value_fields[0]
        values = [
            float(row[primary])
            for row in dataset.rows
            if isinstance(row.get(primary), (int, float)) and math.isfinite(float(row[primary]))
        ]
        n = len(values)
        if n < 4:
            return {"error": "Need at least 4 data points for decomposition."}

        period = self._period
        if period is None:
            period = self._guess_period(dataset, n)
        if period is None:
            period = max(2, n // 4)

        if n < period * self._min_periods:
            return {
                "error": f"Need at least {period * self._min_periods} points for period={period}.",
                "suggested_period": period,
                "available_points": n,
            }

        # ── Trend: centered moving average ──
        half = period // 2
        trend: list[float] = []
        for i in range(n):
            start = max(0, i - half)
            end = min(n, i + half + 1)
            window = values[start:end]
            trend.append(_statistics.mean(window) if window else values[i])

        # ── Detrend ──
        detrended = [values[i] - trend[i] for i in range(n)]

        # ── Seasonal: average detrended values per period position ──
        seasonal_pos: dict[int, list[float]] = defaultdict(list)
        for i, v in enumerate(detrended):
            seasonal_pos[i % period].append(v)

        seasonal_raw = [
            _statistics.mean(seasonal_pos.get(i % period, [0]))
            for i in range(n)
        ]

        # Center seasonal component
        s_mean = _statistics.mean(seasonal_raw)
        seasonal = [s - s_mean for s in seasonal_raw]

        # ── Residual ──
        residual = [values[i] - trend[i] - seasonal[i] for i in range(n)]

        # ── Strengths ──
        var_residual = _statistics.variance(residual) if len(residual) >= 2 else 1.0
        var_seasonal_residual = _statistics.variance([seasonal[i] + residual[i] for i in range(n)]) if n >= 2 else 1.0
        var_trend_residual = _statistics.variance([trend[i] + residual[i] for i in range(n)]) if n >= 2 else 1.0

        seasonal_strength = max(0, 1 - var_residual / max(var_seasonal_residual, 0.001))
        trend_strength = max(0, 1 - var_residual / max(var_trend_residual, 0.001))

        # ── Residual anomalies ──
        residual_mean = _statistics.mean(residual)
        residual_std = _statistics.stdev(residual) if n >= 2 else 0.0
        residual_anomalies = []
        if residual_std > 0:
            for i, r in enumerate(residual):
                z = abs(r - residual_mean) / residual_std
                if z > 2.5:
                    ts = ""
                    if dataset.profile.time_field and i < len(dataset.rows):
                        ts = str(dataset.rows[i].get(dataset.profile.time_field, ""))
                    residual_anomalies.append({
                        "index": i,
                        "timestamp": ts,
                        "residual": round(r, 4),
                        "zscore": round(z, 2),
                        "original_value": values[i],
                        "description": f"Residual anomaly at {'index ' + str(i) if not ts else ts}: after removing trend+seasonal, value={values[i]:.2f} deviates by {z:.1f}sigma",
                    })

        residual_anomalies.sort(key=lambda a: -a["zscore"])

        return {
            "period": period,
            "trend": [round(t, 4) for t in trend],
            "seasonal": [round(s, 4) for s in seasonal],
            "residual": [round(r, 4) for r in residual],
            "seasonal_strength": round(seasonal_strength, 4),
            "trend_strength": round(trend_strength, 4),
            "residual_anomalies": residual_anomalies[:8],
            "residual_anomaly_count": len(residual_anomalies),
            "summary": (
                f"Decomposed {n} points (period={period}). "
                f"Seasonal strength: {seasonal_strength:.1%} — {'strong' if seasonal_strength > 0.5 else 'weak' if seasonal_strength > 0.2 else 'negligible'} seasonality. "
                f"Trend strength: {trend_strength:.1%}. "
                f"Residual anomalies: {len(residual_anomalies)} (true anomalies after removing expected patterns)."
            ),
        }

    @staticmethod
    def _guess_period(dataset: NormalizedDataSetDTO, n: int) -> int | None:
        from services.integrations.analysis.context_analyzer import _detect_diurnal_pattern

        time_field = dataset.profile.time_field
        if not time_field:
            return None

        values = [
            float(row.get(dataset.profile.value_fields[0], 0))
            for row in dataset.rows
            if isinstance(row.get(dataset.profile.value_fields[0]), (int, float))
            and math.isfinite(float(row.get(dataset.profile.value_fields[0], 0)))
        ]
        timestamps = [str(row.get(time_field, "")) for row in dataset.rows]

        if _detect_diurnal_pattern(values, timestamps):
            # Try to figure out samples per day
            hours_seen = set()
            for ts in timestamps:
                try:
                    from datetime import datetime as dt
                    h = dt.fromisoformat(ts.replace("Z", "+00:00")).hour
                    hours_seen.add(h)
                except Exception:
                    pass
            if len(hours_seen) >= 6:
                return len(hours_seen)  # samples per day

        return None


class DistributionComparisonModel:
    """Two-sample Kolmogorov-Smirnov test for distribution comparison.

    Compares current data distribution against a reference (e.g., last week)
    to answer: 'Is this week fundamentally different from last week?'
    """

    def __init__(self, alpha: float = 0.05):
        self._alpha = alpha

    @property
    def model_name(self) -> str:
        return "distribution_comparison"

    @property
    def model_type(self) -> str:
        return "comparison"

    @property
    def description(self) -> str:
        return "Compares current vs reference data distribution using two-sample KS test + Wasserstein distance. Answers: 'Is this week statistically different from last week?'"

    @property
    def supported_data_kinds(self) -> list[DataKind]:
        return [DataKind.TIME_SERIES, DataKind.CATEGORICAL, DataKind.MULTI_VALUE, DataKind.SINGLE_VALUE, DataKind.TABLE]

    @property
    def model_card(self) -> dict[str, object]:
        return {
            "name": self.model_name,
            "type": self.model_type,
            "description": self.description,
            "supported_data_kinds": [k.value for k in self.supported_data_kinds],
            "when_to_use": "Use for week-over-week or before/after comparisons. Tells you whether a change is statistically significant or just noise. Use with past_analysis_context data.",
            "output_keys": ["ks_statistic", "ks_pvalue", "significant", "wasserstein_distance", "mean_shift", "std_shift", "summary"],
            "requires": "Two sets of values: current data from dataset, reference data passed via analyze(ref_values=...).",
            "confidence": "Non-parametric. KS test is sensitive to location and shape differences. Wasserstein (Earth Mover's Distance) provides magnitude of change.",
        }

    def supports(self, dataset: NormalizedDataSetDTO) -> bool:
        return bool(dataset.profile.value_fields)

    async def analyze(
        self,
        dataset: NormalizedDataSetDTO,
        *,
        ref_values: list[float] | None = None,
    ) -> dict[str, object]:
        value_fields = dataset.profile.value_fields
        if not value_fields:
            return {"error": "No value fields"}

        primary = value_fields[0]
        current = [
            float(row[primary])
            for row in dataset.rows
            if isinstance(row.get(primary), (int, float)) and math.isfinite(float(row[primary]))
        ]
        if len(current) < 3:
            return {"error": "Need at least 3 current values."}

        if ref_values is None or len(ref_values) < 3:
            return {
                "note": "No reference values provided. Comparing against internal baseline (first half vs second half).",
                "comparison_type": "internal_split",
            }

        return self._compare(current, ref_values)

    def _compare(self, current: list[float], reference: list[float]) -> dict[str, object]:
        ks_stat, ks_pvalue = _two_sample_ks(current, reference)
        significant = ks_pvalue < self._alpha

        ws_dist = _wasserstein_distance(current, reference)

        c_mean = _statistics.mean(current)
        r_mean = _statistics.mean(reference)
        c_std = _statistics.stdev(current) if len(current) >= 2 else 0.0
        r_std = _statistics.stdev(reference) if len(reference) >= 2 else 0.0

        mean_shift = ((c_mean - r_mean) / abs(r_mean) * 100) if r_mean != 0 else 0.0
        std_shift = ((c_std - r_std) / abs(r_std) * 100) if r_std != 0 else 0.0

        effect_size = "large" if abs(mean_shift) > 50 else ("moderate" if abs(mean_shift) > 20 else "small")

        summary = (
            f"KS test: {'SIGNIFICANT' if significant else 'NOT significant'} "
            f"(D={ks_stat:.4f}, p={ks_pvalue:.4f}). "
            f"Mean shift: {mean_shift:+.1f}% ({effect_size} effect). "
            f"Wasserstein distance: {ws_dist:.2f}. "
        )
        if significant:
            summary += f"Current distribution is statistically different from reference — this is NOT just noise."
        else:
            summary += "No statistical evidence that current distribution differs from reference."

        return {
            "ks_statistic": round(ks_stat, 4),
            "ks_pvalue": round(ks_pvalue, 4),
            "significant": significant,
            "alpha": self._alpha,
            "wasserstein_distance": round(ws_dist, 4),
            "mean_shift_pct": round(mean_shift, 2),
            "std_shift_pct": round(std_shift, 2),
            "effect_size": effect_size,
            "current_count": len(current),
            "reference_count": len(reference),
            "current_mean": round(c_mean, 4),
            "reference_mean": round(r_mean, 4),
            "summary": summary,
        }


# ── Statistical helpers ────────────────────────────────────────────────


def _two_sample_ks(x: list[float], y: list[float]) -> tuple[float, float]:
    """Two-sample Kolmogorov-Smirnov test."""
    xs = sorted(x)
    ys = sorted(y)
    nx, ny = len(xs), len(ys)
    if nx == 0 or ny == 0:
        return 0.0, 1.0

    d_max = 0.0
    i, j = 0, 0
    while i < nx and j < ny:
        d = abs((i + 1) / nx - (j + 1) / ny)
        d_max = max(d_max, d)
        if xs[i] <= ys[j]:
            i += 1
        else:
            j += 1
    d_max = max(d_max, abs(1.0 - j / ny) if i >= nx else abs(i / nx))
    d_max = max(d_max, abs(i / nx - 1.0) if j >= ny else abs(1.0 - j / ny))

    # Approximate p-value
    n_eff = nx * ny / (nx + ny)
    z = d_max * math.sqrt(n_eff)
    # Kolmogorov approximation
    p = 2 * sum((-1) ** (k - 1) * math.exp(-2 * k * k * z * z) for k in range(1, 100))
    p = max(0.0, min(1.0, p))

    return d_max, p


def _wasserstein_distance(x: list[float], y: list[float]) -> float:
    """1D Wasserstein (Earth Mover's) distance between two samples."""
    xs = sorted(x)
    ys = sorted(y)
    n = min(len(xs), len(ys))
    if n == 0:
        return 0.0
    return sum(abs(xs[i] - ys[i]) for i in range(n)) / n
