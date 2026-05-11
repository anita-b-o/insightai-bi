from __future__ import annotations

from dataclasses import dataclass
from math import log2
from pathlib import Path

import pandas as pd

from app.models.dataset import Dataset

MAX_FEATURE_SELECTION_ROWS = 100_000


@dataclass(slots=True)
class FeatureScore:
    column: str
    semantic_type: str
    variance: float
    correlation_strength: float
    entropy: float
    cardinality: float
    non_null_ratio: float
    outlier_score: float
    final_score: float


def _normalize_series(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    minimum = min(values.values())
    maximum = max(values.values())
    if maximum - minimum <= 1e-12:
        return {key: (1.0 if maximum > 0 else 0.0) for key in values}
    return {key: (value - minimum) / (maximum - minimum) for key, value in values.items()}


def _sample_dataset(dataframe: pd.DataFrame) -> pd.DataFrame:
    if len(dataframe) <= MAX_FEATURE_SELECTION_ROWS:
        return dataframe
    return dataframe.sample(n=MAX_FEATURE_SELECTION_ROWS, random_state=42)


def _profile_lookup(schema_profile: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    lookup: dict[str, dict[str, object]] = {}
    for item in schema_profile:
        display_name = str(item.get("display_name") or "").strip()
        sql_name = str(item.get("sql_name") or display_name).strip()
        if display_name:
            lookup[display_name] = item
        if sql_name:
            lookup[sql_name] = item
    return lookup


def _resolve_profile(column: str, lookup: dict[str, dict[str, object]]) -> dict[str, object]:
    return lookup.get(column, {"display_name": column, "sql_name": column, "semantic_type": "categorical"})


def _is_numeric_semantic(profile: dict[str, object]) -> bool:
    return str(profile.get("semantic_type") or "") in {"metric", "numeric"}


def _is_categorical_semantic(profile: dict[str, object]) -> bool:
    return str(profile.get("semantic_type") or "") == "categorical"


def _compute_numeric_variance(series: pd.Series) -> float:
    numeric_series = pd.to_numeric(series, errors="coerce").dropna()
    if len(numeric_series) <= 1:
        return 0.0
    return float(numeric_series.var(ddof=0))


def _compute_numeric_outlier_ratio(series: pd.Series) -> float:
    numeric_series = pd.to_numeric(series, errors="coerce").dropna()
    if len(numeric_series) < 4:
        return 0.0

    q1 = numeric_series.quantile(0.25)
    q3 = numeric_series.quantile(0.75)
    iqr = q3 - q1
    if iqr <= 1e-12:
        return 0.0

    lower = q1 - (1.5 * iqr)
    upper = q3 + (1.5 * iqr)
    outlier_ratio = ((numeric_series < lower) | (numeric_series > upper)).mean()
    return float(outlier_ratio)


def _compute_categorical_entropy(series: pd.Series) -> float:
    value_counts = series.dropna().astype(str).value_counts(normalize=True)
    if value_counts.empty:
        return 0.0

    entropy = -sum(float(probability) * log2(float(probability)) for probability in value_counts.values if probability > 0)
    max_entropy = log2(len(value_counts)) if len(value_counts) > 1 else 0.0
    if max_entropy <= 1e-12:
        return 0.0
    return float(entropy / max_entropy)


def compute_feature_scores(dataset: pd.DataFrame, schema_profile: list[dict[str, object]]) -> list[FeatureScore]:
    sampled = _sample_dataset(dataset)
    profile_by_name = _profile_lookup(schema_profile)

    numeric_columns: list[str] = []
    numeric_variances: dict[str, float] = {}
    numeric_outlier_ratios: dict[str, float] = {}
    for column in sampled.columns:
        profile = _resolve_profile(column, profile_by_name)
        if _is_numeric_semantic(profile):
            numeric_columns.append(column)
            numeric_variances[column] = _compute_numeric_variance(sampled[column])
            numeric_outlier_ratios[column] = _compute_numeric_outlier_ratio(sampled[column])

    correlation_strengths: dict[str, float] = {column: 0.0 for column in sampled.columns}
    if len(numeric_columns) >= 2:
        numeric_frame = sampled[numeric_columns].apply(pd.to_numeric, errors="coerce")
        correlation_matrix = numeric_frame.corr().abs()
        for column in numeric_columns:
            correlations = correlation_matrix[column].drop(labels=[column], errors="ignore").dropna()
            correlation_strengths[column] = float(correlations.mean()) if not correlations.empty else 0.0

    normalized_variances = _normalize_series(numeric_variances)
    normalized_correlations = _normalize_series({column: correlation_strengths.get(column, 0.0) for column in numeric_columns})
    normalized_outliers = _normalize_series(numeric_outlier_ratios)

    results: list[FeatureScore] = []
    row_count = max(len(sampled), 1)
    for column in sampled.columns:
        profile = _resolve_profile(column, profile_by_name)
        semantic_type = str(profile.get("semantic_type") or "categorical")
        series = sampled[column]
        non_null_ratio = float(series.notna().mean())
        distinct_count = int(series.nunique(dropna=True))
        cardinality = min(distinct_count / row_count, 1.0)

        entropy = _compute_categorical_entropy(series) if _is_categorical_semantic(profile) else 0.0
        variance = normalized_variances.get(column, 0.0)
        correlation_strength = normalized_correlations.get(column, 0.0)
        outlier_score = normalized_outliers.get(column, 0.0)

        if semantic_type in {"identifier", "constant", "low_variance", "geographic_lat", "geographic_lon"}:
            final_score = 0.0
        else:
            weighted_components = [
                (variance, 0.25 if _is_numeric_semantic(profile) else 0.0),
                (correlation_strength, 0.25 if _is_numeric_semantic(profile) else 0.0),
                (entropy, 0.25 if _is_categorical_semantic(profile) else 0.0),
                (cardinality, 0.10),
                (non_null_ratio, 0.10),
                (outlier_score, 0.05 if _is_numeric_semantic(profile) else 0.0),
            ]
            active_weight = sum(weight for _, weight in weighted_components if weight > 0)
            weighted_sum = sum(value * weight for value, weight in weighted_components)
            final_score = (weighted_sum / active_weight) if active_weight > 0 else 0.0

        results.append(
            FeatureScore(
                column=column,
                semantic_type=semantic_type,
                variance=variance,
                correlation_strength=correlation_strength,
                entropy=entropy,
                cardinality=cardinality,
                non_null_ratio=non_null_ratio,
                outlier_score=outlier_score,
                final_score=max(0.0, min(1.0, final_score)),
            )
        )

    results.sort(key=lambda item: item.final_score, reverse=True)
    return results


def select_top_features(scores: list[FeatureScore], k: int = 5) -> list[FeatureScore]:
    if k <= 0:
        return []
    return sorted(scores, key=lambda item: item.final_score, reverse=True)[:k]


def load_dataset_dataframe(dataset: Dataset) -> pd.DataFrame:
    csv_path = Path(dataset.storage_path)
    return pd.read_csv(csv_path)
