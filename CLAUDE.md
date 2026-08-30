# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (Python/FastAPI)
- **Start backend**: `cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- **Run tests**: `cd backend && PYTHONPATH=. pytest tests/ -v`
- **Run linter**: `cd backend && ruff check .`
- **Format code**: `cd backend && black .`
- **Type checking**: `cd backend && mypy .` (if configured)

### Frontend (React/Vite)
- **Start dev server**: `cd frontend && npm run dev`
- **Build for production**: `cd frontend && npm run build`
- **Run linter**: `cd frontend && npm run lint`
- **Format code**: `cd frontend && npx prettier --write .`
- **Preview build**: `cd frontend && npm run preview`

### Full Stack (Docker)
- **Start all services**: `docker compose up --build`
- **Start in detached mode**: `docker compose up -d --build`
- **Stop services**: `docker compose down`
- **View logs**: `docker compose logs -f`

### Demo & Testing
- **Run seed script** (sends test traffic): `python demo/seed_transactions.py`
- **Check LLM status**: `curl http://localhost:8000/llm/status`
- **Health check**: `curl http://localhost:8000/health`

## Architecture Overview

### Backend Structure
```
backend/
├── app/
│   ├── main.py             # FastAPI app definition and endpoints
│   ├── proxy.py            # Core orchestration: runs checks, correlation, routing
│   ├── router.py           # Severity decision logic (pass/log/block)
│   ├── correlation.py      # Cross-signal correlation engine
│   ├── config.py           # Tunable constants and thresholds
│   ├── llm_provider.py     # Abstraction for Ollama/Gemini providers
│   ├── ws.py               # WebSocket connection manager for live dashboard
│   ├── db.py, models.py    # SQLite/SQLAlchemy database layer
│   └── checks/
│       ├── performance.py  # Latency + confidence heuristic
│       ├── cost.py         # Token/cost estimation + spike detection
│       └── responsibility.py # PII detection + redaction, toxicity screening
└── tests/                  # Unit tests for checks, correlation, router
```

### Frontend Structure
```
frontend/
├── src/
│   ├── App.tsx             # Main application component
│   ├── main.tsx            # React entry point
│   ├── index.css           # Global styles (Tailwind base)
│   ├── components/
│   │   ├── ScoreForm.tsx   # Main interaction form (prompt/response + provider switch)
│   │   ├── Dashboard.tsx   # Main dashboard layout
│   │   ├── ResponseCard.tsx # Individual scored response display
│   │   ├── SeverityBadge.tsx # Visual indicator for pass/log/block
│   │   ├── Pulseline.tsx   # Mini chart showing recent scores
│   │   └── ThemeToggle.tsx # Light/dark theme switcher
│   └── hooks/
│       └── useLiveFeed.ts  # WebSocket client with reconnect logic + REST bootstrap
```

### Request Lifecycle
1. Client → `POST /score` (with prompt, optional response, model, session_id)
2. If response blank → generate via selected LLM provider (Ollama/Gemini)
3. Run three checks concurrently:
   - Performance: latency + confidence heuristic (hedge phrases, repetition)
   - Cost: token estimate + rolling average spike detection
   - Responsibility: PII detection/redaction + toxicity screening
4. Correlation engine inspects check results for compound flags
5. Severity router decides pass/log/block based on rules
6. Record persisted to SQLite database
7. Result broadcast via WebSocket to all connected dashboards

### Key Files for Modification
- **Add new check**: Create file in `backend/app/checks/` and import in `proxy.py`
- **Modify correlation rules**: Edit `backend/app/correlation.py` (see README for current rules)
- **Change routing logic**: Edit `backend/app/router.py`
- **Update dashboard components**: Work in `frontend/src/components/`
- **Add WebSocket data**: Modify `backend/app/ws.py` and `frontend/src/hooks/useLiveFeed.ts`

## Development Standards

### Code Quality
- **Python**: Ruff linting + Black formatting (CI enforces both)
- **JavaScript/TypeScript**: ESLint + Prettier (CI enforces linting)
- **Tests**: Backend tests in `backend/tests/`; run with `PYTHONPATH=. pytest tests/ -v`

### Branching Strategy
- `main`: Protected branch, demo-stable releases
- `dev`: Integration branch for feature work
- `feat/*`: Feature branches branched from `dev`
- **Workflow**: Branch off `dev` → open PR → 1 reviewer approval → merge to `dev` → periodic `dev`→`main` merges at milestones

### Environment Configuration
- `.env` file at project root (not committed; see `.env.example`)
- Backend loads `.env` automatically on startup regardless of launch directory
- Docker Compose requires `--env-file .env` to pass variables to containers
- LLM provider can be switched live via dashboard dropdown (no restart needed)

## Running Specific Tests

### Single Test File
```bash
cd backend && PYTHONPATH=. pytest tests/test_checks.py -v
```

### Single Test Function
```bash
cd backend && PYTHONPATH=. pytest tests/test_checks.py::test_performance_check -v
```

### Tests with Coverage
```bash
cd backend && PYTHONPATH=. pytest tests/ --cov=app --cov-report=term-missing
```

### Test Watch Mode (development)
```bash
cd backend && PTWATCH=1 pytest tests/ -vw
```

## Important Notes

1. **Database**: SQLite by default (`controlplane.db` in backend/). For Postgres, change `DATABASE_URL` in `.env` or docker-compose.

2. **LLM Providers**:
   - Ollama: Local, no API key needed (good for demos with spotty internet)
   - Gemini: Requires `GEMINI_API_KEY` in `.env`, generally higher quality
   - Provider selection happens per request via dashboard dropdown

3. **PII Handling**: Responsibility check redacts PII before storage — raw PII never written to disk.

4. **WebSocket**: Dashboard connects to `/ws` endpoint for live updates; includes automatic reconnect with backoff.

5. **Demo Mode**: No `.env` required; uses mocked/seeded responses. Add `.env` only for real LLM integration.