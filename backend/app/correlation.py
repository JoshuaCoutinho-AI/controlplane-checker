"""
Cross-signal correlation engine — the project's stated differentiator
(build plan Section 3.4). Implemented as a small, explicit rule set
operating on the three check outputs for one response, plus recent
history for the same session. Kept as plain rules (not a generic
framework) so it ships reliably under time pressure; extend the
RULES list rather than rewriting the evaluator.
"""

from collections import defaultdict
from datetime import datetime, timezone

from app.config import COMPOUND_WINDOW_SECONDS, COMPOUND_REPEAT_THRESHOLD

# in-memory recent compound-flag history per session, for the
# "repeated compound flags" escalation rule. Fine for a single-process
# demo; would move to the DB/Redis for multi-instance deployment.
_recent_compound_flags: dict[str, list[float]] = defaultdict(list)


def _rule_cost_confidence_mismatch(cost: dict, performance: dict) -> bool:
    return (
        "cost_spike" in cost.get("flags", [])
        and performance.get("confidence", 1.0) < 0.5
    )


def _rule_latency_pii(performance: dict, responsibility: dict) -> bool:
    return "latency_over_budget" in performance.get("flags", []) and responsibility.get(
        "pii_found", False
    )


RULES = [
    (
        "cost_confidence_mismatch",
        _rule_cost_confidence_mismatch,
        ("cost", "performance"),
    ),
    ("latency_pii_correlation", _rule_latency_pii, ("performance", "responsibility")),
]


def run(session_id: str, performance: dict, cost: dict, responsibility: dict) -> dict:
    context = {
        "performance": performance,
        "cost": cost,
        "responsibility": responsibility,
    }
    compound_flags = []

    for flag_name, rule_fn, needed in RULES:
        args = [context[k] for k in needed]
        if rule_fn(*args):
            compound_flags.append(flag_name)

    now = datetime.now(timezone.utc).timestamp()
    if compound_flags:
        history = _recent_compound_flags[session_id]
        history.append(now)
        # prune anything outside the window
        _recent_compound_flags[session_id] = [
            t for t in history if now - t <= COMPOUND_WINDOW_SECONDS
        ]
        if len(_recent_compound_flags[session_id]) >= COMPOUND_REPEAT_THRESHOLD:
            compound_flags.append("repeated_compound_escalation")

    # correlation_score: 100 if clean, degrading with each compound flag
    correlation_score = max(0, 100 - 35 * len(compound_flags))

    return {
        "compound_flags": compound_flags,
        "correlation_score": correlation_score,
    }
