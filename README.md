# ControlPlane Checker

**Team DLS &middot; Accenture Innovation Challenge 2026**

AI deployments fail silently — wrong, expensive, or unsafe — and teams find out only after the
damage is done. ControlPlane Checker is a model-agnostic proxy that scores every LLM response live
across three dimensions (**performance**, **cost**, **responsibility**), correlates those signals to
catch compound failures single-metric tools miss, and routes each response by severity
(**pass / log / block**) before it reaches the end user — with a live dashboard showing it all happen.

See [`ControlPlane_Checker_Build_Plan.pdf`](./ControlPlane_Checker_Build_Plan.pdf) for the full
technical spec, data contracts, correlation rules, and day-by-day build timeline.

## Quick start (under 5 minutes)

```bash
git clone https://github.com/JoshuaCoutinho-AI/controlplane-checker.git
cd controlplane-checker
git checkout dev
docker compose up --build
```

- Backend: http://localhost:8000/health → `{"status":"ok"}`
- Frontend: http://localhost:5173 → dashboard renders, live feed connects automatically
- No `.env` required for demo mode. Copy `.env.example` → `.env` only if wiring a real LLM key.

Branch off `dev` for feature work: `git checkout -b feat/your-feature`

## See it work

**Option A — seed script.** With the stack running, fire a burst of demo traffic through the proxy and
watch the dashboard update live:

```bash
python demo/seed_transactions.py
```

This sends clean responses (→ pass), a hedging/low-confidence response (→ log), a response containing
PII (→ block, and redacted before storage), an expensive+low-confidence response (→ triggers the
`cost_confidence_mismatch` correlation flag), and a restricted-category mention — end to end, in about
10 seconds.

**Option B — type your own.** The dashboard (`http://localhost:5173`) has a "Score a response" form
above the live feed (`frontend/src/components/ScoreForm.tsx`). Type a prompt, pick a model, and submit —
it POSTs straight to `/score`, the same endpoint the seed script hits. Because the backend broadcasts
every scored record to all connected dashboards over WebSocket, your submission shows up in the live
feed instantly, same as seeded traffic.

**Leave the response box blank and a real LLM generates it.** This is the default behavior — see
"Real LLM generation" below. Paste your own response instead to test a specific scenario on demand (e.g.
one with an email address, to show PII redaction + block on the spot).

## Real LLM generation

Submitting the form with the response box left blank calls a real LLM to generate the response before
scoring it — this isn't a stub. Two providers are supported, and **which one runs is chosen per request
via the model dropdown right on the dashboard** — no `.env` edit or restart needed to switch:

| Provider | Needs | Why you'd pick it |
|---|---|---|
| **Ollama** | Ollama running locally, no API key, no internet | Safer for a live demo — works even if venue wifi is bad |
| **Gemini** | `GEMINI_API_KEY` set + an internet connection at demo time | Generally higher-quality output |

`LLM_PROVIDER` in `.env` only sets the *fallback* used when a request doesn't name a provider (e.g. a
direct API call rather than the dashboard) — it's not a restart-required switch anymore. Have both
providers configured at once in `.env` and flip between them live from the dropdown.

**To use Ollama:**
```bash
# install from https://ollama.com, then:
ollama serve
ollama pull llama3.2
```
No `.env` needed for Ollama alone — `OLLAMA_HOST` and `OLLAMA_MODEL` default to `http://localhost:11434`
and `llama3.2`. If running the backend in Docker while Ollama runs on your host machine,
`docker-compose.yml` already points at `host.docker.internal:11434` for you.

**To also enable Gemini:** copy `.env.example` → `.env`, set
`GEMINI_API_KEY=<your key from https://aistudio.google.com/apikey>`.

**Already have an Ollama model pulled?** Run `ollama list` to see what you've got, then set
`OLLAMA_MODEL=<that model name>` in `.env` — no code changes needed.

**Where `.env` goes and when it's actually read:** `.env` lives at the project root (next to
`.env.example`), not inside `backend/`. The backend loads it automatically on startup regardless of
which directory you launch `uvicorn` from — no manual `export`/`$env:` needed for anything already in
`.env`. Docker Compose is separate: it reads these vars from your shell environment or `--env-file`, so
if you're using Docker, start it with `docker compose --env-file .env up --build` to pick up the same
file.

Check `GET /llm/status` any time to confirm which provider and model are actually active.

If generation fails (provider unreachable, no key set, etc.) the API returns a 502 with a specific,
actionable error message rather than crashing or hanging — check `GET /llm/status` to see which
provider is currently configured. You can always bypass generation entirely by typing your own response
into the form, or by sending a non-empty `response` field to `/score` directly (as `demo/seed_transactions.py`
does — its examples are fixed text on purpose, so the demo doesn't depend on a model being reachable).

## Architecture

```
controlplane-checker/
├── backend/app/
│   ├── main.py            FastAPI app: /health, /score, /history, /ws
│   ├── proxy.py            orchestration: runs checks concurrently, correlates, routes, persists
│   ├── router.py           severity decision (pass / log / block)
│   ├── correlation.py      cross-signal correlation engine — the differentiator
│   ├── config.py           all tunable thresholds in one place
│   ├── db.py, models.py    SQLite via SQLAlchemy (Postgres-swap: change DATABASE_URL only)
│   ├── ws.py                WebSocket connection manager for the live dashboard feed
│   └── checks/
│       ├── performance.py  latency + deterministic confidence heuristic
│       ├── cost.py         token/cost estimate + rolling-average spike detection
│       └── responsibility.py  PII detection + redaction, toxicity/keyword screen
├── frontend/src/
│   ├── App.tsx, components/Dashboard.tsx, ResponseCard.tsx, SeverityBadge.tsx
│   └── hooks/useLiveFeed.ts   WebSocket client with reconnect backoff + REST history bootstrap
├── demo/seed_transactions.py
├── docker-compose.yml
└── .github/workflows/ci.yml
```

**Request lifecycle:** client → `POST /score` → three checks run concurrently → correlation engine
inspects the three results together → severity router decides pass/log/block → record persisted →
broadcast to all connected dashboards over WebSocket.

**WebSocket/REST payload schema** (both use the same shape):

```json
{
  "id": "uuid",
  "timestamp": "ISO-8601",
  "prompt": "string (truncated)",
  "response": "string (truncated, redacted if PII was found)",
  "checks": {
    "performance": {"score": 0-100, "latency_ms": 0, "confidence": 0-1, "flags": []},
    "cost": {"score": 0-100, "est_tokens": 0, "est_cost_usd": 0.0, "flags": []},
    "responsibility": {"score": 0-100, "pii_found": false, "toxicity": 0-1, "flags": []}
  },
  "correlation": {"compound_flags": [], "correlation_score": 0-100},
  "severity": "pass | log | block",
  "decision_reason": "string",
  "generated": false,
  "llm_provider": "ollama | gemini | null"
}
```

`generated` is `true` when the response came from a real LLM call (the response box was left blank);
`llm_provider` names which one. Both are `false`/`null` for manually-typed or seeded responses.

## Correlation rules (current)

| Rule | Trigger | Effect |
|---|---|---|
| `cost_confidence_mismatch` | cost check flags a spike **and** performance confidence < 0.5 on the same response | logged for review |
| `latency_pii_correlation` | latency over budget **and** PII found on the same response | blocked |
| `repeated_compound_escalation` | 2+ compound flags on the same session within 120s | blocked |

Extend `backend/app/correlation.py`'s `RULES` list to add more — each rule is a small function over
the three check outputs, kept deliberately simple so it ships reliably under time pressure.

## Development standards

- **Branching**: `main` (protected, demo-stable) ← `dev` (integration) ← `feat/*`. No direct pushes to `main`.
- **PRs**: one reviewer approval before merging to `dev`; merge `dev` → `main` only at milestone checkpoints.
- **Lint/format**: `ruff` + `black` (Python), `eslint` + `prettier` (JS). CI runs lint on every PR.
- **Tests**: `backend/tests/test_checks.py` covers checks, correlation, and router — run locally with:
  ```bash
  cd backend && PYTHONPATH=. pytest tests/ -v
  ```

## Security & data

- Repo is public (challenge requirement) — no secrets are ever committed; `.env.example` documents
  required variables without real values.
- Demo mode uses mocked/seeded responses — no real user data or API keys required.
- The responsibility check redacts PII **before** anything is persisted — raw PII is never written to
  the database, even in the tool's own demo store.

## Roles

| Person | Owns |
|---|---|
| Narain Gopinath (Lead) | Correlation logic, demo script, submission checklist |
| Raghav Ram (Frontend) | Dashboard UI, WebSocket live feed |
| Joshua John (Backend) | Checks, severity router, integration |

## Out of scope this sprint

Auto-remediation of flagged responses, multi-tenant auth, and production-grade horizontal scaling are
documented as future work, not built — see the build plan PDF for details.

**Deadline: 30 Aug 2026, 11:59 PM IST.**
