# DECISIONS.md

Decision log (lightweight ADR style). Newest first. Each entry: what was decided,
why, and what it affects. Don't rewrite history — add a new entry that supersedes
an old one if a decision changes.

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
