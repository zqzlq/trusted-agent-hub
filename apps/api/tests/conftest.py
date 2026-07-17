"""Test fixtures: SQLite in-memory database seeded from mock JSON."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from src.database import create_engine_from_url, create_session_factory
from src.dependencies import get_package_repository, get_settings
from src.main import create_app
from src.repositories.mock import JsonPackageRepository
from src.repositories.orm import Base
from src.repositories.sqlalchemy import (
    SqlAlchemyPackageRepository,
    seed_sqlalchemy_repository,
)
from src.settings import Settings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MOCK = ROOT / "packages" / "schema" / "mock"


@pytest.fixture
def repository() -> SqlAlchemyPackageRepository:
    """Return a SQLite in-memory repository seeded with mock data."""
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    repo = SqlAlchemyPackageRepository(create_session_factory(engine))

    # Seed from mock JSON
    source = JsonPackageRepository(
        MOCK / "packages.json", MOCK / "versions"
    )
    seed_sqlalchemy_repository(repo, source)
    return repo


@pytest.fixture
def client(repository: SqlAlchemyPackageRepository) -> Iterator[TestClient]:
    """Return a TestClient with the seeded repository overridden."""
    app = create_app()
    app.dependency_overrides[get_package_repository] = lambda: repository
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url="sqlite:///:memory:"
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
