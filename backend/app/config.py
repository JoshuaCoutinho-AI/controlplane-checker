"""
Central, tunable configuration for all checks and the severity router.
Keep every magic number here so thresholds can be adjusted during demo
rehearsal without touching check/router logic.
"""

import os

from app.llm_provider import has_configured_provider

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
GEOGRAPHY_POLICIES = {
    # Illustrative policy toggles, not legal determinations.
    "US": {"additional_pii_patterns": {}},
    "EU": {"additional_pii_patterns": {"ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b"}},
    "APAC": {"additional_pii_patterns": {}},
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

# Fast pre-filter only: pattern matching is an indicator for review, not a
# complete toxicity classifier. Terms intentionally avoid enumerating slurs.
TOXICITY_KEYWORDS = [
    r"\b(?:go|please)\s+(?:die|disappear|hurt yourself)\b",
    r"\b(?:i(?:'ll| will)|we(?:'ll| will))\s+(?:hurt|kill|destroy|ruin)\s+(?:you|them)\b",
    r"\b(?:you|they)\s+(?:should|deserve to)\s+(?:die|be hurt|suffer)\b",
    r"\b(?:i hope)\s+(?:you|they)\s+(?:die|get hurt|suffer)\b",
    r"\b(?:shut up|nobody wants you|you are worthless|you are useless)\b",
    r"\b(?:everyone|all people)\s+(?:hate|should hate|must avoid)\s+(?:you|them)\b",
    r"\b(?:they|those people)\s+are\s+(?:animals|vermin|subhuman|a disease)\b",
    r"\b(?:get out|go back)\s+(?:where you came from|to your country)\b",
    r"\b(?:harass|bully|intimidate|humiliate)\s+(?:them|him|her|you)\b",
    r"\b(?:make them|make him|make her)\s+(?:afraid|suffer|cry)\b",
    r"\b(?:you|they)\s+(?:do not deserve|should not have)\s+(?:to live|rights|a job)\b",
    r"\b(?:attack|assault|beat up)\s+(?:them|him|her|you)\b",
]

# Protected-characteristic vocabulary for deterministic stereotyping checks.
# Each category has enough common, non-slur terms to catch broad
# generalisations without importing an NLP dependency.
BIAS_PATTERN_TERMS = {
    "race_ethnicity": [
        "black",
        "white",
        "asian",
        "latino",
        "latina",
        "hispanic",
        "arab",
        "middle eastern",
        "indigenous",
        "native american",
        "pacific islander",
        "south asian",
        "east asian",
        "african",
        "european",
        "roma",
        "jewish",
        "irish",
        "mexican",
        "chinese",
    ],
    "gender": [
        "women",
        "woman",
        "men",
        "man",
        "girls",
        "boys",
        "female",
        "male",
        "nonbinary",
        "non-binary",
        "transgender",
        "trans",
        "cisgender",
        "cis",
        "mother",
        "father",
        "wife",
        "husband",
        "feminine",
        "masculine",
    ],
    "religion": [
        "muslim",
        "christian",
        "jewish",
        "hindu",
        "buddhist",
        "sikh",
        "atheist",
        "catholic",
        "protestant",
        "evangelical",
        "mormon",
        "jain",
        "bahai",
        "religious",
        "islamic",
        "faithful",
        "orthodox",
        "secular",
        "pagan",
        "quaker",
    ],
    "nationality": [
        "american",
        "indian",
        "pakistani",
        "russian",
        "ukrainian",
        "german",
        "french",
        "british",
        "japanese",
        "korean",
        "nigerian",
        "kenyan",
        "brazilian",
        "canadian",
        "australian",
        "italian",
        "spanish",
        "turkish",
        "iranian",
        "syrian",
    ],
    "age": [
        "elderly",
        "older people",
        "seniors",
        "senior citizens",
        "young people",
        "teenagers",
        "teens",
        "children",
        "kids",
        "adolescents",
        "millennials",
        "gen z",
        "generation z",
        "gen x",
        "baby boomers",
        "boomer",
        "minors",
        "retirees",
        "middle-aged",
        "youth",
    ],
    "disability": [
        "disabled",
        "people with disabilities",
        "wheelchair users",
        "blind people",
        "deaf people",
        "autistic people",
        "people with autism",
        "neurodivergent people",
        "people with mental illness",
        "people with depression",
        "people with anxiety",
        "people with dyslexia",
        "people with adhd",
        "people with dementia",
        "amputees",
        "people with chronic illness",
        "people with epilepsy",
        "people with down syndrome",
        "people with learning disabilities",
        "hearing impaired",
    ],
}
BIAS_NEGATIVE_TRAIT_TERMS = [
    r"\bbad at\b",
    r"\bworse at\b",
    r"\b(?:cannot|can't)\s+(?:be|do|learn|lead|work|understand)\b",
    r"\b(?:should not|shouldn't)\s+be\s+trusted\b",
    r"\bnaturally\s+less\s+(?:capable|intelligent|competent)\b",
    r"\balways\s+(?:lazy|dishonest|dangerous|inferior|unreliable)\b",
    r"\bnever\s+(?:capable|qualified|reliable|productive)\b",
    r"\b(?:less intelligent|less capable|inferior|unfit|dangerous|dishonest)\b",
    r"\bdo not belong\b",
    r"\bshould be avoided\b",
    r"\bnot suited for\b",
    r"\btoo emotional\b",
    r"\bcriminal by nature\b",
]
BIAS_SCORE_PER_CATEGORY_FLAG = 25

# --- Hallucination check ---
# Heuristics compare factual-looking claims with the supplied prompt/context.
# They are indicators, not proof: a prompt may omit valid shared context.
HALLUCINATION_NUMBER_PATTERN = r"\b\d+(?:\.\d+)?%?\b"
HALLUCINATION_DATE_PATTERN = (
    r"\b(?:19|20)\d{2}\b|\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|"
    r"apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|"
    r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:,\s*\d{4})?\b"
)
HALLUCINATION_CITATION_PATTERN = (
    r"(?:\[[^\]]{1,80}\]|\b(?:according to|source:|doi:)\b)"
)
HALLUCINATION_PROPER_NOUN_PATTERN = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b"
HALLUCINATION_NON_PERSON_ENTITY_ENDINGS = {
    "tower",
    "fair",
    "university",
    "company",
    "bridge",
    "museum",
    "building",
    "river",
    "city",
    "park",
    "airport",
    "station",
    "library",
}
HALLUCINATION_LLM_JUDGE_ENABLED = os.getenv(
    "HALLUCINATION_LLM_JUDGE_ENABLED",
    "true" if has_configured_provider() else "false",
).lower() in {"1", "true", "yes"}
HALLUCINATION_LLM_JUDGE_TIMEOUT_SECONDS = 8

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
        "geography": "US",
        "description": "Fast, public-facing chat. Low latency budget, strict thresholds, aggressive PII/restricted blocks.",
        "latency_budget_ms": 1500,
        "score_block_below": 40,
        "score_log_below": 70,
        "correlation_block_flags": {
            "latency_pii_correlation",
            "hallucination_pii_person_correlation",
            "repeated_compound_escalation",
        },
        "correlation_log_flags": {"cost_confidence_mismatch"},
    },
    "internal_knowledge": {
        "name": "Internal Knowledge",
        "geography": "EU",
        "description": "Employee knowledge assistant. Relaxed latency budget, medium thresholds, flags for review, blocks on PII only.",
        "latency_budget_ms": 4000,
        "score_block_below": 25,
        "score_log_below": 60,
        "correlation_block_flags": {"repeated_compound_escalation"},
        "correlation_log_flags": {
            "cost_confidence_mismatch",
            "latency_pii_correlation",
            "hallucination_pii_person_correlation",
        },
    },
    "decision_support": {
        "name": "Decision Support",
        "geography": "APAC",
        "description": "Regulated employee workflow. Heavy auditing, extremely strict risk tolerance. Blocks on any warning or mismatch.",
        "latency_budget_ms": 8000,
        "score_block_below": 50,
        "score_log_below": 80,
        "correlation_block_flags": {
            "cost_confidence_mismatch",
            "latency_pii_correlation",
            "hallucination_pii_person_correlation",
            "repeated_compound_escalation",
        },
        "correlation_log_flags": set(),
    },
}

# --- Correlation engine ---
COMPOUND_WINDOW_SECONDS = 120
COMPOUND_REPEAT_THRESHOLD = (
    2  # same session hitting 2+ compound flags in window -> escalate
)
