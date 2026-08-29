"""
Central, tunable configuration for all checks and the severity router.
Keep every magic number here so thresholds can be adjusted during demo
rehearsal without touching check/router logic.
"""

# --- Cost check ---
# $ per 1K tokens, by provider name. These match the two LLM providers
# this app actually supports (see llm_provider.py / LLM_PROVIDER env
# var) — "ollama" is free/local, "gemini" uses Google's published
# per-token rate for gemini-1.5-flash as a rough approximation.
MODEL_COST_PER_1K_TOKENS = {
    "ollama": 0.0,
    "gemini": 0.000075,
    "default": 0.002,  # fallback if an unrecognized name is ever sent
}
COST_SPIKE_MULTIPLIER = 2.5  # flag if cost > rolling_avg * this
COST_ROLLING_WINDOW = 20  # number of recent records used for the rolling average

# --- Responsibility check ---
# Deterministic regex patterns for PII (extend as needed; keep conservative
# to avoid over-flagging in the demo).
PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "card_like": r"\b(?:\d[ -]*?){13,16}\b",
    "national_id": r"\b\d{3}-\d{2}-\d{4}\b",
}

# Restricted-category keyword lists, extensible. This mirrors ethical
# screens used on the finance side (defense, weapons, tobacco, alcohol,
# gambling) but is intentionally generic so the proxy is not finance-only.
RESTRICTED_CATEGORIES = {
    "weapons_defense": ["firearm", "explosive", "weapons-grade", "munitions"],
    "tobacco": ["cigarette brand", "tobacco product"],
    "alcohol": ["liquor brand promotion"],
    "gambling": ["betting odds", "casino promotion"],
}

TOXICITY_KEYWORDS = [
    "kill yourself",
    "hate speech placeholder",
    "slur placeholder",
]

# --- Performance check ---
HEDGE_PHRASES = [
    "i'm not sure",
    "i cannot verify",
    "as an ai",
    "i don't have access",
    "it's difficult to say",
    "i apologize, but",
]

# --- Use Case Policies (dynamic risk tolerances and budgets) ---
USE_CASE_POLICIES = {
    "customer_support": {
        "name": "Customer Support",
        "description": "Fast, public-facing chat. Low latency budget, strict thresholds, aggressive PII/restricted blocks.",
        "latency_budget_ms": 1500,
        "score_block_below": 40,
        "score_log_below": 70,
        "correlation_block_flags": {"latency_pii_correlation", "repeated_compound_escalation"},
        "correlation_log_flags": {"cost_confidence_mismatch"},
    },
    "internal_knowledge": {
        "name": "Internal Knowledge",
        "description": "Employee knowledge assistant. Relaxed latency budget, medium thresholds, flags for review, blocks on PII only.",
        "latency_budget_ms": 4000,
        "score_block_below": 25,
        "score_log_below": 60,
        "correlation_block_flags": {"repeated_compound_escalation"},
        "correlation_log_flags": {"cost_confidence_mismatch", "latency_pii_correlation"},
    },
    "decision_support": {
        "name": "Decision Support",
        "description": "Regulated employee workflow. Heavy auditing, extremely strict risk tolerance. Blocks on any warning or mismatch.",
        "latency_budget_ms": 8000,
        "score_block_below": 50,
        "score_log_below": 80,
        "correlation_block_flags": {"cost_confidence_mismatch", "latency_pii_correlation", "repeated_compound_escalation"},
        "correlation_log_flags": set(),
    }
}

# --- Correlation engine ---
COMPOUND_WINDOW_SECONDS = 120
COMPOUND_REPEAT_THRESHOLD = (
    2  # same session hitting 2+ compound flags in window -> escalate
)
