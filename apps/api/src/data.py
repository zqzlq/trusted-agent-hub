"""Data loader that reads mock JSON files and indexes them for fast lookup.

All data is loaded at module-import time into in-memory dicts so that
endpoint handlers can perform O(1) lookups by package name.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Resolve the path to the mock data directory relative to this file.
#   apps/api/src/data.py  -->  ../../../packages/schema/mock/
# ---------------------------------------------------------------------------
_API_SRC_DIR = Path(__file__).resolve().parent  # apps/api/src/
_API_DIR = _API_SRC_DIR.parent  # apps/api/
_PROJECT_ROOT = _API_DIR.parent.parent  # repo root
_MOCK_DIR = _PROJECT_ROOT / "packages" / "schema" / "mock"
_VERSIONS_DIR = _MOCK_DIR / "versions"


def _load_json(path: Path) -> dict[str, Any] | list[Any]:
    """Load a JSON file, returning parsed Python objects."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Module-level caches
# ---------------------------------------------------------------------------

#: Full contents of packages.json (list of raw dicts, kept for iteration).
_packages_list: list[dict[str, Any]] = _load_json(_MOCK_DIR / "packages.json")  # type: ignore[assignment]

#: Package dicts indexed by name for O(1) lookup.
packages_by_name: dict[str, dict[str, Any]] = {
    pkg["name"]: pkg for pkg in _packages_list  # type: ignore[index]
}

#: Package dicts indexed by id for O(1) lookup.
packages_by_id: dict[str, dict[str, Any]] = {
    pkg["id"]: pkg for pkg in _packages_list  # type: ignore[index]
}


def _load_version_files() -> dict[tuple[str, str], dict[str, Any]]:
    """Scan the versions/ directory and load every version detail file.

    Returns a dict keyed by (package_name, version_string).
    """
    cache: dict[tuple[str, str], dict[str, Any]] = {}
    if not _VERSIONS_DIR.is_dir():
        return cache

    for file_path in sorted(_VERSIONS_DIR.glob("*.json")):
        try:
            data = _load_json(file_path)
            if isinstance(data, dict):
                name = data.get("name") or _package_name_from_file(file_path)
                version = data.get("version", "")
                if name and version:
                    cache[(name, version)] = data
        except (json.JSONDecodeError, KeyError):
            continue

    return cache


def _package_name_from_file(file_path: Path) -> str:
    """Extract package name from a version filename like 'code-review-skill-1.0.0.json'.

    Package names are kebab-case; versions are SemVer (MAJOR.MINOR.PATCH).
    We find the first segment that starts with a digit followed by '.' and
    take everything before it as the package name.

    This is a best-effort fallback in case the JSON does not contain a 'name' field.
    """
    stem = file_path.stem  # e.g. "code-review-skill-1.0.0"
    match = re.match(r"^(.+?)-(\d+\.\d+\.\d+)", stem)
    if match:
        return match.group(1)
    return stem


#: Indexed version details: {(name, version): version_dict}
version_details: dict[tuple[str, str], dict[str, Any]] = _load_version_files()


def get_all_packages() -> list[dict[str, Any]]:
    """Return the full list of package summary dicts."""
    return list(_packages_list)  # type: ignore[return-value]


def get_package_by_name(name: str) -> dict[str, Any] | None:
    """Look up a package summary by its unique name."""
    return packages_by_name.get(name)


def get_package_by_id(package_id: str) -> dict[str, Any] | None:
    """Look up a package summary by its unique id."""
    return packages_by_id.get(package_id)


def get_version_detail(name: str, version: str) -> dict[str, Any] | None:
    """Return the full version detail dict if available."""
    return version_details.get((name, version))


def get_versions_for_package(name: str) -> list[dict[str, Any]]:
    """Return a list of version summaries for a given package name.

    If dedicated version files exist they are used; otherwise a single
    synthetic entry is constructed from the package summary data.
    """
    entries: list[dict[str, Any]] = []

    # Collect from dedicated version files.
    for (n, v), data in version_details.items():
        if n == name:
            entries.append({
                "id": data.get("id", ""),
                "version": data.get("version", v),
                "status": data.get("status", "unknown"),
                "submitted_at": data.get("submitted_at"),
                "created_at": data.get("created_at"),
                "trust_score": (
                    data["trust_score"]["score"]
                    if isinstance(data.get("trust_score"), dict)
                    else None
                ),
            })

    # If no dedicated version files exist, construct an entry from the
    # packages.json summary row.
    if not entries:
        pkg = packages_by_name.get(name)
        if pkg:
            entries.append({
                "id": f"{pkg.get('id', '')}-v1",
                "version": pkg.get("latest_version", "0.1.0"),
                "status": pkg.get("status", "unknown"),
                "submitted_at": pkg.get("created_at"),
                "created_at": pkg.get("created_at"),
                "trust_score": pkg.get("trust_score"),
            })

    return entries
