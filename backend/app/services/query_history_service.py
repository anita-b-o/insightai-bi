from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.query_history import QueryHistory
from app.models.query_result import QueryResult
from app.schemas.ai import (
    AIQueryHistoryDetail,
    AIQueryHistorySummary,
    AIQueryHistoryUpdateRequest,
    AIQueryResponse,
    SQLAnalysisResult,
)
from app.services.ai_service import build_visualization_suggestion
from app.services.sql_analysis_service import analyze_sql


def _to_iso8601(value) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _get_owned_query_history_record(
    db: Session,
    *,
    user_id: int,
    query_id: int,
    include_deleted: bool = False,
) -> QueryHistory | None:
    statement = (
        select(QueryHistory)
        .options(joinedload(QueryHistory.result))
        .where(
            QueryHistory.id == query_id,
            QueryHistory.user_id == user_id,
        )
    )
    if not include_deleted:
        statement = statement.where(QueryHistory.deleted_at.is_(None))
    return db.execute(statement).unique().scalar_one_or_none()


def save_query_history(
    db: Session,
    *,
    user_id: int,
    dataset_id: int,
    question: str,
    generated_sql: str | None,
    execution_time_ms: int,
    response: AIQueryResponse,
) -> QueryHistory:
    query = QueryHistory(
        user_id=user_id,
        dataset_id=dataset_id,
        question=question,
        title=None,
        is_favorite=False,
        generated_sql=generated_sql,
    )
    db.add(query)
    db.flush()
    persisted_response = response.model_copy(update={"query_id": query.id})
    persisted_sql_analysis = getattr(persisted_response, "sql_analysis", None)
    persisted_visualization = getattr(persisted_response, "visualization_suggestion", None)

    query.result = QueryResult(
        query_id=query.id,
        execution_time_ms=execution_time_ms,
        result_json=persisted_response.model_dump(mode="json"),
        visualization_suggestion=(
            persisted_visualization.model_dump(mode="json")
            if persisted_visualization
            else None
        ),
        visualization_reason=(
            persisted_visualization.reason
            if persisted_visualization
            else None
        ),
        sql_analysis=(
            persisted_sql_analysis.model_dump(mode="json")
            if persisted_sql_analysis
            else (analyze_sql(generated_sql).model_dump(mode="json") if generated_sql else None)
        ),
    )
    db.commit()
    db.refresh(query)
    return query


def list_query_history(
    db: Session,
    *,
    user_id: int,
    dataset_id: int | None = None,
) -> list[AIQueryHistorySummary]:
    statement = (
        select(QueryHistory)
        .options(joinedload(QueryHistory.result))
        .where(
            QueryHistory.user_id == user_id,
            QueryHistory.deleted_at.is_(None),
        )
        .order_by(QueryHistory.created_at.desc())
    )
    if dataset_id is not None:
        statement = statement.where(QueryHistory.dataset_id == dataset_id)

    records = db.execute(statement).unique().scalars().all()
    return [
        AIQueryHistorySummary(
            id=record.id,
            dataset_id=record.dataset_id,
            question=record.question,
            title=record.title,
            is_favorite=record.is_favorite,
            generated_sql=record.generated_sql,
            execution_time_ms=record.result.execution_time_ms if record.result else None,
            created_at=_to_iso8601(record.created_at),
            updated_at=_to_iso8601(record.updated_at),
        )
        for record in records
    ]


def get_query_history_detail(
    db: Session,
    *,
    user_id: int,
    query_id: int,
) -> AIQueryHistoryDetail:
    record = _get_owned_query_history_record(db=db, user_id=user_id, query_id=query_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query history entry not found")

    result_payload = record.result.result_json if record.result else None
    result = AIQueryResponse.model_validate(result_payload) if result_payload else None
    if result is not None:
        stored_sql_analysis = getattr(record.result, "sql_analysis", None) if record.result else None
        stored_visualization = getattr(record.result, "visualization_suggestion", None) if record.result else None
        stored_visualization_reason = getattr(record.result, "visualization_reason", None) if record.result else None

        if stored_sql_analysis:
            result.sql_analysis = SQLAnalysisResult.model_validate(stored_sql_analysis)
        elif record.generated_sql:
            result.sql_analysis = analyze_sql(record.generated_sql)

        if stored_visualization:
            result.visualization_suggestion = build_visualization_suggestion(
                columns=result.columns,
                rows=result.rows,
                sql_analysis=result.sql_analysis,
            ).model_copy(
                update={
                    **stored_visualization,
                    "reason": stored_visualization_reason
                    or stored_visualization.get("reason"),
                }
            )
        elif result.visualization_suggestion is None:
            result.visualization_suggestion = build_visualization_suggestion(
                columns=result.columns,
                rows=result.rows,
                sql_analysis=result.sql_analysis,
            )
    return AIQueryHistoryDetail(
        id=record.id,
        dataset_id=record.dataset_id,
        question=record.question,
        title=record.title,
        is_favorite=record.is_favorite,
        generated_sql=record.generated_sql,
        execution_time_ms=record.result.execution_time_ms if record.result else None,
        created_at=_to_iso8601(record.created_at),
        updated_at=_to_iso8601(record.updated_at),
        result=result,
    )


def update_query_history(
    db: Session,
    *,
    user_id: int,
    query_id: int,
    payload: AIQueryHistoryUpdateRequest,
) -> AIQueryHistoryDetail:
    record = _get_owned_query_history_record(db=db, user_id=user_id, query_id=query_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query history entry not found")

    if payload.title is not None or "title" in payload.model_fields_set:
        record.title = payload.title
    if payload.is_favorite is not None:
        record.is_favorite = payload.is_favorite
    record.updated_at = datetime.now(timezone.utc)

    db.add(record)
    db.commit()
    db.refresh(record)
    return get_query_history_detail(db=db, user_id=user_id, query_id=query_id)


def soft_delete_query_history(
    db: Session,
    *,
    user_id: int,
    query_id: int,
) -> None:
    record = _get_owned_query_history_record(db=db, user_id=user_id, query_id=query_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query history entry not found")

    now = datetime.now(timezone.utc)
    record.deleted_at = now
    record.updated_at = now
    db.add(record)
    db.commit()
