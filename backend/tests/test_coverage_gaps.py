"""
Gap-coverage tests — 30 Aug deadline push.
Covers:
  1. All three use-case policies' block/edit/log/pass thresholds at the router level
  2. Override endpoint: allow, block, and "none" reset
  3. Malformed-input handling: empty prompt, missing field, invalid override status
"""

from fastapi.testclient import TestClient

from app import router
from app.config import USE_CASE_POLICIES
from app.main import app
from app.db import init_db, engine
from app.models import Base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_inputs(perf_score=90, cost_score=90, resp_score=95, pii=False,
                  resp_flags=None, bias_score=95, hallucination_score=95,
                  compound_flags=None):
    """Build the six dicts router.decide expects, with overridable scores."""
    return (
        {"score": perf_score},
        {"score": cost_score},
        {"score": resp_score, "pii_found": pii, "flags": resp_flags or []},
        {"score": bias_score, "flags": []},
        {"score": hallucination_score, "flags": []},
        {"compound_flags": compound_flags or []},
    )


# ---------------------------------------------------------------------------
# 1. USE-CASE POLICY THRESHOLD ENFORCEMENT (router.decide)
# ---------------------------------------------------------------------------
# Each policy has score_block_below and score_log_below.  The tests confirm
# the router actually blocks/logs/passes at the boundary, not just that
# config values exist.
#
# Policy thresholds from config.py:
#   customer_support:  block < 40, log < 70
#   internal_knowledge: block < 25, log < 60
#   decision_support:  block < 50, log < 80

class TestCustomerSupportPolicy:
    USE_CASE = "customer_support"

    def test_blocks_below_threshold(self):
        """Score 39 is below block_below=40 → must block."""
        perf, cost, resp, bias, hall, corr = _clean_inputs(perf_score=39)
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case=self.USE_CASE)
        assert severity == "block"

    def test_logs_between_block_and_log(self):
        """Score 40 passes block (≥40) but is below log_below=70 → must log."""
        perf, cost, resp, bias, hall, corr = _clean_inputs(perf_score=40)
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case=self.USE_CASE)
        assert severity == "log"

    def test_passes_above_log_threshold(self):
        """Score 70 is at log_below=70 boundary → ≥70 should pass."""
        perf, cost, resp, bias, hall, corr = _clean_inputs(perf_score=70)
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case=self.USE_CASE)
        assert severity == "pass"

    def test_block_on_any_single_check_below_threshold(self):
        """If only cost is critically low, router should still block."""
        perf, cost, resp, bias, hall, corr = _clean_inputs(cost_score=30)
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case=self.USE_CASE)
        assert severity == "block"


class TestInternalKnowledgePolicy:
    USE_CASE = "internal_knowledge"

    def test_blocks_below_threshold(self):
        """Score 24 is below block_below=25 → must block."""
        perf, cost, resp, bias, hall, corr = _clean_inputs(perf_score=24)
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case=self.USE_CASE)
        assert severity == "block"

    def test_logs_between_block_and_log(self):
        """Score 25 passes block (≥25) but is below log_below=60 → must log."""
        perf, cost, resp, bias, hall, corr = _clean_inputs(perf_score=25)
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case=self.USE_CASE)
        assert severity == "log"

    def test_passes_above_log_threshold(self):
        """Score 60 is at log_below=60 boundary → ≥60 should pass."""
        perf, cost, resp, bias, hall, corr = _clean_inputs(perf_score=60)
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case=self.USE_CASE)
        assert severity == "pass"

    def test_score_35_logs_not_blocks(self):
        """Score 35 is between 25 (block) and 60 (log) → log, not block.
        This is the inverse of the existing test: confirm relaxed policy
        doesn't block what customer_support would."""
        perf, cost, resp, bias, hall, corr = _clean_inputs(perf_score=35)
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case=self.USE_CASE)
        assert severity == "log"


class TestDecisionSupportPolicy:
    USE_CASE = "decision_support"

    def test_blocks_below_threshold(self):
        """Score 49 is below block_below=50 → must block."""
        perf, cost, resp, bias, hall, corr = _clean_inputs(perf_score=49)
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case=self.USE_CASE)
        assert severity == "block"

    def test_logs_between_block_and_log(self):
        """Score 50 passes block (≥50) but is below log_below=80 → must log."""
        perf, cost, resp, bias, hall, corr = _clean_inputs(perf_score=50)
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case=self.USE_CASE)
        assert severity == "log"

    def test_passes_above_log_threshold(self):
        """Score 80 is at log_below=80 boundary → ≥80 should pass."""
        perf, cost, resp, bias, hall, corr = _clean_inputs(perf_score=80)
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case=self.USE_CASE)
        assert severity == "pass"

    def test_blocks_on_cost_confidence_mismatch_flag(self):
        """decision_support treats cost_confidence_mismatch as a BLOCK flag
        (unlike customer_support which only logs it). Confirm the correlation
        flag integration actually blocks."""
        perf, cost, resp, bias, hall, corr = _clean_inputs()
        corr["compound_flags"] = ["cost_confidence_mismatch"]
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case=self.USE_CASE)
        assert severity == "block"

    def test_customer_support_only_logs_cost_confidence_mismatch(self):
        """Same flag under customer_support should only log, not block."""
        perf, cost, resp, bias, hall, corr = _clean_inputs()
        corr["compound_flags"] = ["cost_confidence_mismatch"]
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case="customer_support")
        assert severity == "log"


class TestPolicyIsolatedPIIEdits:
    """Isolated PII (no toxicity/restricted/compound context) should return
    'edit' (auto-redact and release) across all policies."""

    def test_isolated_pii_edits_customer_support(self):
        perf, cost, resp, bias, hall, corr = _clean_inputs(pii=True, resp_score=40)
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case="customer_support")
        assert severity == "edit"

    def test_isolated_pii_edits_internal_knowledge(self):
        perf, cost, resp, bias, hall, corr = _clean_inputs(pii=True, resp_score=40)
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case="internal_knowledge")
        assert severity == "edit"

    def test_isolated_pii_edits_decision_support(self):
        perf, cost, resp, bias, hall, corr = _clean_inputs(pii=True, resp_score=40)
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case="decision_support")
        assert severity == "edit"

    def test_pii_with_toxicity_still_blocks(self):
        """PII + toxicity flag = severe context → must block, not edit."""
        perf, cost, resp, bias, hall, corr = _clean_inputs(
            pii=True, resp_score=40, resp_flags=["toxicity_keyword"]
        )
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case="customer_support")
        assert severity == "block"


class TestUnknownUseCaseFallback:
    """An unrecognized use_case should fall back to customer_support policy."""

    def test_unknown_use_case_uses_customer_support(self):
        # Score 39 blocks under customer_support (block_below=40) but would
        # pass under internal_knowledge (block_below=25). If fallback works,
        # we get a block.
        perf, cost, resp, bias, hall, corr = _clean_inputs(perf_score=39)
        severity, _ = router.decide(perf, cost, resp, bias, hall, corr, use_case="nonexistent_policy")
        assert severity == "block"


class TestBiasHallucinationScoreRouting:
    """Confirm router.decide() actually reacts to low bias/hallucination
    scores, not just to the original three checks.

    Thresholds from config.py (customer_support):
        score_block_below = 40
        score_log_below   = 70
    """

    def test_low_bias_score_blocks(self):
        """bias score 20 is below customer_support block_below=40 → block."""
        perf, cost, resp, bias, hall, corr = _clean_inputs(bias_score=20)
        severity, reason = router.decide(
            perf, cost, resp, bias, hall, corr, use_case="customer_support"
        )
        assert severity == "block"
        assert "bias" in reason

    def test_low_hallucination_score_blocks(self):
        """hallucination score 30 is below customer_support block_below=40 → block."""
        perf, cost, resp, bias, hall, corr = _clean_inputs(hallucination_score=30)
        severity, reason = router.decide(
            perf, cost, resp, bias, hall, corr, use_case="customer_support"
        )
        assert severity == "block"
        assert "hallucination" in reason

    def test_bias_flag_with_healthy_score_passes(self):
        """A stereotyping flag on bias with score=95 (above all thresholds)
        should NOT trigger block or log — the router checks scores, not
        check-level flags. This confirms the router ignores bias flags
        when the score is healthy (no correlation rule consumes bias flags
        either)."""
        perf, cost, resp, _, hall, corr = _clean_inputs()
        bias_with_flag = {"score": 95, "flags": ["stereotyping_gender"]}
        severity, _ = router.decide(
            perf, cost, resp, bias_with_flag, hall, corr, use_case="customer_support"
        )
        assert severity == "pass"


# ---------------------------------------------------------------------------
# 2. OVERRIDE ENDPOINT — /score/{id}/override
# ---------------------------------------------------------------------------
# Uses TestClient against the actual FastAPI app with an in-memory SQLite DB.

def _get_test_client():
    """Create a fresh in-memory SQLite DB and return a TestClient.
    
    Uses StaticPool so every connection shares the same in-memory DB —
    without this, SQLite creates a separate empty DB per connection and
    async handlers (which run in worker threads) would hit a DB with
    no tables.
    """
    from sqlalchemy import create_engine as ce
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.db import get_session

    test_engine = ce(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def _override_session():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_session] = _override_session
    client = TestClient(app)
    return client


def _create_scored_record(client) -> str:
    """POST /score with a pre-supplied response (no LLM call) and return the id."""
    resp = client.post("/score", json={
        "prompt": "What is 2+2?",
        "response": "It is 4.",
        "model": "default",
        "use_case": "customer_support",
        "session_id": "test-session",
        "latency_ms": 100.0,
    })
    assert resp.status_code == 200, f"Setup failed: {resp.text}"
    return resp.json()["id"]


class TestOverrideEndpoint:

    def setup_method(self):
        self.client = _get_test_client()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_override_allow_persists(self):
        score_id = _create_scored_record(self.client)
        resp = self.client.post(f"/score/{score_id}/override", json={
            "status": "override_allow",
            "reason": "Manager approved",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["override_status"] == "override_allow"
        assert data["severity"] == "pass"
        assert "Manager approved" in data["decision_reason"]

    def test_override_block_persists(self):
        score_id = _create_scored_record(self.client)
        resp = self.client.post(f"/score/{score_id}/override", json={
            "status": "override_block",
            "reason": "Compliance flagged",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["override_status"] == "override_block"
        assert data["severity"] == "block"

    def test_override_none_resets(self):
        score_id = _create_scored_record(self.client)
        # First override to block
        self.client.post(f"/score/{score_id}/override", json={
            "status": "override_block",
            "reason": "temp block",
        })
        # Then reset
        resp = self.client.post(f"/score/{score_id}/override", json={
            "status": "none",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["override_status"] == "none"
        assert data["override_reason"] is None

    def test_override_nonexistent_record_404(self):
        resp = self.client.post("/score/nonexistent-id/override", json={
            "status": "override_allow",
        })
        assert resp.status_code == 404

    def test_override_invalid_status_400(self):
        score_id = _create_scored_record(self.client)
        resp = self.client.post(f"/score/{score_id}/override", json={
            "status": "invalid_status",
        })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 3. MALFORMED-INPUT HANDLING
# ---------------------------------------------------------------------------

class TestMalformedInput:

    def setup_method(self):
        self.client = _get_test_client()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_missing_prompt_field_422(self):
        """POST /score without 'prompt' → Pydantic validation error (422)."""
        resp = self.client.post("/score", json={
            "response": "some response",
        })
        assert resp.status_code == 422

    def test_empty_body_422(self):
        """POST /score with empty JSON body → 422."""
        resp = self.client.post("/score", json={})
        assert resp.status_code == 422

    def test_score_with_presupplied_response_succeeds(self):
        """Baseline: valid request with pre-supplied response should 200
        (no LLM call needed, so no network dependency)."""
        resp = self.client.post("/score", json={
            "prompt": "Hello",
            "response": "Hi there!",
            "model": "default",
            "latency_ms": 50.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["severity"] in ("pass", "edit", "log", "block")

    def test_override_missing_status_field_422(self):
        """POST /override without 'status' field → 422."""
        score_id = _create_scored_record(self.client)
        resp = self.client.post(f"/score/{score_id}/override", json={
            "reason": "no status provided",
        })
        assert resp.status_code == 422
