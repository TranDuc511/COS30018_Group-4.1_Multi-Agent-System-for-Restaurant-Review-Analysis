# Running and Verifying the Project

Run backend commands from `backend/` so `import app` resolves correctly.

## Setup

```powershell
cd backend
python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill `.env` with a real key and approved provider/model configuration. Never
commit `.env`.

This machine also has a verified interpreter:

```powershell
C:\Users\ADMIN\anaconda3\envs\ml\python.exe
```

Portable project documentation should still prefer a project virtual
environment.

## Backend Tests

```powershell
# All tests. Live tests execute when a key is present.
python -m pytest

# Offline suite only.
python -m pytest -m "not integration"

# Live model tests only.
python -m pytest -m integration

# Full live graph with the fixed in-memory sample.
python -m pytest tests/test_e2e_pipeline.py -v -m integration
```

Verified on 2026-07-14:

- 73 collected;
- 67 offline tests passed;
- 6 live tests deselected.

The live tests use the provider/model from `.env`. Do not label them Gemini,
GPT, Groq, or another provider without recording the actual configuration used.

## Test Scope

| File | Scope | External model |
| --- | --- | --- |
| `test_unit.py` | preprocessing and fuzzy matching | No |
| `test_data_pipeline.py` | mocked flow, seeded raw/SQLite sampling, cap validation | No |
| `test_analysis_agent.py` | analysis and reasoning validation/retries | Mocked |
| `test_strategy_agent.py` | strategy behavior and retries | Mocked |
| `test_report_agent.py` | report behavior and retries | Mocked |
| `test_orchestrator*.py` | retry/skip/halt, provider fallback, chained failures | No |
| `test_graph.py` | happy-path graph wiring | Mocked |
| `test_eval_tier1.py` | deterministic evaluator regressions | No |
| `test_integration.py` | live analysis and reasoning | Yes |
| `test_e2e_pipeline.py` | live full graph on four in-memory reviews | Yes |

Known coverage gaps:

- no endpoint-level FastAPI `TestClient` coverage;
- no SSE integration test;
- no real 5.34 GB raw-loader performance regression;
- no SQLite-builder or partial-DB test;
- no frontend test or lint script;
- no CI workflow.

## Evaluation

From `backend/`:

```powershell
# Deterministic fixture.
python -m eval.tier1_checks eval/fixtures/sample_dump

# Offline degradation scenarios.
python -m eval.harness --skip-live

# Live reproducibility and latency/cost.
python -m eval.harness --name "McDonald's" --pick 1 --runs 3

# Build Tier 2 JSONL after human labeling.
python eval/gold/build_gold_jsonl.py eval/gold/tier2_gold_labeling_worksheet.xlsx
python -m eval.tier2_analysis --gold eval/gold/analysis_gold.jsonl

# Tier 3 against a real stage dump. JUDGE_MODEL must differ from OPENAI_MODEL.
python -m eval.tier3_judge out/
```

Verified on 2026-07-14:

- Tier 1 fixture: 16/16 passed.
- Degradation harness: 6/6 passed.

The focused chained-failure test verifies production node recovery state without
making live model calls. The synthetic harness still does not prove live
provider behavior.

## Run the API

```powershell
uvicorn app.main:app --reload
```

Process-level check:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

`/health` does not check the dataset, DB, API key, or provider.

## Run the Pipeline

```powershell
# Interactive.
python run_pipeline.py

# Select a match non-interactively and dump stages.
python run_pipeline.py --name "McDonald's" --pick 1 --sample-size 100 --dump-stages out/
```

Without `backend/data/processed/yelp.db`, a run scans the 5.34 GB raw review
file. Build the DB before timing or demonstrating the pipeline:

```powershell
python scripts/build_db.py
```

## Frontend

```powershell
cd ../frontend
npm install
npm run dev
```

Production build:

```powershell
npm run build
```

Verified on 2026-07-14: build passed.

There is currently no frontend test or lint command.

## Interpretation Rules

- Offline test success proves code-path behavior, not live model quality.
- The E2E integration test proves model + graph wiring, not Yelp loading or API.
- The loader uses `RANDOM_SEED`; identical candidate IDs, cap, and seed must
  produce identical sampled IDs.
- Record provider, model, dataset path, business ID, cap, and stage dump for any
  reported live result.
