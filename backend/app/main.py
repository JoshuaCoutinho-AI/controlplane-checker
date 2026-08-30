from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import asyncio

from app.db import init_db, get_session
from app.models import ScoredResponse
from app.proxy import score_and_route
from app.ws import manager
from app.llm_provider import (
    generate_response,
    LLMProviderError,
    LLM_PROVIDER,
    VALID_PROVIDERS,
)

app = FastAPI(title="ControlPlane Checker", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local demo only; tighten if ever deployed
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/llm/status")
def llm_status():
    """The default provider (used when a request doesn't specify one)
    plus the full list of providers the frontend can switch between.
    The dashboard's model dropdown picks the provider per request —
    this endpoint just tells it what's available and what the fallback
    is, for display purposes."""
    from app.llm_provider import OLLAMA_MODEL, GEMINI_MODEL
    from app.config import USE_CASE_POLICIES

    # Convert sets to lists in USE_CASE_POLICIES for JSON serialization
    serialized_policies = {}
    for uc, policy in USE_CASE_POLICIES.items():
        serialized_policies[uc] = {
            **policy,
            "correlation_block_flags": list(policy["correlation_block_flags"]),
            "correlation_log_flags": list(policy["correlation_log_flags"]),
        }

    return {
        "default_provider": LLM_PROVIDER,
        "available_providers": list(VALID_PROVIDERS),
        "models": {"ollama": OLLAMA_MODEL, "gemini": GEMINI_MODEL},
        "policies": serialized_policies,
    }


class ScoreRequest(BaseModel):
    prompt: str
    # Optional: if omitted or blank, a real LLM call generates the
    # response (default behavior). Supply it explicitly to score a
    # response you already have — e.g. testing a specific scenario, or
    # replaying a response captured elsewhere — bypassing generation.
    response: str | None = None
    # Doubles as (a) the cost-table rate to score against, and (b) when
    # generating, WHICH provider to call — "ollama" or "gemini". This
    # is how the frontend dropdown switches providers per request with
    # no restart needed. Falls back to LLM_PROVIDER's default if this
    # isn't a recognized provider name (e.g. legacy/manual requests).
    model: str = "default"
    use_case: str = "customer_support"
    geography: str = "US"
    session_id: str = "demo-session"
    latency_ms: float | None = None


@app.post("/score")
async def score(req: ScoreRequest, db: Session = Depends(get_session)):
    response_text = req.response
    latency_ms = req.latency_ms
    generated = False
    provider_used = None

    if not response_text or not response_text.strip():
        requested_provider = req.model if req.model in VALID_PROVIDERS else None
        provider_used = requested_provider or LLM_PROVIDER
        try:
            response_text, gen_latency_ms = await asyncio.to_thread(
                generate_response, req.prompt, requested_provider
            )
        except LLMProviderError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"LLM generation failed (provider={provider_used}): {exc}",
            )
        latency_ms = gen_latency_ms
        generated = True

    record = await score_and_route(
        db,
        prompt=req.prompt,
        response=response_text,
        model=req.model,
        use_case=req.use_case,
        geography=req.geography,
        session_id=req.session_id,
        measured_latency_ms=latency_ms,
    )
    payload = record.to_payload()
    payload["generated"] = generated
    payload["llm_provider"] = provider_used
    await manager.broadcast(payload)
    return payload


class OverrideRequest(BaseModel):
    status: str  # "override_allow" | "override_block" | "none"
    reason: str | None = None


@app.post("/score/{score_id}/override")
async def override(
    score_id: str, req: OverrideRequest, db: Session = Depends(get_session)
):
    record = db.query(ScoredResponse).filter(ScoredResponse.id == score_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Scored response not found")

    if req.status not in ("override_allow", "override_block", "none"):
        raise HTTPException(status_code=400, detail="Invalid override status")

    record.override_status = req.status
    record.override_reason = req.reason

    # Update severity based on override status
    if req.status == "override_allow":
        record.severity = "pass"
        record.decision_reason = f"Override applied: Allowed by human. Reason: {req.reason or 'No reason provided'}"
    elif req.status == "override_block":
        record.severity = "block"
        record.decision_reason = f"Override applied: Blocked by human. Reason: {req.reason or 'No reason provided'}"
    elif req.status == "none":
        record.override_status = "none"
        record.override_reason = None
        record.severity = record.original_severity or record.severity
        record.decision_reason = (
            record.original_decision_reason or record.decision_reason
        )

    db.commit()
    db.refresh(record)

    payload = record.to_payload()
    await manager.broadcast(payload)
    return payload


class FeedbackRequest(BaseModel):
    override: str  # false_positive | false_negative | correct
    note: str | None = None


@app.post("/feedback/{response_id}")
async def feedback(
    response_id: str, req: FeedbackRequest, db: Session = Depends(get_session)
):
    from app.models import FeedbackEntry

    record = db.query(ScoredResponse).filter(ScoredResponse.id == response_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Scored response not found")
    if req.override not in ("false_positive", "false_negative", "correct"):
        raise HTTPException(status_code=400, detail="Invalid feedback override")

    entry = FeedbackEntry(response_id=record.id, override=req.override, note=req.note)
    db.add(entry)
    # Retained for backwards-compatible payloads; the related table is the
    # audit source of truth for future threshold recalibration work.
    record.feedback_text = req.note
    db.commit()
    db.refresh(record)

    payload = record.to_payload()
    payload["feedback_event"] = {"override": entry.override, "note": entry.note}
    await manager.broadcast(payload)
    return payload


@app.get("/history")
def history(limit: int = 50, db: Session = Depends(get_session)):
    rows = (
        db.query(ScoredResponse)
        .order_by(desc(ScoredResponse.timestamp))
        .limit(limit)
        .all()
    )
    return [r.to_payload() for r in rows]


@app.get("/metrics")
def metrics(db: Session = Depends(get_session)):
    """Report feedback-grounded error rates for monitoring, not estimates."""
    from app.models import FeedbackEntry

    total_responses = db.query(func.count(ScoredResponse.id)).scalar() or 0
    total_feedback = db.query(func.count(FeedbackEntry.id)).scalar() or 0
    labels = ("false_positive", "false_negative", "correct")
    label_counts = {
        label: db.query(func.count(FeedbackEntry.id))
        .filter(FeedbackEntry.override == label)
        .scalar()
        or 0
        for label in labels
    }
    by_severity = {}
    for severity in ("pass", "edit", "log", "block"):
        feedback_total = (
            db.query(func.count(FeedbackEntry.id))
            .join(ScoredResponse, FeedbackEntry.response_id == ScoredResponse.id)
            .filter(
                func.coalesce(ScoredResponse.original_severity, ScoredResponse.severity)
                == severity
            )
            .scalar()
            or 0
        )
        false_positive = (
            db.query(func.count(FeedbackEntry.id))
            .join(ScoredResponse, FeedbackEntry.response_id == ScoredResponse.id)
            .filter(
                func.coalesce(ScoredResponse.original_severity, ScoredResponse.severity)
                == severity
            )
            .filter(FeedbackEntry.override == "false_positive")
            .scalar()
            or 0
        )
        false_negative = (
            db.query(func.count(FeedbackEntry.id))
            .join(ScoredResponse, FeedbackEntry.response_id == ScoredResponse.id)
            .filter(
                func.coalesce(ScoredResponse.original_severity, ScoredResponse.severity)
                == severity
            )
            .filter(FeedbackEntry.override == "false_negative")
            .scalar()
            or 0
        )
        by_severity[severity] = {
            "feedback_entries": feedback_total,
            "false_positive_rate": (
                false_positive / feedback_total if feedback_total else None
            ),
            "false_negative_rate": (
                false_negative / feedback_total if feedback_total else None
            ),
        }
    return {
        "total_scored_responses": total_responses,
        "total_feedback_entries": total_feedback,
        "feedback_coverage_percent": round(
            (total_feedback / total_responses * 100) if total_responses else 0, 2
        ),
        "false_positive_rate": (
            label_counts["false_positive"] / total_feedback if total_feedback else None
        ),
        "false_negative_rate": (
            label_counts["false_negative"] / total_feedback if total_feedback else None
        ),
        "by_severity": by_severity,
    }


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # dashboard doesn't send anything meaningful; just keep the
            # connection open and drop incoming pings/messages.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
