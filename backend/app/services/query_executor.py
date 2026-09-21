from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.services.dataset_service import dataset_table_exists, validate_dataset_table_name

logger = logging.getLogger("app.datasets.query_executor")


def ensure_dataset_queryable(db: Session, dataset: Dataset) -> Dataset:
    if dataset.row_count == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dataset is empty")
    if not dataset.columns:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dataset has no detected columns")
    table_name = validate_dataset_table_name(dataset)
    if not dataset_table_exists(db, dataset):
        logger.error("dataset_table_missing", extra={"dataset_id": dataset.id, "table_name": table_name})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Dataset data table is missing; this dataset requires integrity recovery")
    return dataset


def execute_dataset_query(db: Session, dataset: Dataset, sql: str) -> tuple[list[str], list[dict[str, object]]]:
    try:
        result = db.execute(text(sql))
        return list(result.keys()), [dict(row._mapping) for row in result.fetchall()]
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Generated SQL could not be executed on this dataset: {exc.__class__.__name__}") from exc
