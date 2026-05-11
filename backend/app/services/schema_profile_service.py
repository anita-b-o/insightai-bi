from __future__ import annotations

import logging

from app.models.dataset import Dataset
from app.services.column_semantic_service import classify_column_semantics

logger = logging.getLogger(__name__)


def infer_semantic_type(*, inferred_type: str, column_name: str, sample_value: str | None) -> str:
    semantic_profile = classify_column_semantics(
        column_name=column_name,
        inferred_type=inferred_type,
        distinct_count=None,
        sample_values=[sample_value] if sample_value is not None else [],
        row_count=None,
    )
    return str(semantic_profile["semantic_type"])


def cardinality_bucket(distinct_count: int | None) -> str:
    if distinct_count is None:
        return "unknown"
    if distinct_count <= 8:
        return "low"
    if distinct_count <= 30:
        return "medium"
    return "high"


def build_dataset_schema_profile(dataset: Dataset) -> list[dict[str, object]]:
    profile: list[dict[str, object]] = []
    row_count = getattr(dataset, "row_count", None)
    columns = getattr(dataset, "columns", None) or []
    for column in columns:
        column_name = getattr(column, "name", None)
        inferred_type = getattr(column, "inferred_type", "string")
        distinct_count = getattr(column, "distinct_count", None)
        sample_value = getattr(column, "sample_value", None)
        semantic_profile = classify_column_semantics(
            column_name=column_name,
            inferred_type=inferred_type,
            distinct_count=distinct_count,
            sample_values=[sample_value] if sample_value is not None else [],
            row_count=row_count,
        )
        profile.append(
            {
                "display_name": column_name,
                "sql_name": getattr(column, "sql_name", None) or column_name,
                "inferred_type": inferred_type,
                "semantic_type": semantic_profile["semantic_type"],
                "is_metric": semantic_profile["is_metric"],
                "is_dimension": semantic_profile["is_dimension"],
                "usable_for_correlation": semantic_profile["usable_for_correlation"],
                "usable_for_grouping": semantic_profile["usable_for_grouping"],
                "nullable": getattr(column, "nullable", True),
                "distinct_count": distinct_count,
                "cardinality": cardinality_bucket(distinct_count),
                "sample_value": sample_value,
                "row_count": row_count,
            }
        )
    logger.info("Column semantic classification: %s", profile)
    return profile


def get_schema_profile_entry(dataset: Dataset, column_name: str) -> dict[str, object] | None:
    normalized = column_name.lower()
    for item in build_dataset_schema_profile(dataset):
        sql_name = str(item["sql_name"]).lower()
        display_name = str(item["display_name"]).lower()
        if normalized in {sql_name, display_name}:
            return item
    return None
