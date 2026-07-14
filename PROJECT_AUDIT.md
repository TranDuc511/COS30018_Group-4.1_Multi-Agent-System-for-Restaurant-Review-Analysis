# Project Strengths and Weaknesses Audit

**Audit date:** 2026-07-14
**Last updated:** 2026-07-14 after P1 contract and API/frontend boundary remediation
**Scope:** backend, data pipeline, LangGraph recovery, schemas, FastAPI,
frontend, tests, evaluation, configuration, and documentation.

## Verdict

The repository is a solid course prototype with clear architecture, structured
LLM outputs, a working API/frontend path, and strong deterministic evaluation.
The two original P0 defects and the scoped contract/API/frontend P1 defects are
fixed and regression-tested. Remaining business-identity, model-configuration,
data-index, real-data, component, and CI risks still block a production claim.

## Verification Snapshot

- Git worktree was clean before the documentation update.
- Python 3.10.19 environment passed `pip check`.
- 77 backend tests collected.
- 71 offline backend tests passed.
- 6 live integration tests were deselected.
- 2 frontend API-client tests passed.
- Tier 1 fixture passed 16/16 checks.
- Synthetic degradation harness passed 6/6 scenarios.
- Frontend production build passed; JavaScript bundle was 68.13 kB gzip.
- Raw Yelp files were present.
- SQLite index was absent.
- One real raw review lookup scanned 5.34 GB in 77.48 seconds.

Live LLM tests were not rerun because they incur external API usage. The live
E2E test uses a fixed in-memory sample and does not validate the raw Yelp or
FastAPI path.

## Strengths

### 1. Clear architecture

The project separates:

- data loading, matching, and preprocessing;
- agent logic;
- graph/state/orchestration;
- Pydantic contracts;
- FastAPI delivery;
- React presentation;
- offline and live evaluation.

The CLI and API reuse the production pipeline nodes instead of maintaining
separate implementations.

### 2. Structured LLM boundary

`BaseAgent` centralises:

- OpenAI-compatible calls;
- JSON response mode;
- Pydantic validation;
- correction prompts;
- two self-correction retries;
- configured fallback model calls;
- token accounting for evaluation.

Contracts constrain sentiments, aspects, frequencies, evidence presence,
recommendation priorities, report sections, status, and errors.

### 3. Strong deterministic evaluation

Tier 1 checks more than execution success. It verifies:

- schema validity;
- evidence IDs;
- evidence aspect alignment;
- frequency recomputation;
- recommendation traceability;
- report subset consistency;
- pipeline completion.

The committed fixture is small, deterministic, offline, and appropriate for
future CI.

### 4. Practical data design

Strengths include RapidFuzz, business caching, parameterized SQLite queries,
analysis batching, and raw-file fallback. The SQLite index avoids repeated
full-file scans when it exists.

### 5. Functional frontend

The React application includes:

- branch confirmation;
- a report dashboard;
- sentiment and aspect summaries;
- evidence counts;
- root causes and recommendations;
- limitations;
- SSE pipeline progress and timings.

The production build passes.

### 6. Secret and artifact hygiene

Real environment files, raw Yelp files, generated databases, JSONL, CSV,
Parquet, and build outputs are ignored. No live credential was found in tracked
text during the audit.

## Resolved P0 Findings

### Resolved P0: Sampling methodology

The loader now:

- validates `MAX_REVIEW_SAMPLE` from 1 to 100;
- sorts candidates by review ID to remove storage-order dependence;
- samples with `RANDOM_SEED`;
- applies optional request caps in POST, SSE, and CLI paths;
- uses the same sampling helper for raw JSON and SQLite.

Regression coverage verifies repeatability, raw/SQLite parity, non-recency, and
cap validation.

### Resolved P0: Chained recovery

Production nodes now record the current error and clear recovered state at node
boundaries. Failure inference inspects current outputs from report backward to
analysis before consulting explicit routing state.

Graph recovery stops after two retries. Recovery-provider exceptions and invalid
responses retry deterministically while attempts remain; exhausted critical
stages halt and exhausted non-critical stages skip.

A regression reproduces consecutive reasoning and strategy failures, verifies
the correct error detail for each stage, and terminates with the intended skip.

## Resolved P1 Findings

### Resolved P1: Cross-record and trusted metadata invariants

Analysis batch output now enters the normal self-correction path unless its
review IDs exactly equal the input IDs in the original order. This enforces
count, equality, ordering, and duplicate detection without a second retry loop.

Report business name and sample size are overwritten from validated report
input, and the POST/SSE response builders overwrite them again from application
business input and preprocessed sample state. Business ID/name consistency is a
separate unresolved finding. Regressions cover incomplete/reordered batches and
wrong model-generated report metadata.

### Resolved P1: API/frontend client boundaries

Offline FastAPI `TestClient` regressions cover POST report responses, SSE event
delivery, and trusted final metadata. Node's built-in test runner covers frontend
search/report requests, SSE parsing, URL encoding, and connection-error closure.
No frontend testing dependency was added.

## Remaining Weaknesses

### P1: Business identity and matching are weak at the API boundary

`business_id` and `restaurant_name` are accepted independently. Direct API
clients can label one business's reviews with another name.

Fuzzy matching has no minimum acceptance score. Nonsense queries still produce
low-score matches, and the report endpoint auto-selects the first result when no
business ID is supplied.

### P1: Model configuration is inconsistent

- Binding project target: GPT-5.4 / GPT-5.4-mini.
- Code and tracked example defaults: Gemini 2.5 Flash.
- Audited local environment: Groq-hosted Llama models.

The tracked Gemini example uses the same primary and fallback model.

**Impact:** results are not reproducible across machines, evaluation provenance
is unclear, and default fallback resilience is absent.

### P1: Current data path is slow and index creation is not atomic

The audited checkout had no SQLite DB. Each report therefore scans 5.34 GB before
LLM processing.

`build_db.py` writes to the final path and commits intermediate tables. An
interrupted build can leave a partial DB that the loader treats as valid.

### P1: Data, component, and CI boundaries lack tests

Missing automated coverage:

- real-dataset raw-loader behavior and performance;
- SQLite builder and partial DB handling;
- frontend component interactions;
- accessibility;
- CI execution.

The live E2E test bypasses Yelp data and FastAPI and retries the full paid
pipeline up to three times.

### P2: Frontend state can be stale or duplicated

Dashboard and Pipeline Monitor own separate state and can execute the same
expensive pipeline independently. Switching views discards the current stream.
Selecting another restaurant does not clear the previous report.

### P2: Accessibility needs hardening

Known gaps:

- removed focus outlines without complete replacements;
- asynchronous messages without live regions;
- active navigation without state semantics;
- pipeline state communicated mainly by color/icons;
- some small-text color combinations below WCAG AA contrast.

### P2: Local-demo security only

The API has wildcard CORS, no authentication, no rate limits, and no LLM cost
controls. SSE returns raw exception details. This is acceptable only on a trusted
local network.

### P2: Reproducibility and documentation drift

Python dependencies are unpinned and include unused fuzzy-matching packages.
Frontend manifest ranges use `latest`, though the lockfile pins the current
installation.

Before this update, documentation contradicted the code about API wiring,
frontend status, SQLite support, providers, test counts, and evaluation status.

## Minimum Repair Order

1. Add a fuzzy-match threshold and validate business ID/name consistency.
2. Select one approved model configuration and record provider/model per run.
3. Build SQLite atomically and validate schema/completeness before use.
4. Add real-data, frontend component, accessibility, and CI checks.

## Demo Readiness Gate

The sampling and chained-recovery gates now pass. Demo readiness still requires:

- a built and validated SQLite index;
- the actual model/provider is recorded;
- one real dataset + API + frontend run is completed successfully.

## Audit Limitations

- No live LLM request was made during this audit.
- No browser automation or Lighthouse audit was run.
- Coverage percentage is unknown because coverage tooling is not installed.
- Security review was static and local; no penetration test was performed.
