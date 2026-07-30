from app.core.config import Settings


def test_database_url_is_normalized_for_psycopg2() -> None:
    settings = Settings(
        secret_key="test-secret",
        database_url="postgresql://app:encoded%2Fpassword@pooler.example/db?sslmode=require",
    )

    assert settings.sqlalchemy_database_uri == (
        "postgresql+psycopg2://app:encoded%2Fpassword@pooler.example/db?sslmode=require"
    )


def test_alembic_prefers_direct_database_url() -> None:
    settings = Settings(
        secret_key="test-secret",
        database_url="postgresql://app:password@pooler.example/db?sslmode=require",
        database_direct_url="postgresql://app:password@direct.example/db?sslmode=require",
    )

    assert settings.sqlalchemy_database_uri == (
        "postgresql+psycopg2://app:password@pooler.example/db?sslmode=require"
    )
    assert settings.sqlalchemy_migration_uri == (
        "postgresql+psycopg2://app:password@direct.example/db?sslmode=require"
    )


def test_alembic_falls_back_to_application_database_url() -> None:
    settings = Settings(
        secret_key="test-secret",
        database_url="postgresql://app:password@database.example/db",
        database_direct_url=None,
    )

    assert settings.sqlalchemy_migration_uri == settings.sqlalchemy_database_uri
