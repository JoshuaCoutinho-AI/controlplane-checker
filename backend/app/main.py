from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
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

    return {
        "default_provider": LLM_PROVIDER,
        "available_providers": list(VALID_PROVIDERS),
        "models": {"ollama": OLLAMA_MODEL, "gemini": GEMINI_MODEL},
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
        session_id=req.session_id,
        measured_latency_ms=latency_ms,
    )
    payload = record.to_payload()
    payload["generated"] = generated
    payload["llm_provider"] = provider_used
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
