from collections.abc import Generator
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from app.api import deps
from app.api.routes import datasets as dataset_routes
from app.main import app


def mock_return(value):
    return lambda *args, **kwargs: value


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    def override_get_db():
        yield SimpleNamespace()

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_current_user] = lambda: SimpleNamespace(id=1, email="owner@example.com")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_generate_dataset_insights_requires_auth(client: TestClient):
    app.dependency_overrides[deps.get_current_user] = lambda: (_ for _ in ()).throw(
        HTTPException(status_code=401, detail="Not authenticated")
    )

    response = client.post("/api/datasets/7/insights/generate")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_generate_dataset_insights_returns_structured_response(monkeypatch, client: TestClient):
    monkeypatch.setattr(
        dataset_routes,
        "generate_and_save_insights",
        mock_return({
            "run_id": 12,
            "dataset_id": 7,
            "dataset_name": "Wildfire",
            "status": "success",
            "generated_at": "2026-04-30T12:00:00+00:00",
            "is_stale": False,
            "error_message": None,
            "insights": [
                {
                    "type": "top_performer",
                    "title": "Bosques leads superficie_afectada",
                    "summary": "Bosques has the highest total superficie_afectada.",
                    "severity": "info",
                    "metric": "superficie_afectada",
                    "dimension": "cobertura",
                    "value": 29266,
                    "sql": "SELECT cobertura, SUM(superficie_afectada) AS metric FROM dataset GROUP BY cobertura",
                    "chart_suggestion": "bar",
                    "columns": ["category", "metric"],
                    "rows": [{"category": "Bosques", "metric": 29266}],
                    "visualization_suggestion": {"type": "bar", "x": "category", "y": "metric"},
                }
            ],
            "narrative": {
                "summary": "El dataset muestra una concentración clara del impacto en bosques.",
                "key_findings": [
                    "Bosques has the highest total superficie_afectada.",
                    "superficie_total and superficie_afectada show a positive correlation of 0.620.",
                ],
                "risks_or_caveats": [
                    "Some columns are constant across the dataset.",
                ],
                "recommended_next_questions": [
                    "How does superficie afectada evolve over time by cobertura?",
                ],
            },
        }),
    )

    response = client.post("/api/datasets/7/insights/generate")

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_id"] == 7
    assert body["insights"][0]["summary"] == "Bosques has the highest total superficie_afectada."
    assert body["insights"][0]["chart_suggestion"] == "bar"
    assert body["insights"][0]["metric"] == "superficie_afectada"
    assert body["narrative"]["summary"] == "El dataset muestra una concentración clara del impacto en bosques."
    assert body["narrative"]["key_findings"]


def test_get_dataset_insights_returns_404_for_non_owned_dataset(monkeypatch, client: TestClient):
    monkeypatch.setattr(
        dataset_routes,
        "get_latest_insights",
        lambda *args, **kwargs: (_ for _ in ()).throw(HTTPException(status_code=404, detail="Dataset not found")),
    )

    response = client.get("/api/datasets/99/insights")

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found"
