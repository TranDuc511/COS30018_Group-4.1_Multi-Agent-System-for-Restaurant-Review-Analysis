# DECISIONS.md

Decision log (lightweight ADR style). Newest first. Each entry: what was decided,
why, and what it affects. Don't rewrite history — add a new entry that supersedes
an old one if a decision changes.

---

## 2026-07-01 - All agents use Gemini 2.5 Flash via the OpenAI-compatible endpoint

**Decision:** Switch every LLM call (analysis, reasoning, strategy, report, and
the orchestrator recovery call) to **`gemini-2.5-flash`**, reached through
Gemini's OpenAI-compatible endpoint
(`OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`).
`OPENAI_API_KEY` now holds a Google AI Studio key; the `OPENAI_*` variable names
are kept so the existing `openai` client and `langchain_openai.ChatOpenAI` code
runs unchanged. Default model strings in `base_agent.py`, `orchestrator.py`,
`report_agent.py`, and `strategy_agent.py` now default to `gemini-2.5-flash`;
the fallback slot is retained but also points at `gemini-2.5-flash`. Supersedes
the Groq / `llama-3.3-70b-versatile` config noted in the 2026-06-08 entry below.

**Why:** The whole LLM layer is already OpenAI-shaped (base_url override,
`response_format={"type":"json_object"}`), so targeting Gemini's compat endpoint
is a config-plus-defaults change rather than a rewrite, and is trivially
reversible. This is unrelated to commit `a0ef24c` (removed the old *Gemini live
agent* provider) - that was a live/streaming provider; this is standard chat
completions.

**Affects:** `app/agents/base_agent.py`, `app/core/orchestrator.py`,
`app/agents/report_agent.py`, `app/agents/strategy_agent.py`, `.env.example`,
`app/core/nodes.py` (comment). Verify with `test_integration.py` /
`test_e2e_pipeline.py` that Gemini's compat layer honours the JSON `response_format`.
Note: `eval/tier3_judge.py` must use a *different* `JUDGE_MODEL` (e.g. a stronger
Gemini) to keep the LLM-as-judge unbiased now that all agents share one model.

---

## 2026-06-13 - Per-stage JSON dump from the pipeline runner

**Decision:** `run_pipeline.py` gains a `--dump-stages <dir>` flag that writes
each agent phase's output (`analysis.json`, `reasoning.json`, `strategy.json`,
`report.json`) plus a `_summary.json` (status, skipped agents, errors, retry
counts), pulled straight from the final pipeline state.

**Why:** A pipeline run and its evaluation should be decoupled. The dumped JSON
is the input to the Tier-1 evaluator, and the per-phase artifacts make it obvious
which stage degraded during a demo or debugging session. Skipped / failed stages
are written as `null` / their error payload rather than omitted.

**Affects:** `backend/run_pipeline.py`. Feeds the evaluation plan (README 14).

---

## 2026-06-13 - Evaluation approach: three tiers

**Decision:** Evaluate in three tiers - (1) deterministic checks with no labels
or API (schema validity, enum compliance, reasoning groundedness, recomputed
frequencies, cross-stage consistency, completion rate, latency / cost),
(2) a 30-50 review labelled gold set for the analysis agent only (sentiment
accuracy, aspect macro-F1), and (3) rubric scoring (human or different-model LLM
judge) for the subjective stages. Detail in README 14.

**Why:** Each stage's output is derivable from the previous one, so most
correctness questions reduce to deterministic consistency checks that need no
ground truth. Only the analysis agent has objectively checkable labels; the
reasoning / strategy / report stages are subjective and are not gold-setted.

**Affects:** `backend/eval/` (planned), README 14. Resolves the open "evaluation
criteria" gap.

---

## 2026-06-13 - Dataset index: SQLite (default), subset-extract as a demo shortcut

**Decision:** Replace the 5.3 GB linear scan of `review.json` with a SQLite index
keyed on `business_id`. If the demo is scripted to a few known restaurants, a
one-off pre-extracted subset of those businesses' reviews is an acceptable
lighter-weight shortcut.

**Why:** Every `/api/reports` call and every evaluation run currently re-scans
5.3 GB to find one restaurant's reviews. SQLite is stdlib, single-file, and the
option README 6 already names; it makes lookups index-backed without new infra.
This supersedes the open "SQLite vs Parquet" question in favour of SQLite.

**Affects:** `app/data/loader.py`, `backend/data/`.

---

## 2026-06-08 — Project docs live in `docs/`; convention files stay at root

**Decision:** `CLAUDE.md`, `PROGRESS.md`, `DECISIONS.md`, and `RUN_TESTS.md` live in
`docs/`. `README.md` and `AGENTS.md` (and the report `.md` files) stay at the repo
root.

**Why:** Keep the root tidy while preserving GitHub's README landing page and
Claude Code / Codex auto-discovery of root `AGENTS.md`.

**Trade-off:** `CLAUDE.md` moved into `docs/`, so root-level auto-discovery of it
no longer applies — open it explicitly when needed. Links from the moved docs to
root files use `../`.

**Affects:** repo layout, cross-links in the four moved docs.

---

## 2026-06-08 — Shared agent nodes in `app/core`; CLI runner for the full pipeline

**Decision:** The real agent node wrappers live in `app/core/nodes.py`, with a
`run_pipeline()` helper in `app/core/pipeline.py`. The CLI
(`backend/run_pipeline.py`) and the e2e test both import them.

**Why:** Previously the only full-pipeline wiring lived inline in the e2e test. A
single shared implementation lets the CLI, the test, and a future FastAPI
endpoint run the exact same graph.

**Affects:** `app/core/nodes.py`, `app/core/pipeline.py`,
`backend/run_pipeline.py`, `tests/test_e2e_pipeline.py`.

---

## 2026-06-08 — End-to-end test retries the whole pipeline instead of asserting one perfect run

**Decision:** `tests/test_e2e_pipeline.py` runs the full real-LLM pipeline up to 3
times and asserts on the first run that reaches `complete`.

**Why:** Strategy and report are non-critical agents, and every stage (plus the
orchestrator's recovery decision) makes live LLM calls that occasionally fail
schema validation even at temperature 0. When that happens the pipeline
*correctly* degrades (skips a non-critical agent), so a single run can end as
`skip` with no bug. Retrying keeps the strong "all five stages succeed together"
assertion while staying reliable (~80% success/run × 3 attempts ≈ 99%).

**Affects:** `tests/test_e2e_pipeline.py`. Assertions avoid checking that the LLM
echoes input fields verbatim (`business_name`, `sample_size`) — those are
model-controlled and not stable.

---

## 2026-06-08 — Dataset files flattened; `.env` paths are repo-root-relative

**Decision:** Yelp dataset files live directly at
`backend/data/raw/yelp_academic_dataset_{business,review}.json` (plain files).
`.env` paths are written relative to the repo root.

**Why:** The files had been wrapped in redundant same-named folders
(`.../business.json/business.json`), and `loader.py` anchors relative paths to the
repo root (`Path(__file__).parents[3]`). Earlier `.env` values had a stray
`backend/` prefix relative to the wrong base, causing `FileNotFoundError`.

**Affects:** `backend/.env` (git-ignored), `backend/data/raw/`. Dataset files stay
git-ignored; only `.gitkeep` placeholders are committed.

---

## 2026-06-08 — `CLAUDE.md` is a tracked project doc

**Decision:** Removed `CLAUDE.md` from `.gitignore` so it is version-controlled.
`.claude/` stays ignored.

**Why:** The team wants shared agent guidance in the repo, not a local-only file.

**Affects:** `.gitignore`, `CLAUDE.md`.

---

## Pre-existing decisions (from AGENTS.md / README)

These were agreed before this log existed; recorded here for traceability. See
[`AGENTS.md`](../AGENTS.md) §"Current Project Decisions" for the authoritative list.

- **LLM models:** primary `gpt-5.4`, fallback `gpt-5.4-mini` (fall back to `gpt-5` /
  `gpt-5-mini` without access). Configurable via `OPENAI_MODEL` /
  `OPENAI_FALLBACK_MODEL`. Current `.env` uses Groq's OpenAI-compatible endpoint
  with `llama-3.3-70b-versatile` / `llama-3.1-8b-instant`.
- **Sampling:** randomly sample up to 100 reviews per restaurant; cap is
  configurable (`MAX_REVIEW_SAMPLE`). Never claim the whole dataset is analysed.
- **Self-correction:** each agent retries at most 2 times, then returns
  `status: "error"` and lets the orchestrator decide retry/skip/halt.
- **Critical agents:** `analysis` and `reasoning` halt on failure; `strategy` and
  `report` are non-critical and may be skipped.
- **Architecture:** Supervisor / multi-agent collaboration via LangGraph;
  Pydantic contracts (`app/schemas/contracts.py`) are the inter-agent interface.
- **Separation:** data loading is separate from agent logic; fuzzy matching is
  separate from sampling.

---

## Open questions / undecided

- Final report output schema (README §11.9 is still a draft).
- Dataset persistence format — SQLite vs Parquet for the `business_id` index.
- Frontend framework commitment (React vs simpler Streamlit prototype — README §12).
- Whether `orchestrator.decide_recovery` should fall back to `halt` (or a non-LLM heuristic) when its own recovery LLM call fails — today an exception there crashes the graph.
