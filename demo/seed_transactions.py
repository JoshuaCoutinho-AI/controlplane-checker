"""
Demo seed script: fires a burst of mixed good/bad/borderline
prompt-response pairs through the running proxy so the live dashboard
has something to show within ~60 seconds of running it.

Usage (with the stack already up via docker compose, or backend running
locally on :8000):

    python demo/seed_transactions.py
    python demo/seed_transactions.py --url http://localhost:8000 --delay 1.5
"""
import argparse
import time
import urllib.request
import json

SAMPLES = [
    # clean, healthy responses -> should PASS
    {
        "prompt": "What's the weather like for outdoor filming today?",
        "response": "Clear skies expected, light breeze around 10 km/h, good conditions for filming.",
        "model": "gemini",
    },
    {
        "prompt": "Summarize the Q3 revenue trend in two sentences.",
        "response": "Q3 revenue grew 8% quarter-over-quarter, driven mainly by the enterprise segment. Margins held steady despite the growth.",
        "model": "gemini",
    },
    # hedging / low-confidence -> should LOG
    {
        "prompt": "What is the exact number of active users last month?",
        "response": "I'm not sure, I cannot verify this, it's difficult to say without access to the dashboard.",
        "model": "gemini",
    },
    # PII leak -> should BLOCK
    {
        "prompt": "Give me the support contact for this ticket.",
        "response": "Please reach out to john.doe@example.com or call 415-555-0199 for follow-up.",
        "model": "gemini",
    },
    # expensive + low confidence -> should trigger cost_confidence_mismatch correlation
    {
        "prompt": "Explain the entire distributed systems literature in exhaustive detail.",
        "response": (
            "I'm not sure I can cover this fully, it's difficult to say where to start. " * 40
        ),
        "model": "gemini",
    },
    # restricted category mention -> should LOG/BLOCK depending on severity
    {
        "prompt": "Draft ad copy for our client's new product line.",
        "response": "Try our new casino promotion this weekend — betting odds have never been better!",
        "model": "gemini",
    },
    # normal, healthy again
    {
        "prompt": "Draft a one-line status update for the team standup.",
        "response": "Backend checks are implemented and passing tests; frontend dashboard wired to live feed.",
        "model": "gemini",
    },
]


def post_score(base_url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/score", data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Seed the ControlPlane Checker proxy with demo traffic.")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds between requests")
    parser.add_argument("--loops", type=int, default=1, help="How many times to loop through the sample set")
    args = parser.parse_args()

    print(f"Seeding {args.url} with {len(SAMPLES)} sample(s) x {args.loops} loop(s)...")
    for loop in range(args.loops):
        for i, sample in enumerate(SAMPLES):
            payload = {**sample, "session_id": f"demo-session-{loop}"}
            try:
                result = post_score(args.url, payload)
                print(
                    f"[{loop}.{i}] severity={result['severity']:<5} "
                    f"perf={result['checks']['performance']['score']:<3} "
                    f"cost={result['checks']['cost']['score']:<3} "
                    f"resp={result['checks']['responsibility']['score']:<3} "
                    f"compound={result['correlation']['compound_flags']}"
                )
            except Exception as exc:
                print(f"[{loop}.{i}] FAILED: {exc}")
            time.sleep(args.delay)

    print("Done. Open the dashboard to see the live feed.")


if __name__ == "__main__":
    main()
