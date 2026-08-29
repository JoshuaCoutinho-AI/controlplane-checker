"""
Severity router: maps check + correlation output to a single decision
(pass / log / block), per the truth table in the build plan (Section 3.3).
All thresholds come from app.config so they are tunable without touching
this logic.
"""

from app.config import (
    SCORE_BLOCK_BELOW,
    SCORE_LOG_BELOW,
    CORRELATION_BLOCK_FLAGS,
    CORRELATION_LOG_FLAGS,
)


def decide(
    performance: dict, cost: dict, responsibility: dict, correlation: dict
) -> tuple[str, str]:
    scores = {
        "performance": performance["score"],
        "cost": cost["score"],
        "responsibility": responsibility["score"],
    }
    compound_flags = set(correlation.get("compound_flags", []))

    # Hard block: PII found is always a block regardless of score math.
    if responsibility.get("pii_found"):
        return "block", "responsibility check found PII in the response"

    if compound_flags & CORRELATION_BLOCK_FLAGS:
        hit = sorted(compound_flags & CORRELATION_BLOCK_FLAGS)[0]
        return "block", f"correlation engine raised a blocking compound flag: {hit}"

    critical = [name for name, val in scores.items() if val < SCORE_BLOCK_BELOW]
    if critical:
        return "block", f"{critical[0]} score critically low ({scores[critical[0]]})"

    if compound_flags & CORRELATION_LOG_FLAGS:
        hit = sorted(compound_flags & CORRELATION_LOG_FLAGS)[0]
        return "log", f"correlation engine raised a compound flag for review: {hit}"

    degraded = [name for name, val in scores.items() if val < SCORE_LOG_BELOW]
    if degraded:
        return (
            "log",
            f"{degraded[0]} score below healthy threshold ({scores[degraded[0]]})",
        )

    return "pass", "all checks within healthy range, no correlation flags"
