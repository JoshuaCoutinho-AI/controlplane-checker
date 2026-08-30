"""Hallucination check for build-plan Section 3.2.

Regexes only surface claims worth reviewing. They cannot establish truth, so
only a bounded LLM judge may lower the score or emit routing-risk flags.
"""

import asyncio
import json
import re

from app.config import (
    HALLUCINATION_CITATION_PATTERN,
    HALLUCINATION_DATE_PATTERN,
    HALLUCINATION_LLM_JUDGE_ENABLED,
    HALLUCINATION_LLM_JUDGE_TIMEOUT_SECONDS,
    HALLUCINATION_NON_PERSON_ENTITY_ENDINGS,
    HALLUCINATION_NUMBER_PATTERN,
    HALLUCINATION_PROPER_NOUN_PATTERN,
)
from app.llm_provider import (
    LLMProviderError,
    generate_response,
    has_configured_provider,
)

_NUMBER_RE = re.compile(HALLUCINATION_NUMBER_PATTERN)
_DATE_RE = re.compile(HALLUCINATION_DATE_PATTERN, re.IGNORECASE)
_CITATION_RE = re.compile(HALLUCINATION_CITATION_PATTERN, re.IGNORECASE)
_PROPER_NOUN_RE = re.compile(HALLUCINATION_PROPER_NOUN_PATTERN)


def _missing_values(pattern: re.Pattern, prompt: str, response: str) -> list[str]:
    prompt_values = {match.group(0).lower() for match in pattern.finditer(prompt)}
    return [
        match.group(0)
        for match in pattern.finditer(response)
        if match.group(0).lower() not in prompt_values
    ]


def _heuristic_result(prompt: str, response: str) -> dict:
    """Generate candidate claims, never a factual verdict."""
    candidates = []
    for label, pattern in (
        ("number", _NUMBER_RE),
        ("date", _DATE_RE),
        ("citation", _CITATION_RE),
    ):
        candidates.extend(
            {"type": label, "text": value}
            for value in _missing_values(pattern, prompt, response)[:3]
        )

    entities = [
        value
        for value in _missing_values(_PROPER_NOUN_RE, prompt, response)
        if value.rsplit(" ", 1)[-1].lower()
        not in HALLUCINATION_NON_PERSON_ENTITY_ENDINGS
    ]
    candidates.extend(
        {"type": "possible_person_or_entity", "text": value} for value in entities[:3]
    )
    return {
        "score": 100,
        "flags": [],
        "claims_not_grounded_in_prompt": candidates,
        "verified_fabricated_claims": [],
        "judge_used": False,
        "judge_confidence": None,
    }


def _judge_prompt(prompt: str, response: str, candidates: list[dict]) -> str:
    return (
        "Evaluate only the listed candidate claims. Identify claims that are actually "
        "false or fabricated, not claims that are merely absent from the prompt. "
        "For any fabricated person claim, include its exact text in person_claims. "
        'Answer with JSON only: {"fabricated_claims": ["..."], '
        '"person_claims": ["..."], "confidence": 0.0}.\n\n'
        f"Prompt/context:\n{prompt}\n\nResponse:\n{response}\n\n"
        f"Candidate claims:\n{json.dumps(candidates)}"
    )


def _parse_judge_result(text: str) -> tuple[list[str], list[str], float]:
    start = text.find("{")
    end = text.rfind("}") + 1
    data = json.loads(text[start:end])
    claims = data.get("fabricated_claims", [])
    person_claims = data.get("person_claims", [])
    confidence = float(data.get("confidence", 0))
    if not isinstance(claims, list) or not isinstance(person_claims, list):
        raise ValueError("judge claims were not lists")
    return (
        [str(claim) for claim in claims],
        [str(claim) for claim in person_claims],
        max(0.0, min(1.0, confidence)),
    )


async def run(prompt: str, response: str, provider: str | None = None) -> dict:
    """Return neutral candidates or a judge-verified fabrication assessment."""
    result = _heuristic_result(prompt, response)
    if not HALLUCINATION_LLM_JUDGE_ENABLED:
        return result
    if not has_configured_provider(provider):
        result["flags"].append("hallucination_check_unavailable_no_provider")
        return result

    try:
        judge_text, _ = await asyncio.wait_for(
            asyncio.to_thread(
                generate_response,
                _judge_prompt(
                    prompt, response, result["claims_not_grounded_in_prompt"]
                ),
                provider,
            ),
            timeout=HALLUCINATION_LLM_JUDGE_TIMEOUT_SECONDS,
        )
        claims, person_claims, confidence = _parse_judge_result(judge_text)
    except (asyncio.TimeoutError, LLMProviderError, ValueError, json.JSONDecodeError):
        result["flags"].append("hallucination_check_unavailable_no_provider")
        return result

    result["judge_used"] = True
    result["judge_confidence"] = round(confidence, 2)
    if claims:
        result["flags"].append("judge_verified_fabricated_claim")
        result["verified_fabricated_claims"] = list(dict.fromkeys(claims))
        if set(person_claims) & set(claims):
            result["flags"].append("judge_verified_fabricated_person_claim")
        result["score"] = max(0, 100 - int(confidence * 50))
    return result
