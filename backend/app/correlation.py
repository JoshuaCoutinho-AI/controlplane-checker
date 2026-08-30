"""
Cross-signal correlation engine — the project's stated differentiator
(build plan Section 3.4). Implemented as a small, explicit rule set
operating on the three check outputs for one response, plus recent
history for the same session. Kept as plain rules (not a generic
framework) so it ships reliably under time pressure; extend the
RULES list rather than rewriting the evaluator.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import COMPOUND_WINDOW_SECONDS, COMPOUND_REPEAT_THRESHOLD


def _rule_cost_confidence_mismatch(cost: dict, performance: dict) -> bool:
    return (
        "cost_spike" in cost.get("flags", [])
        and performance.get("confidence", 1.0) < 0.5
    )


def _rule_latency_pii(performance: dict, responsibility: dict) -> bool:
    return "latency_over_budget" in performance.get("flags", []) and responsibility.get(
        "pii_found", False
    )


def _rule_hallucination_pii_person(hallucination: dict, responsibility: dict) -> bool:
    return "judge_verified_fabricated_person_claim" in hallucination.get(
        "flags", []
    ) and responsibility.get("pii_found", False)


RULES = [
    (
        "cost_confidence_mismatch",
        _rule_cost_confidence_mismatch,
        ("cost", "performance"),
    ),
    ("latency_pii_correlation", _rule_latency_pii, ("performance", "responsibility")),
    (
        "hallucination_pii_person_correlation",
        _rule_hallucination_pii_person,
        ("hallucination", "responsibility"),
    ),
]


def _recent_compound_count(db: Session, session_id: str) -> int:
    from app.models import ScoredResponse

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=COMPOUND_WINDOW_SECONDS)
    rows = (
        db.query(ScoredResponse)
        .filter(ScoredResponse.session_id == session_id)
        .filter(ScoredResponse.timestamp >= cutoff)
        .all()
    )
    return sum(bool((row.correlation or {}).get("compound_flags")) for row in rows)


def run(
    db: Session,
    session_id: str,
    performance: dict,
    cost: dict,
    responsibility: dict,
    bias: dict,
    hallucination: dict,
) -> dict:
    context = {
        "performance": performance,
        "cost": cost,
        "responsibility": responsibility,
        "bias": bias,
        "hallucination": hallucination,
    }
    compound_flags = []

    for flag_name, rule_fn, needed in RULES:
        args = [context[k] for k in needed]
        if rule_fn(*args):
            compound_flags.append(flag_name)

    if compound_flags:
        if _recent_compound_count(db, session_id) + 1 >= COMPOUND_REPEAT_THRESHOLD:
            compound_flags.append("repeated_compound_escalation")

    # correlation_score: 100 if clean, degrading with each compound flag
    correlation_score = max(0, 100 - 35 * len(compound_flags))

    return {
        "compound_flags": compound_flags,
        "correlation_score": correlation_score,
    }
