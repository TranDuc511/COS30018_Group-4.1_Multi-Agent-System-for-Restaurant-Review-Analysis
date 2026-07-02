# eval/fixtures/

`sample_dump/` is a committed `--dump-stages`-shaped output so Tier 1 checks can
run in CI with **no LLM / no API**.

## Provenance of `sample_dump/`

Built deterministically, not from a live pipeline run:

- `analysis.json` / `reasoning.json` — hand-authored review data (12 reviews for
  "Example Bistro", same style as `tests/mock_data.py`), with every pattern's
  `frequency` and `evidence_review_ids` computed programmatically from the
  authored analysis so the numbers are genuinely consistent, not just typed in.
- `strategy.json` / `report.json` — produced by the **real** deterministic
  (non-LLM) agent code paths: `generate_recommendations(..., use_llm=False)`
  and `generate_report(..., use_llm=False)`. No mocking involved for these two.

This makes the fixture fully offline and reproducible — the ideal property for
a permanent CI fixture (no flakiness, no API key ever needed to run Tier 1).
A live-LLM dump (`python run_pipeline.py --name "<restaurant>" --pick 1
--dump-stages eval/fixtures/live_dump`) can be added alongside this one later
for a realism spot-check, but is not required for CI.

`tests/test_eval_tier1.py` runs `eval.tier1_checks.run_all("eval/fixtures/sample_dump")`
and asserts all 16 checks pass (i.e. this is a "healthy" fixture — every
groundedness/traceability/subset check succeeds by construction).

Keep fixtures small and free of anything sensitive - they are committed to git.
