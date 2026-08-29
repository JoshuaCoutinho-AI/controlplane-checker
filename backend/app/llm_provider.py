"""
Pluggable LLM provider used to actually generate a response for a given
prompt when the caller doesn't supply one. Two providers are supported:

  - "ollama": local, free, no API key, no internet dependency at demo
    time — the safer choice for a live demo where venue wifi is a risk.
    Requires Ollama running locally (https://ollama.com) with a model
    pulled, e.g. `ollama pull llama3.2`.
  - "gemini": Google's Gemini API. Needs GEMINI_API_KEY set and an
    internet connection at demo time; generally higher-quality output.

Which provider is used is chosen PER REQUEST — the caller (main.py)
passes the value straight from the frontend's model dropdown. The
LLM_PROVIDER env var only supplies the default when a request doesn't
specify one (e.g. a direct API call from something other than the
dashboard). This means switching providers in the running app is just
picking a different dropdown option — no .env edit or restart needed.

Both raise LLMProviderError on failure so the caller can decide how to
handle it (return a clear error to the client) rather than crashing the
request. No extra pip dependency is required — both providers are
called with the standard library's urllib, since they're plain HTTP
JSON APIs.
"""

import os
import time
import json
import urllib.request
import urllib.error


class LLMProviderError(Exception):
    pass


VALID_PROVIDERS = ("ollama", "gemini")

# Only used as the fallback when a request doesn't specify a provider.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")


def _generate_ollama(prompt: str) -> str:
    url = f"{OLLAMA_HOST}/api/generate"
    payload = json.dumps(
        {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    ).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            return (data.get("response") or "").strip()
    except urllib.error.URLError as exc:
        raise LLMProviderError(
            f"Could not reach Ollama at {OLLAMA_HOST} ({exc}). "
            f"Is `ollama serve` running and is the '{OLLAMA_MODEL}' model pulled?"
        ) from exc
    except Exception as exc:
        raise LLMProviderError(f"Ollama generation failed: {exc}") from exc


def _generate_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise LLMProviderError(
            "GEMINI_API_KEY is not set. Add it to your .env, or pick 'ollama' instead."
        )
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="ignore")
        raise LLMProviderError(f"Gemini API returned {exc.code}: {body[:300]}") from exc
    except urllib.error.URLError as exc:
        raise LLMProviderError(
            f"Could not reach Gemini API ({exc}). Check your internet connection."
        ) from exc
    except (KeyError, IndexError) as exc:
        raise LLMProviderError(f"Unexpected Gemini response shape: {exc}") from exc


def generate_response(prompt: str, provider: str | None = None) -> tuple[str, float]:
    """Generate a real LLM response for `prompt`.

    `provider` picks which backend to call for THIS request — pass the
    value straight from the frontend's dropdown ("ollama" or "gemini").
    If omitted, falls back to the LLM_PROVIDER env var's default.

    Returns (response_text, latency_ms). Raises LLMProviderError on
    failure — callers should surface this as a clear error rather than
    silently falling back to a different provider.
    """
    chosen = (provider or LLM_PROVIDER).lower()
    if chosen not in VALID_PROVIDERS:
        raise LLMProviderError(
            f"Unknown provider '{chosen}' — use one of {VALID_PROVIDERS}."
        )

    start = time.perf_counter()
    if chosen == "gemini":
        text = _generate_gemini(prompt)
    else:
        text = _generate_ollama(prompt)
    latency_ms = (time.perf_counter() - start) * 1000

    if not text:
        raise LLMProviderError(f"{chosen} returned an empty response.")
    return text, latency_ms
