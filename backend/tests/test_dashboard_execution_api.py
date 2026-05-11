from collections.abc import Generator
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from app.api import deps
from app.api.routes import dashboards as dashboard_routes
from app.api.routes import public as public_routes
from app.main import app


def mock_return(value):
    return lambda *args, **kwargs: value


def _widget() -> dict[str, object]:
    return {
        "id": 7,
        "dashboard_id": 3,
        "type": "chart",
        "widget_type": "chart",
        "source_type": "query",
        "source_id": 9,
        "execution_type": "query",
        "execution_status": "success",
        "chart_type": "bar",
        "query_sql": "select * from dataset",
        "layout": {"column_span": 1, "order": 0, "use_snapshot": False, "x": 0, "y": 0, "width": 6, "height": 4},
        "title": "Revenue",
        "config_json": {"x": "month", "y": "revenue"},
        "data_json": [{"month": "Jan", "revenue": 10}],
        "last_run_at": "2026-04-30T13:15:00+00:00",
        "error_message": None,
        "insight_index": None,
        "has_snapshot": False,
        "using_snapshot": False,
        "snapshot_created_at": None,
        "source_changed": False,
        "created_at": "2026-04-30T13:00:00+00:00",
        "source": {"query": None, "insight": None},
    }


def _dashboard_detail() -> dict[str, object]:
    return {
        "id": 3,
        "name": "Ops",
        "dataset_id": 12,
        "auto_refresh_enabled": True,
        "refresh_interval_minutes": 60,
        "last_successful_refresh_at": "2026-04-30T13:15:00+00:00",
        "next_refresh_at": "2026-04-30T14:15:00+00:00",
        "freshness_status": "fresh",
        "created_at": "2026-04-30T13:00:00+00:00",
        "updated_at": "2026-04-30T13:15:00+00:00",
        "widgets": [_widget()],
    }


def _share_link() -> dict[str, object]:
    return {
        "id": 5,
        "dashboard_id": 3,
        "expires_at": None,
        "revoked_at": None,
        "created_at": "2026-04-30T13:00:00+00:00",
        "share_url": "/public/dashboards/5.signature",
    }


def _shared_dashboard() -> dict[str, object]:
    return {
        "id": 3,
        "name": "Ops",
        "freshness_status": "fresh",
        "last_successful_refresh_at": "2026-04-30T13:15:00+00:00",
        "next_refresh_at": "2026-04-30T14:15:00+00:00",
        "narrative": {
            "summary": "The dashboard Ops contains 1 widgets.",
            "key_findings": ["Revenue is visible."],
            "risks_or_caveats": [],
            "recommended_next_actions": ["Review the shared dashboard regularly."],
            "stale_or_failed_widgets": [],
        },
        "widgets": [
            {
                "id": 7,
                "dashboard_id": 3,
                "type": "chart",
                "widget_type": "chart",
                "source_type": "query",
                "execution_type": "query",
                "execution_status": "success",
                "chart_type": "bar",
                "layout": {"column_span": 1, "order": 0, "use_snapshot": False, "x": 0, "y": 0, "width": 6, "height": 4},
                "title": "Revenue",
                "config_json": {"x": "month", "y": "revenue"},
                "data_json": [{"month": "Jan", "revenue": 10}],
                "last_run_at": "2026-04-30T13:15:00+00:00",
                "error_message": None,
                "created_at": "2026-04-30T13:00:00+00:00",
            }
        ],
    }


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    def override_get_db():
        yield SimpleNamespace()

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_current_user] = lambda: SimpleNamespace(id=1, email="owner@example.com")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_refresh_dashboard_endpoint_returns_dashboard(monkeypatch, client: TestClient):
    monkeypatch.setattr(
        dashboard_routes,
        "refresh_dashboard",
        mock_return(_dashboard_detail()),
    )

    response = client.post("/api/dashboards/3/refresh")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 3
    assert body["widgets"][0]["execution_type"] == "query"
    assert body["widgets"][0]["execution_status"] == "success"
    assert body["widgets"][0]["last_run_at"] == "2026-04-30T13:15:00+00:00"


def test_refresh_dashboard_widget_endpoint_returns_widget(monkeypatch, client: TestClient):
    monkeypatch.setattr(
        dashboard_routes,
        "refresh_dashboard_widget_read",
        mock_return(_widget()),
    )

    response = client.post("/api/dashboards/3/widgets/7/refresh")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 7
    assert body["execution_status"] == "success"
    assert body["last_run_at"] == "2026-04-30T13:15:00+00:00"


def test_get_dashboard_narrative_endpoint_returns_narrative(monkeypatch, client: TestClient):
    monkeypatch.setattr(
        dashboard_routes,
        "get_dashboard_narrative",
        mock_return(
            {
                "summary": "The dashboard Ops contains 1 widgets.",
                "key_findings": ["Revenue by month is active as a bar query widget with 1 row of current data."],
                "risks_or_caveats": [],
                "recommended_next_actions": ["Refresh the dashboard regularly and review the highest-signal widgets first."],
                "stale_or_failed_widgets": [],
            }
        ),
    )

    response = client.get("/api/dashboards/3/narrative")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == "The dashboard Ops contains 1 widgets."
    assert body["key_findings"]


def test_refresh_settings_endpoint_returns_dashboard(monkeypatch, client: TestClient):
    monkeypatch.setattr(
        dashboard_routes,
        "update_dashboard_refresh_settings",
        mock_return(_dashboard_detail()),
    )

    response = client.patch(
        "/api/dashboards/3/refresh-settings",
        json={"auto_refresh_enabled": True, "refresh_interval_minutes": 60},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["auto_refresh_enabled"] is True
    assert body["refresh_interval_minutes"] == 60
    assert body["freshness_status"] == "fresh"


def test_create_share_link_endpoint_returns_plain_token_once(monkeypatch, client: TestClient):
    monkeypatch.setattr(
        dashboard_routes,
        "create_dashboard_share_link",
        mock_return({**_share_link(), "token": "5.signature"}),
    )

    response = client.post("/api/dashboards/3/share-links", json={})

    assert response.status_code == 201
    body = response.json()
    assert body["token"] == "5.signature"
    assert body["share_url"].endswith(body["token"])


def test_list_share_links_endpoint_returns_metadata_only(monkeypatch, client: TestClient):
    monkeypatch.setattr(
        dashboard_routes,
        "list_dashboard_share_links",
        mock_return([_share_link()]),
    )

    response = client.get("/api/dashboards/3/share-links")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == 5
    assert "token" not in body[0]


def test_public_dashboard_endpoint_returns_read_only_dashboard(monkeypatch, client: TestClient):
    monkeypatch.setattr(
        public_routes,
        "get_shared_dashboard_by_token",
        mock_return(_shared_dashboard()),
    )

    response = client.get("/api/public/dashboards/5.signature")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 3
    assert body["narrative"]["summary"]
    assert "query_sql" not in body["widgets"][0]
