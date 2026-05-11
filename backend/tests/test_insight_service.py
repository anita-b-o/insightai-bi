from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException
import pytest

from app.schemas.ai import AIInsight, AIInsightsResponse
from app.services import insight_service


def mock_return(value):
    return lambda *args, **kwargs: value


def _dataset(
    *,
    dataset_id: int = 3,
    owner_id: int = 1,
    name: str = "Sales",
    updated_at: datetime | None = None,
    table_name: str = "dataset_sales",
):
    return SimpleNamespace(
        id=dataset_id,
        owner_id=owner_id,
        name=name,
        table_name=table_name,
        row_count=100,
        updated_at=updated_at or datetime.now(timezone.utc),
    )


def _run(*, run_id: int = 11, dataset_id: int = 3, user_id: int = 1, status: str = "success", error_message: str | None = None):
    now = datetime.now(timezone.utc)
    dataset = _dataset(dataset_id=dataset_id, owner_id=user_id, updated_at=now)
    return SimpleNamespace(
        id=run_id,
        dataset_id=dataset_id,
        user_id=user_id,
        dataset=dataset,
        status=status,
        generated_at=now,
        created_at=now,
        updated_at=now,
        dataset_updated_at_snapshot=now,
        error_message=error_message,
        insights_json=[
            AIInsight(
                type="distribution",
                title="Revenue distribution snapshot",
                description="Revenue ranges from 10 to 100.",
                columns=["stat", "value"],
                rows=[{"stat": "Minimum", "value": 10}],
            ).model_dump(mode="json")
        ],
    )


def test_save_successful_insight_run_persists_payload():
    db = MagicMock()
    dataset = _dataset()
    response = AIInsightsResponse(
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        generated_at=datetime.now(timezone.utc).isoformat(),
        insights=[
            AIInsight(
                type="trend",
                title="Revenue increased over time",
                summary="Summed revenue increased over time.",
                columns=["period", "metric"],
                rows=[{"period": "2026-04-01", "metric": 120}],
            )
        ],
    )

    run = insight_service.save_insight_run(
        db,
        dataset=dataset,
        user_id=1,
        status="success",
        insights_response=response,
    )

    assert run.status == "success"
    assert run.dataset_id == dataset.id
    assert run.insights_json[0]["type"] == "trend"
    db.commit.assert_called_once()


def test_generate_and_save_failed_run_persists_error(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    dataset = _dataset()
    captured: list[tuple[str, str | None]] = []

    monkeypatch.setattr(insight_service, "_load_owned_dataset", mock_return(dataset))
    monkeypatch.setattr(insight_service, "ensure_dataset_queryable", mock_return(dataset))
    monkeypatch.setattr(
        insight_service,
        "generate_insights",
        lambda *args, **kwargs: (_ for _ in ()).throw(HTTPException(status_code=400, detail="Dataset is empty")),
    )

    def fake_save(db, *, dataset, user_id, status, insights_response=None, error_message=None):
        captured.append((status, error_message))
        return _run(status=status, error_message=error_message)

    monkeypatch.setattr(insight_service, "save_insight_run", fake_save)

    with pytest.raises(HTTPException) as exc:
        insight_service.generate_and_save_insights(db=db, current_user=current_user, dataset_id=dataset.id)

    assert exc.value.status_code == 400
    assert captured == [("failed", "Dataset is empty")]


def test_get_latest_insights_returns_latest_success(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    dataset = _dataset()
    run = _run()

    monkeypatch.setattr(insight_service, "_load_owned_dataset", mock_return(dataset))
    db.execute.return_value.unique.return_value.scalars.return_value.first.return_value = run

    response = insight_service.get_latest_insights(db=db, current_user=current_user, dataset_id=dataset.id)

    assert response.run_id == run.id
    assert response.dataset_id == dataset.id
    assert response.status == "success"
    assert response.is_stale is False


def test_get_insight_run_detail_denies_other_user():
    db = MagicMock()
    db.execute.return_value.unique.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(HTTPException) as exc:
        insight_service.get_insight_run_detail(db=db, current_user=SimpleNamespace(id=1), run_id=99)

    assert exc.value.status_code == 404


def test_stale_detection_marks_old_run(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=1)
    snapshot = datetime.now(timezone.utc) - timedelta(hours=2)
    dataset = _dataset(updated_at=datetime.now(timezone.utc))
    run = _run()
    run.dataset_updated_at_snapshot = snapshot
    run.dataset = dataset

    monkeypatch.setattr(insight_service, "_load_owned_dataset", mock_return(dataset))
    db.execute.return_value.unique.return_value.scalars.return_value.first.return_value = run

    response = insight_service.get_latest_insights(db=db, current_user=current_user, dataset_id=dataset.id)

    assert response.is_stale is True


def test_generate_insights_keeps_deterministic_summary_when_openai_polish_fails(monkeypatch):
    dataset = _dataset()
    numeric_column = {
        "display_name": "revenue",
        "sql_name": "revenue",
        "semantic_type": "numeric",
        "distinct_count": 3,
    }

    monkeypatch.setattr(insight_service, "build_dataset_schema_profile", lambda _: [numeric_column])
    monkeypatch.setattr(insight_service, "_pick_preferred_numeric", lambda _: numeric_column)
    monkeypatch.setattr(insight_service, "_pick_preferred_categorical", lambda _: None)
    monkeypatch.setattr(insight_service.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(
        insight_service,
        "_build_distribution_insight",
        lambda db, dataset, numeric: AIInsight(
            type="distribution",
            title="Revenue distribution snapshot",
            summary="Revenue ranges from 10.00 to 100.00, with an average of 55.00.",
            metric="revenue",
            value=55.0,
            columns=["stat", "value"],
            rows=[{"stat": "Average", "value": 55.0}],
        ),
    )
    monkeypatch.setattr(insight_service, "_build_outlier_insight", lambda *args, **kwargs: None)
    monkeypatch.setattr(insight_service, "request_openai_text", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("quota")))

    response = insight_service.generate_insights(db=MagicMock(), dataset=dataset)

    assert response.status == "success"
    assert response.insights[0].summary == "Revenue ranges from 10.00 to 100.00, with an average of 55.00."
    assert response.insights[0].description == response.insights[0].summary
    assert response.insights[0].metric == "revenue"


def test_correlation_insight_returns_scatterable_point_pairs(monkeypatch):
    dataset = _dataset(table_name="wildfire_metrics")
    first = {
        "display_name": "superficie_total",
        "sql_name": "superficie_total",
        "semantic_type": "metric",
        "is_metric": True,
        "usable_for_correlation": True,
        "distinct_count": 10,
    }
    second = {
        "display_name": "superficie_afectada",
        "sql_name": "superficie_afectada",
        "semantic_type": "metric",
        "is_metric": True,
        "usable_for_correlation": True,
        "distinct_count": 10,
    }

    def fake_run_sql(db, sql):
        if "SELECT CORR" in sql:
            return ["correlation"], [{"correlation": 0.62}]
        if "LIMIT 200" in sql:
            return (
                ["superficie_total", "superficie_afectada"],
                [{"superficie_total": float(1000 + index), "superficie_afectada": float(50 + index)} for index in range(10)],
            )
        raise AssertionError(f"Unexpected SQL: {sql}")

    monkeypatch.setattr(insight_service, "_run_sql", fake_run_sql)
    monkeypatch.setattr(
        insight_service,
        "build_visualization_suggestion",
        lambda *args, **kwargs: {"type": "table_only", "reason": "summary table"},
    )

    insight = insight_service._build_correlation_insight(
        db=MagicMock(),
        dataset=dataset,
        first=first,
        second=second,
    )

    assert insight is not None
    assert insight.chart_type == "scatter"
    assert insight.metric == "superficie_afectada"
    assert insight.dimension == "superficie_total"
    assert insight.value == 0.62
    assert insight.sql is not None
    assert "CORR(" in insight.sql
    assert insight.rows == [{"pair": "superficie_total vs superficie_afectada", "correlation": 0.62}]
    assert insight.columns == ["superficie_total", "superficie_afectada"]
    assert len(insight.data) >= 10
    assert set(insight.data[0].keys()) == {"superficie_total", "superficie_afectada"}
    assert "pair" not in insight.data[0]
    assert all(isinstance(row["superficie_total"], float) for row in insight.data)
    assert all(isinstance(row["superficie_afectada"], float) for row in insight.data)


def test_correlation_insight_falls_back_to_table_when_scatter_points_are_insufficient(monkeypatch):
    dataset = _dataset(table_name="wildfire_metrics")
    first = {
        "display_name": "superficie_total",
        "sql_name": "superficie_total",
        "semantic_type": "metric",
        "is_metric": True,
        "usable_for_correlation": True,
        "distinct_count": 4,
    }
    second = {
        "display_name": "superficie_afectada",
        "sql_name": "superficie_afectada",
        "semantic_type": "metric",
        "is_metric": True,
        "usable_for_correlation": True,
        "distinct_count": 4,
    }

    def fake_run_sql(db, sql):
        if "SELECT CORR" in sql:
            return ["correlation"], [{"correlation": 0.71}]
        if "LIMIT 200" in sql:
            return (
                ["superficie_total", "superficie_afectada"],
                [
                    {"superficie_total": 1000.0, "superficie_afectada": 10.0},
                    {"superficie_total": 1100.0, "superficie_afectada": None},
                    {"superficie_total": None, "superficie_afectada": 14.0},
                    {"superficie_total": 1300.0, "superficie_afectada": 16.0},
                ],
            )
        raise AssertionError(f"Unexpected SQL: {sql}")

    monkeypatch.setattr(insight_service, "_run_sql", fake_run_sql)
    monkeypatch.setattr(
        insight_service,
        "build_visualization_suggestion",
        lambda *args, **kwargs: {"type": "table_only", "reason": "summary table"},
    )

    insight = insight_service._build_correlation_insight(
        db=MagicMock(),
        dataset=dataset,
        first=first,
        second=second,
    )

    assert insight is not None
    assert insight.chart_type == "table"
    assert insight.value == 0.71
    assert insight.data == insight.rows
    assert insight.summary == "Correlation detected but insufficient data to visualize."


def test_filter_correlation_columns_excludes_id_foreign_key_and_geographic_columns(monkeypatch):
    dataset = _dataset(table_name="wildfire_metrics")
    id_column = {
        "display_name": "id",
        "sql_name": "id",
        "semantic_type": "identifier",
        "distinct_count": 100,
        "usable_for_correlation": False,
    }
    province_id_column = {
        "display_name": "provincia_id",
        "sql_name": "provincia_id",
        "semantic_type": "identifier",
        "distinct_count": 100,
        "usable_for_correlation": False,
    }
    centroide_lat_column = {
        "display_name": "centroide_lat",
        "sql_name": "centroide_lat",
        "semantic_type": "geographic_lat",
        "distinct_count": 20,
        "usable_for_correlation": False,
    }
    revenue_column = {
        "display_name": "revenue",
        "sql_name": "revenue",
        "semantic_type": "metric",
        "distinct_count": 80,
        "usable_for_correlation": True,
    }

    monkeypatch.setattr(insight_service, "_column_has_low_variance", lambda *args, **kwargs: False)
    valid_columns = insight_service._filter_correlation_columns(
        MagicMock(),
        dataset,
        [id_column, province_id_column, centroide_lat_column, revenue_column],
    )

    assert [column["sql_name"] for column in valid_columns] == ["revenue"]


def test_generate_insights_does_not_generate_correlation_with_identifier_columns(monkeypatch):
    dataset = _dataset()
    captured_pairs: list[tuple[str, str]] = []
    profile = [
        {"display_name": "id", "sql_name": "id", "semantic_type": "identifier", "distinct_count": 100, "is_metric": False, "usable_for_correlation": False},
        {"display_name": "revenue", "sql_name": "revenue", "semantic_type": "metric", "distinct_count": 80, "is_metric": True, "usable_for_correlation": True},
        {"display_name": "profit", "sql_name": "profit", "semantic_type": "metric", "distinct_count": 75, "is_metric": True, "usable_for_correlation": True},
    ]

    monkeypatch.setattr(insight_service, "build_dataset_schema_profile", lambda _: profile)
    monkeypatch.setattr(insight_service, "_pick_preferred_numeric", lambda columns: columns[0] if columns else None)
    monkeypatch.setattr(insight_service, "_pick_preferred_categorical", lambda _: None)
    monkeypatch.setattr(insight_service, "_build_distribution_insight", lambda *args, **kwargs: None)
    monkeypatch.setattr(insight_service, "_build_outlier_insight", lambda *args, **kwargs: None)
    monkeypatch.setattr(insight_service, "_column_has_low_variance", lambda *args, **kwargs: False)

    def fake_build_correlation_insight(db, dataset, first, second):
        captured_pairs.append((str(first["sql_name"]), str(second["sql_name"])))
        return AIInsight(
            type="correlation",
            title="Correlation",
            summary="Valid metric correlation.",
            metric=str(second["display_name"]),
            dimension=str(first["display_name"]),
            quality_score=90,
            columns=["pair", "correlation"],
            rows=[{"pair": "revenue vs profit", "correlation": 0.8}],
        )

    monkeypatch.setattr(insight_service, "_build_correlation_insight", fake_build_correlation_insight)

    response = insight_service.generate_insights(db=MagicMock(), dataset=dataset)

    assert captured_pairs == [("revenue", "profit")]
    assert all(insight.type != "correlation" or insight.dimension != "id" for insight in response.insights)


def test_generate_insights_skips_constant_dimension_insights(monkeypatch):
    dataset = _dataset()
    profile = [
        {"display_name": "fuente", "sql_name": "fuente", "semantic_type": "constant", "distinct_count": 1, "is_metric": False, "usable_for_grouping": False},
        {"display_name": "revenue", "sql_name": "revenue", "semantic_type": "metric", "distinct_count": 50, "is_metric": True, "usable_for_correlation": True},
    ]

    monkeypatch.setattr(insight_service, "build_dataset_schema_profile", lambda _: profile)
    monkeypatch.setattr(insight_service, "_pick_preferred_numeric", lambda columns: columns[0] if columns else None)
    monkeypatch.setattr(insight_service, "_pick_preferred_categorical", lambda _: None)
    monkeypatch.setattr(
        insight_service,
        "_build_distribution_insight",
        lambda db, dataset, numeric: AIInsight(
            type="distribution",
            title="Revenue distribution snapshot",
            summary="Revenue ranges from 10.00 to 100.00, with an average of 55.00.",
            metric="revenue",
            quality_score=90,
            columns=["stat", "value"],
            rows=[{"stat": "Average", "value": 55.0}],
        ),
    )
    monkeypatch.setattr(insight_service, "_build_outlier_insight", lambda *args, **kwargs: None)
    monkeypatch.setattr(insight_service, "_filter_correlation_columns", lambda *args, **kwargs: [])

    response = insight_service.generate_insights(db=MagicMock(), dataset=dataset)

    assert all(insight.dimension != "fuente" for insight in response.insights)
    assert [insight.type for insight in response.insights] == ["distribution"]


def test_generate_insights_returns_real_metric_insight_with_quality_score(monkeypatch):
    dataset = _dataset()
    metric_column = {
        "display_name": "superficie_total",
        "sql_name": "superficie_total",
        "semantic_type": "metric",
        "distinct_count": 90,
        "is_metric": True,
        "usable_for_correlation": True,
    }

    monkeypatch.setattr(insight_service, "build_dataset_schema_profile", lambda _: [metric_column])
    monkeypatch.setattr(insight_service, "_pick_preferred_numeric", lambda _: metric_column)
    monkeypatch.setattr(insight_service, "_pick_preferred_categorical", lambda _: None)
    monkeypatch.setattr(
        insight_service,
        "_build_distribution_insight",
        lambda db, dataset, numeric: AIInsight(
            type="distribution",
            title="Surface distribution snapshot",
            summary="Surface ranges from 10.00 to 100.00, with an average of 55.00.",
            metric="superficie_total",
            quality_score=90,
            columns=["stat", "value"],
            rows=[{"stat": "Average", "value": 55.0}],
        ),
    )
    monkeypatch.setattr(insight_service, "_build_outlier_insight", lambda *args, **kwargs: None)
    monkeypatch.setattr(insight_service, "_filter_correlation_columns", lambda *args, **kwargs: [])

    response = insight_service.generate_insights(db=MagicMock(), dataset=dataset)

    assert response.insights
    assert response.insights[0].metric == "superficie_total"
    assert response.insights[0].quality_score >= 40


def test_generate_insights_filters_low_quality_insights(monkeypatch):
    dataset = _dataset()
    metric_column = {
        "display_name": "revenue",
        "sql_name": "revenue",
        "semantic_type": "metric",
        "distinct_count": 50,
        "is_metric": True,
        "usable_for_correlation": True,
    }

    monkeypatch.setattr(insight_service, "build_dataset_schema_profile", lambda _: [metric_column])
    monkeypatch.setattr(insight_service, "_pick_preferred_numeric", lambda _: metric_column)
    monkeypatch.setattr(insight_service, "_pick_preferred_categorical", lambda _: None)
    monkeypatch.setattr(
        insight_service,
        "_build_distribution_insight",
        lambda db, dataset, numeric: AIInsight(
            type="distribution",
            title="Low quality distribution",
            summary="Low quality.",
            metric="revenue",
            quality_score=20,
            columns=["stat", "value"],
            rows=[{"stat": "Average", "value": 55.0}],
        ),
    )
    monkeypatch.setattr(insight_service, "_build_outlier_insight", lambda *args, **kwargs: None)
    monkeypatch.setattr(insight_service, "_filter_correlation_columns", lambda *args, **kwargs: [])

    response = insight_service.generate_insights(db=MagicMock(), dataset=dataset)

    assert len(response.insights) == 1
    assert response.insights[0].title == "Dataset structure overview"


def test_generate_insights_prioritizes_top_ranked_features(monkeypatch):
    dataset = _dataset()
    low_priority_metric = {
        "display_name": "metric_a",
        "sql_name": "metric_a",
        "semantic_type": "metric",
        "distinct_count": 80,
        "is_metric": True,
        "usable_for_correlation": True,
    }
    high_priority_metric = {
        "display_name": "metric_b",
        "sql_name": "metric_b",
        "semantic_type": "metric",
        "distinct_count": 90,
        "is_metric": True,
        "usable_for_correlation": True,
    }
    category = {
        "display_name": "segment",
        "sql_name": "segment",
        "semantic_type": "categorical",
        "distinct_count": 4,
        "cardinality": "low",
        "usable_for_grouping": True,
    }

    monkeypatch.setattr(insight_service, "build_dataset_schema_profile", lambda _: [low_priority_metric, high_priority_metric, category])
    monkeypatch.setattr(
        insight_service,
        "_prioritize_profile_by_feature_scores",
        lambda dataset, profile: [high_priority_metric, low_priority_metric, category],
    )
    monkeypatch.setattr(insight_service, "_pick_preferred_categorical", lambda columns: category)
    monkeypatch.setattr(insight_service, "_build_trend_insight", lambda *args, **kwargs: None)
    monkeypatch.setattr(insight_service, "_build_distribution_insight", lambda *args, **kwargs: None)
    monkeypatch.setattr(insight_service, "_build_outlier_insight", lambda *args, **kwargs: None)
    monkeypatch.setattr(insight_service, "_filter_correlation_columns", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        insight_service,
        "_build_top_performer_insight",
        lambda db, dataset, categorical, numeric, **kwargs: AIInsight(
            type="top_performer",
            title="Top performer",
            summary=f"{numeric['display_name']} selected.",
            metric=str(numeric["display_name"]),
            dimension=str(categorical["display_name"]),
            quality_score=90,
            columns=["category", "metric"],
            rows=[{"category": "A", "metric": 10}],
        ),
    )
    monkeypatch.setattr(insight_service, "_build_concentration_insight", lambda *args, **kwargs: None)
    monkeypatch.setattr(insight_service, "_build_comparison_insight", lambda *args, **kwargs: None)

    response = insight_service.generate_insights(db=MagicMock(), dataset=dataset)

    assert response.insights
    assert response.insights[0].metric == "metric_b"


def test_generate_insights_falls_back_when_ranking_fails(monkeypatch):
    dataset = _dataset()
    metric_column = {
        "display_name": "revenue",
        "sql_name": "revenue",
        "semantic_type": "metric",
        "distinct_count": 90,
        "is_metric": True,
        "usable_for_correlation": True,
    }

    monkeypatch.setattr(insight_service, "build_dataset_schema_profile", lambda _: [metric_column])
    monkeypatch.setattr(insight_service, "_compute_feature_scores_safe", lambda *args, **kwargs: [])
    monkeypatch.setattr(insight_service, "_prioritize_profile_by_feature_scores", lambda profile, feature_scores: profile)
    monkeypatch.setattr(insight_service, "_pick_preferred_numeric", lambda _: metric_column)
    monkeypatch.setattr(insight_service, "_pick_preferred_categorical", lambda _: None)
    monkeypatch.setattr(
        insight_service,
        "_build_distribution_insight",
        lambda db, dataset, numeric: AIInsight(
            type="distribution",
            title="Revenue distribution snapshot",
            summary="Revenue ranges from 10.00 to 100.00, with an average of 55.00.",
            metric="revenue",
            quality_score=90,
            columns=["stat", "value"],
            rows=[{"stat": "Average", "value": 55.0}],
        ),
    )
    monkeypatch.setattr(insight_service, "_build_outlier_insight", lambda *args, **kwargs: None)
    monkeypatch.setattr(insight_service, "_filter_correlation_columns", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        insight_service,
        "_rank_and_trim_insights",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("ranking failed")),
    )

    response = insight_service.generate_insights(db=MagicMock(), dataset=dataset)

    assert len(response.insights) == 1
    assert response.insights[0].title == "Revenue distribution snapshot"
