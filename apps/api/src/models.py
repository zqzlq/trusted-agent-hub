"""Pydantic models for API responses.

These models define the shape of data returned by the Consumer-side (分发侧)
endpoints.  They are derived from the shared agent-package schema and adapted
for API presentation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------


class Owner(BaseModel):
    """Package owner / author summary."""

    id: str
    username: str
    display_name: str
    role: str


class Author(BaseModel):
    """Detailed author information (from version detail)."""

    name: str
    email: str
    url: str | None = None


class Source(BaseModel):
    """Source repository reference."""

    type: str
    repository_url: str
    owner: str | None = None
    repo: str | None = None
    ref_type: str | None = None
    ref: str
    commit_hash: str
    verified_owner: bool = False
    stars: int | None = None
    last_commit_at: str | None = None


class Integrity(BaseModel):
    """Integrity / verification information."""

    sha256: str
    signature: str | None = None
    attestation_url: str | None = None
    sbom_url: str | None = None


class FilesystemPermissions(BaseModel):
    read: list[str] = Field(default_factory=list)
    write: list[str] = Field(default_factory=list)
    delete: bool = False


class ShellPermissions(BaseModel):
    allowed: bool = False
    commands: list[str] = Field(default_factory=list)
    description: str | None = None


class NetworkPermissions(BaseModel):
    allowed: bool = False
    domains: list[str] = Field(default_factory=list)
    description: str | None = None


class EnvironmentPermissions(BaseModel):
    read: list[str] = Field(default_factory=list)
    write: list[str] = Field(default_factory=list)


class CredentialsPermissions(BaseModel):
    access: list[str] = Field(default_factory=list)
    description: str | None = None


class Permissions(BaseModel):
    filesystem: FilesystemPermissions | None = None
    shell: ShellPermissions | None = None
    network: NetworkPermissions | None = None
    environment: EnvironmentPermissions | None = None
    credentials: CredentialsPermissions | None = None
    database: dict[str, Any] | None = None
    browser: dict[str, Any] | None = None
    external_services: list[Any] | None = None


class InstallTarget(BaseModel):
    client: str
    destination: str
    config_template: str | None = None


class Installation(BaseModel):
    method: str
    targets: list[InstallTarget] = Field(default_factory=list)
    command: str | None = None
    pre_install_message: str | None = None
    post_install_message: str | None = None


class Dependencies(BaseModel):
    npm: list[dict[str, str]] | None = None
    pip: list[dict[str, str]] | None = None
    system: list[str] | None = None
    docker: list[dict[str, str]] | None = None
    mcp_servers: list[dict[str, str]] | None = None


class EntryPoints(BaseModel):
    main: str | None = None
    config: str | None = None
    scripts: list[str] | None = None


# ---------------------------------------------------------------------------
# Trust score
# ---------------------------------------------------------------------------


class TrustScoreDimension(BaseModel):
    score: float
    weight: float
    details: dict[str, Any] | None = None


class TrustScoreExplanation(BaseModel):
    dimension: str
    message: str
    deduction: float | None = None
    evidence: str | None = None


class RiskSummary(BaseModel):
    level: str
    top_risks: list[str] = Field(default_factory=list)
    install_recommendation: str


class TrustScore(BaseModel):
    score: float
    model_version: str | None = None
    dimensions: dict[str, TrustScoreDimension] | None = None
    explanations: list[TrustScoreExplanation] | None = None
    risk_summary: RiskSummary | None = None
    calculated_at: str | None = None


# ---------------------------------------------------------------------------
# Scan report
# ---------------------------------------------------------------------------


class ScanFinding(BaseModel):
    id: str
    rule_id: str | None = None
    severity: str
    category: str
    title: str
    description: str
    location: dict[str, Any] | None = None
    remediation: str | None = None
    cwe_id: str | None = None


class ScanReport(BaseModel):
    scan_id: str
    scanner_version: str
    duration_ms: int | None = None
    summary: dict[str, Any] | None = None
    findings: list[ScanFinding] | None = None
    metadata_validation: dict[str, Any] | None = None
    structure_check: dict[str, Any] | None = None
    dependency_check: dict[str, Any] | None = None
    scanned_at: str | None = None


# ---------------------------------------------------------------------------
# API response models
# ---------------------------------------------------------------------------


class PackageSummary(BaseModel):
    """Lightweight package row for list views."""

    id: str
    name: str
    description: str
    type: str
    license: str | None = None
    keywords: list[str] = Field(default_factory=list)
    category: str | None = None
    homepage: str | None = None
    icon_url: str | None = None
    owner: Owner | None = None
    latest_version: str
    status: str
    trust_score: float | None = None
    risk_level: str | None = None
    install_count: int = 0
    avg_rating: float | None = None
    created_at: str | None = None
    updated_at: str | None = None


class PackageDetail(BaseModel):
    """Full package detail including metadata fields."""

    id: str
    name: str
    description: str
    type: str
    license: str | None = None
    keywords: list[str] = Field(default_factory=list)
    category: str | None = None
    homepage: str | None = None
    icon_url: str | None = None
    owner: Owner | None = None
    latest_version: str
    status: str
    trust_score: float | None = None
    risk_level: str | None = None
    install_count: int = 0
    avg_rating: float | None = None
    created_at: str | None = None
    updated_at: str | None = None


class VersionSummary(BaseModel):
    """Summary row for a package version listing."""

    id: str
    version: str
    status: str
    submitted_at: str | None = None
    created_at: str | None = None
    trust_score: float | None = None


class VersionDetail(BaseModel):
    """Full version detail including trust scores, scan report, etc."""

    id: str
    package_id: str
    version: str
    author: Author | None = None
    source: Source | None = None
    integrity: Integrity | None = None
    compatibility: list[str] = Field(default_factory=list)
    permissions: Permissions | None = None
    installation: Installation | None = None
    type_config: dict[str, Any] | None = None
    dependencies: Dependencies | None = None
    entry_points: EntryPoints | None = None
    status: str
    submitted_at: str | None = None
    published_at: str | None = None
    created_at: str | None = None
    trust_score: TrustScore | None = None
    scan_report: ScanReport | None = None


class InstallManifest(BaseModel):
    """Installation manifest returned to the consumer."""

    package_name: str
    version: str
    method: str
    targets: list[InstallTarget] = Field(default_factory=list)
    command: str | None = None
    dependencies: Dependencies | None = None
    compatibility: list[str] = Field(default_factory=list)
    pre_install_warnings: list[str] = Field(default_factory=list)
    pre_install_message: str | None = None
    post_install_message: str | None = None
    trust_score: TrustScoreResponse | None = None


class TrustScoreResponse(BaseModel):
    """Trust score data returned to the consumer."""

    version_id: str
    score: float
    level: str | None = None
    recommendation: str | None = None
    dimensions: dict[str, Any] | None = None
    explanations: list[dict[str, Any]] | None = None
    calculated_at: str | None = None


class PackageStats(BaseModel):
    """Install / download statistics for a package."""

    package_name: str
    install_count: int = 0
    avg_rating: float | None = None
    total_versions: int = 0
    latest_version: str | None = None
    status: str | None = None


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list wrapper."""

    items: list[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    limit: int = 20
