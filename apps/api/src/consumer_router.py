"""Consumer-side (分发侧) API endpoints.

These endpoints serve the package registry to end-users: search, detail,
version listing, install manifest, trust scores, and statistics.

All data is sourced from mock JSON files under packages/schema/mock/.
"""

from __future__ import annotations

import math
import re
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, Query, status

from . import data as _data
from .models import (
    InstallManifest,
    PackageDetail,
    PackageStats,
    PackageSummary,
    PaginatedResponse,
    TrustScoreResponse,
    VersionDetail,
    VersionSummary,
)

router = APIRouter(tags=["consumer"])

# ---------------------------------------------------------------------------
# Sort helpers
# ---------------------------------------------------------------------------

_SORT_FIELDS: Dict[str, str] = {
    "trust_score": "trust_score",
    "updated_at": "updated_at",
    "install_count": "install_count",
    "name": "name",
}


def _apply_sort(
    packages: List[Dict[str, Any]], sort: str
) -> List[Dict[str, Any]]:
    """Sort packages in-place (stable) by the given field."""
    key = _SORT_FIELDS.get(sort, "updated_at")
    reverse = True  # default: newest / highest first

    # name is sorted ascending by convention
    if sort == "name":
        reverse = False

    # Treat None as the lowest value for numeric sorts
    def sort_key(pkg: Dict[str, Any]) -> Any:
        val = pkg.get(key)
        if val is None:
            return (0,)  # sort None last when descending
        if isinstance(val, str):
            return val.lower()
        return val

    packages.sort(key=sort_key, reverse=reverse)
    return packages


# ---------------------------------------------------------------------------
# Filter helpers
# ---------------------------------------------------------------------------


def _matches_query(pkg: Dict[str, Any], q: str) -> bool:
    """Check whether package name, description, or keywords contain `q`.

    Matching is case-insensitive.
    """
    q_lower = q.lower()
    if q_lower in pkg.get("name", "").lower():
        return True
    if q_lower in pkg.get("description", "").lower():
        return True
    for kw in pkg.get("keywords", []):
        if q_lower in kw.lower():
            return True
    return False


# ---------------------------------------------------------------------------
# GET /packages
# ---------------------------------------------------------------------------


@router.get("/packages", response_model=PaginatedResponse[PackageSummary])
def list_packages(
    q: Optional[str] = Query(default=None, description="Keyword search across name, description, keywords"),
    type: Optional[str] = Query(default=None, description="Filter by package type (skill, mcp_server, etc.)"),
    status: Optional[str] = Query(default=None, description="Filter by version status"),
    client: Optional[str] = Query(default=None, description="Filter by client compatibility"),
    sort: str = Query(default="updated_at", description="Sort field: trust_score, updated_at, install_count, name"),
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> Dict[str, Any]:
    """List and search published packages.

    Supports keyword search, type/status/client filtering, sorting, and
    pagination.  Only packages visible to consumers are returned.
    """
    # Collect all packages
    items: List[Dict[str, Any]] = _data.get_all_packages()

    # --- Filtering ---
    if q:
        items = [p for p in items if _matches_query(p, q)]

    if type:
        items = [p for p in items if p.get("type") == type]

    if status:
        items = [p for p in items if p.get("status") == status]

    if client:
        # Client filter: check the version compatibility list.
        # Since this is the list-level endpoint we approximate by checking
        # if any known version supports this client.
        items = [p for p in items if _package_supports_client(p, client)]

    # --- Sorting ---
    items = _apply_sort(items, sort)

    # --- Pagination ---
    total = len(items)
    start = (page - 1) * limit
    end = start + limit
    page_items = items[start:end]

    # Convert raw dicts to Pydantic models
    summaries = [_dict_to_summary(p) for p in page_items]

    return {
        "items": summaries,
        "total": total,
        "page": page,
        "limit": limit,
    }


def _dict_to_summary(pkg: Dict[str, Any]) -> PackageSummary:
    """Convert a raw package dict to a PackageSummary model."""
    return PackageSummary(**{k: v for k, v in pkg.items() if k in PackageSummary.__fields__})


def _package_supports_client(pkg: Dict[str, Any], client: str) -> bool:
    """Check whether a package is compatible with the given client.

    We look through available version details for the package; if no
    version files exist at all, we return True (optimistic fallback).
    Otherwise, only return True if at least one version explicitly lists
    the client in its compatibility array.
    """
    versions = _data.get_versions_for_package(pkg["name"])
    if not versions:
        return True

    found_any_detail = False
    for ver in versions:
        detail = _data.get_version_detail(pkg["name"], ver["version"])
        if detail:
            found_any_detail = True
            if client in detail.get("compatibility", []):
                return True

    # If no version detail files existed, be permissive.
    return not found_any_detail


# ---------------------------------------------------------------------------
# GET /packages/{name}
# ---------------------------------------------------------------------------


@router.get("/packages/{name}", response_model=PackageDetail)
def get_package(name: str) -> Dict[str, Any]:
    """Get package detail by its unique name.

    Returns 404 if no package with the given name exists.
    """
    pkg = _data.get_package_by_name(name)
    if pkg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package '{name}' not found",
        )
    return {k: v for k, v in pkg.items() if k in PackageDetail.__fields__}


# ---------------------------------------------------------------------------
# GET /packages/{name}/versions
# ---------------------------------------------------------------------------


@router.get("/packages/{name}/versions", response_model=List[VersionSummary])
def list_versions(name: str) -> List[Dict[str, Any]]:
    """List all versions for a package.

    Returns an empty list if the package does not exist.
    """
    pkg = _data.get_package_by_name(name)
    if pkg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package '{name}' not found",
        )
    return _data.get_versions_for_package(name)


# ---------------------------------------------------------------------------
# GET /packages/{name}/versions/{version}
# ---------------------------------------------------------------------------


@router.get("/packages/{name}/versions/{version}", response_model=VersionDetail)
def get_version(name: str, version: str) -> Dict[str, Any]:
    """Get full detail for a specific version of a package.

    Reads from the dedicated version file if available; otherwise returns
    a synthetic response built from the package summary.
    """
    pkg = _data.get_package_by_name(name)
    if pkg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package '{name}' not found",
        )

    detail = _data.get_version_detail(name, version)
    if detail is None:
        # No version file exists; build a minimal synthetic detail.
        return _build_synthetic_version_detail(pkg, version)

    # Version file exists but the file might not store the package name.
    # Make sure the response includes it correctly.
    detail.setdefault("package_id", pkg.get("id", ""))
    # The version file uses "type_config" for the type-specific config block.
    # Map it if needed (already named type_config in the mock files so it's fine).
    return detail


def _build_synthetic_version_detail(
    pkg: Dict[str, Any], version: str
) -> Dict[str, Any]:
    """Build a minimal VersionDetail when no dedicated version file exists."""
    return {
        "id": f"{pkg.get('id', '')}-{version}",
        "package_id": pkg.get("id", ""),
        "version": version,
        "status": pkg.get("status", "unknown"),
        "created_at": pkg.get("created_at"),
        "submitted_at": pkg.get("created_at"),
        "published_at": pkg.get("updated_at"),
        "compatibility": [],
        "trust_score": {"score": pkg.get("trust_score")} if pkg.get("trust_score") is not None else None,
    }


# ---------------------------------------------------------------------------
# GET /packages/{name}/install
# ---------------------------------------------------------------------------


@router.get("/packages/{name}/install", response_model=InstallManifest)
def get_install_manifest(
    name: str,
    version: Optional[str] = Query(default=None, description="Specific version; defaults to latest"),
) -> Dict[str, Any]:
    """Get the install manifest for a package.

    Returns installation configuration, target paths, dependencies, and
    any pre-install warnings derived from the package's risk level.
    """
    pkg = _data.get_package_by_name(name)
    if pkg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package '{name}' not found",
        )

    resolved_version = version or pkg.get("latest_version", "0.0.0")
    detail = _data.get_version_detail(name, resolved_version)

    # --- Installation info ---
    install = detail.get("installation", {}) if detail else {}

    # --- Pre-install warnings based on risk level ---
    risk_level = pkg.get("risk_level", "unknown")
    pre_install_warnings: List[str] = []
    if risk_level == "high_risk":
        pre_install_warnings.append(
            "This package requests extensive permissions. Review carefully before installing."
        )
    elif risk_level == "medium_risk":
        pre_install_warnings.append(
            "This package requests moderate permissions. Review the trust score before installing."
        )
    if risk_level in ("untrusted", "high_risk"):
        pre_install_warnings.append(
            "This package has been flagged with high-risk findings. Installation is not recommended."
        )

    # --- Trust score summary ---
    trust: Optional[Dict[str, Any]] = None
    if detail and detail.get("trust_score"):
        ts = detail["trust_score"]
        risk_summary = ts.get("risk_summary", {})
        trust = {
            "version_id": detail.get("id", ""),
            "score": ts.get("score"),
            "level": risk_summary.get("level") if isinstance(risk_summary, dict) else None,
            "recommendation": risk_summary.get("install_recommendation") if isinstance(risk_summary, dict) else None,
            "dimensions": None,
            "explanations": None,
            "calculated_at": ts.get("calculated_at"),
        }

    targets_raw = install.get("targets", [])
    return {
        "package_name": name,
        "version": resolved_version,
        "method": install.get("method", "copy_directory"),
        "targets": targets_raw,
        "command": install.get("command"),
        "dependencies": detail.get("dependencies") if detail else None,
        "compatibility": detail.get("compatibility", []) if detail else [],
        "pre_install_warnings": pre_install_warnings,
        "pre_install_message": install.get("pre_install_message"),
        "post_install_message": install.get("post_install_message"),
        "trust_score": trust,
    }


# ---------------------------------------------------------------------------
# GET /trust-scores/{version_id}
# ---------------------------------------------------------------------------


@router.get("/trust-scores/{version_id}", response_model=TrustScoreResponse)
def get_trust_score(version_id: str) -> Dict[str, Any]:
    """Get the trust score for a specific version by version ID.

    Returns mock trust score data if available, or a default structure
    indicating no score has been computed.
    """
    # Search through all version detail files for the version_id
    for (_name, _ver), detail in _data.version_details.items():
        if detail.get("id") == version_id:
            ts = detail.get("trust_score")
            if ts is None:
                return _default_trust_score(version_id)
            risk_summary = ts.get("risk_summary", {})
            return {
                "version_id": version_id,
                "score": ts.get("score", 0),
                "level": risk_summary.get("level") if isinstance(risk_summary, dict) else None,
                "recommendation": risk_summary.get("install_recommendation") if isinstance(risk_summary, dict) else None,
                "dimensions": ts.get("dimensions"),
                "explanations": ts.get("explanations"),
                "calculated_at": ts.get("calculated_at"),
            }

    # No version file found
    return _default_trust_score(version_id)


def _default_trust_score(version_id: str) -> Dict[str, Any]:
    """Return a default trust score structure for versions without computed scores."""
    return {
        "version_id": version_id,
        "score": 0.0,
        "level": "unknown",
        "recommendation": "review_recommended",
        "dimensions": None,
        "explanations": None,
        "calculated_at": None,
    }


# ---------------------------------------------------------------------------
# GET /stats/packages/{name}
# ---------------------------------------------------------------------------


@router.get("/stats/packages/{name}", response_model=PackageStats)
def get_package_stats(name: str) -> Dict[str, Any]:
    """Get install/download statistics for a package."""
    pkg = _data.get_package_by_name(name)
    if pkg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Package '{name}' not found",
        )

    versions = _data.get_versions_for_package(name)
    return {
        "package_name": name,
        "install_count": pkg.get("install_count", 0),
        "avg_rating": pkg.get("avg_rating"),
        "total_versions": len(versions),
        "latest_version": pkg.get("latest_version"),
        "status": pkg.get("status"),
    }
