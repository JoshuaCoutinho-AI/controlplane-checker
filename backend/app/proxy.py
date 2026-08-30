"""
Proxy orchestration: the core pipeline described in the build plan
(Section 2.2). Given a prompt/response pair, runs five checks
concurrently, runs correlation across their results, routes by
severity, persists the record, and returns the payload to broadcast.
"""

import time
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app import correlation, router
from app.config import USE_CASE_POLICIES
from app.checks import cost as cost_check
from app.checks import performance as performance_check
from app.checks import responsibility as responsibility_check
from app.checks import bias as bias_check
from app.checks import hallucination as hallucination_check
from app.models import ScoredResponse


def _recent_costs(db: Session, model: str, limit: int) -> list[float]:
    rows = (
        db.query(ScoredResponse)
        .filter(ScoredResponse.model == model)
        .order_by(desc(ScoredResponse.timestamp))
        .limit(limit)
        .all()
    )
    return [r.cost.get("est_cost_usd", 0.0) for r in rows if r.cost]


async def score_and_route(
    db: Session,
    prompt: str,
    response: str,
    model: str = "default",
    use_case: str = "customer_support",
    geography: str = "US",
    session_id: str = "demo-session",
    measured_latency_ms: float | None = None,
) -> ScoredResponse:
    start = time.perf_counter()

    recent_costs = _recent_costs(db, model, limit=20)

    policy = USE_CASE_POLICIES.get(use_case, USE_CASE_POLICIES["customer_support"])
    latency_budget = policy["latency_budget_ms"]

    # Keep bias and hallucination as top-level outputs rather than hiding them
    # inside responsibility: judges can inspect each risk system independently.
    # All five checks are independent and execute concurrently.
    perf_task = asyncio.to_thread(
        performance_check.run,
        prompt,
        response,
        (
            measured_latency_ms
            if measured_latency_ms is not None
            else (time.perf_counter() - start) * 1000
        ),
        latency_budget,
    )
    cost_task = asyncio.to_thread(cost_check.run, prompt, response, model, recent_costs)
    resp_task = asyncio.to_thread(responsibility_check.run, response, geography)
    bias_task = asyncio.to_thread(bias_check.run, response)
    hallucination_task = hallucination_check.run(prompt, response, model)

    perf_result, cost_result, resp_result, bias_result, hallucination_result = (
        await asyncio.gather(
            perf_task, cost_task, resp_task, bias_task, hallucination_task
        )
    )

    correlation_result = correlation.run(
        db,
        session_id,
        perf_result,
        cost_result,
        resp_result,
        bias_result,
        hallucination_result,
    )
    severity, reason = router.decide(
        perf_result,
        cost_result,
        resp_result,
        bias_result,
        hallucination_result,
        correlation_result,
        use_case,
    )

    record = ScoredResponse(
        session_id=session_id,
        model=model,
        use_case=use_case,
        geography=geography,
        prompt_excerpt=prompt,
        # never store raw response text if PII was found — store the
        # redacted (but full-length) text the responsibility check
        # already computed instead
        response_excerpt=(
            resp_result["redacted_excerpt"] if resp_result["pii_found"] else response
        ),
        performance=perf_result,
        cost=cost_result,
        responsibility={
            k: v for k, v in resp_result.items() if k != "redacted_excerpt"
        },
        bias=bias_result,
        hallucination=hallucination_result,
        correlation=correlation_result,
        severity=severity,
        decision_reason=reason,
        original_severity=severity,
        original_decision_reason=reason,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
