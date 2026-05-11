from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.dataset import Dataset
from app.models.user import User
from app.schemas.ai import AIInsightsResponse, DatasetInsightRunSummary
from app.schemas.dataset import DatasetListItem, DatasetRead
from app.services.dataset_service import process_uploaded_csv
from app.services.insight_service import generate_and_save_insights, get_latest_insights, list_insight_runs

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/upload", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dataset:
    if Path(file.filename or "").suffix.lower() != ".csv":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV files are allowed")

    dataset = await process_uploaded_csv(
        db=db,
        owner_id=current_user.id,
        dataset_name=name,
        description=description,
        upload=file,
    )
    return dataset


@router.get("", response_model=list[DatasetListItem])
def list_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Dataset]:
    return (
        db.query(Dataset)
        .filter(Dataset.owner_id == current_user.id)
        .order_by(Dataset.created_at.desc())
        .all()
    )


@router.get("/{dataset_id}", response_model=DatasetRead)
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dataset:
    dataset = (
        db.query(Dataset)
        .options(joinedload(Dataset.columns))
        .filter(Dataset.id == dataset_id, Dataset.owner_id == current_user.id)
        .first()
    )
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset


@router.post("/{dataset_id}/insights/generate", response_model=AIInsightsResponse)
def generate_dataset_insights_for_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIInsightsResponse:
    return generate_and_save_insights(db=db, current_user=current_user, dataset_id=dataset_id)


@router.get("/{dataset_id}/insights", response_model=AIInsightsResponse)
def get_latest_dataset_insights_for_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIInsightsResponse:
    return get_latest_insights(db=db, current_user=current_user, dataset_id=dataset_id)


@router.get("/{dataset_id}/insights/runs", response_model=list[DatasetInsightRunSummary])
def list_dataset_insight_runs_for_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DatasetInsightRunSummary]:
    return list_insight_runs(db=db, current_user=current_user, dataset_id=dataset_id)
