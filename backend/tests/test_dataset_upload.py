from collections.abc import Generator
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.db.base_class import Base
from app.db.session import get_db
from app.main import app
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.user import User
from app.services import dataset_service
from app.core.config import settings


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        class_=Session,
    )
    Base.metadata.create_all(bind=engine, tables=[User.__table__, Dataset.__table__, DatasetColumn.__table__])

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_current_user() -> SimpleNamespace:
        return SimpleNamespace(id=1, email="owner@example.com")

    with TestingSessionLocal() as db:
        db.add(
            User(
                id=1,
                email="owner@example.com",
                full_name="Owner",
                hashed_password="hashed",
                is_active=True,
            )
        )
        db.commit()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine, tables=[DatasetColumn.__table__, Dataset.__table__, User.__table__])
    engine.dispose()


def test_upload_dataset_accepts_valid_comma_csv(client: TestClient):
    response = client.post(
        "/api/datasets/upload",
        data={"name": "Sales", "description": "comma"},
        files={"file": ("sales.csv", b"name,amount\nAlice,10\nBob,20\n", "text/csv")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Sales"
    assert body["row_count"] == 2
    assert body["column_count"] == 2
    assert [column["name"] for column in body["columns"]] == ["name", "amount"]


def test_upload_dataset_accepts_valid_semicolon_csv(client: TestClient):
    response = client.post(
        "/api/datasets/upload",
        data={"name": "Sales", "description": "semicolon"},
        files={"file": ("sales.csv", b"name;amount\nAlice;10\nBob;20\n", "text/csv")},
    )

    assert response.status_code == 201
    assert response.json()["row_count"] == 2


def test_upload_dataset_accepts_utf8_bom_csv(client: TestClient):
    response = client.post(
        "/api/datasets/upload",
        data={"name": "Sales", "description": "bom"},
        files={"file": ("sales.csv", b"\xef\xbb\xbfname,amount\nAlice,10\n", "text/csv")},
    )

    assert response.status_code == 201
    assert response.json()["columns"][0]["name"] == "name"


def test_upload_dataset_rejects_missing_data_row(client: TestClient):
    response = client.post(
        "/api/datasets/upload",
        data={"name": "Sales", "description": "header only"},
        files={"file": ("sales.csv", b"name,amount\n", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The CSV file must include at least one data row"


def test_upload_dataset_rejects_invalid_csv_with_clear_message(client: TestClient):
    response = client.post(
        "/api/datasets/upload",
        data={"name": "Sales", "description": "invalid"},
        files={"file": ("sales.csv", b"not,a,csv\n\"unterminated\n", "text/csv")},
    )

    assert response.status_code == 400
    assert "not a valid CSV" in response.json()["detail"]


def test_upload_dataset_requires_file(client: TestClient):
    response = client.post(
        "/api/datasets/upload",
        data={"name": "Sales", "description": "missing file"},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_upload_dataset_requires_name(client: TestClient):
    response = client.post(
        "/api/datasets/upload",
        data={"description": "missing name"},
        files={"file": ("sales.csv", b"name,amount\nAlice,10\n", "text/csv")},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "name"]


def test_upload_uses_content_validation_not_filename_and_never_writes_csv(client: TestClient, tmp_path):
    response = client.post(
        "/api/datasets/upload",
        data={"name": "Sales"},
        files={"file": ("../../sensitive-not-a-path.bin", b"name,amount\nAlice,10\n", "application/octet-stream")},
    )
    assert response.status_code == 201
    assert not list(tmp_path.iterdir())


def test_upload_rejects_too_many_rows(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "max_dataset_rows", 1)
    response = client.post(
        "/api/datasets/upload",
        data={"name": "Sales"},
        files={"file": ("sales.csv", b"name\nAlice\nBob\n", "text/csv")},
    )
    assert response.status_code == 413
    assert "row limit" in response.json()["detail"]


def test_upload_rejects_too_many_columns(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "max_dataset_columns", 1)
    response = client.post(
        "/api/datasets/upload",
        data={"name": "Sales"},
        files={"file": ("sales.csv", b"name,amount\nAlice,10\n", "text/csv")},
    )
    assert response.status_code == 413
    assert "column limit" in response.json()["detail"]


def test_upload_rejects_too_large_before_parsing(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 10)
    response = client.post(
        "/api/datasets/upload",
        data={"name": "Sales"},
        files={"file": ("sales.csv", b"name,amount\nAlice,10\n", "text/csv")},
    )
    assert response.status_code == 413
    assert "byte limit" in response.json()["detail"]


def test_upload_database_failure_rolls_back_metadata_and_dynamic_table(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    original_materialize = dataset_service.materialize_dataset_table

    def fail_after_table(*args, **kwargs):
        original_materialize(*args, **kwargs)
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(dataset_service, "materialize_dataset_table", fail_after_table)
    response = client.post(
        "/api/datasets/upload",
        data={"name": "Sales"},
        files={"file": ("sales.csv", b"name,amount\nAlice,10\n", "text/csv")},
    )
    assert response.status_code == 500
