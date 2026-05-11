from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any


TEMPORAL_NAME_TOKENS = ("date", "time", "day", "month", "year", "week", "quarter", "timestamp")
LATITUDE_NAME_TOKENS = ("lat", "latitude", "centroide_lat", "coord_lat")
LONGITUDE_NAME_TOKENS = ("lon", "lng", "longitude", "centroide_lon", "coord_lon")


def _normalize_values(sample_values: Sequence[object] | object | None) -> list[object]:
    if sample_values is None:
        return []
    if isinstance(sample_values, (str, int, float, bool)):
        return [sample_values]
    return [value for value in sample_values if value is not None]


def _parse_numeric_value(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    normalized = value.strip().replace(",", "")
    if not normalized:
        return None
    try:
        return float(normalized)
    except ValueError:
        return None


def _is_temporal_value(value: object) -> bool:
    if not isinstance(value, str):
        return False

    candidate = value.strip()
    if not candidate:
        return False

    if len(candidate) >= 10 and candidate[4:5] == "-" and candidate[7:8] == "-":
        try:
            datetime.fromisoformat(candidate.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False

    for date_format in ("%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            datetime.strptime(candidate[:10], date_format)
            return True
        except ValueError:
            continue
    return False


def _is_identifier_name(column_name: str) -> bool:
    normalized = column_name.strip().lower()
    return normalized == "id" or normalized.endswith("_id")


def _has_any_token(column_name: str, tokens: tuple[str, ...]) -> bool:
    normalized = column_name.strip().lower()
    return any(token in normalized for token in tokens)


def _infer_geographic_type(column_name: str, numeric_values: Sequence[float]) -> str | None:
    if not numeric_values:
        return None

    if _has_any_token(column_name, LATITUDE_NAME_TOKENS) and all(-90 <= value <= 90 for value in numeric_values):
        return "geographic_lat"
    if _has_any_token(column_name, LONGITUDE_NAME_TOKENS) and all(-180 <= value <= 180 for value in numeric_values):
        return "geographic_lon"
    return None


def _is_low_variance_numeric(distinct_count: int | None, row_count: int | None) -> bool:
    if distinct_count is None:
        return False
    if distinct_count <= 1:
        return False
    if distinct_count <= 2:
        return True
    if isinstance(row_count, int) and row_count > 0 and distinct_count <= 5:
        return (distinct_count / row_count) <= 0.02
    return False


def _is_high_cardinality_text(distinct_count: int | None, row_count: int | None) -> bool:
    if not isinstance(distinct_count, int) or not isinstance(row_count, int) or row_count <= 0:
        return False
    if distinct_count < 20:
        return False
    return (distinct_count / row_count) >= 0.5


def _is_metric_numeric(distinct_count: int | None, row_count: int | None) -> bool:
    if not isinstance(distinct_count, int):
        return True
    if isinstance(row_count, int) and row_count > 0:
        return (distinct_count / row_count) >= 0.1 or distinct_count >= 10
    return distinct_count >= 5


def classify_column_semantics(
    *,
    column_name: str,
    inferred_type: str,
    distinct_count: int | None,
    sample_values: Sequence[object] | object | None,
    row_count: int | None,
) -> dict[str, Any]:
    normalized_type = inferred_type.strip().lower()
    normalized_samples = _normalize_values(sample_values)
    numeric_values = [value for value in (_parse_numeric_value(item) for item in normalized_samples) if value is not None]

    semantic_type = "categorical"
    is_metric = False
    is_dimension = False
    usable_for_correlation = False
    usable_for_grouping = False

    if distinct_count == 1:
        semantic_type = "constant"
    elif _is_identifier_name(column_name):
        semantic_type = "identifier"
    elif normalized_type in {"datetime", "date"} or _has_any_token(column_name, TEMPORAL_NAME_TOKENS) or any(
        _is_temporal_value(item) for item in normalized_samples
    ):
        semantic_type = "temporal"
        is_dimension = True
        usable_for_grouping = True
    elif normalized_type in {"integer", "float"}:
        geographic_type = _infer_geographic_type(column_name, numeric_values)
        if geographic_type is not None:
            semantic_type = geographic_type
        elif _is_low_variance_numeric(distinct_count, row_count):
            semantic_type = "low_variance"
        elif _is_metric_numeric(distinct_count, row_count):
            semantic_type = "metric"
            is_metric = True
            usable_for_correlation = True
        else:
            semantic_type = "categorical"
            is_dimension = True
            usable_for_grouping = True
    elif normalized_type == "boolean":
        semantic_type = "categorical"
        is_dimension = True
        usable_for_grouping = True
    elif _is_high_cardinality_text(distinct_count, row_count):
        semantic_type = "high_cardinality_text"
    else:
        semantic_type = "categorical"
        is_dimension = True
        usable_for_grouping = True

    return {
        "column": column_name,
        "semantic_type": semantic_type,
        "is_metric": is_metric,
        "is_dimension": is_dimension,
        "usable_for_correlation": usable_for_correlation,
        "usable_for_grouping": usable_for_grouping,
    }
