from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime, timezone
from itertools import combinations
import logging
import re
import time

from fastapi import HTTPException, status
from sqlalchemy import desc, select, text
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.observability import log_event
from app.models.dataset import Dataset
from app.models.dataset_insight_run import DatasetInsightRun
from app.models.user import User
from app.schemas.ai import AIInsight, AIInsightNarrative, AIInsightsResponse, DatasetInsightRunDetail, DatasetInsightRunSummary
from app.services.ai_service import build_visualization_suggestion
from app.services.feature_selection_service import FeatureScore, compute_feature_scores, load_dataset_dataframe, select_top_features
from app.services.insight_narrative_service import build_insight_narrative
from app.services.insight_ranking_service import deduplicate_insights, rank_insights, select_top_insights
from app.services.openai_service import request_openai_text
from app.services.query_executor import ensure_dataset_queryable
from app.services.schema_profile_service import build_dataset_schema_profile

logger = logging.getLogger(__name__)


def _to_iso8601(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _load_owned_dataset(db: Session, *, dataset_id: int, user_id: int) -> Dataset:
    dataset = (
        db.query(Dataset)
        .options(joinedload(Dataset.columns))
        .filter(Dataset.id == dataset_id, Dataset.owner_id == user_id)
        .first()
    )
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset


def _get_owned_insight_run(db: Session, *, run_id: int, user_id: int) -> DatasetInsightRun | None:
    statement = (
        select(DatasetInsightRun)
        .options(joinedload(DatasetInsightRun.dataset))
        .where(DatasetInsightRun.id == run_id, DatasetInsightRun.user_id == user_id)
    )
    return db.execute(statement).unique().scalar_one_or_none()


def _run_sql(db: Session, sql: str) -> tuple[list[str], list[dict[str, object]]]:
    result = db.execute(text(sql))
    columns = list(result.keys())
    rows = [dict(row._mapping) for row in result.fetchall()]
    return columns, rows


def _is_stale(dataset_updated_at: datetime, snapshot: datetime) -> bool:
    left = dataset_updated_at if dataset_updated_at.tzinfo else dataset_updated_at.replace(tzinfo=timezone.utc)
    right = snapshot if snapshot.tzinfo else snapshot.replace(tzinfo=timezone.utc)
    return left > right


def _pick_preferred_numeric(profile: Sequence[dict[str, object]]) -> dict[str, object] | None:
    preferred_tokens = ("revenue", "sales", "amount", "price", "cost", "profit", "total", "count", "quantity")

    def score(item: dict[str, object]) -> tuple[int, int]:
        name = str(item["sql_name"]).lower()
        matched = 1 if any(token in name for token in preferred_tokens) else 0
        distinct_count = item.get("distinct_count")
        numeric_rank = distinct_count if isinstance(distinct_count, int) else 0
        return (matched, numeric_rank)

    return max(profile, key=score, default=None)


def _pick_preferred_categorical(profile: Sequence[dict[str, object]]) -> dict[str, object] | None:
    eligible = [
        item
        for item in profile
        if item.get("semantic_type") == "categorical"
        and item.get("cardinality") in {"low", "medium"}
        and isinstance(item.get("sql_name"), str)
        and isinstance(item.get("distinct_count"), int)
        and int(item["distinct_count"]) > 1
    ]
    return min(
        eligible,
        key=lambda item: item.get("distinct_count") if isinstance(item.get("distinct_count"), int) else 999_999,
        default=None,
    )


def _is_metric_profile(column: dict[str, object]) -> bool:
    is_metric = column.get("is_metric")
    if isinstance(is_metric, bool):
        return is_metric
    return column.get("semantic_type") in {"metric", "numeric"}


def _is_grouping_profile(column: dict[str, object]) -> bool:
    usable_for_grouping = column.get("usable_for_grouping")
    if isinstance(usable_for_grouping, bool):
        return usable_for_grouping
    return column.get("semantic_type") in {"categorical", "temporal"}


def _is_temporal_profile(column: dict[str, object]) -> bool:
    return column.get("semantic_type") == "temporal"


def _is_correlation_profile(column: dict[str, object]) -> bool:
    usable_for_correlation = column.get("usable_for_correlation")
    if isinstance(usable_for_correlation, bool):
        return usable_for_correlation
    return column.get("semantic_type") in {"metric", "numeric"}


def _is_valid_dimension_profile(column: dict[str, object] | None) -> bool:
    if column is None:
        return False
    if column.get("semantic_type") != "categorical":
        return False
    distinct_count = column.get("distinct_count")
    return isinstance(distinct_count, int) and distinct_count > 1 and _is_grouping_profile(column)


def _has_real_variability(column: dict[str, object] | None) -> bool:
    if column is None:
        return False
    distinct_count = column.get("distinct_count")
    if not isinstance(distinct_count, int):
        return False
    return distinct_count > 1 and column.get("semantic_type") not in {"constant", "low_variance"}


def _has_adequate_cardinality(column: dict[str, object] | None) -> bool:
    if column is None:
        return False
    distinct_count = column.get("distinct_count")
    if not isinstance(distinct_count, int):
        return False
    semantic_type = str(column.get("semantic_type") or "")
    if semantic_type == "categorical":
        return 2 <= distinct_count <= 20
    if semantic_type in {"metric", "numeric"}:
        return distinct_count >= 5
    if semantic_type == "temporal":
        return distinct_count >= 2
    return False


def _column_penalty(column: dict[str, object] | None) -> int:
    if column is None:
        return 0
    semantic_type = str(column.get("semantic_type") or "")
    if semantic_type == "constant":
        return 50
    if semantic_type == "identifier":
        return 40
    return 0


def _score_insight_quality(
    *,
    dataset: Dataset,
    metric_column: dict[str, object] | None = None,
    dimension_column: dict[str, object] | None = None,
    allow_metric_dimension: bool = False,
) -> int:
    score = 0

    valid_metric = metric_column is not None and _is_metric_profile(metric_column)
    valid_dimension = (
        dimension_column is None
        or _is_valid_dimension_profile(dimension_column)
        or _is_temporal_profile(dimension_column)
        or (allow_metric_dimension and dimension_column is not None and _is_metric_profile(dimension_column))
    )
    if valid_metric and valid_dimension:
        score += 40

    if _has_real_variability(metric_column) or _has_real_variability(dimension_column):
        score += 30

    if _has_adequate_cardinality(dimension_column) or _has_adequate_cardinality(metric_column):
        score += 20

    score -= _column_penalty(metric_column)
    score -= _column_penalty(dimension_column)

    if getattr(dataset, "row_count", 0) < 20:
        score -= 30

    return max(0, min(100, score))


def _quality_gate(insight: AIInsight | None) -> AIInsight | None:
    if insight is None:
        return None
    if insight.quality_score < 40:
        logger.info("Insight rejected due to low quality score: %s", insight.type)
        return None
    return insight


def _compute_feature_scores_safe(dataset: Dataset, profile: list[dict[str, object]]) -> list[FeatureScore]:
    try:
        dataframe = load_dataset_dataframe(dataset)
        return compute_feature_scores(dataframe, profile)
    except Exception:
        logger.exception("dataset_feature_selection_failed", extra={"dataset_id": dataset.id})
        return []


def _prioritize_profile_by_feature_scores(
    profile: list[dict[str, object]],
    feature_scores: list[FeatureScore],
) -> list[dict[str, object]]:
    if not feature_scores:
        return profile

    score_by_name = {item.column: item.final_score for item in feature_scores}
    prioritized_columns = {item.column for item in select_top_features(feature_scores, k=min(max(len(profile), 5), 10))}

    def profile_score(item: dict[str, object]) -> tuple[int, float]:
        display_name = str(item.get("display_name") or "")
        sql_name = str(item.get("sql_name") or display_name)
        score = score_by_name.get(display_name, score_by_name.get(sql_name, 0.0))
        is_top = 1 if display_name in prioritized_columns or sql_name in prioritized_columns else 0
        return (is_top, score)

    return sorted(profile, key=profile_score, reverse=True)


def _rank_and_trim_insights(
    profile: list[dict[str, object]],
    insights: list[AIInsight],
    feature_scores: list[FeatureScore],
    limit: int = 6,
) -> list[AIInsight]:
    try:
        deduplicated = deduplicate_insights(insights)
        ranked = rank_insights(deduplicated, feature_scores)
        return select_top_insights(ranked, limit=limit)
    except Exception:
        logger.exception("dataset_insight_ranking_failed")
        return insights


def _looks_identifier_column(column: dict[str, object], dataset: Dataset) -> bool:
    if column.get("semantic_type") == "identifier":
        return True

    sql_name = str(column.get("sql_name") or "").strip().lower()
    display_name = str(column.get("display_name") or "").strip().lower()
    if sql_name == "id" or display_name == "id":
        return True
    if sql_name.endswith("_id") or display_name.endswith("_id"):
        return True

    distinct_count = column.get("distinct_count")
    row_count = getattr(dataset, "row_count", None)
    if isinstance(distinct_count, int) and isinstance(row_count, int) and row_count > 0:
        if distinct_count / row_count > 0.95:
            return True
    return False


def _column_has_low_variance(db: Session, dataset: Dataset, column: dict[str, object]) -> bool:
    distinct_count = column.get("distinct_count")
    if isinstance(distinct_count, int) and distinct_count <= 1:
        return True

    table_name = _quote_identifier(dataset.table_name or "")
    column_name = _quote_identifier(str(column["sql_name"]))
    sql = (
        f"SELECT COALESCE(STDDEV_POP(CAST({column_name} AS DOUBLE PRECISION)), 0) AS stddev_value "
        f"FROM {table_name} "
        f"WHERE {column_name} IS NOT NULL"
    )
    _, rows = _run_sql(db, sql)
    if not rows:
        return True
    stddev_value = rows[0].get("stddev_value")
    return isinstance(stddev_value, (int, float)) and abs(float(stddev_value)) < 1e-9


def _is_correlation_candidate(db: Session, dataset: Dataset, column: dict[str, object]) -> bool:
    if not _is_correlation_profile(column):
        return False

    if _looks_identifier_column(column, dataset):
        logger.info(
            "dataset_insight_correlation_column_skipped_identifier",
            extra={"dataset_id": dataset.id, "column": column.get("sql_name")},
        )
        return False

    if _column_has_low_variance(db, dataset, column):
        logger.info(
            "dataset_insight_correlation_column_skipped_low_variance",
            extra={"dataset_id": dataset.id, "column": column.get("sql_name")},
        )
        return False

    return True


def _filter_correlation_columns(
    db: Session,
    dataset: Dataset,
    numeric_columns: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    logger.info(
        "Correlation candidates BEFORE filter: %s",
        [str(column.get("sql_name")) for column in numeric_columns],
    )
    valid_columns = [
        column
        for column in numeric_columns
        if _is_correlation_profile(column)
        and not _looks_identifier_column(column, dataset)
        and not _column_has_low_variance(db, dataset, column)
    ]
    logger.info("Filtered columns for correlation: %s", valid_columns)
    return valid_columns


def _format_metric_value(value: object) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def _slugify_token(value: str | None, fallback: str) -> str:
    text = (value or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return slug or fallback


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, value))


def _priority_from_scores(*, confidence: float, impact: float) -> str:
    weighted = (confidence * 0.45) + (impact * 0.55)
    if weighted >= 0.72:
        return "high"
    if weighted >= 0.45:
        return "medium"
    return "low"


def _normalize_chart_suggestion(suggestion_type: str | None) -> str | None:
    if suggestion_type is None:
        return None
    if suggestion_type == "table_only":
        return "table"
    if suggestion_type in {"bar", "line", "pie", "scatter"}:
        return suggestion_type
    return None


def _chart_suggestion_from_visualization(visualization: object) -> str | None:
    suggestion_type = getattr(visualization, "type", None)
    if isinstance(visualization, dict):
        suggestion_type = visualization.get("type")
    return _normalize_chart_suggestion(suggestion_type if isinstance(suggestion_type, str) else None)


def _build_insight(
    *,
    insight_type: str,
    title: str,
    summary: str,
    confidence: float = 0.5,
    impact: float = 0.5,
    priority: str | None = None,
    severity: str = "info",
    metric: str | None = None,
    dimension: str | None = None,
    value: int | float | str | None = None,
    quality_score: int | None = None,
    sql: str | None = None,
    chart_type: str | None = None,
    columns: list[str] | None = None,
    rows: list[dict[str, object]] | None = None,
    data: list[dict[str, object]] | None = None,
    visualization_suggestion: object = None,
) -> AIInsight:
    confidence = _clamp_score(confidence)
    impact = _clamp_score(impact)
    resolved_priority = priority or _priority_from_scores(confidence=confidence, impact=impact)
    chart_suggestion = _chart_suggestion_from_visualization(visualization_suggestion)
    resolved_chart_type = chart_type or chart_suggestion or "table"
    insight_id = (
        f"{_slugify_token(insight_type, 'insight')}:"
        f"{_slugify_token(metric, 'metric')}:"
        f"{_slugify_token(dimension, 'dimension')}"
    )
    return AIInsight(
        type=insight_type,
        id=insight_id,
        title=title,
        description=summary,
        summary=summary,
        confidence=confidence,
        impact=impact,
        quality_score=max(0, min(100, quality_score if quality_score is not None else 50)),
        priority=resolved_priority,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        metric=metric,
        dimension=dimension,
        value=value,
        sql=sql,
        chart_suggestion=chart_suggestion,  # type: ignore[arg-type]
        chart_type=resolved_chart_type,  # type: ignore[arg-type]
        data=data or rows or [],
        columns=columns or [],
        rows=rows or [],
        visualization_suggestion=visualization_suggestion,
    )


def _polish_insight_summary(insight: AIInsight) -> AIInsight:
    if not settings.openai_api_key:
        return insight

    try:
        polished_summary = asyncio.run(
            request_openai_text(
                system_prompt=(
                    "You are a BI analyst. Rewrite the provided deterministic finding as one concise, plain-language "
                    "summary sentence. Preserve all facts and numbers. Do not add markdown."
                ),
                user_prompt=(
                    f"Insight type: {insight.type}\n"
                    f"Title: {insight.title}\n"
                    f"Summary: {insight.summary}\n"
                    f"Metric: {insight.metric or 'n/a'}\n"
                    f"Dimension: {insight.dimension or 'n/a'}\n"
                    f"Value: {insight.value if insight.value is not None else 'n/a'}"
                ),
                error_prefix="Could not polish insight summary",
            )
        ).strip()
    except Exception:
        logger.exception("dataset_insight_polish_failed", extra={"title": insight.title, "type": insight.type})
        return insight

    if polished_summary:
        insight.summary = polished_summary
        insight.description = polished_summary
    return insight


def _build_trend_insight(db: Session, dataset: Dataset, temporal: dict[str, object], numeric: dict[str, object]) -> AIInsight | None:
    table_name = _quote_identifier(dataset.table_name or "")
    time_column = _quote_identifier(str(temporal["sql_name"]))
    metric_column = _quote_identifier(str(numeric["sql_name"]))
    sql = (
        f"SELECT {time_column} AS period, "
        f"SUM(CAST({metric_column} AS DOUBLE PRECISION)) AS metric "
        f"FROM {table_name} "
        f"WHERE {time_column} IS NOT NULL AND {metric_column} IS NOT NULL "
        f"GROUP BY {time_column} "
        f"ORDER BY {time_column} "
        f"LIMIT 24"
    )
    columns, rows = _run_sql(db, sql)
    if len(rows) < 2:
        return None

    first_value = rows[0].get("metric")
    last_value = rows[-1].get("metric")
    if not isinstance(first_value, (int, float)) or not isinstance(last_value, (int, float)):
        return None

    direction = "increased" if last_value >= first_value else "declined"
    change_percent = ((last_value - first_value) / first_value * 100) if first_value else None
    change_text = (
        f" by {abs(change_percent):.1f}% across the available periods"
        if isinstance(change_percent, (int, float))
        else " across the available periods"
    )
    suggestion = build_visualization_suggestion(columns=columns, rows=rows, dataset=dataset)
    return _build_insight(
        insight_type="trend",
        title=f"{str(numeric['display_name']).replace('_', ' ').title()} {direction} over time",
        summary=(
            f"{numeric['display_name']} moved from {_format_metric_value(first_value)} to "
            f"{_format_metric_value(last_value)} when grouped by {temporal['display_name']}{change_text}."
        ),
        confidence=0.78,
        impact=_clamp_score(abs(change_percent) / 100) if isinstance(change_percent, (int, float)) else 0.6,
        quality_score=_score_insight_quality(dataset=dataset, metric_column=numeric, dimension_column=temporal),
        severity="info",
        metric=str(numeric["display_name"]),
        dimension=str(temporal["display_name"]),
        value=last_value,
        sql=sql,
        columns=columns,
        rows=rows,
        visualization_suggestion=suggestion,
    )


def _query_grouped_metric_rows(
    db: Session,
    dataset: Dataset,
    categorical: dict[str, object],
    numeric: dict[str, object],
) -> tuple[str, list[str], list[dict[str, object]]]:
    table_name = _quote_identifier(dataset.table_name or "")
    category_column = _quote_identifier(str(categorical["sql_name"]))
    metric_column = _quote_identifier(str(numeric["sql_name"]))
    sql = (
        f"SELECT {category_column} AS category, "
        f"SUM(CAST({metric_column} AS DOUBLE PRECISION)) AS metric "
        f"FROM {table_name} "
        f"WHERE {category_column} IS NOT NULL AND {metric_column} IS NOT NULL "
        f"GROUP BY {category_column} "
        f"ORDER BY metric DESC "
        f"LIMIT 5"
    )
    columns, rows = _run_sql(db, sql)
    return sql, columns, rows


def _build_top_performer_insight(
    db: Session,
    dataset: Dataset,
    categorical: dict[str, object],
    numeric: dict[str, object],
    *,
    sql: str | None = None,
    columns: list[str] | None = None,
    rows: list[dict[str, object]] | None = None,
) -> AIInsight | None:
    if sql is None or columns is None or rows is None:
        sql, columns, rows = _query_grouped_metric_rows(db, dataset, categorical, numeric)
    if not rows:
        return None
    if not _is_valid_dimension_profile(categorical):
        return None

    leader = rows[0]
    leader_name = leader.get("category")
    leader_metric = leader.get("metric")
    suggestion = build_visualization_suggestion(columns=columns, rows=rows, dataset=dataset)
    leader_label = str(leader_name) if leader_name is not None else "The leading category"
    return _build_insight(
        insight_type="top_performer",
        title=f"{leader_label} leads {numeric['display_name']}",
        summary=(
            f"{leader_label} has the highest total {numeric['display_name']} grouped by "
            f"{categorical['display_name']}, reaching {_format_metric_value(leader_metric)}."
        ),
        confidence=0.84,
        impact=0.82,
        quality_score=_score_insight_quality(dataset=dataset, metric_column=numeric, dimension_column=categorical),
        severity="info",
        metric=str(numeric["display_name"]),
        dimension=str(categorical["display_name"]),
        value=leader_metric if isinstance(leader_metric, (int, float, str)) else None,
        sql=sql,
        columns=columns,
        rows=rows,
        visualization_suggestion=suggestion,
    )


def _build_distribution_insight(db: Session, dataset: Dataset, numeric: dict[str, object]) -> AIInsight | None:
    if not _is_metric_profile(numeric):
        return None

    table_name = _quote_identifier(dataset.table_name or "")
    metric_column = _quote_identifier(str(numeric["sql_name"]))
    sql = (
        f"SELECT "
        f"MIN(CAST({metric_column} AS DOUBLE PRECISION)) AS min_value, "
        f"AVG(CAST({metric_column} AS DOUBLE PRECISION)) AS avg_value, "
        f"MAX(CAST({metric_column} AS DOUBLE PRECISION)) AS max_value "
        f"FROM {table_name} "
        f"WHERE {metric_column} IS NOT NULL"
    )
    _, rows = _run_sql(db, sql)
    if not rows:
        return None

    summary = rows[0]
    min_value = summary.get("min_value")
    avg_value = summary.get("avg_value")
    max_value = summary.get("max_value")
    if not all(isinstance(value, (int, float)) for value in (min_value, avg_value, max_value)):
        return None

    distribution_rows = [
        {"stat": "Minimum", "value": min_value},
        {"stat": "Average", "value": avg_value},
        {"stat": "Maximum", "value": max_value},
    ]
    columns = ["stat", "value"]
    suggestion = build_visualization_suggestion(columns=columns, rows=distribution_rows, dataset=dataset)
    return _build_insight(
        insight_type="distribution",
        title=f"{numeric['display_name']} distribution snapshot",
        summary=(
            f"{numeric['display_name']} ranges from {min_value:,.2f} to {max_value:,.2f}, "
            f"with an average of {avg_value:,.2f}."
        ),
        confidence=0.74,
        impact=_clamp_score((max_value - min_value) / max(max_value, 1)) if max_value else 0.35,
        quality_score=_score_insight_quality(dataset=dataset, metric_column=numeric),
        priority="low",
        severity="info",
        metric=str(numeric["display_name"]),
        value=avg_value,
        sql=sql,
        chart_type="table",
        columns=columns,
        rows=distribution_rows,
        visualization_suggestion=suggestion,
    )


def _build_outlier_insight(
    db: Session,
    dataset: Dataset,
    label_column_profile: dict[str, object] | None,
    numeric: dict[str, object],
) -> AIInsight | None:
    if not _is_metric_profile(numeric):
        return None

    label_sql_name = str((label_column_profile or numeric)["sql_name"])
    label_display_name = str((label_column_profile or numeric)["display_name"])
    table_name = _quote_identifier(dataset.table_name or "")
    label_column = _quote_identifier(label_sql_name)
    metric_column = _quote_identifier(str(numeric["sql_name"]))
    sql = (
        f"SELECT {label_column} AS label, "
        f"CAST({metric_column} AS DOUBLE PRECISION) AS metric "
        f"FROM {table_name} "
        f"WHERE {label_column} IS NOT NULL AND {metric_column} IS NOT NULL "
        f"AND CAST({metric_column} AS DOUBLE PRECISION) > ("
        f"  SELECT AVG(CAST({metric_column} AS DOUBLE PRECISION)) + (2 * COALESCE(STDDEV_POP(CAST({metric_column} AS DOUBLE PRECISION)), 0)) "
        f"  FROM {table_name} "
        f"  WHERE {metric_column} IS NOT NULL"
        f") "
        f"ORDER BY metric DESC "
        f"LIMIT 5"
    )
    columns, rows = _run_sql(db, sql)
    if not rows:
        return None

    suggestion = build_visualization_suggestion(columns=columns, rows=rows, dataset=dataset)
    top_metric = rows[0].get("metric")
    top_label = rows[0].get("label")
    return _build_insight(
        insight_type="outlier",
        title=f"Potential outliers in {numeric['display_name']}",
        summary=(
            f"Found unusually high {numeric['display_name']} values using a mean plus two standard deviations threshold, "
            f"labeled by {label_display_name}. The strongest outlier is {top_label} at {_format_metric_value(top_metric)}."
        ),
        confidence=0.86,
        impact=0.8,
        quality_score=_score_insight_quality(dataset=dataset, metric_column=numeric, dimension_column=label_column_profile),
        severity="warning",
        metric=str(numeric["display_name"]),
        dimension=label_display_name,
        value=top_metric if isinstance(top_metric, (int, float, str)) else None,
        sql=sql,
        columns=columns,
        rows=rows,
        visualization_suggestion=suggestion,
    )


def _build_correlation_insight(db: Session, dataset: Dataset, first: dict[str, object], second: dict[str, object]) -> AIInsight | None:
    if not _is_correlation_profile(first) or not _is_correlation_profile(second):
        return None

    first_sql_name = str(first["sql_name"]).strip().lower()
    second_sql_name = str(second["sql_name"]).strip().lower()
    if first_sql_name == "id" or second_sql_name == "id":
        return None
    if first_sql_name.endswith("_id") or second_sql_name.endswith("_id"):
        return None

    table_name = _quote_identifier(dataset.table_name or "")
    first_column = _quote_identifier(str(first["sql_name"]))
    second_column = _quote_identifier(str(second["sql_name"]))
    sql = (
        f"SELECT CORR(CAST({first_column} AS DOUBLE PRECISION), CAST({second_column} AS DOUBLE PRECISION)) AS correlation "
        f"FROM {table_name} "
        f"WHERE {first_column} IS NOT NULL AND {second_column} IS NOT NULL"
    )
    _, rows = _run_sql(db, sql)
    if not rows:
        return None

    correlation = rows[0].get("correlation")
    if not isinstance(correlation, (int, float)) or abs(correlation) < 0.6:
        return None

    direction = "positive" if correlation > 0 else "negative"
    rounded = round(correlation, 3)
    insight_rows = [{"pair": f"{first['display_name']} vs {second['display_name']}", "correlation": rounded}]
    summary_columns = ["pair", "correlation"]
    scatter_sql = (
        f"SELECT "
        f"CAST({first_column} AS DOUBLE PRECISION) AS {_quote_identifier(str(first['sql_name']))}, "
        f"CAST({second_column} AS DOUBLE PRECISION) AS {_quote_identifier(str(second['sql_name']))} "
        f"FROM {table_name} "
        f"WHERE {first_column} IS NOT NULL AND {second_column} IS NOT NULL "
        f"LIMIT 200"
    )
    scatter_columns, scatter_rows = _run_sql(db, scatter_sql)
    logger.info(
        "dataset_insight_correlation_scatter_query",
        extra={
            "dataset_id": dataset.id,
            "scatter_sql": scatter_sql,
            "scatter_rows_length": len(scatter_rows),
            "scatter_columns": scatter_columns,
        },
    )

    x_key = str(first["sql_name"])
    y_key = str(second["sql_name"])
    valid_rows = [
        row
        for row in scatter_rows
        if isinstance(row.get(x_key), (int, float)) and isinstance(row.get(y_key), (int, float))
    ]
    if len(valid_rows) == 0:
        logger.warning(
            "dataset_insight_correlation_scatter_empty",
            extra={
                "dataset_id": dataset.id,
                "first_column": x_key,
                "second_column": y_key,
                "scatter_sql": scatter_sql,
            },
        )

    suggestion = build_visualization_suggestion(columns=summary_columns, rows=insight_rows, dataset=dataset)
    if len(valid_rows) < 5:
        return _build_insight(
            insight_type="correlation",
            title=f"{direction.title()} correlation detected",
            summary="Correlation detected but insufficient data to visualize.",
            severity="warning" if abs(correlation) >= 0.85 else "info",
            confidence=_clamp_score(abs(correlation)),
            impact=_clamp_score(abs(correlation) * 0.9),
            quality_score=_score_insight_quality(
                dataset=dataset,
                metric_column=second,
                dimension_column=first,
                allow_metric_dimension=True,
            ),
            metric=str(second["display_name"]),
            dimension=str(first["display_name"]),
            value=rounded,
            sql=sql,
            chart_type="table",
            columns=summary_columns,
            rows=insight_rows,
            data=insight_rows,
            visualization_suggestion=suggestion,
        )

    return _build_insight(
        insight_type="correlation",
        title=f"{direction.title()} correlation detected",
        summary=f"{first['display_name']} and {second['display_name']} show a {direction} correlation of {rounded:.3f}.",
        severity="warning" if abs(correlation) >= 0.85 else "info",
        confidence=_clamp_score(abs(correlation)),
        impact=_clamp_score(abs(correlation) * 0.9),
        quality_score=_score_insight_quality(
            dataset=dataset,
            metric_column=second,
            dimension_column=first,
            allow_metric_dimension=True,
        ),
        metric=str(second["display_name"]),
        dimension=str(first["display_name"]),
        value=rounded,
        sql=sql,
        chart_type="scatter",
        columns=scatter_columns,
        rows=insight_rows,
        data=valid_rows,
        visualization_suggestion=suggestion,
    )


def _build_concentration_insight(
    dataset: Dataset,
    categorical: dict[str, object],
    numeric: dict[str, object],
    *,
    sql: str,
    columns: list[str],
    rows: list[dict[str, object]],
) -> AIInsight | None:
    if not _is_valid_dimension_profile(categorical):
        return None
    if len(rows) < 2:
        return None

    total = sum(row.get("metric") for row in rows if isinstance(row.get("metric"), (int, float)))
    leader_metric = rows[0].get("metric")
    leader_name = rows[0].get("category")
    if not isinstance(total, (int, float)) or total <= 0 or not isinstance(leader_metric, (int, float)):
        return None

    ratio = leader_metric / total
    severity = "critical" if ratio >= 0.7 else "warning" if ratio >= 0.5 else "info"
    suggestion = build_visualization_suggestion(columns=columns, rows=rows, dataset=dataset)
    return _build_insight(
        insight_type="concentration",
        title=f"{leader_name} concentrates the largest share of {numeric['display_name']}",
        summary=(
            f"{leader_name} accounts for {ratio * 100:.1f}% of total {numeric['display_name']} when grouped by "
            f"{categorical['display_name']}."
        ),
        confidence=0.82,
        impact=_clamp_score(ratio),
        quality_score=_score_insight_quality(dataset=dataset, metric_column=numeric, dimension_column=categorical),
        severity=severity,
        metric=str(numeric["display_name"]),
        dimension=str(categorical["display_name"]),
        value=ratio,
        sql=sql,
        columns=columns,
        rows=rows,
        visualization_suggestion=suggestion,
    )


def _build_comparison_insight(
    dataset: Dataset,
    categorical: dict[str, object],
    numeric: dict[str, object],
    *,
    sql: str,
    columns: list[str],
    rows: list[dict[str, object]],
) -> AIInsight | None:
    if not _is_valid_dimension_profile(categorical):
        return None
    if len(rows) < 2:
        return None

    first_row, second_row = rows[0], rows[1]
    first_metric = first_row.get("metric")
    second_metric = second_row.get("metric")
    first_name = first_row.get("category")
    second_name = second_row.get("category")
    if not isinstance(first_metric, (int, float)) or not isinstance(second_metric, (int, float)) or second_metric == 0:
        return None

    ratio = first_metric / second_metric
    delta = first_metric - second_metric
    suggestion = build_visualization_suggestion(columns=columns, rows=rows[:2], dataset=dataset)
    return _build_insight(
        insight_type="comparison",
        title=f"{first_name} outperforms {second_name}",
        summary=(
            f"{first_name} exceeds {second_name} by {_format_metric_value(delta)} in {numeric['display_name']}, "
            f"about {ratio:.2f}x higher."
        ),
        confidence=0.77,
        impact=_clamp_score(min(abs(delta) / max(abs(first_metric), 1), 1.0)),
        quality_score=_score_insight_quality(dataset=dataset, metric_column=numeric, dimension_column=categorical),
        severity="info",
        metric=str(numeric["display_name"]),
        dimension=str(categorical["display_name"]),
        value=delta,
        sql=sql,
        columns=columns,
        rows=rows[:2],
        visualization_suggestion=suggestion,
    )


def _serialize_insight_run(run: DatasetInsightRun, dataset: Dataset | None = None) -> AIInsightsResponse:
    attached_dataset = dataset or run.dataset
    insights = [AIInsight.model_validate(item) for item in (run.insights_json or [])]
    narrative = (
        build_insight_narrative(dataset=attached_dataset, insights=insights)
        if attached_dataset is not None
        else AIInsightNarrative()
    )
    dataset_name = attached_dataset.name if attached_dataset is not None else ""
    dataset_updated_at = attached_dataset.updated_at if attached_dataset is not None else run.dataset_updated_at_snapshot
    return AIInsightsResponse(
        run_id=run.id,
        dataset_id=run.dataset_id,
        dataset_name=dataset_name,
        status=run.status,
        generated_at=_to_iso8601(run.generated_at),
        is_stale=_is_stale(dataset_updated_at, run.dataset_updated_at_snapshot),
        error_message=run.error_message,
        insights=insights,
        narrative=narrative,
    )


def _serialize_insight_run_summary(run: DatasetInsightRun, dataset: Dataset | None = None) -> DatasetInsightRunSummary:
    attached_dataset = dataset or run.dataset
    dataset_name = attached_dataset.name if attached_dataset is not None else ""
    dataset_updated_at = attached_dataset.updated_at if attached_dataset is not None else run.dataset_updated_at_snapshot
    return DatasetInsightRunSummary(
        id=run.id,
        dataset_id=run.dataset_id,
        dataset_name=dataset_name,
        status=run.status,
        generated_at=_to_iso8601(run.generated_at),
        created_at=_to_iso8601(run.created_at),
        updated_at=_to_iso8601(run.updated_at),
        is_stale=_is_stale(dataset_updated_at, run.dataset_updated_at_snapshot),
        error_message=run.error_message,
    )


def _serialize_insight_run_detail(run: DatasetInsightRun, dataset: Dataset | None = None) -> DatasetInsightRunDetail:
    summary = _serialize_insight_run_summary(run, dataset)
    insights = [AIInsight.model_validate(item) for item in (run.insights_json or [])]
    return DatasetInsightRunDetail(**summary.model_dump(), insights=insights)


def generate_insights(*, db: Session, dataset: Dataset) -> AIInsightsResponse:
    base_profile = build_dataset_schema_profile(dataset)
    feature_scores = _compute_feature_scores_safe(dataset, base_profile)
    profile = _prioritize_profile_by_feature_scores(base_profile, feature_scores)
    numeric_columns = [item for item in profile if _is_metric_profile(item)]
    categorical_columns = [item for item in profile if item.get("semantic_type") == "categorical" and _is_grouping_profile(item)]
    temporal_columns = [item for item in profile if _is_temporal_profile(item)]

    insights: list[AIInsight] = []
    primary_numeric = _pick_preferred_numeric(numeric_columns)
    primary_categorical = _pick_preferred_categorical(categorical_columns)
    primary_temporal = temporal_columns[0] if temporal_columns else None
    label_column = primary_categorical or primary_temporal

    if primary_temporal and primary_numeric:
        try:
            trend_insight = _build_trend_insight(db, dataset, primary_temporal, primary_numeric)
        except Exception:
            logger.exception("dataset_insight_trend_failed", extra={"dataset_id": dataset.id})
            trend_insight = None
        trend_insight = _quality_gate(trend_insight)
        if trend_insight is not None:
            insights.append(trend_insight)

    if primary_categorical and primary_numeric:
        grouped_sql: str | None = None
        grouped_columns: list[str] | None = None
        grouped_rows: list[dict[str, object]] | None = None
        try:
            grouped_sql, grouped_columns, grouped_rows = _query_grouped_metric_rows(
                db,
                dataset,
                primary_categorical,
                primary_numeric,
            )
        except Exception:
            logger.exception("dataset_insight_grouped_metric_failed", extra={"dataset_id": dataset.id})

        try:
            top_performer_insight = _build_top_performer_insight(
                db,
                dataset,
                primary_categorical,
                primary_numeric,
                sql=grouped_sql,
                columns=grouped_columns,
                rows=grouped_rows,
            )
        except Exception:
            logger.exception("dataset_insight_top_performer_failed", extra={"dataset_id": dataset.id})
            top_performer_insight = None
        top_performer_insight = _quality_gate(top_performer_insight)
        if top_performer_insight is not None:
            insights.append(top_performer_insight)

        if grouped_sql and grouped_columns and grouped_rows:
            try:
                concentration_insight = _build_concentration_insight(
                    dataset,
                    primary_categorical,
                    primary_numeric,
                    sql=grouped_sql,
                    columns=grouped_columns,
                    rows=grouped_rows,
                )
            except Exception:
                logger.exception("dataset_insight_concentration_failed", extra={"dataset_id": dataset.id})
                concentration_insight = None
            concentration_insight = _quality_gate(concentration_insight)
            if concentration_insight is not None:
                insights.append(concentration_insight)

            try:
                comparison_insight = _build_comparison_insight(
                    dataset,
                    primary_categorical,
                    primary_numeric,
                    sql=grouped_sql,
                    columns=grouped_columns,
                    rows=grouped_rows,
                )
            except Exception:
                logger.exception("dataset_insight_comparison_failed", extra={"dataset_id": dataset.id})
                comparison_insight = None
            comparison_insight = _quality_gate(comparison_insight)
            if comparison_insight is not None:
                insights.append(comparison_insight)

    if primary_numeric:
        try:
            distribution_insight = _build_distribution_insight(db, dataset, primary_numeric)
        except Exception:
            logger.exception("dataset_insight_distribution_failed", extra={"dataset_id": dataset.id})
            distribution_insight = None
        distribution_insight = _quality_gate(distribution_insight)
        if distribution_insight is not None:
            insights.append(distribution_insight)

        try:
            outlier_insight = _build_outlier_insight(db, dataset, label_column, primary_numeric)
        except Exception:
            logger.exception("dataset_insight_outlier_failed", extra={"dataset_id": dataset.id})
            outlier_insight = None
        outlier_insight = _quality_gate(outlier_insight)
        if outlier_insight is not None:
            insights.append(outlier_insight)

    try:
        valid_correlation_columns = _filter_correlation_columns(db, dataset, numeric_columns[:6])
    except Exception:
        logger.exception("dataset_insight_correlation_candidate_filter_failed", extra={"dataset_id": dataset.id})
        valid_correlation_columns = []

    for first, second in combinations(valid_correlation_columns[:4], 2):
        try:
            correlation_insight = _build_correlation_insight(db, dataset, first, second)
        except Exception:
            logger.exception("dataset_insight_correlation_failed", extra={"dataset_id": dataset.id})
            correlation_insight = None
        correlation_insight = _quality_gate(correlation_insight)
        if correlation_insight is not None:
            insights.append(correlation_insight)
            break

    if not insights:
        fallback_rows = [
            {"metric": "Numeric columns", "count": len(numeric_columns)},
            {"metric": "Categorical columns", "count": len(categorical_columns)},
            {"metric": "Temporal columns", "count": len(temporal_columns)},
        ]
        insights.append(
            _build_insight(
                insight_type="distribution",
                title="Dataset structure overview",
                summary="The dataset is queryable, but no strong automatic insight was detected from the available schema and value patterns.",
                severity="info",
                metric="dataset_structure",
                quality_score=45,
                columns=["metric", "count"],
                rows=fallback_rows,
                visualization_suggestion=build_visualization_suggestion(
                    columns=["metric", "count"],
                    rows=fallback_rows,
                    dataset=dataset,
                ),
            )
        )

    try:
        insights = _rank_and_trim_insights(profile, insights, feature_scores, limit=6)
    except Exception:
        logger.exception("dataset_insight_ranking_failed", extra={"dataset_id": dataset.id})
    insights = [_polish_insight_summary(insight) for insight in insights]
    narrative = build_insight_narrative(dataset=dataset, insights=insights, profile=profile)

    return AIInsightsResponse(
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        status="success",
        generated_at=datetime.now(timezone.utc).isoformat(),
        is_stale=False,
        insights=insights,
        narrative=narrative,
    )


def save_insight_run(
    db: Session,
    *,
    dataset: Dataset,
    user_id: int,
    status: str,
    insights_response: AIInsightsResponse | None = None,
    error_message: str | None = None,
) -> DatasetInsightRun:
    generated_at = (
        datetime.fromisoformat(insights_response.generated_at)
        if insights_response is not None
        else datetime.now(timezone.utc)
    )
    run = DatasetInsightRun(
        dataset_id=dataset.id,
        user_id=user_id,
        generated_at=generated_at,
        status=status,
        insights_json=(
            [insight.model_dump(mode="json") for insight in insights_response.insights]
            if insights_response is not None
            else None
        ),
        error_message=error_message,
        dataset_updated_at_snapshot=dataset.updated_at,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def generate_and_save_insights(db: Session, current_user: User, dataset_id: int) -> AIInsightsResponse:
    started_at = time.perf_counter()
    dataset = _load_owned_dataset(db, dataset_id=dataset_id, user_id=current_user.id)
    try:
        dataset = ensure_dataset_queryable(db=db, dataset=dataset)
        response = generate_insights(db=db, dataset=dataset)
        run = save_insight_run(
            db,
            dataset=dataset,
            user_id=current_user.id,
            status="success",
            insights_response=response,
        )
        response.run_id = run.id
        log_event(
            logger,
            logging.INFO,
            "insight_generation_succeeded",
            dataset_id=dataset.id,
            user_id=current_user.id,
            run_id=run.id,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
        )
        return response
    except HTTPException as exc:
        save_insight_run(
            db,
            dataset=dataset,
            user_id=current_user.id,
            status="failed",
            error_message=str(exc.detail),
        )
        log_event(
            logger,
            logging.WARNING,
            "insight_generation_failed",
            dataset_id=dataset.id,
            user_id=current_user.id,
            error_code="insight_generation_http_error",
            duration_ms=int((time.perf_counter() - started_at) * 1000),
        )
        raise
    except Exception as exc:
        logger.exception("dataset_insight_generation_failed", extra={"dataset_id": dataset.id, "user_id": current_user.id})
        save_insight_run(
            db,
            dataset=dataset,
            user_id=current_user.id,
            status="failed",
            error_message=str(exc),
        )
        log_event(
            logger,
            logging.ERROR,
            "insight_generation_failed",
            dataset_id=dataset.id,
            user_id=current_user.id,
            error_code="insight_generation_unhandled_error",
            duration_ms=int((time.perf_counter() - started_at) * 1000),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate insights for this dataset",
        ) from exc


def get_latest_insights(db: Session, current_user: User, dataset_id: int) -> AIInsightsResponse:
    dataset = _load_owned_dataset(db, dataset_id=dataset_id, user_id=current_user.id)
    statement = (
        select(DatasetInsightRun)
        .options(joinedload(DatasetInsightRun.dataset))
        .where(
            DatasetInsightRun.dataset_id == dataset.id,
            DatasetInsightRun.user_id == current_user.id,
            DatasetInsightRun.status == "success",
        )
        .order_by(desc(DatasetInsightRun.generated_at), desc(DatasetInsightRun.id))
    )
    run = db.execute(statement).unique().scalars().first()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No insights generated yet")
    return _serialize_insight_run(run, dataset)


def list_insight_runs(db: Session, current_user: User, dataset_id: int) -> list[DatasetInsightRunSummary]:
    dataset = _load_owned_dataset(db, dataset_id=dataset_id, user_id=current_user.id)
    statement = (
        select(DatasetInsightRun)
        .options(joinedload(DatasetInsightRun.dataset))
        .where(DatasetInsightRun.dataset_id == dataset.id, DatasetInsightRun.user_id == current_user.id)
        .order_by(desc(DatasetInsightRun.generated_at), desc(DatasetInsightRun.id))
    )
    runs = db.execute(statement).unique().scalars().all()
    return [_serialize_insight_run_summary(run, dataset) for run in runs]


def get_insight_run_detail(db: Session, current_user: User, run_id: int) -> DatasetInsightRunDetail:
    run = _get_owned_insight_run(db, run_id=run_id, user_id=current_user.id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight run not found")
    return _serialize_insight_run_detail(run)
