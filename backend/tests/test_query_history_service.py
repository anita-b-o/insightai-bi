from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException
import pytest

from app.schemas.ai import AIQueryHistoryUpdateRequest
from app.services import query_history_service
from app.services.ai_service import build_visualization_suggestion


def _query_record(*, user_id: int = 1, deleted_at=None, title=None, is_favorite=False):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=7,
        user_id=user_id,
        dataset_id=3,
        question="Top products",
        title=title,
        is_favorite=is_favorite,
        generated_sql="select * from sales",
        created_at=now,
        updated_at=now,
        deleted_at=deleted_at,
        result=SimpleNamespace(
            execution_time_ms=42,
            result_json={
                "query_id": 7,
                "answer": "Answer",
                "sql": "select * from sales",
                "rows": [],
                "columns": [],
                "chart_suggestion": None,
                "visualization_suggestion": None,
                "metadata": None,
            },
            visualization_suggestion=None,
            visualization_reason=None,
        ),
    )


def test_detail_denies_history_from_other_user():
    db = MagicMock()
    db.execute.return_value.unique.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(HTTPException) as exc:
        query_history_service.get_query_history_detail(db=db, user_id=1, query_id=99)

    assert exc.value.status_code == 404


def test_update_denies_history_from_other_user():
    db = MagicMock()
    db.execute.return_value.unique.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(HTTPException) as exc:
        query_history_service.update_query_history(
            db=db,
            user_id=1,
            query_id=99,
            payload=AIQueryHistoryUpdateRequest(title="Renamed"),
        )

    assert exc.value.status_code == 404


def test_delete_denies_history_from_other_user():
    db = MagicMock()
    db.execute.return_value.unique.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(HTTPException) as exc:
        query_history_service.soft_delete_query_history(db=db, user_id=1, query_id=99)

    assert exc.value.status_code == 404


def test_soft_delete_excludes_entry_from_list():
    db = MagicMock()
    active = _query_record(deleted_at=None)
    deleted = _query_record(deleted_at=datetime.now(timezone.utc))
    db.execute.return_value.unique.return_value.scalars.return_value.all.return_value = [active]

    result = query_history_service.list_query_history(db=db, user_id=1, dataset_id=3)

    assert len(result) == 1
    assert result[0].id == active.id
    assert all(item.id != deleted.id or item.created_at != deleted.created_at.isoformat() for item in result)


def test_update_favorite_persists_change(monkeypatch):
    db = MagicMock()
    record = _query_record(is_favorite=False)
    db.execute.return_value.unique.return_value.scalar_one_or_none.return_value = record

    monkeypatch.setattr(
        query_history_service,
        "get_query_history_detail",
        MagicMock(
            return_value=SimpleNamespace(
                id=record.id,
                is_favorite=True,
                title=record.title,
                result=None,
                question=record.question,
            )
        ),
    )

    result = query_history_service.update_query_history(
        db=db,
        user_id=1,
        query_id=record.id,
        payload=AIQueryHistoryUpdateRequest(is_favorite=True),
    )

    assert record.is_favorite is True
    assert result.is_favorite is True
    db.commit.assert_called_once()


def test_update_rename_trims_and_persists_title(monkeypatch):
    db = MagicMock()
    record = _query_record(title=None)
    db.execute.return_value.unique.return_value.scalar_one_or_none.return_value = record

    monkeypatch.setattr(
        query_history_service,
        "get_query_history_detail",
        MagicMock(
            return_value=SimpleNamespace(
                id=record.id,
                is_favorite=record.is_favorite,
                title="Revenue snapshot",
                result=None,
                question=record.question,
            )
        ),
    )

    result = query_history_service.update_query_history(
        db=db,
        user_id=1,
        query_id=record.id,
        payload=AIQueryHistoryUpdateRequest(title="  Revenue snapshot  "),
    )

    assert record.title == "Revenue snapshot"
    assert result.title == "Revenue snapshot"
    db.commit.assert_called_once()


def test_bar_suggestion_persists_in_query_result():
    response = SimpleNamespace(
        model_copy=lambda update: SimpleNamespace(
            visualization_suggestion=SimpleNamespace(
                model_dump=lambda mode="json": {"type": "bar", "x": "product_name", "y": "revenue", "reason": "Detected a categorical column and a numeric metric, which fits a bar chart."},
                reason="Detected a categorical column and a numeric metric, which fits a bar chart.",
            ),
            model_dump=lambda mode="json": {
                "query_id": 7,
                "answer": "Answer",
                "sql": "select product_name, revenue from sales",
                "rows": [{"product_name": "A", "revenue": 100}],
                "columns": ["product_name", "revenue"],
                "chart_suggestion": None,
                "visualization_suggestion": {"type": "bar", "x": "product_name", "y": "revenue", "reason": "Detected a categorical column and a numeric metric, which fits a bar chart."},
                "metadata": None,
            },
        ),
        visualization_suggestion=SimpleNamespace(
            model_dump=lambda mode="json": {"type": "bar", "x": "product_name", "y": "revenue", "reason": "Detected a categorical column and a numeric metric, which fits a bar chart."},
            reason="Detected a categorical column and a numeric metric, which fits a bar chart.",
        ),
    )
    db = MagicMock()

    record = query_history_service.save_query_history(
        db=db,
        user_id=1,
        dataset_id=3,
        question="Top products",
        generated_sql="select product_name, revenue from sales",
        execution_time_ms=42,
        response=response,
    )

    created_result = record.result
    assert created_result.visualization_suggestion["type"] == "bar"
    assert created_result.visualization_reason == "Detected a categorical column and a numeric metric, which fits a bar chart."


def test_table_only_fallback_works_for_old_history():
    db = MagicMock()
    record = _query_record()
    record.result.result_json["rows"] = [{"note": "alpha"}]
    record.result.result_json["columns"] = ["note"]
    record.result.result_json["visualization_suggestion"] = None
    record.result.visualization_suggestion = None
    record.result.visualization_reason = None
    db.execute.return_value.unique.return_value.scalar_one_or_none.return_value = record

    result = query_history_service.get_query_history_detail(db=db, user_id=1, query_id=record.id)

    assert result.result is not None
    assert result.result.visualization_suggestion is not None
    assert result.result.visualization_suggestion.type == "table_only"


def test_line_visualization_reason_detected():
    suggestion = build_visualization_suggestion(
        columns=["order_date", "revenue"],
        rows=[{"order_date": "2026-04-01", "revenue": 100}, {"order_date": "2026-04-02", "revenue": 120}],
    )

    assert suggestion.type == "line"
    assert suggestion.reason == "Detected a temporal dimension and a numeric metric, which fits a line chart."
