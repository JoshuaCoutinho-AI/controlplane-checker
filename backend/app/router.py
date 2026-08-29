"""
Severity router: maps check + correlation output to a single decision
(pass / log / block), per the truth table in the build plan (Section 3.3).
All thresholds come from app.config so they are tunable without touching
this logic.
"""

from app.config import USE_CASE_POLICIES


def decide(
    performance: dict,
    cost: dict,
    responsibility: dict,
    correlation: dict,
    use_case: str = "customer_support",
) -> tuple[str, str]:
    policy = USE_CASE_POLICIES.get(use_case, USE_CASE_POLICIES["customer_support"])

    scores = {
        "performance": performance["score"],
        "cost": cost["score"],
        "responsibility": responsibility["score"],
    }
    compound_flags = set(correlation.get("compound_flags", []))

    # Hard block: PII found is always a block regardless of score math.
    if responsibility.get("pii_found"):
        return "block", "responsibility check found PII in the response"

    block_flags = policy["correlation_block_flags"]
    if compound_flags & block_flags:
        hit = sorted(compound_flags & block_flags)[0]
        return "block", f"correlation engine raised a blocking compound flag: {hit}"

    critical = [name for name, val in scores.items() if val < policy["score_block_below"]]
    if critical:
        return "block", f"{critical[0]} score critically low ({scores[critical[0]]})"

    log_flags = policy["correlation_log_flags"]
    if compound_flags & log_flags:
        hit = sorted(compound_flags & log_flags)[0]
        return "log", f"correlation engine raised a compound flag for review: {hit}"

    degraded = [name for name, val in scores.items() if val < policy["score_log_below"]]
    if degraded:
        return (
            "log",
            f"{degraded[0]} score below healthy threshold ({scores[degraded[0]]})",
        )

    return "pass", f"all checks within healthy range for {policy['name']} policy"
