from app.checks import cost, performance, responsibility
from app import correlation, router


def test_cost_check_basic():
    result = cost.run("hello", "a short reply", "default", recent_costs=[])
    assert result["score"] == 100
    assert result["est_tokens"] > 0


def test_cost_check_flags_spike():
    result = cost.run(
        "hello", "x" * 5000, "default", recent_costs=[0.001, 0.001, 0.001]
    )
    assert "cost_spike" in result["flags"]
    assert result["score"] < 100


def test_responsibility_detects_pii():
    result = responsibility.run("contact me at john.doe@example.com please")
    assert result["pii_found"] is True
    assert result["score"] < 100
    assert "REDACTED_EMAIL" in result["redacted_excerpt"]


def test_responsibility_clean_response():
    result = responsibility.run("The weather today is sunny with a light breeze.")
    assert result["pii_found"] is False
    assert result["score"] == 100


def test_performance_flags_hedging():
    result = performance.run(
        "What is the capital of France?",
        "I'm not sure, I cannot verify this.",
        latency_ms=500,
    )
    assert "hedging_language" in result["flags"]


def test_correlation_cost_confidence_mismatch():
    perf = {"score": 40, "confidence": 0.3, "flags": []}
    cost_result = {"score": 50, "flags": ["cost_spike"]}
    resp = {"score": 100, "pii_found": False, "flags": []}
    result = correlation.run("session-a", perf, cost_result, resp)
    assert "cost_confidence_mismatch" in result["compound_flags"]


def test_router_blocks_on_pii():
    perf = {"score": 90}
    cost_result = {"score": 90}
    resp = {"score": 40, "pii_found": True}
    corr = {"compound_flags": []}
    severity, reason = router.decide(perf, cost_result, resp, corr)
    assert severity == "block"


def test_router_passes_clean_response():
    perf = {"score": 90}
    cost_result = {"score": 90}
    resp = {"score": 95, "pii_found": False}
    corr = {"compound_flags": []}
    severity, reason = router.decide(perf, cost_result, resp, corr)
    assert severity == "pass"


def test_performance_dynamic_budget():
    # Latency 2000ms: over budget of 1500 (customer_support), but within budget of 4000 (internal_knowledge)
    res_strict = performance.run("prompt", "response", latency_ms=2000, latency_budget_ms=1500)
    assert "latency_over_budget" in res_strict["flags"]
    assert res_strict["score"] < 100

    res_relaxed = performance.run("prompt", "response", latency_ms=2000, latency_budget_ms=4000)
    assert "latency_over_budget" not in res_relaxed["flags"]
    assert res_relaxed["score"] == 100


def test_router_use_case_thresholds():
    # Performance score 35. 
    # Under customer_support (block_below=40), this should block.
    # Under internal_knowledge (block_below=25, log_below=60), this should log.
    perf = {"score": 35}
    cost_result = {"score": 90}
    resp = {"score": 95, "pii_found": False}
    corr = {"compound_flags": []}

    sev_strict, reason_strict = router.decide(perf, cost_result, resp, corr, use_case="customer_support")
    assert sev_strict == "block"

    sev_relaxed, reason_relaxed = router.decide(perf, cost_result, resp, corr, use_case="internal_knowledge")
    assert sev_relaxed == "log"
