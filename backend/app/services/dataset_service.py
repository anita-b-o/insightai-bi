import csv
import io
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import Boolean, DateTime, Float, Integer, Text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.observability import log_event
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn

logger = logging.getLogger("app.datasets.service")


def _decode_csv_content(content: bytes) -> tuple[str, str]:
    encodings_to_try = ["utf-8-sig", "utf-8", "latin-1"]
    last_error: UnicodeDecodeError | None = None

    for encoding in encodings_to_try:
        try:
            return content.decode(encoding), encoding
        except UnicodeDecodeError as exc:
            last_error = exc

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="The uploaded CSV could not be decoded as UTF-8, UTF-8 BOM, or Latin-1",
    ) from last_error


def _detect_csv_delimiter(text: str) -> str:
    sample = "\n".join(text.splitlines()[:5]).strip()
    if not sample:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The CSV file is empty")

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        return dialect.delimiter
    except csv.Error:
        first_line = sample.splitlines()[0]
        if ";" in first_line and "," not in first_line:
            return ";"
        return ","


def _load_csv_dataframe(content: bytes) -> tuple[pd.DataFrame, str, str]:
    text, encoding = _decode_csv_content(content)
    delimiter = _detect_csv_delimiter(text)

    try:
        dataframe = pd.read_csv(io.StringIO(text), sep=delimiter)
    except pd.errors.EmptyDataError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The CSV file is empty") from exc
    except pd.errors.ParserError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The uploaded CSV could not be parsed with delimiter '{delimiter}'",
        ) from exc

    if len(dataframe.columns) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The CSV file must include a header row")

    normalized_headers = [str(column).strip() for column in dataframe.columns]
    if any(not header for header in normalized_headers):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The CSV file contains an empty header name",
        )

    if dataframe.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The CSV file must include at least one data row",
        )

    dataframe.columns = normalized_headers
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
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        normalized = "column"
    if normalized[0].isdigit():
        normalized = f"col_{normalized}"
    return normalized[:63]


def _build_sql_column_names(columns: list[str]) -> list[str]:
    used: set[str] = set()
    result: list[str] = []
    for column in columns:
        base = _normalize_sql_identifier(column)
        candidate = base
        suffix = 1
        while candidate in used:
            suffix += 1
            candidate = f"{base}_{suffix}"
        used.add(candidate)
        result.append(candidate)
    return result


def _build_table_name(dataset_id: int) -> str:
    return f"dataset_{dataset_id}"


def _sqlalchemy_type_for_series(series: pd.Series):
    inferred_type = _normalize_inferred_type(series)
    if inferred_type == "integer":
        return Integer()
    if inferred_type == "float":
        return Float()
    if inferred_type == "boolean":
        return Boolean()
    if inferred_type == "datetime":
        return DateTime(timezone=False)
    return Text()


def materialize_dataset_table(
    db: Session,
    dataset: Dataset,
    dataframe: pd.DataFrame,
    sql_column_names: list[str] | None = None,
) -> Dataset:
    if sql_column_names is None:
        sql_column_names = _build_sql_column_names([str(column) for column in dataframe.columns])

    dataset.table_name = dataset.table_name or _build_table_name(dataset.id)
    dataset.updated_at = datetime.now(timezone.utc)
    dataframe_to_store = dataframe.copy()
    dataframe_to_store.columns = sql_column_names

    dtype_mapping = {
        sql_name: _sqlalchemy_type_for_series(dataframe.iloc[:, index])
        for index, sql_name in enumerate(sql_column_names)
    }
    dataframe_to_store.to_sql(
        name=dataset.table_name,
        con=db.connection(),
        if_exists="replace",
        index=False,
        dtype=dtype_mapping,
    )
    return dataset


async def process_uploaded_csv(
    db: Session,
    owner_id: int,
    dataset_name: str,
    description: str | None,
    upload: UploadFile,
) -> Dataset:
    filename = upload.filename or "unknown.csv"
    content_type = upload.content_type or "unknown"
    content = b""
    try:
        content = await upload.read()
        file_size = len(content)
        log_event(
            logger,
            logging.INFO,
            "dataset_upload_started",
            filename=filename,
            content_type=content_type,
            size_bytes=file_size,
            owner_id=owner_id,
        )

        dataframe, encoding, delimiter = _load_csv_dataframe(content)
        log_event(
            logger,
            logging.INFO,
            "dataset_upload_parsed",
            filename=filename,
            encoding=encoding,
            delimiter=delimiter,
            rows=int(dataframe.shape[0]),
            columns=int(dataframe.shape[1]),
            owner_id=owner_id,
        )
    except HTTPException as exc:
        log_event(
            logger,
            logging.WARNING,
            "dataset_upload_failed",
            filename=filename,
            content_type=content_type,
            size_bytes=len(content) if "content" in locals() else None,
            owner_id=owner_id,
            error_code="dataset_upload_rejected",
        )
        raise
    except Exception as exc:
        logger.exception(
            "[DATASET UPLOAD] failed filename=%s content_type=%s size_bytes=%s parser_error=%s owner_id=%s",
            filename,
            content_type,
            len(content) if "content" in locals() else None,
            str(exc),
            owner_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid CSV",
        ) from exc

    stored_filename = f"{uuid4()}_{upload.filename}"
    target_path = settings.storage_dir / stored_filename

    try:
        target_path.write_bytes(content)
        log_event(
            logger,
            logging.INFO,
            "dataset_upload_stored",
            filename=filename,
            target_path=str(Path(target_path).as_posix()),
            size_bytes=len(content),
            owner_id=owner_id,
        )

        dataset = Dataset(
            name=dataset_name,
            description=description,
            original_filename=upload.filename or stored_filename,
            storage_path=str(Path(target_path).as_posix()),
            table_name=None,
            file_size_bytes=len(content),
            row_count=int(dataframe.shape[0]),
            column_count=int(dataframe.shape[1]),
            owner_id=owner_id,
        )
        db.add(dataset)
        db.flush()
        sql_column_names = _build_sql_column_names([str(column) for column in dataframe.columns])

        for position, column_name in enumerate(dataframe.columns):
            series = dataframe[column_name]
            sample_value = None
            non_null_values = series.dropna()
            if not non_null_values.empty:
                sample_value = str(non_null_values.iloc[0])[:500]

            db.add(
                DatasetColumn(
                    dataset_id=dataset.id,
                    name=str(column_name),
                    sql_name=sql_column_names[position],
                    position=position,
                    inferred_type=_normalize_inferred_type(series),
                    nullable=bool(series.isnull().any()),
                    distinct_count=int(series.nunique(dropna=True)),
                    sample_value=sample_value,
                )
            )

        materialize_dataset_table(db=db, dataset=dataset, dataframe=dataframe, sql_column_names=sql_column_names)
        db.commit()
        log_event(
            logger,
            logging.INFO,
            "dataset_upload_succeeded",
            dataset_id=dataset.id,
            owner_id=owner_id,
            row_count=dataset.row_count,
            column_count=dataset.column_count,
        )
        return (
            db.query(Dataset)
            .options(joinedload(Dataset.columns))
            .filter(Dataset.id == dataset.id)
            .one()
        )
    except SQLAlchemyError as exc:
        db.rollback()
        if target_path.exists():
            target_path.unlink(missing_ok=True)
        logger.exception(
            "[DATASET UPLOAD] database failure filename=%s size_bytes=%s owner_id=%s error=%s",
            filename,
            len(content),
            owner_id,
            str(exc),
        )
        log_event(
            logger,
            logging.ERROR,
            "dataset_upload_failed",
            filename=filename,
            owner_id=owner_id,
            error_code="dataset_upload_database_failure",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dataset upload failed because the database schema is out of date. Run migrations and retry.",
        ) from exc
