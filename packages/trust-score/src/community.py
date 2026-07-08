"""
Layer 3: Community & Review Assessment

C1 — Manual Review: evaluates the human review status of the package.
C2 — Author History: assesses the author's track record with time decay
     and quality-weighted scoring.

All functions operate on plain dicts and return dict results.
Uses only the Python standard library.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _decay_violation_weight(
    date_str: str,
    now: datetime | None = None,
) -> float:
    """Compute a time-decay weight for a single violation.

    Recent violations (≤365 days) carry full weight (1.0).
    Older violations are decayed:
      ≤730 days → 0.5
      >730 days → 0.25

    Invalid or missing date strings default to full weight (1.0).

    Args:
        date_str: ISO 8601 timestamp string
        now: reference datetime (defaults to UTC now)

    Returns:
        float between 0.0 and 1.0
    """
    if now is None:
        now = datetime.now(timezone.utc)
    try:
        # Accept both 'Z' and '+00:00' suffixes
        ts = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
    except (ValueError, TypeError, AttributeError):
        return 1.0  # unparseable date → assume recent

    age_days = (now - dt).days
    if age_days <= 365:
        return 1.0
    elif age_days <= 730:
        return 0.5
    else:
        return 0.25


def _compute_effective_violations(
    violations_count: int,
    violation_dates: list[str] | None,
) -> tuple[float, list[str]]:
    """Compute effective violation count with time decay.

    Args:
        violations_count: total raw violations
        violation_dates: optional list of ISO 8601 date strings, one per violation.
            When shorter than violations_count, remaining violations are assumed
            recent (weight 1.0).

    Returns:
        (effective_count, evidence_lines) where effective_count is a float
        that may be fractional due to decay.
    """
    evidence: list[str] = []
    if violations_count == 0:
        return 0.0, evidence

    if not violation_dates:
        # No dates provided — cannot decay; treat all as recent
        return float(violations_count), evidence

    now = datetime.now(timezone.utc)
    effective = 0.0
    decayed = 0
    # Only process up to violations_count dates — extra dates are ignored
    # to prevent the effective count from exceeding the declared total.
    dates_to_process = violation_dates[:violations_count]
    for date_str in dates_to_process:
        w = _decay_violation_weight(date_str, now)
        effective += w
        if w < 1.0:
            decayed += 1

    # Any violations beyond the provided dates are assumed recent
    remaining = violations_count - len(dates_to_process)
    if remaining > 0:
        effective += float(remaining)

    if decayed > 0:
        evidence.append(
            f"{decayed} of {violations_count} violation(s) partially decayed "
            f"(effective count: {effective:.1f})"
        )

    return effective, evidence


def assess_manual_review(review_records: dict[str, Any]) -> dict[str, Any]:
    """C1: Assess the manual review status of the package.

    Levels:
        approved          — review passed, package accepted
        pending           — awaiting review or unreviewed
        changes_requested — reviewer requested modifications
        rejected          — review rejected the package

    Args:
        review_records: dict with optional keys:
            status (str): "approved", "rejected", "changes_requested", "pending",
                          "pending_review", or "unreviewed"
            reviewer_count (int): number of reviewers
            last_reviewed_at (str): ISO 8601 timestamp

    Returns:
        dict with keys: level (str), score (int 0-100), evidence (list[str]),
                        reviewer_count (int)
    """
    records = review_records or {}

    status: str = records.get("status", "unreviewed")
    reviewer_count: int = records.get("reviewer_count", 0)
    last_reviewed_at: str = records.get("last_reviewed_at", "")

    evidence: list[str] = []

    # Normalize status values
    status_lower = status.lower()
    if status_lower in ("approved",):
        level = "approved"
        score = 95
        evidence.append(f"Package approved by {reviewer_count} reviewer(s)")
        if last_reviewed_at:
            evidence.append(f"Last reviewed: {last_reviewed_at}")
    elif status_lower in ("rejected",):
        level = "rejected"
        score = 5
        evidence.append("Package was rejected during review")
    elif status_lower in ("changes_requested",):
        level = "changes_requested"
        score = 35
        evidence.append("Reviewer(s) requested changes")
    else:
        # pending, pending_review, unreviewed, or unknown
        level = "pending"
        score = 50
        if status_lower == "unreviewed":
            evidence.append("Package has not been reviewed yet")
        else:
            evidence.append(f"Review status is '{status}' — awaiting review")

    return {
        "level": level,
        "score": score,
        "evidence": evidence,
        "reviewer_count": reviewer_count,
    }


def assess_author_history(author_history: dict[str, Any]) -> dict[str, Any]:
    """C2: Assess the author's publishing history and reputation.

    Levels:
        consistent_good — strong track record, many quality packages, no violations
        newcomer        — first-time publisher or very few packages
        inconsistent    — mixed record; some violations or low scores
        tainted         — history of serious violations or very poor scores

    Violation scoring uses time decay: violations older than 365 days are
    weighted less heavily.  Quality (avg_historical_score) contributes more
    to the final score than raw volume (packages_published).

    Args:
        author_history: dict with optional keys:
            packages_published (int): total packages published by author
            avg_historical_score (int): average score of author's packages (0-100)
            violations_count (int): number of policy violations
            violation_dates (list[str]): optional ISO 8601 timestamps, one per
                violation, used for time-decay weighting

    Returns:
        dict with keys: level (str), score (int 0-100), evidence (list[str]),
                        packages_published (int), avg_historical_score (int),
                        violations_count (int)
    """
    history = author_history or {}

    packages_published: int = history.get("packages_published", 0)
    avg_historical_score: int = history.get("avg_historical_score", 0)
    violations_count: int = history.get("violations_count", 0)
    violation_dates: list[str] | None = history.get("violation_dates")

    evidence: list[str] = []
    evidence.append(f"Published {packages_published} package(s)")

    # Compute effective violation count with time decay
    effective_violations, decay_evidence = _compute_effective_violations(
        violations_count, violation_dates
    )
    evidence.extend(decay_evidence)

    # ---- Level and score determination ----

    # Tainted: serious violations or very poor scores
    if effective_violations >= 2.5:
        level = "tainted"
        score = max(5, 15 - round(effective_violations) * 3)
        evidence.append(
            f"Author has effective {effective_violations:.1f} policy violations "
            f"(raw: {violations_count}) — history is tainted"
        )
    elif avg_historical_score < 30 and packages_published > 0:
        level = "tainted"
        score = max(8, avg_historical_score - 10)
        evidence.append(
            f"Average historical score is very low ({avg_historical_score}) — tainted record"
        )
    # Inconsistent: some violations or low scores
    elif effective_violations > 0:
        level = "inconsistent"
        # Quality-weighted base, penalised per effective violation
        score = max(25, min(65, avg_historical_score - round(effective_violations) * 12))
        evidence.append(
            f"Author has effective {effective_violations:.1f} violation(s) "
            f"(raw: {violations_count}) — mixed record"
        )
        if avg_historical_score > 0:
            evidence.append(f"Average historical score: {avg_historical_score}")
    elif avg_historical_score < 60 and packages_published > 0:
        level = "inconsistent"
        score = max(25, avg_historical_score - 5)
        evidence.append(f"Average historical score is below threshold: {avg_historical_score}")
    # Newcomer: few or no packages
    elif packages_published == 0:
        level = "newcomer"
        score = 55  # neutral — no data to judge
        evidence.append("Author is a newcomer with no published packages")
    elif packages_published < 3:
        level = "newcomer"
        # Small quality bonus if the few packages score well
        quality_bonus = max(0, avg_historical_score - 60) // 5
        score = min(65, 55 + quality_bonus)
        evidence.append(
            f"Author has only {packages_published} package(s) — still establishing reputation"
        )
    # Consistent good: strong track record — quality-weighted
    else:
        level = "consistent_good"
        # Quality (avg score) contributes ~70% of the score;
        # volume contributes at most ~25 points.
        quality_part = avg_historical_score * 0.7
        volume_part = min(25, packages_published * 2.5)
        score = min(100, round(quality_part + volume_part))
        evidence.append(
            f"Strong track record: {packages_published} packages, "
            f"average score {avg_historical_score}"
        )
        if violations_count == 0:
            evidence.append("No policy violations on record")
        if avg_historical_score >= 85:
            score = min(100, score + 3)

    return {
        "level": level,
        "score": score,
        "evidence": evidence,
        "packages_published": packages_published,
        "avg_historical_score": avg_historical_score,
        "violations_count": violations_count,
        "effective_violations": effective_violations,
    }
