"""
Layer 1: Source Provenance Assessment

P1 — Source Verifiability: determines how trustworthy the package's origin is.
P2 — Content Signature Chain: evaluates integrity guarantees of the package contents.

All functions operate on plain dicts (JSON-deserialized) and return dict results.
Uses only the Python standard library.
"""

from __future__ import annotations

import re
from typing import Any


def assess_source_verifiability(package_metadata: dict[str, Any]) -> dict[str, Any]:
    """P1: Assess how verifiable the package source is.

    Levels:
        verified  — verified owner, commit-hash-pinned, known source type
        traceable — source info present but not fully verified (missing commit, not verified)
        opaque    — minimal or no source provenance

    Args:
        package_metadata: dict conforming to agent-package.schema.json

    Returns:
        dict with keys: level (str), score (int 0-100), evidence (list[str])
    """
    source: dict[str, Any] = package_metadata.get("source", {}) or {}
    evidence: list[str] = []
    checks_passed: int = 0
    checks_total: int = 4

    source_type: str = source.get("type", "")
    verified_owner: bool = source.get("verified_owner", False)
    commit_hash: str = source.get("commit_hash", "")
    repository_url: str = source.get("repository_url", "")
    ref_type: str = source.get("ref_type", "")

    # Check 1: Has a known source type
    if source_type and source_type != "local_upload":
        checks_passed += 1
        evidence.append(f"Source type is '{source_type}'")
    else:
        evidence.append("Missing or unknown source type")

    # Check 2: Verified owner
    if verified_owner:
        checks_passed += 1
        evidence.append("Owner is verified")
    else:
        evidence.append("Owner is not verified")

    # Check 3: Pinned commit hash (40 hex chars)
    if re.fullmatch(r"^[a-f0-9]{40}$", commit_hash):
        checks_passed += 1
        evidence.append("Commit hash is pinned")
    else:
        evidence.append("Missing or invalid commit hash")

    # Check 4: Has repository URL and a stable ref (tag or release)
    if repository_url:
        if ref_type in ("tag", "release"):
            checks_passed += 1
            evidence.append(f"Repository URL present with stable ref type '{ref_type}'")
        elif ref_type in ("branch", "commit"):
            checks_passed += 0.5  # partial credit
            evidence.append(f"Repository URL present but ref type is '{ref_type}' (less stable)")
        else:
            checks_passed += 0.5
            evidence.append("Repository URL present but ref type is unspecified")
    else:
        evidence.append("No repository URL")

    # Determine level
    if checks_passed >= 3.5:
        level = "verified"
    elif checks_passed >= 1.5:
        level = "traceable"
    else:
        level = "opaque"

    # Derive score from checks_passed
    score = _checks_to_score(checks_passed, checks_total)

    return {"level": level, "score": score, "evidence": evidence}


def assess_signature_chain(package_metadata: dict[str, Any]) -> dict[str, Any]:
    """P2: Assess the content signature / integrity chain.

    Levels:
        complete — sha256 + signature/attestation + sbom present
        partial  — sha256 present but missing other elements
        none     — no integrity info at all

    Args:
        package_metadata: dict conforming to agent-package.schema.json

    Returns:
        dict with keys: level (str), score (int 0-100), evidence (list[str])
    """
    integrity: dict[str, Any] = package_metadata.get("integrity", {}) or {}
    evidence: list[str] = []
    checks_passed: int = 0
    checks_total: int = 3

    sha256: str = integrity.get("sha256", "")
    signature: str = integrity.get("signature", "")
    attestation_url: str = integrity.get("attestation_url", "")
    sbom_url: str = integrity.get("sbom_url", "")

    # Check 1: SHA256 hash (64 hex chars)
    if re.fullmatch(r"^[a-f0-9]{64}$", sha256):
        checks_passed += 1
        evidence.append("SHA256 integrity hash is present")
    else:
        evidence.append("Missing or invalid SHA256 integrity hash")

    # Check 2: Signature or attestation
    if signature or attestation_url:
        checks_passed += 1
        if signature:
            evidence.append("Cryptographic signature is present")
        if attestation_url:
            evidence.append("Build attestation URL is present")
    else:
        evidence.append("No cryptographic signature or attestation")

    # Check 3: SBOM
    if sbom_url:
        checks_passed += 1
        evidence.append("SBOM URL is present")
    else:
        evidence.append("No SBOM URL")

    # Determine level
    if checks_passed == 3:
        level = "complete"
    elif checks_passed >= 1:
        level = "partial"
    else:
        level = "none"

    score = _checks_to_score(checks_passed, checks_total)

    return {"level": level, "score": score, "evidence": evidence}


def _checks_to_score(passed: float, total: int) -> int:
    """Convert a check-passed ratio to a 0-100 integer score."""
    ratio = passed / max(total, 1)
    # Map to 10-100 range (never 0 to leave room for truly broken cases)
    return max(10, min(100, round(10 + ratio * 90)))
