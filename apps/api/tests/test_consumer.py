"""Basic tests for the consumer-side (分发侧) endpoints.

Uses FastAPI TestClient so no live server is required.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.consumer_router import router as consumer_router

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient wired to the consumer router."""
    app = FastAPI()
    app.include_router(consumer_router, prefix="/api/v0")
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /packages
# ---------------------------------------------------------------------------


def test_list_packages_returns_list(client: TestClient) -> None:
    """GET /packages should return a paginated list of packages."""
    resp = client.get("/api/v0/packages")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "page" in body
    assert "limit" in body
    assert isinstance(body["items"], list)
    assert body["total"] >= 1


def test_list_packages_with_type_filter(client: TestClient) -> None:
    """GET /packages?type=skill should only return skill packages."""
    resp = client.get("/api/v0/packages", params={"type": "skill"})
    assert resp.status_code == 200
    body = resp.json()
    for item in body["items"]:
        assert item["type"] == "skill"


def test_list_packages_with_search_query(client: TestClient) -> None:
    """GET /packages?q=code should return matching packages."""
    resp = client.get("/api/v0/packages", params={"q": "code"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    # At least "code-review-skill" should match
    names = [item["name"] for item in body["items"]]
    assert "code-review-skill" in names or any("code" in n or "code" in body["items"][0]["description"].lower() for n in names)


def test_list_packages_with_status_filter(client: TestClient) -> None:
    """GET /packages?status=published should only return published packages."""
    resp = client.get("/api/v0/packages", params={"status": "published"})
    assert resp.status_code == 200
    body = resp.json()
    for item in body["items"]:
        assert item["status"] == "published"


def test_list_packages_pagination(client: TestClient) -> None:
    """GET /packages with page and limit should respect pagination params."""
    resp = client.get("/api/v0/packages", params={"page": 1, "limit": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["limit"] == 2
    assert len(body["items"]) <= 2


def test_list_packages_sort_by_name(client: TestClient) -> None:
    """GET /packages?sort=name should return results sorted by name."""
    resp = client.get("/api/v0/packages", params={"sort": "name"})
    assert resp.status_code == 200
    body = resp.json()
    names = [item["name"] for item in body["items"]]
    assert names == sorted(names)


# ---------------------------------------------------------------------------
# GET /packages/{name}
# ---------------------------------------------------------------------------


def test_get_package_detail(client: TestClient) -> None:
    """GET /packages/code-review-skill should return a full detail object."""
    resp = client.get("/api/v0/packages/code-review-skill")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "code-review-skill"
    assert body["id"] == "pkg-001"
    assert body["type"] == "skill"
    assert body["description"]
    assert body["latest_version"]


def test_get_package_404_for_unknown(client: TestClient) -> None:
    """GET /packages/nonexistent-pkg should return 404."""
    resp = client.get("/api/v0/packages/nonexistent-pkg-zzz")
    assert resp.status_code == 404
    body = resp.json()
    assert "detail" in body


# ---------------------------------------------------------------------------
# GET /packages/{name}/versions
# ---------------------------------------------------------------------------


def test_list_versions_returns_list(client: TestClient) -> None:
    """GET /packages/code-review-skill/versions should return versions."""
    resp = client.get("/api/v0/packages/code-review-skill/versions")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    # First entry should have version info
    assert "version" in body[0]
    assert body[0]["version"] == "1.0.0"


def test_list_versions_404_for_unknown_package(client: TestClient) -> None:
    """GET /packages/unknown-pkg/versions should return 404."""
    resp = client.get("/api/v0/packages/nonexistent-pkg-zzz/versions")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /packages/{name}/versions/{version}
# ---------------------------------------------------------------------------


def test_get_version_detail(client: TestClient) -> None:
    """GET /packages/code-review-skill/versions/1.0.0 should return full detail."""
    resp = client.get("/api/v0/packages/code-review-skill/versions/1.0.0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == "1.0.0"
    assert "compatibility" in body
    assert "trust_score" in body


def test_get_version_synthetic_for_missing_file(client: TestClient) -> None:
    """GET a version without a dedicated file should still return data."""
    resp = client.get("/api/v0/packages/postgres-explorer/versions/2.1.0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == "2.1.0"


# ---------------------------------------------------------------------------
# GET /packages/{name}/install
# ---------------------------------------------------------------------------


def test_get_install_manifest(client: TestClient) -> None:
    """GET /packages/code-review-skill/install should return install config."""
    resp = client.get("/api/v0/packages/code-review-skill/install")
    assert resp.status_code == 200
    body = resp.json()
    assert body["package_name"] == "code-review-skill"
    assert body["method"]
    assert "targets" in body
    assert "pre_install_warnings" in body


def test_get_install_manifest_404_for_unknown(client: TestClient) -> None:
    """GET /packages/unknown/install should return 404."""
    resp = client.get("/api/v0/packages/nonexistent-pkg-zzz/install")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /trust-scores/{version_id}
# ---------------------------------------------------------------------------


def test_get_trust_score(client: TestClient) -> None:
    """GET /trust-scores/ver-001 should return a trust score."""
    resp = client.get("/api/v0/trust-scores/ver-001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version_id"] == "ver-001"
    assert body["score"] == 92
    assert body["level"] == "trusted"
    assert body["recommendation"] == "safe"


def test_get_trust_score_default_for_unknown(client: TestClient) -> None:
    """GET /trust-scores/unknown-id should return a default structure."""
    resp = client.get("/api/v0/trust-scores/nonexistent-version-id")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version_id"] == "nonexistent-version-id"
    assert body["score"] == 0.0
    assert body["level"] == "unknown"


# ---------------------------------------------------------------------------
# GET /stats/packages/{name}
# ---------------------------------------------------------------------------


def test_get_package_stats(client: TestClient) -> None:
    """GET /stats/packages/code-review-skill should return stats."""
    resp = client.get("/api/v0/stats/packages/code-review-skill")
    assert resp.status_code == 200
    body = resp.json()
    assert body["package_name"] == "code-review-skill"
    assert body["install_count"] == 1280
    assert body["avg_rating"] == 4.7
    assert body["latest_version"] == "1.0.0"


def test_get_package_stats_404_for_unknown(client: TestClient) -> None:
    """GET /stats/packages/unknown-pkg should return 404."""
    resp = client.get("/api/v0/stats/packages/nonexistent-pkg-zzz")
    assert resp.status_code == 404
