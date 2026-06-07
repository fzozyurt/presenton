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
