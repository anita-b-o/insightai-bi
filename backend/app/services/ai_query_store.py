from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models.ai_query import AIQuery


def normalize_question(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip().lower())


def get_cached_ai_query(
    db: Session,
    *,
    dataset_id: int,
    user_id: int,
    question: str,
) -> AIQuery | None:
    normalized = normalize_question(question)
    return (
        db.query(AIQuery)
        .filter(
            AIQuery.dataset_id == dataset_id,
            AIQuery.user_id == user_id,
            AIQuery.question_normalized == normalized,
            AIQuery.error_message.is_(None),
            AIQuery.answer.is_not(None),
        )
        .order_by(AIQuery.created_at.desc())
        .first()
    )


def build_result_payload(
    *,
    rows: list[dict[str, object]],
    columns: list[str],
) -> dict[str, object]:
    return {"rows": rows, "columns": columns}


def save_ai_query(
    db: Session,
    *,
    dataset_id: int,
    user_id: int,
    question: str,
    sql: str | None = None,
    result: dict | list | None = None,
    answer: str | None = None,
    chart_suggestion: str | None = None,
    error_message: str | None = None,
) -> AIQuery:
    record = AIQuery(
        dataset_id=dataset_id,
        user_id=user_id,
        question=question,
        question_normalized=normalize_question(question),
        sql=sql,
        result=result,
        answer=answer,
        chart_suggestion=chart_suggestion,
        error_message=error_message,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def save_successful_ai_query(
    db: Session,
    *,
    dataset_id: int,
    user_id: int,
    question: str,
    sql: str | None,
    rows: list[dict[str, object]],
    columns: list[str],
    answer: str,
    chart_suggestion: str | None,
) -> AIQuery:
    return save_ai_query(
        db=db,
        dataset_id=dataset_id,
        user_id=user_id,
        question=question,
        sql=sql,
        result=build_result_payload(rows=rows, columns=columns),
        answer=answer,
        chart_suggestion=chart_suggestion,
    )


def save_failed_ai_query(
    db: Session,
    *,
    dataset_id: int,
    user_id: int,
    question: str,
    sql: str | None,
    error_message: str,
    rows: list[dict[str, object]] | None = None,
    columns: list[str] | None = None,
    answer: str | None = None,
    chart_suggestion: str | None = None,
) -> AIQuery:
    result = None
    if rows is not None and columns is not None:
        result = build_result_payload(rows=rows, columns=columns)

    return save_ai_query(
        db=db,
        dataset_id=dataset_id,
        user_id=user_id,
        question=question,
        sql=sql,
        result=result,
        answer=answer,
        chart_suggestion=chart_suggestion,
        error_message=error_message,
    )
