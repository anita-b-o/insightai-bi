from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.services.dataset_service import _build_sql_column_names, materialize_dataset_table


def ensure_dataset_queryable(db: Session, dataset: Dataset) -> Dataset:
    if dataset.row_count == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dataset is empty")

    if not dataset.columns:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dataset has no detected columns")

    engine = db.get_bind()
    inspector = inspect(engine)
    table_exists = bool(dataset.table_name) and inspector.has_table(dataset.table_name)

    if table_exists:
        return dataset

    csv_path = Path(dataset.storage_path)
    if not csv_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dataset source file is missing and cannot be materialized",
        )

    try:
        dataframe = pd.read_csv(csv_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dataset source file could not be loaded for querying",
        ) from exc

    ordered_columns = sorted(dataset.columns, key=lambda item: item.position)
    sql_column_names = _build_sql_column_names([column.name for column in ordered_columns])
    materialize_dataset_table(db=db, dataset=dataset, dataframe=dataframe, sql_column_names=sql_column_names)

    for column, sql_name in zip(ordered_columns, sql_column_names):
        if column.sql_name != sql_name:
            column.sql_name = sql_name
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def execute_dataset_query(db: Session, dataset: Dataset, sql: str) -> tuple[list[str], list[dict[str, object]]]:
    try:
        result = db.execute(text(sql))
        columns = list(result.keys())
        rows = [dict(row._mapping) for row in result.fetchall()]
        return columns, rows
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Generated SQL could not be executed on this dataset: {exc.__class__.__name__}",
        ) from exc
