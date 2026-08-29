"""
Deterministic responsibility check: PII detection, toxicity keyword
heuristic, and restricted-category screen. No model call required.

IMPORTANT (handoff Section 7): this check's own output must never store
raw PII. Callers should persist only the redacted excerpt this module
returns, never the original response text, once PII is found.
"""

import re

from app.config import PII_PATTERNS, RESTRICTED_CATEGORIES, TOXICITY_KEYWORDS

_COMPILED_PII = {name: re.compile(pattern) for name, pattern in PII_PATTERNS.items()}


def redact(text: str) -> str:
    redacted = text
    for name, pattern in _COMPILED_PII.items():
        redacted = pattern.sub(f"[REDACTED_{name.upper()}]", redacted)
    return redacted


def run(response: str) -> dict:
    flags = []
    pii_found = False

    for name, pattern in _COMPILED_PII.items():
        if pattern.search(response):
            pii_found = True
            flags.append(f"pii_{name}")

    lowered = response.lower()
    toxicity_hits = sum(1 for phrase in TOXICITY_KEYWORDS if phrase in lowered)
    toxicity = min(1.0, toxicity_hits * 0.5)
    if toxicity_hits:
        flags.append("toxicity_keyword")

    for category, keywords in RESTRICTED_CATEGORIES.items():
        if any(k in lowered for k in keywords):
            flags.append(f"restricted_category_{category}")

    # Score: start at 100, subtract heavily for PII, moderately for
    # toxicity/restricted content.
    score = 100
    if pii_found:
        score -= 60
    score -= int(toxicity * 30)
    if any(f.startswith("restricted_category_") for f in flags):
        score -= 20
    score = max(0, score)

    return {
        "score": score,
        "pii_found": pii_found,
        "toxicity": round(toxicity, 2),
        "flags": flags,
        # never surface raw response text from this check — only redacted,
        # and full-length (not truncated), so nothing real gets cut off
        "redacted_excerpt": redact(response),
    }
