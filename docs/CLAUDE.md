# AI-Agent Working Guide

Read [AGENTS.md](../AGENTS.md) first. It contains the binding project rules.
This file contains practical repository guidance.

## Project

COS30018 multi-agent restaurant-review analysis system:

- Python, FastAPI, LangGraph, and Pydantic backend;
- Yelp raw JSON with optional SQLite index;
- analysis, reasoning, strategy, and report agents;
- React dashboard and SSE pipeline monitor;
- three-tier evaluation tooling.

Current status: [PROGRESS.md](PROGRESS.md).

Decision history: [DECISIONS.md](DECISIONS.md).

Verification commands: [RUN_TESTS.md](RUN_TESTS.md).
Confirmed defects and priorities: [PROJECT_AUDIT.md](../PROJECT_AUDIT.md).

## Layout

- `backend/app/agents/`: agents and shared LLM/self-correction loop.
- `backend/app/core/`: state, nodes, graph, orchestrator, pipeline.
- `backend/app/data/`: loader, matching, preprocessing.
- `backend/app/schemas/contracts.py`: executable Pydantic contracts.
- `backend/app/main.py`: FastAPI endpoints.
- `backend/eval/`: Tier 1, Tier 1b, Tier 2, and Tier 3 tools.
- `backend/tests/`: offline and live tests.
- `frontend/src/`: dashboard, pipeline monitor, API client, and styles.

## Commands

Run backend commands from `backend/`:

```powershell
pip install -r requirements.txt
python -m pytest -m "not integration"
uvicorn app.main:app --reload
python run_pipeline.py --name "McDonald's" --pick 1 --dump-stages out/
```

Prefer `backend/venv/`. On the audited Windows machine,
`C:\Users\ADMIN\anaconda3\envs\ml\python.exe` is also verified.

Frontend:

```powershell
cd frontend
npm install
npm run dev
npm run build
```

## Contracts and Boundaries

- Every agent returns JSON-compatible output with `status` and
  `error_detail`.
- Validate inter-agent output with `app/schemas/contracts.py`.
- Self-correction retries at most two times.
- Analysis and reasoning are critical; strategy and report are non-critical.
- Keep loading, matching, sampling, and agent logic separate.
- API and CLI must reuse `app/core/pipeline.py`; do not create parallel
  pipeline implementations.

## Implemented P0 Contracts

- Raw and SQLite loaders use `RANDOM_SEED` for reproducible random sampling.
- `sample_size` is validated and applied by POST and SSE report endpoints.
- Production nodes write and clear recovery metadata at node boundaries.
- Graph recovery stops after two retries and handles recovery-provider failure
  deterministically.

## Known Implementation Deviations

- `AGENTS.md` specifies the GPT-5.4 family; code/example defaults use Gemini,
  while local `.env` may override both.
- Batch analysis validation does not enforce exact input/output review IDs.
- Report identity and sample size remain model-controlled.

Do not describe any deviation as compliant behavior. Link
[PROJECT_AUDIT.md](../PROJECT_AUDIT.md) until it is fixed.

## Dataset

- Paths are resolved relative to the repository root.
- Raw files live directly under `backend/data/raw/`.
- Raw data and generated DB/output files are git-ignored.
- Build `backend/data/processed/yelp.db` before demos:

```powershell
cd backend
python scripts/build_db.py
```

Without the DB, one report scans the full 5.34 GB review file.

## Tests

```powershell
python -m pytest                      # includes live tests when configured
python -m pytest -m "not integration" # offline
python -m pytest -m integration       # external model calls
```

The live E2E test uses four in-memory reviews. It validates model + graph wiring,
not Yelp loading, FastAPI, or the frontend.

## Secrets and Git

- Never commit `.env`, raw datasets, generated DBs, or evaluation outputs.
- Keep `.env.example` free of real credentials.
- Do not commit or push unless asked.
- Check `git status --short`.
- Stage only task-related files.
- Never rewrite history unless explicitly requested.
