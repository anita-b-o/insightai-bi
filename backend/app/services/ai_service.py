import json
import logging
import re
import time
from numbers import Number

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.observability import log_event
from app.models.dataset import Dataset
from app.models.user import User
from app.schemas.ai import AIQueryMetadata, AIQueryResponse, AIVisualizationSuggestion, SQLAnalysisResult
from app.services.ai_query_store import (
    get_cached_ai_query,
    save_failed_ai_query,
    save_successful_ai_query,
)
from app.services.openai_service import request_openai_text
from app.services.query_executor import ensure_dataset_queryable, execute_dataset_query
from app.services.schema_profile_service import build_dataset_schema_profile, get_schema_profile_entry
from app.services.sql_analysis_service import analyze_sql
from app.services.sql_generator import correct_sql, generate_sql
from app.services.sql_validator import validate_and_normalize_sql

logger = logging.getLogger(__name__)


_CHART_SUGGESTION_MAP = {
    "bar_chart": "bar",
    "bar": "bar",
    "line_chart": "line",
    "line": "line",
    "pie_chart": "pie",
    "pie": "pie",
    "table_chart": "table",
    "table": "table",
}


def _strip_markdown_fences(text: str) -> str:
    trimmed = text.strip()
    fenced_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", trimmed, flags=re.DOTALL)
    if fenced_match:
        return fenced_match.group(1).strip()
    return trimmed


def normalize_chart_suggestion(value: object) -> str | None:
    if not value:
        return None
    normalized = str(value).strip().lower()
    return _CHART_SUGGESTION_MAP.get(normalized)


def parse_ai_answer_text(text: str) -> dict[str, str | None]:
    original_text = text.strip()
    unfenced_text = _strip_markdown_fences(original_text)

    try:
        parsed = json.loads(unfenced_text)
    except json.JSONDecodeError:
        return {"answer": unfenced_text or original_text, "chart_suggestion": None}

    if not isinstance(parsed, dict):
        return {"answer": unfenced_text or original_text, "chart_suggestion": None}

    answer = str(parsed.get("answer", "")).strip() or unfenced_text or original_text
    chart_suggestion = normalize_chart_suggestion(
        parsed.get("chart_suggestion") or parsed.get("visualization_suggestion")
    )
    return {"answer": answer, "chart_suggestion": chart_suggestion}


class SQLPipelineExecutionError(Exception):
    def __init__(self, *, sql: str, http_exception: HTTPException) -> None:
        super().__init__(str(http_exception.detail))
        self.sql = sql
        self.http_exception = http_exception


def _is_numeric_value(value: object) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool)


def _looks_temporal_column(name: str, values: list[object]) -> bool:
    normalized = name.lower()
    if any(token in normalized for token in ("date", "time", "day", "month", "year")):
        return True
    return any(isinstance(value, str) and any(char == "-" for char in value[:10]) for value in values if value is not None)


def build_visualization_suggestion(
    columns: list[str],
    rows: list[dict[str, object]],
    dataset: Dataset | None = None,
    sql_analysis: SQLAnalysisResult | None = None,
) -> AIVisualizationSuggestion:
    if not columns or not rows:
        return AIVisualizationSuggestion(type="table_only", reason="This result is better represented as a table.")

    if sql_analysis is not None and not sql_analysis.is_aggregated:
        if len(rows) > 12:
            return AIVisualizationSuggestion(
                type="table_only",
                reason="This query returns raw rows. Aggregating the data may produce a better chart.",
            )
        if len(rows) > 3:
            return AIVisualizationSuggestion(
                type="table_only",
                reason="This query returns raw rows. A table is clearer unless the data is aggregated first.",
            )

    non_null_values_by_column = {
        column: [row.get(column) for row in rows if row.get(column) is not None]
        for column in columns
    }
    numeric_columns = [
        column
        for column, values in non_null_values_by_column.items()
        if values and all(_is_numeric_value(value) for value in values)
    ]

    if len(columns) == 1:
        return AIVisualizationSuggestion(type="table_only", reason="This result is better represented as a table.")

    if len(columns) == 2:
        first_column, second_column = columns
        first_values = non_null_values_by_column[first_column]
        second_values = non_null_values_by_column[second_column]
        first_profile = get_schema_profile_entry(dataset, first_column) if dataset is not None else None
        second_profile = get_schema_profile_entry(dataset, second_column) if dataset is not None else None

        if first_values and second_values and all(_is_numeric_value(value) for value in second_values):
            if sql_analysis is not None and sql_analysis.is_aggregated and first_column in sql_analysis.group_by_columns:
                if (
                    (first_profile and first_profile.get("semantic_type") == "temporal")
                    or _looks_temporal_column(first_column, first_values)
                ):
                    return AIVisualizationSuggestion(
                        type="line",
                        x=first_column,
                        y=second_column,
                        reason="Detected an aggregated result grouped by a temporal column, which fits a line chart.",
                    )
                distinct_count = first_profile.get("distinct_count") if first_profile else None
                effective_cardinality = distinct_count if isinstance(distinct_count, int) else len({str(value) for value in first_values})
                if 0 < effective_cardinality <= 8:
                    return AIVisualizationSuggestion(
                        type="pie",
                        label=first_column,
                        value=second_column,
                        reason="Detected an aggregated result grouped by a low-cardinality category, which can be shown as a pie chart.",
                    )
                return AIVisualizationSuggestion(
                    type="bar",
                    x=first_column,
                    y=second_column,
                    reason="Detected an aggregated result grouped by a category, which fits a bar chart.",
                )
            if (
                (first_profile and first_profile.get("semantic_type") == "temporal")
                or _looks_temporal_column(first_column, first_values)
            ):
                return AIVisualizationSuggestion(
                    type="line",
                    x=first_column,
                    y=second_column,
                    reason="Detected a temporal dimension and a numeric metric, which fits a line chart.",
                )
            distinct_count = first_profile.get("distinct_count") if first_profile else None
            unique_labels = {str(value) for value in first_values}
            effective_cardinality = distinct_count if isinstance(distinct_count, int) else len(unique_labels)
            if 0 < effective_cardinality <= 8:
                return AIVisualizationSuggestion(
                    type="pie",
                    label=first_column,
                    value=second_column,
                    reason="Detected a categorical column with low cardinality and a numeric metric, which fits a pie chart.",
                )
            return AIVisualizationSuggestion(
                type="bar",
                x=first_column,
                y=second_column,
                reason="Detected a categorical column and a numeric metric, which fits a bar chart.",
            )

        return AIVisualizationSuggestion(type="table_only", reason="This result is better represented as a table.")

    if numeric_columns:
        dimension_columns = [column for column in columns if column not in numeric_columns]
        dimension_columns.sort(
            key=lambda column: 0
            if dataset is not None and (get_schema_profile_entry(dataset, column) or {}).get("semantic_type") == "temporal"
            else 1
        )
        if dimension_columns:
            x_column = dimension_columns[0]
            y_column = numeric_columns[0]
            x_values = non_null_values_by_column[x_column]
            x_profile = get_schema_profile_entry(dataset, x_column) if dataset is not None else None
            if sql_analysis is not None and sql_analysis.is_aggregated and x_column in sql_analysis.group_by_columns:
                if (
                    (x_profile and x_profile.get("semantic_type") == "temporal")
                    or _looks_temporal_column(x_column, x_values)
                ):
                    return AIVisualizationSuggestion(
                        type="line",
                        x=x_column,
                        y=y_column,
                        reason="Detected an aggregated result grouped by a temporal column, which fits a line chart.",
                    )
                return AIVisualizationSuggestion(
                    type="bar",
                    x=x_column,
                    y=y_column,
                    reason="Detected an aggregated result grouped by a category, which fits a bar chart.",
                )
            if (
                (x_profile and x_profile.get("semantic_type") == "temporal")
                or _looks_temporal_column(x_column, x_values)
            ):
                return AIVisualizationSuggestion(
                    type="line",
                    x=x_column,
                    y=y_column,
                    reason="Detected a temporal dimension and a numeric metric, which fits a line chart.",
                )
            return AIVisualizationSuggestion(
                type="bar",
                x=x_column,
                y=y_column,
                reason="Detected a categorical column and a numeric metric, which fits a bar chart.",
            )

        if len(numeric_columns) >= 2:
            return AIVisualizationSuggestion(
                type="line",
                x=numeric_columns[0],
                y=numeric_columns[1],
                reason="Detected two numeric series, which can be compared with a line chart.",
            )

    return AIVisualizationSuggestion(type="table_only", reason="This result is better represented as a table.")


def _build_dataset_context(dataset: Dataset) -> str:
    columns = build_dataset_schema_profile(dataset)
    payload = {
        "dataset_name": dataset.name,
        "description": dataset.description,
        "original_filename": dataset.original_filename,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "columns": columns,
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def _build_prompt(dataset: Dataset, question: str) -> tuple[str, str]:
    system_prompt = (
        "You are an AI data assistant for a Business Intelligence platform. "
        "Answer using only the dataset metadata provided. "
        "Do not invent rows, aggregates, or values that are not present in the metadata. "
        "If the answer cannot be determined from the schema-level context, say so clearly and explain what is missing. "
        "Be concise, practical, and oriented to business users. "
        "Return ONLY valid JSON with keys: answer, chart_suggestion. "
        "Do not wrap the JSON in markdown. Do not include code fences."
    )
    user_prompt = (
        f"Dataset name: {dataset.name}\n"
        f"Question: {question}\n\n"
        "Dataset context:\n"
        f"{_build_dataset_context(dataset)}"
    )
    return system_prompt, user_prompt


def _build_result_prompt(
    dataset: Dataset,
    question: str,
    sql: str,
    columns: list[str],
    rows: list[dict[str, object]],
) -> tuple[str, str]:
    system_prompt = (
        "You are an AI data assistant for a Business Intelligence platform. "
        "Answer using only the SQL result provided. "
        "Do not invent metrics or data beyond the query output. "
        "If the result set is empty, say that no matching rows were found. "
        "Also suggest the most appropriate chart type for the result shape. "
        "Return ONLY valid JSON with keys: answer, chart_suggestion. "
        "Do not wrap the JSON in markdown. Do not include code fences."
    )
    user_prompt = (
        f"Dataset name: {dataset.name}\n"
        f"Question: {question}\n"
        f"Executed SQL: {sql}\n"
        f"Columns: {json.dumps(columns, ensure_ascii=True)}\n"
        f"Rows: {json.dumps(rows, ensure_ascii=True, default=str)}"
    )
    return system_prompt, user_prompt


def _build_cache_response(record, dataset: Dataset) -> AIQueryResponse:
    payload = record.result if isinstance(record.result, dict) else {}
    rows = payload.get("rows", [])
    columns = payload.get("columns", [])
    sql_analysis = analyze_sql(record.sql) if record.sql else None
    return AIQueryResponse(
        answer=record.answer or "Cached response",
        sql=record.sql,
        rows=rows,
        columns=columns,
        chart_suggestion=record.chart_suggestion,
        visualization_suggestion=build_visualization_suggestion(
            columns=columns,
            rows=rows,
            dataset=dataset,
            sql_analysis=sql_analysis,
        ),
        sql_analysis=sql_analysis,
        metadata=AIQueryMetadata(
            dataset_id=dataset.id,
            dataset_name=dataset.name,
            column_count=dataset.column_count,
            model=settings.openai_model,
            cache_hit=True,
        ),
    )


def _parse_answer_payload(payload_text: str) -> tuple[str, str | None]:
    parsed = parse_ai_answer_text(payload_text)
    return str(parsed["answer"] or "").strip(), parsed["chart_suggestion"]


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


def _build_response_metadata(dataset: Dataset, *, cache_hit: bool = False, fallback_used: bool = False) -> AIQueryMetadata:
    return AIQueryMetadata(
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        column_count=dataset.column_count,
        model=settings.openai_model,
        cache_hit=cache_hit,
        fallback_used=fallback_used,
    )


def _build_query_response(
    *,
    dataset: Dataset,
    answer: str,
    sql: str | None = None,
    rows: list[dict[str, object]] | None = None,
    columns: list[str] | None = None,
    chart_suggestion: str | None = None,
    sql_analysis: SQLAnalysisResult | None = None,
    cache_hit: bool = False,
    fallback_used: bool = False,
) -> AIQueryResponse:
    normalized_rows = rows or []
    normalized_columns = columns or []
    return AIQueryResponse(
        answer=answer,
        sql=sql,
        rows=normalized_rows,
        columns=normalized_columns,
        chart_suggestion=chart_suggestion,
        visualization_suggestion=build_visualization_suggestion(
            columns=normalized_columns,
            rows=normalized_rows,
            dataset=dataset,
            sql_analysis=sql_analysis,
        ),
        sql_analysis=sql_analysis,
        metadata=_build_response_metadata(dataset, cache_hit=cache_hit, fallback_used=fallback_used),
    )


async def _generate_metadata_answer(dataset: Dataset, question: str) -> tuple[str, str | None]:
    system_prompt, user_prompt = _build_prompt(dataset=dataset, question=question)
    payload_text = await request_openai_text(
        system_prompt,
        user_prompt,
        error_prefix="OpenAI API request failed",
    )
    return _parse_answer_payload(payload_text)


async def _execute_sql_with_retry(
    *,
    db: Session,
    dataset: Dataset,
    user_id: int,
    question: str,
) -> tuple[str, SQLAnalysisResult, list[str], list[dict[str, object]]]:
    candidate_sql = await generate_sql(question=question, dataset=dataset)
    last_error: HTTPException | None = None
    last_sql = candidate_sql

    for attempt in range(settings.ai_sql_max_retries + 1):
        try:
            normalized_sql = validate_and_normalize_sql(sql=candidate_sql, dataset=dataset)
            last_sql = normalized_sql
            sql_analysis = analyze_sql(normalized_sql)
            columns, rows = execute_dataset_query(db=db, dataset=dataset, sql=normalized_sql)
            if attempt > 0:
                log_event(
                    logger,
                    logging.INFO,
                    "ai_sql_retry_succeeded",
                    dataset_id=dataset.id,
                    user_id=user_id,
                    attempt=attempt + 1,
                )
            return normalized_sql, sql_analysis, columns, rows
        except HTTPException as exc:
            last_error = exc
            log_event(
                logger,
                logging.WARNING,
                "ai_sql_attempt_failed",
                dataset_id=dataset.id,
                user_id=user_id,
                attempt=attempt + 1,
                error_code="sql_generation_failed",
            )
            if attempt >= settings.ai_sql_max_retries:
                break
            candidate_sql = await correct_sql(
                question=question,
                dataset=dataset,
                failed_sql=candidate_sql,
                execution_error=str(exc.detail),
            )
            last_sql = candidate_sql

    assert last_error is not None
    raise SQLPipelineExecutionError(sql=last_sql, http_exception=last_error)


async def query_dataset_with_ai(
    db: Session,
    current_user: User,
    dataset_id: int,
    question: str,
) -> AIQueryResponse:
    started_at = time.perf_counter()
    dataset = _load_owned_dataset(db, dataset_id=dataset_id, user_id=current_user.id)
    if not dataset.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset has no detected columns",
        )
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPENAI_API_KEY is not configured",
        )

    answer, chart_suggestion = await _generate_metadata_answer(dataset=dataset, question=question)
    log_event(
        logger,
        logging.INFO,
        "ai_metadata_answer_generated",
        dataset_id=dataset.id,
        user_id=current_user.id,
        chart_suggestion=chart_suggestion,
        duration_ms=int((time.perf_counter() - started_at) * 1000),
    )

    return _build_query_response(
        dataset=dataset,
        answer=answer,
        chart_suggestion=chart_suggestion,
    )


async def _generate_answer_from_rows(
    dataset: Dataset,
    question: str,
    sql: str,
    columns: list[str],
    rows: list[dict[str, object]],
) -> tuple[str, str | None]:
    system_prompt, user_prompt = _build_result_prompt(
        dataset=dataset,
        question=question,
        sql=sql,
        columns=columns,
        rows=rows,
    )
    payload_text = await request_openai_text(
        system_prompt,
        user_prompt,
        error_prefix="OpenAI API request failed while generating the final answer",
    )
    return _parse_answer_payload(payload_text)


async def query_dataset_with_sql_ai(
    db: Session,
    current_user: User,
    dataset_id: int,
    question: str,
) -> AIQueryResponse:
    started_at = time.perf_counter()
    dataset = ensure_dataset_queryable(
        db=db,
        dataset=_load_owned_dataset(db, dataset_id=dataset_id, user_id=current_user.id),
    )
    log_event(
        logger,
        logging.INFO,
        "ai_query_started",
        dataset_id=dataset.id,
        user_id=current_user.id,
    )
    cached_query = get_cached_ai_query(
        db=db,
        dataset_id=dataset.id,
        user_id=current_user.id,
        question=question,
    )
    if cached_query is not None:
        log_event(
            logger,
            logging.INFO,
            "ai_query_cache_hit",
            dataset_id=dataset.id,
            user_id=current_user.id,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
        )
        return _build_cache_response(cached_query, dataset)

    try:
        normalized_sql, sql_analysis, columns, rows = await _execute_sql_with_retry(
            db=db,
            dataset=dataset,
            user_id=current_user.id,
            question=question,
        )
    except SQLPipelineExecutionError as pipeline_error:
        exc = pipeline_error.http_exception
        if exc.status_code in {status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY}:
            fallback = await query_dataset_with_ai(
                db=db,
                current_user=current_user,
                dataset_id=dataset_id,
                question=question,
            )
            if fallback.metadata is not None:
                fallback.metadata.fallback_used = True
            log_event(
                logger,
                logging.ERROR,
                "ai_sql_fallback_used",
                dataset_id=dataset.id,
                user_id=current_user.id,
                error_code="ai_sql_fallback_used",
                duration_ms=int((time.perf_counter() - started_at) * 1000),
            )
            save_failed_ai_query(
                db=db,
                dataset_id=dataset.id,
                user_id=current_user.id,
                question=question,
                sql=pipeline_error.sql,
                rows=fallback.rows,
                columns=fallback.columns,
                answer=fallback.answer,
                chart_suggestion=fallback.chart_suggestion,
                error_message=str(exc.detail),
            )
            return fallback
        log_event(
            logger,
            logging.ERROR,
            "ai_query_failed",
            dataset_id=dataset.id,
            user_id=current_user.id,
            error_code="sql_pipeline_failed",
            duration_ms=int((time.perf_counter() - started_at) * 1000),
        )
        raise exc

    if not rows:
        response = _build_query_response(
            dataset=dataset,
            answer="No matching rows were found for the question on this dataset.",
            sql=normalized_sql,
            rows=[],
            columns=columns,
            chart_suggestion="table",
            sql_analysis=sql_analysis,
        )
        save_successful_ai_query(
            db=db,
            dataset_id=dataset.id,
            user_id=current_user.id,
            question=question,
            sql=normalized_sql,
            rows=response.rows,
            columns=response.columns,
            answer=response.answer,
            chart_suggestion=response.chart_suggestion,
        )
        log_event(
            logger,
            logging.INFO,
            "ai_query_succeeded",
            dataset_id=dataset.id,
            user_id=current_user.id,
            status="no_rows",
            duration_ms=int((time.perf_counter() - started_at) * 1000),
        )
        return response

    answer, chart_suggestion = await _generate_answer_from_rows(
        dataset=dataset,
        question=question,
        sql=normalized_sql,
        columns=columns,
        rows=rows,
    )
    log_event(
        logger,
        logging.INFO,
        "ai_query_answer_generated",
        dataset_id=dataset.id,
        user_id=current_user.id,
        chart_suggestion=chart_suggestion,
    )
    response = _build_query_response(
        dataset=dataset,
        answer=answer,
        sql=normalized_sql,
        rows=rows,
        columns=columns,
        chart_suggestion=chart_suggestion,
        sql_analysis=sql_analysis,
    )
    save_successful_ai_query(
        db=db,
        dataset_id=dataset.id,
        user_id=current_user.id,
        question=question,
        sql=normalized_sql,
        rows=rows,
        columns=columns,
        answer=answer,
        chart_suggestion=chart_suggestion,
    )
    log_event(
        logger,
        logging.INFO,
        "ai_query_succeeded",
        dataset_id=dataset.id,
        user_id=current_user.id,
        status="success",
        chart_suggestion=chart_suggestion,
        duration_ms=int((time.perf_counter() - started_at) * 1000),
    )
    return response
