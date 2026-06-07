"""
LTTB (Largest Triangle Three Buckets) downsampling for time-series data.

Preserves visual features (peaks, valleys, trend changes) while reducing
data point count to fit chart rendering limits. This is the algorithm used
by Grafana for its own chart downsampling.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from services.integrations.dto import ChartDatumDTO, DataKind, NormalizedDataSetDTO


def lttb_downsample(
    data: list[tuple[float, float]],
    target_points: int,
) -> list[tuple[float, float]]:
    """
    Largest Triangle Three Buckets downsampling.

    Preserves the visual characteristics of the data (peaks, valleys,
    inflection points) by selecting the point in each bucket that forms
    the largest triangle with the selected point from the previous bucket
    and the average point of the next bucket.

    Args:
        data: List of (x_timestamp_or_index, y_value) tuples, sorted by x.
        target_points: Desired number of output points (minimum 3).

    Returns:
        Downsampled list of (x, y) tuples.
    """
    if not data:
        return []

    n = len(data)
    if n <= target_points:
        return data

    target_points = max(3, min(target_points, n))

    # Always keep first and last points
    result: list[tuple[float, float]] = [data[0]]

    bucket_size = (n - 2) / (target_points - 2)

    prev_selected = 0  # index of last selected point in data

    for bucket_idx in range(1, target_points - 1):
        bucket_start = int((bucket_idx - 1) * bucket_size) + 1
        bucket_end = int(bucket_idx * bucket_size) + 1
        bucket_end = min(bucket_end, n - 1)
        next_bucket_start = bucket_end
        next_bucket_end = int((bucket_idx + 1) * bucket_size) + 1
        next_bucket_end = min(next_bucket_end, n)

        # Average point of the next bucket (for area calculation)
        next_avg_x = 0.0
        next_avg_y = 0.0
        next_count = next_bucket_end - next_bucket_start
        if next_count > 0:
            for j in range(next_bucket_start, next_bucket_end):
                next_avg_x += data[j][0]
                next_avg_y += data[j][1]
            next_avg_x /= next_count
            next_avg_y /= next_count

        # Find point in current bucket with largest triangle area
        max_area = -1.0
        max_idx = bucket_start

        p_x, p_y = data[prev_selected]
        for idx in range(bucket_start, bucket_end):
            a_x, a_y = data[idx]
            # Triangle area = |(p_x - n_x)*(a_y - p_y) - (p_x - a_x)*(n_y - p_y)| / 2
            area = abs(
                (p_x - next_avg_x) * (a_y - p_y)
                - (p_x - a_x) * (next_avg_y - p_y)
            ) * 0.5
            if area > max_area:
                max_area = area
                max_idx = idx

        result.append(data[max_idx])
        prev_selected = max_idx

    # Last point
    result.append(data[-1])

    return result


def build_chart_data_intelligent(
    dataset: NormalizedDataSetDTO,
    *,
    max_points: int = 12,
    anomaly_weight: float = 2.0,
) -> list[ChartDatumDTO]:
    """
    Intelligent chart data builder with LTTB downsampling for time-series
    and importance-based selection for categorical data.

    For time-series: Uses LTTB to preserve visual features (peaks/valleys).
    For categorical: Selects top-N by absolute value, ensures anomalies are kept.
    """
    rows = dataset.rows
    if not rows:
        return []

    value_fields = dataset.profile.value_fields
    if not value_fields:
        return []

    primary = value_fields[0]
    time_field = dataset.profile.time_field

    if time_field and dataset.data_kind == DataKind.TIME_SERIES:
        return _build_time_series_chart(rows, primary, time_field, max_points, anomaly_weight)

    return _build_categorical_chart(rows, primary, dataset, max_points, anomaly_weight)


def _build_time_series_chart(
    rows: list[dict[str, object]],
    primary_field: str,
    time_field: str,
    max_points: int,
    anomaly_weight: float,
) -> list[ChartDatumDTO]:
    """Build time-series chart data with LTTB downsampling."""
    points: list[tuple[float, float]] = []
    for i, row in enumerate(rows):
        v = row.get(primary_field)
        if isinstance(v, (int, float)) and math.isfinite(float(v)):
            ts = row.get(time_field)
            if isinstance(ts, str):
                try:
                    from datetime import datetime as dt
                    parsed = dt.fromisoformat(ts.replace("Z", "+00:00"))
                    x_val = parsed.timestamp()
                except (ValueError, TypeError):
                    x_val = float(i)
            else:
                x_val = float(i)
            points.append((x_val, float(v)))

    if not points:
        return []
    if len(points) <= max_points:
        return [ChartDatumDTO(label=_format_label(p[0], rows, time_field), value=p[1]) for p in points]

    # Compute anomaly scores for weighting
    values = [p[1] for p in points]
    mean_v = sum(values) / len(values)
    std_v = math.sqrt(sum((v - mean_v) ** 2 for v in values) / len(values)) if len(values) > 1 else 1.0

    anomaly_scores: dict[int, float] = {}
    for i, (_, v) in enumerate(points):
        z = abs(v - mean_v) / max(std_v, 0.001)
        if z > 1.5:
            anomaly_scores[i] = z * anomaly_weight

    downsampled = lttb_downsample(points, max_points)
    result: list[ChartDatumDTO] = []

    # Ensure anomaly points are included
    down_x_set = {d[0] for d in downsampled}
    for idx, weight in sorted(anomaly_scores.items(), key=lambda x: -x[1]):
        if idx < len(points) and points[idx][0] not in down_x_set and len(result) < max_points:
            p = points[idx]
            result.append(ChartDatumDTO(label=_format_label(p[0], rows, time_field), value=p[1]))
            down_x_set.add(p[0])

    for p in downsampled:
        if len(result) >= max_points:
            break
        if p[0] not in {d.label for d in result}:
            result.append(ChartDatumDTO(label=_format_label(p[0], rows, time_field), value=p[1]))

    result.sort(key=lambda d: d.label)
    return result[:max_points]


def _build_categorical_chart(
    rows: list[dict[str, object]],
    primary_field: str,
    dataset: NormalizedDataSetDTO,
    max_points: int,
    anomaly_weight: float,
) -> list[ChartDatumDTO]:
    """Build categorical chart data, selecting most significant points."""
    label_field = next(
        (f for f in [dataset.profile.series_field, *dataset.profile.label_fields]
         if f is not None),
        None,
    )

    # Collect all valid entries
    entries: list[tuple[str, float]] = []
    for row in rows:
        v = row.get(primary_field)
        if isinstance(v, (int, float)) and math.isfinite(float(v)):
            label = str(row.get(label_field or primary_field, ""))[:24] if label_field else ""
            entries.append((label, float(v)))

    if not entries:
        return []

    # Compute "importance" = abs(value) × anomaly_factor
    values = [v for _, v in entries]
    mean_v = sum(values) / len(values)
    std_v = math.sqrt(sum((v - mean_v) ** 2 for v in values) / len(values)) if len(values) > 1 else 1.0

    scored: list[tuple[str, float, float]] = []
    for label, val in entries:
        z = abs(val - mean_v) / max(std_v, 0.001)
        importance = abs(val) * (1.0 + z * (anomaly_weight - 1.0)) if z > 1.0 else abs(val)
        scored.append((label, val, importance))

    # Sort by importance descending
    scored.sort(key=lambda x: -x[2])

    # Select top-N, deduplicating by label
    result: list[ChartDatumDTO] = []
    seen_labels: set[str] = set()
    for label, val, _ in scored:
        if label in seen_labels:
            continue
        seen_labels.add(label)
        result.append(ChartDatumDTO(label=label or "?", value=val))
        if len(result) >= max_points:
            break

    return result


def _format_label(x_val: float, rows: list[dict[str, object]], time_field: str) -> str:
    """Create a readable label from a timestamp or index."""
    from datetime import datetime as dt, timezone as tz

    try:
        d = dt.fromtimestamp(x_val, tz=tz.utc)
        return d.strftime("%H:%M")
    except (ValueError, OSError):
        pass
    try:
        return str(dt.fromtimestamp(x_val))
    except (ValueError, OSError):
        return str(round(x_val, 0))

__all__ = ["lttb_downsample", "build_chart_data_intelligent"]
