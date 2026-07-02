# RUN_TESTS.md

How to run the test suite. All commands assume you are in the **`backend/`**
directory and using the project virtualenv at `backend/venv/`.

## Setup (once)

```bash
cd backend
python -m venv venv               # if venv/ does not exist yet
./venv/Scripts/Activate.ps1       # PowerShell (Windows)
# source venv/bin/activate        # macOS/Linux
pip install -r requirements.txt
```

If you'd rather not activate, call the interpreter directly:
`./venv/Scripts/python.exe -m pytest ...`

## Configuration

- Copy `.env.example` to `.env` and fill in values. **Do not commit `.env`.**
- `OPENAI_API_KEY` is required for integration/e2e tests. Without it, those tests
  **auto-skip** (unit tests still run).
- The current `.env` targets Gemini's OpenAI-compatible endpoint
  (`OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`,
  `OPENAI_MODEL=gemini-2.5-flash`).

> ⚠️ `backend/.env.example` has historically shipped a real-looking key. Replace
> it with a placeholder and rotate any exposed key.

## Common commands

From `backend/`:

```bash
# Everything (58 tests; integration/e2e need a key)
python -m pytest

# Fast unit suite only — no LLM calls, no network (52 tests)
python -m pytest -m "not integration"

# Only the real-LLM tests (needs OPENAI_API_KEY)
python -m pytest -m integration

# A single file, verbose
python -m pytest tests/test_e2e_pipeline.py -v

# A single test
python -m pytest tests/test_orchestrator_routing.py::test_halt_ends_pipeline -v
```

## Test markers

Defined in `pytest.ini`:

- `integration` — makes real LLM API calls. Deselect with `-m "not integration"`.

## What each test group covers

| File | Scope | LLM |
| --- | --- | --- |
| `test_unit.py` | preprocessing + fuzzy matching | none |
| `test_data_pipeline.py` | data flow (search → load → preprocess → save); also an interactive demo via `python -m tests.test_data_pipeline` | mocked |
| `test_analysis_agent.py` | analysis + reasoning agent logic | mocked |
| `test_strategy_agent.py` / `test_report_agent.py` | strategy / report agents | mocked |
| `test_orchestrator.py` / `test_orchestrator_routing.py` | retry/skip/halt decisions and routing | none |
| `test_graph.py` / `test_state.py` | full graph wiring + state | mocked agents |
| `test_integration.py` | analysis + reasoning | **real Gemini** |
| `test_e2e_pipeline.py` | **full pipeline, all 5 stages through the real graph** | **real Gemini** |

## Running the full pipeline (not a test)

From `backend/` (needs `OPENAI_API_KEY` and the dataset files):

```bash
# Interactive
python run_pipeline.py

# Non-interactive, and dump each agent phase's JSON for inspection / evaluation
python run_pipeline.py --name "McDonald's" --pick 1 --dump-stages out/
```

`--dump-stages` writes `analysis|reasoning|strategy|report.json` plus
`_summary.json` from the final pipeline state - the input the Tier-1 evaluator
consumes (README section 14).

## Notes & gotchas

- **Run from `backend/`.** `pytest.ini` sets `pythonpath = .` and `conftest.py`
  adds the backend root to `sys.path`, so `import app` / `import tests` work — but
  only when launched from `backend/`.
- **Use the venv interpreter.** System Python lacks the dependencies.
- **Real-LLM tests are non-deterministic.** The e2e test retries the whole
  pipeline up to 3 times to absorb occasional model/schema failures and the
  pipeline's own graceful degradation. A single failed attempt is not necessarily
  a regression — read the assertion message.
- **Interactive data demo** (`python -m tests.test_data_pipeline`) scans the full
  5.3 GB review file linearly on the first review lookup; expect a delay.
