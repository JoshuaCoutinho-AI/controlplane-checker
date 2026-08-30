import asyncio
import time

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import correlation, main, router
from app.checks import bias, cost, hallucination, performance, responsibility
from app.llm_provider import LLMProviderError
from app.models import Base, FeedbackEntry, ScoredResponse
from app.proxy import score_and_route


def _results():
    return (
        {"score": 90, "confidence": 0.9, "flags": []},
        {"score": 90, "flags": []},
        {"score": 95, "pii_found": False, "flags": []},
        {"score": 95, "flags": []},
        {"score": 95, "flags": []},
    )


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_cost_check_basic():
    result = cost.run("hello", "a short reply", "default", recent_costs=[])
    assert result["score"] == 100
    assert result["est_tokens"] > 0


def test_cost_check_flags_spike():
    result = cost.run("hello", "x" * 5000, "default", [0.001, 0.001, 0.001])
    assert "cost_spike" in result["flags"]
    assert result["score"] < 100


def test_responsibility_detects_pii():
    result = responsibility.run("contact john.doe@example.com please")
    assert result["pii_found"] is True
    assert "REDACTED_EMAIL" in result["redacted_excerpt"]


def test_responsibility_flags_real_toxicity_pattern():
    result = responsibility.run("You should die because nobody wants you.")
    assert "toxicity_keyword" in result["flags"]
    assert result["toxicity"] > 0


def test_responsibility_clean_response():
    assert responsibility.run("Sunny with a light breeze.")["score"] == 100


def test_geography_changes_pii_outcome():
    response = "The source IP was 203.0.113.8."
    assert responsibility.run(response, "US")["pii_found"] is False
    assert responsibility.run(response, "EU")["pii_found"] is True


def test_bias_flags_protected_group_generalization():
    result = bias.run("Women are always bad at technical work.")
    assert "stereotyping_gender" in result["flags"]
    assert result["score"] < 100


def test_bias_does_not_flag_neutral_or_positive_statements():
    examples = [
        "Black people are valued colleagues.",
        "Asian applicants are welcome on the team.",
        "Women are capable of doing any job men can do.",
        "Men are equally entitled to parental leave.",
        "Muslims are welcome in this workplace.",
        "Christians are represented in the community report.",
        "Russian people are invited to the event.",
        "Indian employees are included in the survey.",
        "Older people are experienced mentors.",
        "Young people are represented on the advisory board.",
        "Disabled people are valued team members.",
        "Blind people are supported with accessible materials.",
    ]
    for response in examples:
        assert bias.run(response)["flags"] == [], response


def test_bias_flags_actual_stereotypes_per_category():
    examples = {
        "race_ethnicity": "Black people are naturally less capable.",
        "gender": "Women are bad at math.",
        "religion": "Muslims cannot be trusted.",
        "nationality": "Russian people are always dishonest.",
        "age": "Older people are worse at learning technology.",
        "disability": "Disabled people should not be trusted with responsibility.",
    }
    for category, response in examples.items():
        assert f"stereotyping_{category}" in bias.run(response)["flags"]


def test_hallucination_judge_flags_verified_fabrication(monkeypatch):
    monkeypatch.setattr(hallucination, "HALLUCINATION_LLM_JUDGE_ENABLED", True)
    monkeypatch.setattr(hallucination, "has_configured_provider", lambda provider: True)
    monkeypatch.setattr(
        hallucination,
        "generate_response",
        lambda *args: (
            '{"fabricated_claims": ["Ada Lovelace won 95% in 2024"], '
            '"person_claims": ["Ada Lovelace won 95% in 2024"], "confidence": 0.9}',
            1.0,
        ),
    )
    result = asyncio.run(
        hallucination.run(
            "The product launched in 2020.", "Ada Lovelace won 95% in 2024."
        )
    )
    assert "judge_verified_fabricated_claim" in result["flags"]
    assert "judge_verified_fabricated_person_claim" in result["flags"]
    assert result["score"] == 55


def test_hallucination_does_not_penalize_accurate_detailed_answer(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(hallucination, "HALLUCINATION_LLM_JUDGE_ENABLED", False)
    db = _session(tmp_path)
    record = asyncio.run(
        score_and_route(
            db,
            "Tell me about the Eiffel Tower.",
            (
                "The Eiffel Tower, designed by Gustave Eiffel, opened on March 31, "
                "1889 in Paris, France, for the World Fair. It stands 330 meters tall."
            ),
            measured_latency_ms=100,
        )
    )
    assert record.hallucination["score"] == 100
    assert record.severity != "block"


def test_hallucination_judge_falls_back_when_provider_errors(monkeypatch):
    def unavailable(*args, **kwargs):
        raise LLMProviderError("offline")

    monkeypatch.setattr(hallucination, "HALLUCINATION_LLM_JUDGE_ENABLED", True)
    monkeypatch.setattr(hallucination, "generate_response", unavailable)
    result = asyncio.run(hallucination.run("Context", "A response."))
    assert "hallucination_check_unavailable_no_provider" in result["flags"]
    assert result["judge_used"] is False


def test_hallucination_judge_falls_back_when_provider_times_out(monkeypatch):
    def slow_provider(*args, **kwargs):
        time.sleep(0.05)
        return '{"unsupported_claims": [], "confidence": 0}', 1.0

    monkeypatch.setattr(hallucination, "HALLUCINATION_LLM_JUDGE_ENABLED", True)
    monkeypatch.setattr(hallucination, "HALLUCINATION_LLM_JUDGE_TIMEOUT_SECONDS", 0.001)
    monkeypatch.setattr(hallucination, "generate_response", slow_provider)
    result = asyncio.run(hallucination.run("Context", "A response."))
    assert "hallucination_check_unavailable_no_provider" in result["flags"]


def test_performance_flags_hedging():
    result = performance.run("Capital?", "I'm not sure, I cannot verify this.", 500)
    assert "hedging_language" in result["flags"]


def test_correlation_cost_confidence_mismatch(tmp_path):
    db = _session(tmp_path)
    perf, cost_result, resp, bias_result, hallucination_result = _results()
    perf["confidence"] = 0.3
    cost_result["flags"] = ["cost_spike"]
    result = correlation.run(
        db, "session-a", perf, cost_result, resp, bias_result, hallucination_result
    )
    assert "cost_confidence_mismatch" in result["compound_flags"]


def test_correlation_flags_hallucinated_person_with_pii(tmp_path):
    db = _session(tmp_path)
    perf, cost_result, resp, bias_result, hallucination_result = _results()
    resp["pii_found"] = True
    hallucination_result["flags"] = ["judge_verified_fabricated_person_claim"]
    result = correlation.run(
        db, "session-a", perf, cost_result, resp, bias_result, hallucination_result
    )
    assert "hallucination_pii_person_correlation" in result["compound_flags"]


def test_correlation_history_is_db_backed(tmp_path):
    db = _session(tmp_path)
    db.add(
        ScoredResponse(
            session_id="session-a",
            model="default",
            use_case="customer_support",
            prompt_excerpt="prompt",
            response_excerpt="response",
            performance={},
            cost={},
            responsibility={},
            bias={},
            hallucination={},
            correlation={"compound_flags": ["cost_confidence_mismatch"]},
        )
    )
    db.commit()
    perf, cost_result, resp, bias_result, hallucination_result = _results()
    perf["confidence"] = 0.3
    cost_result["flags"] = ["cost_spike"]
    result = correlation.run(
        db, "session-a", perf, cost_result, resp, bias_result, hallucination_result
    )
    assert "repeated_compound_escalation" in result["compound_flags"]


def test_router_blocks_on_pii():
    perf, cost_result, resp, bias_result, hallucination_result = _results()
    resp["pii_found"] = True
    resp["flags"] = ["toxicity_keyword"]
    severity, _ = router.decide(
        perf,
        cost_result,
        resp,
        bias_result,
        hallucination_result,
        {"compound_flags": []},
    )
    assert severity == "block"


def test_router_edits_isolated_pii_and_returns_redaction(tmp_path):
    response = "Contact ava@example.com for help."
    responsibility_result = responsibility.run(response)
    perf, cost_result, _, bias_result, hallucination_result = _results()
    severity, _ = router.decide(
        perf,
        cost_result,
        responsibility_result,
        bias_result,
        hallucination_result,
        {"compound_flags": []},
    )
    assert severity == "edit"
    db = _session(tmp_path)
    record = asyncio.run(
        score_and_route(db, "Need contact", response, measured_latency_ms=1)
    )
    assert record.severity == "edit"
    assert record.to_payload()["response"] == "Contact [REDACTED_EMAIL] for help."


def test_router_passes_clean_response():
    perf, cost_result, resp, bias_result, hallucination_result = _results()
    severity, _ = router.decide(
        perf,
        cost_result,
        resp,
        bias_result,
        hallucination_result,
        {"compound_flags": []},
    )
    assert severity == "pass"


def test_performance_dynamic_budget():
    strict = performance.run(
        "prompt", "response", latency_ms=2000, latency_budget_ms=1500
    )
    relaxed = performance.run(
        "prompt", "response", latency_ms=2000, latency_budget_ms=4000
    )
    assert "latency_over_budget" in strict["flags"]
    assert "latency_over_budget" not in relaxed["flags"]
    assert relaxed["score"] == 85


def test_router_use_case_thresholds():
    perf, cost_result, resp, bias_result, hallucination_result = _results()
    perf["score"] = 35
    strict, _ = router.decide(
        perf,
        cost_result,
        resp,
        bias_result,
        hallucination_result,
        {"compound_flags": []},
        "customer_support",
    )
    relaxed, _ = router.decide(
        perf,
        cost_result,
        resp,
        bias_result,
        hallucination_result,
        {"compound_flags": []},
        "internal_knowledge",
    )
    assert strict == "block"
    assert relaxed == "log"


def test_feedback_endpoint_persists_override(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'feedback.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    record = ScoredResponse(
        model="default",
        use_case="customer_support",
        prompt_excerpt="prompt",
        response_excerpt="response",
        performance={},
        cost={},
        responsibility={},
        bias={},
        hallucination={},
        correlation={},
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    def get_test_session():
        test_db = factory()
        try:
            yield test_db
        finally:
            test_db.close()

    monkeypatch.setattr(main, "init_db", lambda: None)
    main.app.dependency_overrides[main.get_session] = get_test_session
    try:
        with TestClient(main.app) as client:
            response = client.post(
                f"/feedback/{record.id}",
                json={"override": "false_positive", "note": "Expected exception"},
            )
        assert response.status_code == 200
        assert response.json()["feedback"][0]["override"] == "false_positive"
        assert db.query(FeedbackEntry).count() == 1
    finally:
        main.app.dependency_overrides.clear()
        db.close()


def test_override_preserves_original_decision(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'override.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    record = ScoredResponse(
        model="default",
        use_case="customer_support",
        prompt_excerpt="prompt",
        response_excerpt="response",
        performance={},
        cost={},
        responsibility={},
        bias={},
        hallucination={},
        correlation={},
        severity="block",
        decision_reason="PII found",
        original_severity="block",
        original_decision_reason="PII found",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    def get_test_session():
        test_db = factory()
        try:
            yield test_db
        finally:
            test_db.close()

    monkeypatch.setattr(main, "init_db", lambda: None)
    main.app.dependency_overrides[main.get_session] = get_test_session
    try:
        with TestClient(main.app) as client:
            response = client.post(
                f"/score/{record.id}/override",
                json={"status": "override_allow", "reason": "Verified exception"},
            )
        payload = response.json()
        assert response.status_code == 200
        assert payload["severity"] == "pass"
        assert payload["original_severity"] == "block"
        assert payload["original_decision_reason"] == "PII found"
    finally:
        main.app.dependency_overrides.clear()
        db.close()


def test_metrics_reports_feedback_rates(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'metrics.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    records = []
    for severity in ("block", "block", "pass", "edit"):
        record = ScoredResponse(
            model="default",
            use_case="customer_support",
            prompt_excerpt="prompt",
            response_excerpt="response",
            performance={},
            cost={},
            responsibility={},
            bias={},
            hallucination={},
            correlation={},
            severity=severity,
            original_severity=severity,
        )
        db.add(record)
        records.append(record)
    db.commit()
    db.add_all(
        [
            FeedbackEntry(response_id=records[0].id, override="false_positive"),
            FeedbackEntry(response_id=records[1].id, override="correct"),
            FeedbackEntry(response_id=records[2].id, override="false_negative"),
        ]
    )
    db.commit()

    def get_test_session():
        test_db = factory()
        try:
            yield test_db
        finally:
            test_db.close()

    monkeypatch.setattr(main, "init_db", lambda: None)
    main.app.dependency_overrides[main.get_session] = get_test_session
    try:
        with TestClient(main.app) as client:
            payload = client.get("/metrics").json()
        assert payload["total_scored_responses"] == 4
        assert payload["total_feedback_entries"] == 3
        assert payload["feedback_coverage_percent"] == 75.0
        assert payload["false_positive_rate"] == 1 / 3
        assert payload["false_negative_rate"] == 1 / 3
        assert payload["by_severity"]["block"]["false_positive_rate"] == 0.5
    finally:
        main.app.dependency_overrides.clear()
        db.close()
