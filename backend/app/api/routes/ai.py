from time import perf_counter

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import (
    AIInsightRefreshRequest,
    AIInsightsRequest,
    AIInsightsResponse,
    DatasetInsightRunDetail,
    DatasetInsightRunSummary,
    AIQueryHistoryDetail,
    AIQueryHistorySummary,
    AIQueryHistoryUpdateRequest,
    AIQueryRequest,
    AIQueryResponse,
)
from app.services.ai_service import query_dataset_with_sql_ai
from app.services.insight_service import (
    generate_and_save_insights,
    get_insight_run_detail,
    get_latest_insights,
    list_insight_runs,
)
from app.services.query_history_service import (
    get_query_history_detail,
    list_query_history,
    save_query_history,
    soft_delete_query_history,
    update_query_history,
)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/insights", response_model=AIInsightsResponse)
def read_latest_dataset_insights(
    dataset_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIInsightsResponse:
    return get_latest_insights(db=db, current_user=current_user, dataset_id=dataset_id)


@router.get("/insights/runs", response_model=list[DatasetInsightRunSummary])
def read_dataset_insight_runs(
    dataset_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DatasetInsightRunSummary]:
    return list_insight_runs(db=db, current_user=current_user, dataset_id=dataset_id)


@router.get("/insights/runs/{run_id}", response_model=DatasetInsightRunDetail)
def read_dataset_insight_run_detail(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DatasetInsightRunDetail:
    return get_insight_run_detail(db=db, current_user=current_user, run_id=run_id)


@router.post("/insights", response_model=AIInsightsResponse)
def generate_dataset_insights(
    payload: AIInsightsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIInsightsResponse:
    return generate_and_save_insights(db=db, current_user=current_user, dataset_id=payload.dataset_id)


@router.post("/insights/refresh", response_model=AIInsightsResponse)
def refresh_dataset_insights(
    payload: AIInsightRefreshRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIInsightsResponse:
    return generate_and_save_insights(db=db, current_user=current_user, dataset_id=payload.dataset_id)


@router.post("/query", response_model=AIQueryResponse)
async def query_dataset(
    payload: AIQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIQueryResponse:
    started_at = perf_counter()
    response = await query_dataset_with_sql_ai(
        db=db,
        current_user=current_user,
        dataset_id=payload.dataset_id,
        question=payload.question,
    )
    duration_ms = max(1, int((perf_counter() - started_at) * 1000))
    history_record = save_query_history(
        db=db,
        user_id=current_user.id,
        dataset_id=payload.dataset_id,
        question=payload.question,
        generated_sql=response.sql,
        execution_time_ms=duration_ms,
        response=response,
    )
    response.query_id = history_record.id
    return response


@router.get("/history", response_model=list[AIQueryHistorySummary])
def read_query_history(
    dataset_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AIQueryHistorySummary]:
    return list_query_history(db=db, user_id=current_user.id, dataset_id=dataset_id)


@router.get("/history/{query_id}", response_model=AIQueryHistoryDetail)
def read_query_history_detail(
    query_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIQueryHistoryDetail:
    return get_query_history_detail(db=db, user_id=current_user.id, query_id=query_id)


@router.patch("/history/{query_id}", response_model=AIQueryHistoryDetail)
def patch_query_history(
    query_id: int,
    payload: AIQueryHistoryUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIQueryHistoryDetail:
    return update_query_history(db=db, user_id=current_user.id, query_id=query_id, payload=payload)


@router.delete("/history/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_query_history(
    query_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    soft_delete_query_history(db=db, user_id=current_user.id, query_id=query_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
