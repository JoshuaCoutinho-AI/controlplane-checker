"""
Performance check: measured latency plus a deterministic confidence
heuristic (hedge-phrase detection, repetition ratio, length-vs-prompt
sanity). Deliberately avoids a second model call so it stays fast and
demo-reliable, per the build plan (Section 3.2).
"""

from app.config import HEDGE_PHRASES


def _repetition_ratio(text: str) -> float:
    words = text.lower().split()
    if len(words) < 4:
        return 0.0
    unique = len(set(words))
    return 1.0 - (unique / len(words))


def _confidence_heuristic(prompt: str, response: str) -> tuple[float, list[str]]:
    flags = []
    lowered = response.lower()

    hedge_hits = sum(1 for phrase in HEDGE_PHRASES if phrase in lowered)
    if hedge_hits:
        flags.append("hedging_language")

    repetition = _repetition_ratio(response)
    if repetition > 0.5:
        flags.append("high_repetition")

    too_short = len(response.strip()) < max(10, len(prompt.strip()) // 10)
    if too_short:
        flags.append("response_too_short")

    confidence = 1.0
    confidence -= min(0.4, hedge_hits * 0.15)
    confidence -= min(0.4, max(0.0, repetition - 0.3))
    confidence -= 0.3 if too_short else 0.0
    return max(0.0, confidence), flags


def run(
    prompt: str, response: str, latency_ms: float, latency_budget_ms: float = 2500
) -> dict:
    confidence, flags = _confidence_heuristic(prompt, response)

    if latency_ms > latency_budget_ms:
        flags.append("latency_over_budget")

    latency_score = max(0, 100 - int(max(0, latency_ms - latency_budget_ms) / 20))
    confidence_score = int(confidence * 100)
    score = round(0.5 * latency_score + 0.5 * confidence_score)

    return {
        "score": score,
        "latency_ms": round(latency_ms, 1),
        "confidence": round(confidence, 2),
        "flags": flags,
    }
