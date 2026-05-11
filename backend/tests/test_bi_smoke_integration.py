from __future__ import annotations

import time
from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect, text

from app.api.routes import ai as ai_routes
from app.core.config import settings
from app.db.base import Base
from app.schemas.ai import AIQueryResponse, AIVisualizationSuggestion, SQLAnalysisResult
from app.main import app


TEST_TABLES = [
    "users",
    "datasets",
    "dataset_columns",
    "dataset_insight_runs",
    "query_history",
    "query_results",
    "dashboards",
    "dashboard_share_links",
    "dashboard_widgets",
]


def _wait_for_postgres() -> None:
    engine = create_engine(settings.sqlalchemy_database_uri, future=True, pool_pre_ping=True)
    try:
        for _ in range(30):
            try:
                with engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                return
            except Exception:
                time.sleep(1)
        raise RuntimeError("PostgreSQL is not ready for backend integration tests")
    finally:
        engine.dispose()


def _run_migrations() -> None:
    alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    config = Config(str(alembic_ini))
    command.upgrade(config, "head")


def _truncate_database() -> None:
    table_names = [f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables)]
    if not table_names:
        return
    engine = create_engine(settings.sqlalchemy_database_uri, future=True, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            connection.execute(text(f"TRUNCATE TABLE {', '.join(table_names)} RESTART IDENTITY CASCADE"))
    finally:
        engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def postgres_schema_ready() -> None:
    _wait_for_postgres()
    _run_migrations()


@pytest.fixture(autouse=True)
def isolated_backend_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[None, None, None]:
    storage_dir = tmp_path / "datasets"
    storage_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "storage_path", str(storage_dir))
    monkeypatch.setattr(settings, "openai_api_key", None)

    _truncate_database()
    yield
    _truncate_database()


@pytest.fixture()
def client(postgres_schema_ready) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def user(client: TestClient) -> dict[str, str]:
    payload = {
        "email": "smoke@example.com",
        "full_name": "Smoke Tester",
        "password": "smoke-pass-123",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return payload


@pytest.fixture()
def auth_headers(client: TestClient, user: dict[str, str]) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def dataset(client: TestClient, auth_headers: dict[str, str]) -> dict[str, object]:
    csv_content = (
        b"category,revenue,cost,event_date\n"
        b"Bosques,100,50,2026-04-01\n"
        b"Pastizales,80,38,2026-04-02\n"
        b"Bosques,120,58,2026-04-03\n"
        b"Turberas,40,14,2026-04-04\n"
        b"Pastizales,95,44,2026-04-05\n"
        b"Bosques,130,63,2026-04-06\n"
    )
    response = client.post(
        "/api/datasets/upload",
        headers=auth_headers,
        data={"name": "Wildfire BI", "description": "smoke test dataset"},
        files={"file": ("wildfire.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def mock_ai_query(monkeypatch: pytest.MonkeyPatch):
    async def fake_query_dataset_with_sql_ai(*, db, current_user, dataset_id: int, question: str):
        sql = (
            f'SELECT "category" AS category, '
            f'SUM(CAST("revenue" AS DOUBLE PRECISION)) AS metric '
            f'FROM "dataset_{dataset_id}" '
            f'GROUP BY "category" '
            f'ORDER BY metric DESC'
        )
        return AIQueryResponse(
            answer=f"Mocked answer for: {question}",
            sql=sql,
            rows=[
                {"category": "Bosques", "metric": 350.0},
                {"category": "Pastizales", "metric": 175.0},
                {"category": "Turberas", "metric": 40.0},
            ],
            columns=["category", "metric"],
            chart_suggestion="bar",
            visualization_suggestion=AIVisualizationSuggestion(
                type="bar",
                x="category",
                y="metric",
                reason="Detected an aggregated categorical result with a numeric metric.",
            ),
            sql_analysis=SQLAnalysisResult(
                is_aggregated=True,
                aggregation_functions=["SUM"],
                group_by_columns=["category"],
                selected_columns=["category", "metric"],
                has_group_by=True,
                has_order_by=True,
                has_limit=False,
            ),
        )

    monkeypatch.setattr(ai_routes, "query_dataset_with_sql_ai", fake_query_dataset_with_sql_ai)


@pytest.fixture()
def dashboard(client: TestClient, auth_headers: dict[str, str], dataset: dict[str, object]) -> dict[str, object]:
    response = client.post(
        "/api/dashboards",
        headers=auth_headers,
        json={"name": "Operations overview", "dataset_id": dataset["id"]},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def second_user_headers(client: TestClient) -> dict[str, str]:
    payload = {
        "email": "other@example.com",
        "full_name": "Other User",
        "password": "other-pass-123",
    }
    register_response = client.post("/api/auth/register", json=payload)
    assert register_response.status_code == 201, register_response.text
    login_response = client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_backend_migrations_apply_to_postgres(postgres_schema_ready):
    engine = create_engine(settings.sqlalchemy_database_uri, future=True, pool_pre_ping=True)
    try:
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())
    finally:
        engine.dispose()

    for table_name in TEST_TABLES:
        assert table_name in table_names


def test_bi_smoke_flow_end_to_end(
    client: TestClient,
    auth_headers: dict[str, str],
    dataset: dict[str, object],
    dashboard: dict[str, object],
    mock_ai_query,
):
    query_response = client.post(
        "/api/ai/query",
        headers=auth_headers,
        json={"dataset_id": dataset["id"], "question": "Show revenue by category"},
    )
    assert query_response.status_code == 200, query_response.text
    query_payload = query_response.json()
    assert query_payload["query_id"] is not None
    assert query_payload["sql"]
    assert query_payload["rows"]

    insights_response = client.post(
        f"/api/datasets/{dataset['id']}/insights/generate",
        headers=auth_headers,
    )
    assert insights_response.status_code == 200, insights_response.text
    insights_payload = insights_response.json()
    assert insights_payload["run_id"] is not None
    assert insights_payload["insights"]
    assert insights_payload["narrative"]["summary"]

    query_widget_response = client.post(
        f"/api/dashboards/{dashboard['id']}/widgets",
        headers=auth_headers,
        json={
            "widget_type": "chart",
            "source_type": "query",
            "source_id": query_payload["query_id"],
            "execution_type": "query",
            "chart_type": query_payload["chart_suggestion"] or "bar",
            "query_sql": query_payload["sql"],
            "title": "Revenue by category",
            "config_json": query_payload["visualization_suggestion"],
            "data_json": query_payload["rows"],
            "layout": {"x": 0, "y": 0, "width": 12, "height": 4, "column_span": 1, "order": 0, "use_snapshot": False},
        },
    )
    assert query_widget_response.status_code == 201, query_widget_response.text
    query_widget_dashboard = query_widget_response.json()
    assert len(query_widget_dashboard["widgets"]) == 1
    query_widget_id = query_widget_dashboard["widgets"][0]["id"]

    first_insight = insights_payload["insights"][0]
    insight_widget_response = client.post(
        f"/api/dashboards/{dashboard['id']}/widgets",
        headers=auth_headers,
        json={
            "widget_type": "chart" if first_insight["chart_type"] != "table" else "insight",
            "source_type": "insight",
            "source_id": insights_payload["run_id"],
            "execution_type": "insight",
            "chart_type": first_insight["chart_type"],
            "title": first_insight["title"],
            "config_json": first_insight["visualization_suggestion"],
            "data_json": first_insight["rows"] or first_insight["data"],
            "insight_index": 0,
            "layout": {"x": 12, "y": 0, "width": 12, "height": 4, "column_span": 1, "order": 1, "use_snapshot": False},
        },
    )
    assert insight_widget_response.status_code == 201, insight_widget_response.text
    dashboard_with_widgets = insight_widget_response.json()
    assert len(dashboard_with_widgets["widgets"]) == 2

    refresh_dashboard_response = client.post(
        f"/api/dashboards/{dashboard['id']}/refresh",
        headers=auth_headers,
    )
    assert refresh_dashboard_response.status_code == 200, refresh_dashboard_response.text
    refreshed_dashboard = refresh_dashboard_response.json()
    assert len(refreshed_dashboard["widgets"]) == 2
    assert all(widget["execution_status"] == "success" for widget in refreshed_dashboard["widgets"])
    assert all(widget["last_run_at"] for widget in refreshed_dashboard["widgets"])

    refresh_widget_response = client.post(
        f"/api/dashboards/{dashboard['id']}/widgets/{query_widget_id}/refresh",
        headers=auth_headers,
    )
    assert refresh_widget_response.status_code == 200, refresh_widget_response.text
    refreshed_widget = refresh_widget_response.json()
    assert refreshed_widget["execution_status"] == "success"
    assert refreshed_widget["last_run_at"] is not None
    assert refreshed_widget["data_json"]

    narrative_response = client.get(
        f"/api/dashboards/{dashboard['id']}/narrative",
        headers=auth_headers,
    )
    assert narrative_response.status_code == 200, narrative_response.text
    narrative = narrative_response.json()
    assert narrative["summary"]
    assert narrative["key_findings"]
    assert narrative["recommended_next_actions"]


def test_dashboard_share_links_are_hashed_and_publicly_read_only(
    client: TestClient,
    auth_headers: dict[str, str],
    dashboard: dict[str, object],
):
    share_response = client.post(
        f"/api/dashboards/{dashboard['id']}/share-links",
        headers=auth_headers,
        json={},
    )
    assert share_response.status_code == 201, share_response.text
    share_payload = share_response.json()
    assert share_payload["token"]
    assert "." in share_payload["token"]
    assert share_payload["share_url"].endswith(share_payload["token"])

    list_response = client.get(f"/api/dashboards/{dashboard['id']}/share-links", headers=auth_headers)
    assert list_response.status_code == 200, list_response.text
    listed = list_response.json()
    assert len(listed) == 1
    assert "token" not in listed[0]

    public_response = client.get(f"/api/public/dashboards/{share_payload['token']}")
    assert public_response.status_code == 200, public_response.text
    public_payload = public_response.json()
    assert public_payload["id"] == dashboard["id"]
    assert "dataset_id" not in public_payload
    assert "user_id" not in public_payload
    if public_payload["widgets"]:
        assert "query_sql" not in public_payload["widgets"][0]
        assert "source" not in public_payload["widgets"][0]


def test_dashboard_share_link_revoked_and_expired_fail(
    client: TestClient,
    auth_headers: dict[str, str],
    dashboard: dict[str, object],
):
    expired_response = client.post(
        f"/api/dashboards/{dashboard['id']}/share-links",
        headers=auth_headers,
        json={"expires_at": "2020-01-01T00:00:00+00:00"},
    )
    assert expired_response.status_code == 201, expired_response.text
    expired_token = expired_response.json()["token"]

    public_expired = client.get(f"/api/public/dashboards/{expired_token}")
    assert public_expired.status_code == 404

    active_response = client.post(
        f"/api/dashboards/{dashboard['id']}/share-links",
        headers=auth_headers,
        json={},
    )
    assert active_response.status_code == 201, active_response.text
    active_share = active_response.json()

    revoke_response = client.delete(
        f"/api/dashboards/{dashboard['id']}/share-links/{active_share['id']}",
        headers=auth_headers,
    )
    assert revoke_response.status_code == 204, revoke_response.text

    public_revoked = client.get(f"/api/public/dashboards/{active_share['token']}")
    assert public_revoked.status_code == 404


def test_other_user_cannot_manage_dashboard_share_links(
    client: TestClient,
    auth_headers: dict[str, str],
    second_user_headers: dict[str, str],
    dashboard: dict[str, object],
):
    create_response = client.post(
        f"/api/dashboards/{dashboard['id']}/share-links",
        headers=auth_headers,
        json={},
    )
    assert create_response.status_code == 201, create_response.text
    share_id = create_response.json()["id"]

    list_response = client.get(f"/api/dashboards/{dashboard['id']}/share-links", headers=second_user_headers)
    assert list_response.status_code == 404

    revoke_response = client.delete(
        f"/api/dashboards/{dashboard['id']}/share-links/{share_id}",
        headers=second_user_headers,
    )
    assert revoke_response.status_code == 404
