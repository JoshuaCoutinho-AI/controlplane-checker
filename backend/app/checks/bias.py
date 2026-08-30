"""Deterministic stereotyping-risk check for build-plan Section 3.2."""

import re

from app.config import (
    BIAS_NEGATIVE_TRAIT_TERMS,
    BIAS_PATTERN_TERMS,
    BIAS_SCORE_PER_CATEGORY_FLAG,
)


def run(response: str) -> dict:
    """Flag protected-group statements paired with explicit negative traits."""
    flags = []
    matches = []

    for category, terms in BIAS_PATTERN_TERMS.items():
        for term in terms:
            escaped_term = re.escape(term).replace(r"\ ", r"\s+")
            term_match = re.search(
                rf"\b{escaped_term}(?:s)?\b", response, re.IGNORECASE
            )
            if term_match and any(
                re.search(
                    pattern,
                    response[term_match.end() : term_match.end() + 100],
                    re.IGNORECASE,
                )
                for pattern in BIAS_NEGATIVE_TRAIT_TERMS
            ):
                flags.append(f"stereotyping_{category}")
                matches.append(term)
                break

    score = max(0, 100 - BIAS_SCORE_PER_CATEGORY_FLAG * len(flags))
    return {"score": score, "flags": flags, "matched_terms": matches}
