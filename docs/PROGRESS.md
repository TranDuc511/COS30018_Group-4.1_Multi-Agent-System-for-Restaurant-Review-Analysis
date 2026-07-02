# PROGRESS.md

Living status of the project. Update when a stage lands or a milestone moves.

_Last updated: 2026-07-02._

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
| LLM provider | ✅ Gemini 2.5 Flash | All agents + orchestrator use `gemini-2.5-flash` via Gemini's OpenAI-compatible endpoint. Verified: 6 real-LLM tests pass. See [`DECISIONS.md`](DECISIONS.md) 2026-07-01. |
| Evaluation harness | ✅ Working (Tier 2 gold set pending) | `backend/eval/` — Tiers 1, 1b, 2, 3 all implemented (`tier1_checks.py`, `harness.py`, `tier2_analysis.py`, `tier3_judge.py`) + committed fixture (`eval/fixtures/sample_dump/`) + `tests/test_eval_tier1.py` (9 tests, offline). Tier 2 needs a human to hand-label `eval/gold/analysis_gold.jsonl` before it can be run. See 2026-07-02 entry below. |
| FastAPI app | 🚧 Stub | `main.py` exposes `/health` and a `/api/reports` placeholder; pipeline not wired to HTTP yet. |
| Frontend dashboard | 🚧 Placeholder | Vite/React scaffold (`App.jsx`, `Dashboard.jsx`); no real data binding. |
| Dataset persistence (SQLite index) | ⬜ Planned | Currently a linear scan of the 5.3 GB review file. |

Legend: ✅ done · 🚧 in progress · ⬜ not started

## Tests

- 69 tests total (`python -m pytest` from `backend/`): 63 pass offline, 6 integration/e2e tests (real Gemini, auto-skip without `OPENAI_API_KEY`).
- `python -m pytest -m "not integration"` → 63 passed (verified 2026-07-02, includes 9 new `tests/test_eval_tier1.py` cases).
- Full end-to-end test (`tests/test_e2e_pipeline.py`) runs the real graph through all 5 stages with live LLM calls.
- After the Gemini switch, the whole suite was re-run: **all 60 pass** (the one default-model assertion in `test_strategy_agent.py` was updated to `gemini-2.5-flash`).

## Milestones (from README)

| Phase | Target | Status |
| --- | --- | --- |
| Phase 0 — scope + contracts | 25/05 | ✅ Done |
| Phase 1 — components vs mock data, validators, self-correction | 05/06 | ✅ Done |
| Phase 2 — full pipeline on Yelp data, error handling tested | 17/06 | 🚧 In progress (pipeline runs; HTTP + real-data e2e wiring pending) |
| Phase 3 — polished report, recovery tested, demo | 30/06 | ⬜ Not started |

## 🔖 Handoff for the next session (2026-07-02)

**Done and verified this session — the evaluation harness (all tiers) is implemented:**
- ✅ `eval/common.py` — `load_dump`, `CheckResult`, `print_scorecard`.
- ✅ `eval/tier1_checks.py` — schema validity, reasoning groundedness (evidence
  exists / aspect present / frequency recomputed within tolerance), strategy
  traceability (issue↔root-cause matching + priority/frequency ordering),
  report-subset (root causes / recommendations verbatim, key findings soft
  match), completion status. `python -m eval.tier1_checks <dump_dir>` prints a
  scorecard, writes `tier1_report.json`, exits non-zero on any failure.
- ✅ `eval/harness.py` (Tier 1b) — `measure_reproducibility`,
  `measure_latency_and_cost` (added a minimal, additive token-usage counter to
  `BaseAgent` — `total_tokens_used` / `reset_token_usage()` — to make the
  "LLM cost per 100 reviews" metric measurable), and `check_degradation_paths`
  (6 scenarios covering retry/skip/halt, including the two hard-rule paths and
  the critical-agent skip→halt downgrade). `python -m eval.harness --skip-live`
  runs the degradation checks with **no API/dataset needed**; drop `--skip-live`
  (with `--name`) to also exercise the live reproducibility/latency checks.
- ✅ `eval/tier2_analysis.py` — `load_gold`, a review-fetch helper (SQLite index
  if present, else a single linear scan of the raw review file), `score_sentiment`
  (accuracy), `score_aspects_macro_f1` (per-category binary presence F1 via
  scikit-learn, macro-averaged). Verified against synthetic data; **not** run
  against real gold labels — see blocker below.
- ✅ `eval/tier3_judge.py` — `judge_model()` (warns if `JUDGE_MODEL` matches
  `OPENAI_MODEL`, defaults to `gemini-2.5-pro` so it never silently self-judges),
  `score_with_rubric()` (OpenAI-compatible client call + robust JSON/regex score
  parsing), `main()` scores every root cause, every recommendation, and the
  report as a whole, writing `tier3_scores.json`.
- ✅ Committed fixture at `eval/fixtures/sample_dump/` — **built deterministically**
  (see `eval/fixtures/README.md` for exact provenance), not from a live run: the
  sandbox this session ran in has no network route to the Gemini endpoint, so
  analysis/reasoning are hand-authored-but-internally-consistent (frequencies
  computed programmatically from the authored data) and strategy/report are
  produced by the project's own real deterministic (`use_llm=False`) agent code.
  This is actually the ideal shape for a permanent CI fixture (zero flakiness,
  never needs an API key).
- ✅ `tests/test_eval_tier1.py` — 9 tests, all offline: the healthy fixture
  passes all 16 checks, and 6 deliberately-corrupted variants (hallucinated
  evidence id, wrong frequency, fabricated root cause, halted status,
  hallucinated sentiment enum, skipped-stage vacuous-pass) each trip the
  specific check they're supposed to. Full suite re-run: **63/63 pass**
  (`python -m pytest -m "not integration"`), no regressions from the
  `BaseAgent` token-counter change.

**Outstanding blockers — need a human, not more agent time:**
1. **Tier 2 gold set — worksheet ready, labeling itself still needs you.**
   `eval/gold/tier2_gold_labeling_worksheet.xlsx` has 40 real reviews for
   "LOVE Grille" (Philadelphia, business_id `4Env6uGYxMhXFKPfcuzUuQ`, 3.0★,
   73 reviews total in the dataset), stratified across star ratings so the
   sample isn't all 5-star fluff. Sentiment/aspect columns are dropdowns
   (see the Instructions tab). Deliberately not filled in by the agent — the
   whole point of Tier 2 is independent human judgment as ground truth, and
   an LLM labeling its own eval set would invalidate the metric. Once filled:
   `python eval/gold/build_gold_jsonl.py eval/gold/tier2_gold_labeling_worksheet.xlsx`
   writes `eval/gold/analysis_gold.jsonl` in the exact schema `tier2_analysis.py`
   expects (verified round-trip on a partially-filled test copy this session).
   Ideally have a second annotator label independently and compare (Cohen's
   kappa) before treating it as final ground truth.
2. **Live-LLM fixture (optional).** `eval/fixtures/sample_dump/` is deterministic
   by construction (see above). Consider also generating a real
   `--dump-stages` dump from an actual restaurant (needs the Gemini API +
   Yelp dataset, both unavailable in this session's sandbox) to spot-check
   Tier 1 against genuine LLM output, not just hand-authored data.
3. **`harness.py` live checks.** `measure_reproducibility` /
   `measure_latency_and_cost` need real dataset access + `OPENAI_API_KEY` and
   were only smoke-tested via `--skip-live` (degradation paths only) this
   session — run the full command once with a real `--name` to confirm.
4. **Tier 3 run.** `tier3_judge.py` was unit-tested (`_extract_score`,
   `judge_model`) but never run end-to-end against a real dump (same network
   constraint) — run it once a live dump exists.

Eval design + methodology references are in README §14 and `DECISIONS.md`.

**Also still outstanding from last session:** the 🔴 security item below
appears already resolved in the working tree (`.env.example` currently holds a
placeholder, not a real key) but hasn't been committed — confirm before
committing. Nothing from the Gemini switch or this eval work is committed yet.

## Known gaps / next steps

Ownership and sequencing for the tasks below live in [`PLAN.md`](PLAN.md).

1. **🔴 SECURITY — real key in tracked `backend/.env.example`.** A real Gemini
   key is currently in `.env.example` (a git-tracked file). It has **not** been
   committed (verified via `git log -S`). Restore the placeholder
   (`OPENAI_API_KEY=your-gemini-api-key-here`), keep the real key only in `.env`
   (git-ignored), and **rotate the key** in Google AI Studio to be safe. Do this
   before any commit.
2. **Evaluation harness** (`backend/eval/`) — ✅ all tiers implemented
   2026-07-02 (see handoff block above). Remaining: hand-label the Tier 2 gold
   set, and run Tier 1b/Tier 3 live (both need real dataset + API access this
   session's sandbox didn't have).
3. **Wire the pipeline into `main.py`** — node wrappers are in `app/core/nodes.py`,
   with `run_pipeline()` in `app/core/pipeline.py`. `main.py`'s `/api/reports`
   still needs to call `run_pipeline()` and return the report.
4. **Harden `orchestrator.decide_recovery`** — its recovery LLM call has no error
   handling, so a provider error (e.g. Gemini 429 / quota) crashes the graph
   instead of halting cleanly. Wrap in try/except with a safe fallback (`halt`).
5. **Dataset indexing** — replace the linear 5.3 GB review scan with a SQLite
   index keyed on `business_id` (see README §6; `scripts/build_db.py` exists).
6. **Frontend** — bind `Dashboard.jsx` to a real `/api/reports` response.

## Recent changes (2026-07-02)

- Implemented all eval tiers in `backend/eval/`: `tier1_checks.py`,
  `harness.py` (Tier 1b), `tier2_analysis.py`, `tier3_judge.py`, plus
  `common.py`'s `load_dump`/`print_scorecard`. See the handoff block above for
  the full rundown and outstanding human blockers (gold-set labeling, a
  live-LLM fixture, running the live harness/Tier 3 checks).
- Added a minimal, additive token-usage counter to `BaseAgent`
  (`total_tokens_used`, `reset_token_usage()`) so `eval/harness.py` can report
  LLM cost per 100 reviews; no existing call sites changed behavior.
- Added `eval/fixtures/sample_dump/` (committed, deterministic — see
  `eval/fixtures/README.md`) and `tests/test_eval_tier1.py` (9 tests, all
  offline). Full suite: 63/63 non-integration tests pass.

## Recent changes (2026-06-13)

- Added `--dump-stages <dir>` to `run_pipeline.py`: writes each agent phase's
  JSON (`analysis|reasoning|strategy|report.json`) plus `_summary.json` from the
  final pipeline state, for inspection and evaluation. See [`DECISIONS.md`](DECISIONS.md).
- Defined the evaluation plan (three tiers) - see README section 14 and [`PLAN.md`](PLAN.md).
- Chose SQLite (keyed on `business_id`) as the dataset index to replace the
  5.3 GB linear scan; a pre-extracted subset is acceptable for a scripted demo.
- Added [`PLAN.md`](PLAN.md): Phase 2 / Phase 3 backlog with 4-member lane ownership.

## Recent changes (this session)

- Updated README repository-structure tree to match the real file layout.
- Flattened the Yelp dataset files out of redundant same-named folders; fixed `.env` paths (repo-root-relative).
- Added `tests/test_e2e_pipeline.py` — first real-LLM, all-5-stages end-to-end test.
- Factored shared agent node wrappers into `app/core/nodes.py` and added `app/core/pipeline.py` (`run_pipeline()`); refactored the e2e test to reuse them.
- Added `backend/run_pipeline.py` — interactive CLI to run the full pipeline on a real restaurant.
- Found: a live run crashed in the `error_handler` node because `orchestrator.decide_recovery` doesn't handle provider errors (Groq daily token cap, HTTP 429). Logged as a gap above.
- Added `CLAUDE.md`, `PROGRESS.md`, `DECISIONS.md`, `RUN_TESTS.md`; un-ignored `CLAUDE.md` in `.gitignore`; then moved these four docs into `docs/`.
