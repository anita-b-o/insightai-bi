import csv
import io
import logging
import re
from datetime import datetime, timezone

import pandas as pd
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import Boolean, DateTime, Float, Integer, Text, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.observability import log_event
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dashboard import Dashboard
from app.models.dashboard_widget import DashboardWidget
from app.models.dataset_insight_run import DatasetInsightRun
from app.models.query_history import QueryHistory
from app.models.user import User

logger = logging.getLogger("app.datasets.service")
DATASET_TABLE_PATTERN = re.compile(r"^dataset_[1-9][0-9]*$")
SQL_IDENTIFIER_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
UPLOAD_READ_CHUNK_BYTES = 64 * 1024


def dataset_table_name(dataset_id: int) -> str:
    if isinstance(dataset_id, bool) or not isinstance(dataset_id, int) or dataset_id <= 0:
        raise ValueError("Dataset id must be a positive integer")
    return f"dataset_{dataset_id}"


def validate_dataset_table_name(dataset: Dataset) -> str:
    expected = dataset_table_name(dataset.id)
    if dataset.table_name != expected or not DATASET_TABLE_PATTERN.fullmatch(expected):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Dataset table metadata is invalid")
    return expected


def dataset_table_exists(db: Session, dataset: Dataset) -> bool:
    return inspect(db.connection()).has_table(validate_dataset_table_name(dataset))


def _decode_csv_content(content: bytes) -> tuple[str, str]:
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return content.decode(encoding), encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded CSV must use UTF-8, UTF-8 BOM, or Latin-1") from last_error


def _detect_csv_delimiter(text_value: str) -> str:
    sample = "\n".join(text_value.splitlines()[:5]).strip()
    if not sample:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The CSV file is empty")
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;").delimiter
    except csv.Error:
        return ";" if ";" in sample.splitlines()[0] and "," not in sample.splitlines()[0] else ","


def _validate_headers(text_value: str, delimiter: str) -> list[str]:
    try:
        reader = csv.reader(io.StringIO(text_value), delimiter=delimiter, strict=True)
        headers = next(reader)
    except (csv.Error, StopIteration) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is not a valid CSV") from exc
    normalized = [header.strip() for header in headers]
    if not normalized or any(not header for header in normalized):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The CSV file must include non-empty header names")
    if len(normalized) != len(set(normalized)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The CSV file contains duplicate header names")
    return normalized


def _load_csv_dataframe(content: bytes) -> tuple[pd.DataFrame, str, str]:
    text_value, encoding = _decode_csv_content(content)
    delimiter = _detect_csv_delimiter(text_value)
    headers = _validate_headers(text_value, delimiter)
    try:
        dataframe = pd.read_csv(io.StringIO(text_value), sep=delimiter, on_bad_lines="error")
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is not a valid CSV") from exc
    if dataframe.empty:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The CSV file must include at least one data row")
    dataframe.columns = headers
    if dataframe.shape[1] > settings.max_dataset_columns:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"The CSV exceeds the {settings.max_dataset_columns} column limit")
    if dataframe.shape[0] > settings.max_dataset_rows:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"The CSV exceeds the {settings.max_dataset_rows} row limit")
    lengths = dataframe.astype("string").apply(lambda column: column.str.len().max()).fillna(0)
    if int(lengths.max()) > settings.max_cell_length:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"The CSV exceeds the {settings.max_cell_length} character cell limit")
    return dataframe, encoding, delimiter


def _normalize_inferred_type(series: pd.Series) -> str:
    dtype = str(series.dtype)
    if dtype.startswith("int"):
        return "integer"
    if dtype.startswith("float"):
        return "float"
    if dtype == "bool":
        return "boolean"
    if "datetime" in dtype:
        return "datetime"
    return "string"


def _normalize_sql_identifier(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_") or "column"
    if normalized[0].isdigit():
        normalized = f"col_{normalized}"
    return normalized[:63]


def _build_sql_column_names(columns: list[str]) -> list[str]:
    used: set[str] = set()
    result: list[str] = []
    for column in columns:
        base = _normalize_sql_identifier(column)
        candidate, suffix = base, 1
        while candidate in used:
            suffix += 1
            candidate = f"{base[: 63 - len(str(suffix)) - 1]}_{suffix}"
        used.add(candidate)
        result.append(candidate)
    return result


def _sqlalchemy_type_for_series(series: pd.Series):
    return {"integer": Integer(), "float": Float(), "boolean": Boolean(), "datetime": DateTime(timezone=False)}.get(_normalize_inferred_type(series), Text())


def materialize_dataset_table(db: Session, dataset: Dataset, dataframe: pd.DataFrame, sql_column_names: list[str] | None = None) -> Dataset:
    sql_column_names = sql_column_names or _build_sql_column_names([str(column) for column in dataframe.columns])
    table_name = dataset_table_name(dataset.id)
    if dataset.table_name not in (None, table_name):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Dataset table metadata is invalid")
    if inspect(db.connection()).has_table(table_name):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Dataset table already exists")
    dataset.table_name = table_name
    dataset.updated_at = datetime.now(timezone.utc)
    db.flush()
    stored = dataframe.copy()
    stored.columns = sql_column_names
    stored.to_sql(name=table_name, con=db.connection(), if_exists="fail", index=False, dtype={sql_name: _sqlalchemy_type_for_series(dataframe.iloc[:, index]) for index, sql_name in enumerate(sql_column_names)})
    return dataset


async def _read_upload_with_limit(upload: UploadFile) -> bytes:
    content = bytearray()
    while chunk := await upload.read(UPLOAD_READ_CHUNK_BYTES):
        content.extend(chunk)
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"The upload exceeds the {settings.max_upload_bytes} byte limit")
    return bytes(content)


def _cleanup_dynamic_table(db: Session, table_name: str | None) -> None:
    if table_name is None or not DATASET_TABLE_PATTERN.fullmatch(table_name):
        return
    try:
        db.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("dataset_upload_cleanup_failed", extra={"table_name": table_name})


async def process_uploaded_csv(db: Session, owner_id: int, dataset_name: str, description: str | None, upload: UploadFile) -> Dataset:
    try:
        content = await _read_upload_with_limit(upload)
        dataframe, encoding, delimiter = _load_csv_dataframe(content)
        log_event(logger, logging.INFO, "dataset_upload_parsed", owner_id=owner_id, size_bytes=len(content), encoding=encoding, delimiter=delimiter, rows=int(dataframe.shape[0]), columns=int(dataframe.shape[1]))
    except HTTPException:
        log_event(logger, logging.WARNING, "dataset_upload_rejected", owner_id=owner_id)
        raise
    except Exception as exc:
        logger.exception("dataset_upload_parse_failed", extra={"owner_id": owner_id})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is not a valid CSV") from exc
    finally:
        await upload.close()

    table_name: str | None = None
    try:
        dataset = Dataset(name=dataset_name, description=description, original_filename=upload.filename or "uploaded.csv", storage_path=None, table_name=None, file_size_bytes=len(content), row_count=int(dataframe.shape[0]), column_count=int(dataframe.shape[1]), owner_id=owner_id)
        db.add(dataset)
        db.flush()
        table_name = dataset_table_name(dataset.id)
        sql_column_names = _build_sql_column_names([str(column) for column in dataframe.columns])
        for position, column_name in enumerate(dataframe.columns):
            series = dataframe[column_name]
            values = series.dropna()
            db.add(DatasetColumn(dataset_id=dataset.id, name=str(column_name), sql_name=sql_column_names[position], position=position, inferred_type=_normalize_inferred_type(series), nullable=bool(series.isnull().any()), distinct_count=int(series.nunique(dropna=True)), sample_value=(str(values.iloc[0])[:500] if not values.empty else None)))
        materialize_dataset_table(db, dataset, dataframe, sql_column_names)
        db.commit()
        log_event(logger, logging.INFO, "dataset_upload_succeeded", dataset_id=dataset.id, owner_id=owner_id, row_count=dataset.row_count, column_count=dataset.column_count)
        return db.query(Dataset).options(joinedload(Dataset.columns)).filter(Dataset.id == dataset.id).one()
    except Exception as exc:
        db.rollback()
        _cleanup_dynamic_table(db, table_name)
        logger.exception("dataset_upload_database_failed", extra={"owner_id": owner_id, "table_name": table_name})
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Dataset upload could not be completed safely") from exc


def _dataset_has_dashboard_references(db: Session, dataset_id: int) -> bool:
    if db.scalar(select(Dashboard.id).where(Dashboard.dataset_id == dataset_id).limit(1)) is not None:
        return True
    query_ids = select(QueryHistory.id).where(QueryHistory.dataset_id == dataset_id)
    insight_ids = select(DatasetInsightRun.id).where(DatasetInsightRun.dataset_id == dataset_id)
    return db.scalar(
        select(DashboardWidget.id)
        .where(
            ((DashboardWidget.source_type == "query") & DashboardWidget.source_id.in_(query_ids))
            | ((DashboardWidget.source_type == "insight") & DashboardWidget.source_id.in_(insight_ids))
        )
        .limit(1)
    ) is not None


def delete_dataset(db: Session, *, current_user: User, dataset_id: int) -> None:
    dataset = db.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.owner_id == current_user.id))
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    if _dataset_has_dashboard_references(db, dataset.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Dataset is used by a dashboard and cannot be deleted until those references are removed")
    table_name = validate_dataset_table_name(dataset)
    if not dataset_table_exists(db, dataset):
        logger.error("dataset_delete_table_missing", extra={"dataset_id": dataset.id, "table_name": table_name})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Dataset data table is missing; deletion was not attempted")
    try:
        db.execute(text(f'DROP TABLE "{table_name}"'))
        db.delete(dataset)
        db.commit()
        log_event(logger, logging.INFO, "dataset_deleted", dataset_id=dataset_id, owner_id=current_user.id)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("dataset_delete_failed", extra={"dataset_id": dataset_id, "owner_id": current_user.id})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Dataset could not be deleted safely") from exc
