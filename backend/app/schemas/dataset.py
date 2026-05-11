from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DatasetColumnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    position: int
    inferred_type: str
    nullable: bool
    distinct_count: int | None
    sample_value: str | None


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    original_filename: str
    file_size_bytes: int
    row_count: int
    column_count: int
    created_at: datetime
    columns: list[DatasetColumnRead]


class DatasetListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    original_filename: str
    row_count: int
    column_count: int
    created_at: datetime
