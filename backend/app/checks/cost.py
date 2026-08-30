"""
Deterministic cost check. No model call required — pure heuristics on
text length plus a rolling average of recent costs for spike detection.
"""

from app.config import MODEL_COST_PER_1K_TOKENS, COST_SPIKE_MULTIPLIER


def estimate_tokens(text: str) -> int:
    """Cheap heuristic tokenizer: ~4 chars per token (English-text average).
    This is commonly about +/-15-20% inaccurate for English and worse for
    code or non-English text. Kept dependency-free so it never blocks demo
    scoring on a missing optional tokenizer."""
    return max(1, len(text) // 4)


def run(prompt: str, response: str, model: str, recent_costs: list[float]) -> dict:
    tokens = estimate_tokens(prompt) + estimate_tokens(response)
    rate = MODEL_COST_PER_1K_TOKENS.get(model, MODEL_COST_PER_1K_TOKENS["default"])
    est_cost_usd = round((tokens / 1000) * rate, 6)

    flags = []
    if recent_costs:
        rolling_avg = sum(recent_costs) / len(recent_costs)
        if rolling_avg > 0 and est_cost_usd > rolling_avg * COST_SPIKE_MULTIPLIER:
            flags.append("cost_spike")

    # Score: 100 if well within normal range, degrading toward 0 the
    # further this response's cost is above the rolling average.
    score = 100
    if recent_costs:
        rolling_avg = sum(recent_costs) / len(recent_costs)
        if rolling_avg > 0:
            overage_ratio = max(0.0, (est_cost_usd - rolling_avg) / rolling_avg)
            score = max(0, round(100 - min(overage_ratio, 1.0) * 100))

    return {
        "score": score,
        "est_tokens": tokens,
        "est_cost_usd": est_cost_usd,
        "flags": flags,
    }
