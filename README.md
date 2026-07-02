# COS30018 Intelligent Systems

## Multi-Agent System for Restaurant Review Analysis

This project builds a Python-based multi-agent AI system for F&B business owners.
Given a restaurant name, the system searches the Yelp Open Dataset, randomly selects
up to 100 matching review records, analyses the feedback, identifies recurring
patterns, and generates an actionable business report.

The goal is to turn raw restaurant feedback into clear operational recommendations
without requiring the owner to manually process review text.

## Repository Structure

```text
COS30018-IS/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── base_agent.py          # shared agent base + self-correction loop
│   │   │   ├── analysis_agent.py      # per-review sentiment + aspect classification
│   │   │   ├── reasoning_agent.py     # pattern + root-cause reasoning
│   │   │   ├── strategy_agent.py      # prioritised recommendations
│   │   │   └── report_agent.py        # final web report generation
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py              # settings / env + model config
│   │   │   ├── state.py               # PipelineState
│   │   │   ├── graph.py               # LangGraph graph wiring
│   │   │   ├── orchestrator.py        # routing, retries, error reasoning
│   │   │   ├── nodes.py               # real agent node wrappers (shared)
│   │   │   └── pipeline.py            # build + run the full pipeline
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── loader.py              # load Yelp dataset
│   │   │   ├── matching.py            # fuzzy restaurant-name matching
│   │   │   └── preprocessor.py        # clean + sample reviews
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── contracts.py           # shared JSON schemas (all agree on this)
│   │   └── main.py                    # FastAPI app + endpoints
│   ├── data/
│   │   ├── raw/                       # yelp_academic_dataset_business.json
│   │   │   └── .gitkeep               # commit placeholder, not the actual files
│   │   └── processed/                 # cached/cleaned outputs
│   │       └── .gitkeep
│   ├── tests/
│   │   ├── .gitkeep
│   │   ├── mock_data.py               # stub data for testing
│   │   ├── mock_agents.py             # stub agent implementations
│   │   ├── test_analysis_agent.py
│   │   ├── test_data_pipeline.py
│   │   ├── test_e2e_pipeline.py
│   │   ├── test_graph.py
│   │   ├── test_integration.py
│   │   ├── test_orchestrator.py
│   │   ├── test_orchestrator_routing.py
│   │   ├── test_report_agent.py
│   │   ├── test_state.py
│   │   ├── test_strategy_agent.py
│   │   └── test_unit.py
│   ├── conftest.py                    # shared pytest fixtures
│   ├── pytest.ini                     # pytest configuration
│   ├── run_pipeline.py                # CLI: run the full pipeline on a real restaurant
│   ├── .env.example                   # OPENAI_API_KEY=, DATA_PATH=
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js              # API calls to FastAPI
│   │   ├── components/                # reusable UI pieces (.gitkeep)
│   │   ├── pages/
│   │   │   └── Dashboard.jsx          # the web report view
│   │   ├── App.jsx                    # root React component
│   │   └── main.jsx                   # React entry point
│   ├── index.html
│   └── package.json
├── docs/
│   ├── CLAUDE.md                      # how AI agents should work in this repo
│   ├── PROGRESS.md                    # living project status
│   ├── DECISIONS.md                   # decision log
│   └── RUN_TESTS.md                   # how to run the test suite
├── AGENTS.md
├── Member2 changes report.MD
├── Codebase Review & Integration Report.md
└── README.md
```

Team members should read `AGENTS.md` before changing architecture, agent
contracts, data handling, or repository structure.

## 1. Project Overview

Restaurant owners often receive more review data than they can realistically read.
Important business signals can be buried inside unstructured text, such as repeated
complaints about wait time, staff attitude, pricing, food quality, or ambience.

This system automates the pipeline from restaurant lookup to final report:

1. Match a restaurant name against the Yelp dataset.
2. Randomly sample up to 100 review records for that restaurant.
3. Classify sentiment and business aspects in each selected review.
4. Detect patterns across the analysed sample.
5. Infer likely root causes.
6. Produce prioritised recommendations.
7. Generate a readable web report for the business owner.

## 2. Problem Statement

Restaurant feedback is useful, but raw review text is hard to use at scale.
Owners may miss repeated issues because the feedback is scattered across many
individual comments.

This project addresses three problems:

- Recurring complaints are difficult to detect manually.
- Root causes are not obvious from individual reviews.
- Owners need prioritised actions, not only sentiment summaries.

## 3. Proposed Solution

The system uses a supervisor-based multi-agent collaboration pattern with
LangGraph. An Orchestrator Agent manages shared pipeline state, routes work between
specialised agents, validates outputs, and handles failures.

LLM-powered agents use `gpt-5.4` as the primary model and `gpt-5.4-mini` as the
fallback model for generation and correction. If the account does not have access
to those models, configure `OPENAI_MODEL=gpt-5` and
`OPENAI_FALLBACK_MODEL=gpt-5-mini`. Each agent must validate its own output
against a JSON schema before passing results back to the Orchestrator.

## 4. User Flow

This section is reserved for a future user-flow diagram.

Planned flow:

1. User enters restaurant name.
2. System returns possible business matches if the name is ambiguous.
3. User confirms the correct restaurant.
4. System randomly selects up to 100 review records.
5. Agents analyse the selected sample.
6. System generates the final web report.

## 5. Data Source

The project uses the Yelp Open Dataset from Kaggle.

Required files:

- `business.json`: used to resolve a restaurant name to a `business_id`.
- `review.json`: used to retrieve review records for the selected `business_id`.

The dataset contains millions of reviews, so the system must not load or process
the full dataset inside the LLM pipeline. After matching a restaurant, the system
randomly samples a maximum of 100 review records for analysis.

### 5.1 Build the SQLite index (one-time, after pulling)

The raw `.json` files and the generated SQLite database are **git-ignored** (too
large for git), so each teammate builds the index locally from their own copy of
the dataset.

1. Place the Yelp files in `backend/data/raw/`:
   - `yelp_academic_dataset_business.json`
   - `yelp_academic_dataset_review.json`
2. From `backend/`, run the one-time build (~2–3 minutes; scans the 5 GB review
   file once):

   ```bash
   python scripts/build_db.py            # add --rebuild to overwrite an existing DB
   ```

   This creates `backend/data/processed/yelp.db` with a `reviews` and
   `businesses` table indexed by `business_id`.

After this, `loader.load_reviews` queries the index (a few **milliseconds**)
instead of scanning the raw file (~**52 seconds**). Once built, you may delete the
raw `.json` files to reclaim disk — the app reads everything from the DB.

> Fallback: if `yelp.db` is missing but the raw `.json` files are present, the app
> still works by scanning the files directly (just slower). If neither is present,
> there is no data to analyse. Override the DB location with `YELP_DB_PATH`.

## 6. Dataset Plan

This section is reserved for the detailed implementation plan.

Planned approach:

- Store preprocessed review data in a SQLite index keyed on `business_id` (SQLite chosen over Parquet; a pre-extracted subset of demo restaurants is acceptable for a scripted demo).
- Create an index on `business_id` for fast review lookup.
- Create a searchable restaurant-name field for fuzzy matching.
- Return the top 3 restaurant matches when the input name is ambiguous.
- Randomly sample up to 100 review records after a restaurant is confirmed.
- Keep the random seed configurable so demo results can be reproduced.
- Pass only the selected sample into the agent pipeline.

## 7. System Architecture

The system follows a Supervisor / Multi-Agent Collaboration architecture.

The Orchestrator Agent is responsible for:

- Managing the shared pipeline state.
- Calling each agent in the correct order.
- Validating agent status values.
- Handling retries, skips, and halt conditions.
- Returning partial output when the full pipeline cannot complete.

Agent sequence:

1. Data Pipeline
2. Analysis Agent
3. Reasoning Agent
4. Strategic Agent
5. Report Generator Agent

## 8. Agent Roles

| Agent | Role | LLM | Responsibility |
| --- | --- | --- | --- |
| Orchestrator Agent | Supervisor | `gpt-5.4` / `gpt-5.4-mini` | Routes work, checks status, handles failures, retries agents, skips non-critical steps, or halts with partial output. |
| Analysis Agent | Review analysis | `gpt-5.4` / `gpt-5.4-mini` | Classifies each selected review by sentiment and aspect. Runs once per sampled review. |
| Reasoning Agent | Pattern and root-cause reasoning | `gpt-5.4` / `gpt-5.4-mini` | Detects recurring patterns across the analysed sample and proposes likely root causes. |
| Strategic Agent | Recommendation generation | `gpt-5.4` / `gpt-5.4-mini` | Converts root causes into prioritised business actions. |
| Report Generator Agent | Final report generation | `gpt-5.4` / `gpt-5.4-mini` | Produces a structured human-readable web report from upstream outputs. |

## 9. Data Flow Summary

```text
Yelp Dataset
-> Preprocessing
-> Restaurant fuzzy match
-> Random sample, max 100 reviews
-> Pandas DataFrame
-> Orchestrator Agent
-> Analysis Agent
-> Reasoning Agent
-> Strategic Agent
-> Report Generator Agent
-> Web Report
```

All agent communication uses structured JSON payloads. The Orchestrator validates
each agent output before routing to the next step.

## 10. Autonomous Error Handling

The system uses a two-layer error-handling pattern.

### 10.1 Layer 1: Agent Self-Correction

Each LLM-powered agent validates its own JSON output immediately after generation.
If validation fails, the agent retries with a correction prompt that includes:

- The original task.
- The invalid output.
- The validation error.
- The required schema.

Each agent may retry a maximum of 2 times. If the output is still invalid after
2 retries, the agent returns `status: "error"` and passes the error details to the
Orchestrator.

### 10.2 Layer 2: Orchestrator Intervention

If an agent cannot self-correct, the Orchestrator chooses one of three strategies:

| Strategy | When to use | Behaviour |
| --- | --- | --- |
| Retry with simplified prompt | The output is close to valid but still fails schema validation. | The Orchestrator rewrites the prompt with stricter constraints and retries the same agent. |
| Skip agent and flag state | The failed agent is non-critical and the pipeline can continue with partial data. | The Orchestrator marks the step as skipped and downstream agents receive `null` for that input. |
| Halt and return partial report | A critical agent fails and meaningful output cannot be produced. | The Orchestrator stops the pipeline and returns a partial report with a clear error message. |

## 11. Interface Contracts

These contracts define the expected inputs and outputs for each component. They
should not be changed without team agreement because downstream agents depend on
them.

### 11.1 Preprocessed Review Record

```json
{
  "review_id": "abc123",
  "business_id": "business_001",
  "stars": 4,
  "text": "Food was good but the wait was too long.",
  "date": "2024-05-10"
}
```

### 11.2 Analysis Agent Input

```json
{
  "review_id": "abc123",
  "stars": 4,
  "text": "Food was good but the wait was too long.",
  "date": "2024-05-10"
}
```

### 11.3 Analysis Agent Output

```json
{
  "review_id": "abc123",
  "sentiment": "mixed",
  "aspects": [
    {
      "category": "food_quality",
      "label": "positive"
    },
    {
      "category": "wait_time",
      "label": "negative"
    }
  ],
  "status": "success",
  "error_detail": null
}
```

Allowed sentiment values:

- `positive`
- `negative`
- `neutral`
- `mixed`

Allowed aspect categories:

- `food_quality`
- `staff_attitude`
- `pricing`
- `wait_time`
- `ambience`
- `cleanliness`
- `other`

### 11.4 Reasoning Agent Input

```json
{
  "business_id": "business_001",
  "sample_size": 100,
  "analysis_results": [
    {
      "review_id": "abc123",
      "sentiment": "mixed",
      "aspects": [
        {
          "category": "food_quality",
          "label": "positive"
        },
        {
          "category": "wait_time",
          "label": "negative"
        }
      ]
    }
  ]
}
```

### 11.5 Reasoning Agent Output

```json
{
  "patterns": [
    {
      "description": "Wait-time complaints appear repeatedly in the selected sample.",
      "aspect": "wait_time",
      "frequency": 0.42,
      "evidence_review_ids": ["abc123", "abc456"]
    }
  ],
  "root_causes": [
    {
      "pattern": "Repeated wait-time complaints",
      "cause": "Possible staffing or table-turnover issue during busy periods",
      "confidence": "medium"
    }
  ],
  "status": "success",
  "error_detail": null
}
```

### 11.6 Strategic Agent Input

```json
{
  "patterns": [],
  "root_causes": []
}
```

### 11.7 Strategic Agent Output

```json
{
  "recommendations": [
    {
      "priority": 1,
      "issue": "Possible staffing or table-turnover issue during busy periods",
      "action": "Review weekend staffing levels and table assignment workflow.",
      "category": "operations",
      "expected_impact": "Reduce wait-time complaints"
    }
  ],
  "status": "success",
  "error_detail": null
}
```

### 11.8 Report Generator Agent Input

```json
{
  "business_name": "Example Restaurant",
  "sample_size": 100,
  "analysis_summary": {},
  "reasoning_summary": {},
  "recommendations": []
}
```

### 11.9 Report Output Schema

This section is reserved for the final report schema.

Draft schema:

```json
{
  "title": "Restaurant Review Analysis Report",
  "business_name": "Example Restaurant",
  "sample_size": 100,
  "executive_summary": "Short plain-English summary.",
  "key_findings": [],
  "root_causes": [],
  "recommendations": [],
  "limitations": [],
  "status": "success",
  "error_detail": null
}
```

### 11.10 Error Schema

This section is reserved for the final error schema.

Draft schema:

```json
{
  "status": "error",
  "agent": "analysis_agent",
  "error_type": "schema_validation_error",
  "error_detail": "Missing required field: sentiment",
  "retry_count": 2,
  "recoverable": true
}
```

### 11.11 Orchestrator State Schema

This section is reserved for the final Orchestrator state schema.

Draft schema:

```json
{
  "business_id": "business_001",
  "business_name": "Example Restaurant",
  "sample_size": 100,
  "selected_reviews": [],
  "analysis_results": [],
  "reasoning_result": null,
  "strategy_result": null,
  "report_result": null,
  "retry_counts": {
    "analysis_agent": 0,
    "reasoning_agent": 0,
    "strategy_agent": 0,
    "report_agent": 0
  },
  "skipped_agents": [],
  "errors": [],
  "status": "running"
}
```

## 12. Technology Stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.10+ |
| Agent framework | LangChain + LangGraph |
| LLM | OpenAI `gpt-5.4` primary, `gpt-5.4-mini` fallback |
| Data processing | Pandas |
| Business-name matching | Fuzzy matching library such as RapidFuzz |
| Dataset | Yelp Open Dataset from Kaggle |
| Backend | FastAPI |
| UI | React or Streamlit |
| Output | Web report / dashboard |

Note: Streamlit is simpler for the prototype. React can be used if the team wants
a more polished dashboard, but it increases implementation work.

## 13. Milestones

| Phase | Target | Deliverable |
| --- | --- | --- |
| Phase 0 | 25/05 | Project brief reviewed, scope confirmed, interface contracts drafted. |
| Phase 1 | 05/06 | Components working in isolation against mock data, including output validators and self-correction prompts. |
| Phase 2 | 17/06 | Full pipeline running with Yelp data and random sample of up to 100 reviews. Error handling tested with malformed outputs. |
| Phase 3 | 30/06 | Web report polished, recovery strategies tested, final demo prepared. |

## 14. Evaluation Plan

The pipeline is evaluated in three tiers, cheapest and highest-signal first.
Tiers 1 and 2 consume the per-stage JSON written by
`python run_pipeline.py --dump-stages <dir>`, so a pipeline run and its scoring
stay decoupled.

### 14.1 Tier 1 - Deterministic checks (no labels, no API)

These run in CI and catch real bugs (hallucinated categories, invented evidence,
wrong frequencies) with no ground truth required.

Whole pipeline:

- Completion rate: share of runs ending `complete` vs `skip` / `halted`.
- Schema-validity rate: every per-stage payload validates against
  `app/schemas/contracts.py`.
- Latency and LLM cost per 100 reviews.
- Reproducibility: a fixed sample seed yields the same sample twice.
- Degradation correctness: an injected malformed output triggers the designed
  retry / skip / halt path.

Per agent:

- Analysis: every `sentiment` and aspect `category` is one of the allowed enum
  values (anything else is a hallucination).
- Reasoning (groundedness): every `evidence_review_id` is an analysis result
  that actually carries that aspect, and each claimed `frequency` matches the
  frequency recomputed from the analysis results (within tolerance).
- Strategy: each recommendation `issue` traces back to a reasoning pattern or
  root cause; higher-frequency issues get higher priority.
- Report: findings, root causes, and recommendations are subsets of upstream
  outputs (no new claims); all schema sections are populated.

### 14.2 Tier 2 - Labeled gold set (analysis agent only)

The analysis agent is the only stage with objectively checkable answers.
Hand-label 30-50 reviews with sentiment and aspects, then compute sentiment
accuracy and per-aspect macro-F1. Star rating is used only as a noisy
cross-check (5 stars -> positive, 1-2 stars -> negative), not as ground truth.

### 14.3 Tier 3 - Rubric scoring (subjective stages)

Root-cause plausibility, recommendation actionability, and report usefulness
have no formula. They are scored 1-5 against a rubric, by a human (for the final
report) or by an LLM judge using a different / stronger model than the one that
produced the output. Kept small - this informs the demo writeup, not CI.

## 15. Key Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Restaurant name is ambiguous or not found | Return top 3 fuzzy matches and ask the user to confirm. |
| Dataset is too large to process directly | Preprocess into SQLite or Parquet and query by `business_id`. |
| LLM cost is too high | Randomly sample up to 100 reviews and keep the cap configurable. |
| Agent output is invalid | Validate every JSON output and allow up to 2 self-correction retries. |
| Agent enters repeated failure loop | Track retry counts in Orchestrator state and halt or skip after limits are reached. |
| Downstream agents receive missing data | Require downstream agents to handle `null` input and produce partial output when possible. |

## 16. Frontend Dashboard Status

The frontend is now a Vite + React dashboard for viewing the restaurant review
analysis report.

Current frontend entry points:

- `frontend/src/App.jsx`: renders the dashboard page.
- `frontend/src/pages/Dashboard.jsx`: main report dashboard UI.
- `frontend/src/api/client.js`: calls the FastAPI `/api/reports` endpoint.
- `frontend/src/styles.css`: dashboard styling and responsive layout.

The dashboard includes:

- restaurant-name and sample-cap inputs;
- report status display;
- executive summary;
- sample-size, top-issue, issue-frequency, and priority-action KPI cards;
- sentiment distribution bar;
- key findings;
- aspect breakdown table;
- detected patterns;
- root causes;
- prioritised recommendations;
- limitations and error detail display.

The dashboard uses local preview data when the backend returns the current
placeholder response (`status: "not_implemented"`). Once `/api/reports` is wired
to the backend pipeline, the frontend should render the real API response through
the same dashboard components.

Run the frontend locally:

```bash
cd frontend
npm install
npm run dev
```

Build the frontend:

```bash
cd frontend
npm run build
```

The frontend expects the backend API at `http://localhost:8000` by default. Set
`VITE_API_BASE_URL` if the FastAPI server runs elsewhere.

Current limitation: the dashboard is ready to consume a report response, but the
backend `/api/reports` route still needs to call the real pipeline and return the
report schema described above.
