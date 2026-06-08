# PROGRESS.md

Living status of the project. Update when a stage lands or a milestone moves.

_Last updated: 2026-06-08._

## Snapshot

| Layer | Status | Notes |
| --- | --- | --- |
| Data loading & matching | ✅ Working | `loader.py` + `matching.py`, fuzzy search over Yelp `business.json`. |
| Preprocessing & sampling | ✅ Working | `preprocessor.py`, cap of 100 reviews (configurable). |
| Analysis agent | ✅ Working | Real LLM, self-correction, contract-validated. |
| Reasoning agent | ✅ Working | Real LLM, pattern + root-cause detection. |
| Strategy agent | ✅ Working | LLM + deterministic mode. |
| Report agent | ✅ Working | LLM + deterministic mode. |
| Orchestrator | ✅ Working | retry / skip / halt; critical = analysis, reasoning. |
| LangGraph graph | ✅ Working | `build_graph()` wires all 5 stages + error handler. |
| Pipeline runner (CLI) | ✅ Working | `backend/run_pipeline.py` + `app/core/pipeline.py` run all 5 stages on real data. |
| FastAPI app | 🚧 Stub | `main.py` exposes `/health` and a `/api/reports` placeholder; pipeline not wired to HTTP yet. |
| Frontend dashboard | 🚧 Placeholder | Vite/React scaffold (`App.jsx`, `Dashboard.jsx`); no real data binding. |
| Dataset persistence (SQLite/Parquet index) | ⬜ Planned | Currently a linear scan of the 5.3 GB review file. |

Legend: ✅ done · 🚧 in progress · ⬜ not started

## Tests

- 58 tests passing (`python -m pytest` from `backend/`).
- 52 unit tests (no LLM) + 6 integration/e2e tests (real Groq, auto-skip without `OPENAI_API_KEY`).
- Full end-to-end test (`tests/test_e2e_pipeline.py`) runs the real graph through all 5 stages with live LLM calls.

## Milestones (from README)

| Phase | Target | Status |
| --- | --- | --- |
| Phase 0 — scope + contracts | 25/05 | ✅ Done |
| Phase 1 — components vs mock data, validators, self-correction | 05/06 | ✅ Done |
| Phase 2 — full pipeline on Yelp data, error handling tested | 17/06 | 🚧 In progress (pipeline runs; HTTP + real-data e2e wiring pending) |
| Phase 3 — polished report, recovery tested, demo | 30/06 | ⬜ Not started |

## Known gaps / next steps

1. **Wire the pipeline into `main.py`** — node wrappers are now factored into `app/core/nodes.py`, with a `run_pipeline()` helper in `app/core/pipeline.py` (shared by the CLI runner and the e2e test). `main.py`'s `/api/reports` still needs to call `run_pipeline()` and return the report.
2. **Harden `orchestrator.decide_recovery`** — its recovery LLM call (orchestrator.py) has no error handling, so a provider error raised there (e.g. Groq 429 rate limit) crashes the whole graph instead of halting cleanly. Wrap it in try/except with a safe fallback (`halt`).
3. **Dataset indexing** — replace the linear 5.3 GB review scan with SQLite/Parquet keyed on `business_id` (see README §6).
4. **Frontend** — bind `Dashboard.jsx` to a real `/api/reports` response once the report schema is final.
5. **Rotate the leaked key** in `backend/.env.example` and replace with a placeholder.

## Recent changes (this session)

- Updated README repository-structure tree to match the real file layout.
- Flattened the Yelp dataset files out of redundant same-named folders; fixed `.env` paths (repo-root-relative).
- Added `tests/test_e2e_pipeline.py` — first real-LLM, all-5-stages end-to-end test.
- Factored shared agent node wrappers into `app/core/nodes.py` and added `app/core/pipeline.py` (`run_pipeline()`); refactored the e2e test to reuse them.
- Added `backend/run_pipeline.py` — interactive CLI to run the full pipeline on a real restaurant.
- Found: a live run crashed in the `error_handler` node because `orchestrator.decide_recovery` doesn't handle provider errors (Groq daily token cap, HTTP 429). Logged as a gap above.
- Added `CLAUDE.md`, `PROGRESS.md`, `DECISIONS.md`, `RUN_TESTS.md`; un-ignored `CLAUDE.md` in `.gitignore`; then moved these four docs into `docs/`.
