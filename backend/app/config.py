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
LATENCY_BUDGET_MS = 2500
HEDGE_PHRASES = [
    "i'm not sure",
    "i cannot verify",
    "as an ai",
    "i don't have access",
    "it's difficult to say",
    "i apologize, but",
]

# --- Severity router thresholds (0-100 scale, higher = healthier) ---
SCORE_BLOCK_BELOW = 30  # any single check below this -> critical
SCORE_LOG_BELOW = 65  # any single check below this -> log
CORRELATION_BLOCK_FLAGS = {"latency_pii_correlation", "repeated_compound_escalation"}
CORRELATION_LOG_FLAGS = {"cost_confidence_mismatch"}

# --- Correlation engine ---
COMPOUND_WINDOW_SECONDS = 120
COMPOUND_REPEAT_THRESHOLD = (
    2  # same session hitting 2+ compound flags in window -> escalate
)
