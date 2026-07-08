"""
Main entry point for the TrustedAgentHub Trust Score Engine.

Usage:
    from trust_score.src.main import calculate_trust_score

    result = calculate_trust_score(
        package_metadata=...,
        scan_report=...,
        author_history=...,
        review_records=...,
    )
    # result is a dict compatible with trust-score.schema.json

Uses only the Python standard library.
"""

from __future__ import annotations

from typing import Any

from .engine import rate


def calculate_trust_score(
    package_metadata: dict[str, Any],
    scan_report: dict[str, Any] | None = None,
    author_history: dict[str, Any] | None = None,
    review_records: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Calculate a trust score for an agent package.

    This is the primary public API. It orchestrates the full three-layer
    assessment funnel and returns a result compatible with the Trust Score
    schema (trust-score.schema.json).

    Args:
        package_metadata: dict conforming to agent-package.schema.json.
            Must include name, version, type, permissions, source, integrity,
            and all other required fields from the agent package schema.

        scan_report: dict conforming to scan-report.schema.json, or None.
            If None, prompt safety (I2) defaults to "suspicious" and behavior
            consistency (I3) defaults to "gap".

        author_history: dict with optional keys:
            packages_published (int): total packages published by author
            avg_historical_score (int): average score 0-100
            violations_count (int): number of policy violations
            If None or empty, defaults to newcomer.

        review_records: dict with optional keys:
            status (str): "approved", "rejected", "changes_requested", "pending",
                          or "unreviewed"
            reviewer_count (int): number of reviewers
            last_reviewed_at (str): ISO 8601 timestamp
            If None or empty, defaults to pending/unreviewed.

    Returns:
        dict with keys:
            score (int): 0-100 overall trust score
            package_name (str): package name
            version (str): package version
            calculated_at (str): ISO 8601 timestamp
            model_version (str): scoring model version
            dimensions (dict): nine dimension sub-scores with weights and details
            explanations (list): human-readable deduction explanations
            risk_summary (dict): level, top_risks, install_recommendation
    """
    return rate(
        package_metadata=package_metadata,
        scan_report=scan_report,
        author_history=author_history,
        review_records=review_records,
    )
