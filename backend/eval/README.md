# eval/ - Three-Tier Evaluation Harness

Implements the evaluation plan in [README section 14](../../README.md) and the
decision log in [docs/DECISIONS.md](../../docs/DECISIONS.md). All tiers consume
the per-stage JSON written by `run_pipeline.py --dump-stages <dir>`, so a
pipeline run and its scoring stay decoupled.

> **STATUS: implemented (2026-07-02).** All four modules are functional; the
> committed fixture (`fixtures/sample_dump/`) lets Tier 1 run fully offline.
> Outstanding: hand-label `gold/analysis_gold.jsonl` for Tier 2, and run Tier 1b
> / Tier 3 live at least once (both need a real dataset + `OPENAI_API_KEY`).
> See `docs/PROGRESS.md`'s 2026-07-02 handoff for details.

## Layout

| Path | Tier | Purpose |
|------|------|---------|
| `common.py` | - | Load a dump dir; `CheckResult`; scorecard printing. |
| `tier1_checks.py` | 1 | Deterministic checks (schema validity, reasoning groundedness, strategy traceability, report-subset, completion). No labels, no API. |
| `harness.py` | 1b | Runs the pipeline: reproducibility, latency & cost, degradation-path correctness. |
| `tier2_analysis.py` | 2 | Analysis-agent gold set: sentiment accuracy + per-aspect macro-F1 (scikit-learn). |
| `tier3_judge.py` | 3 | Rubric LLM-as-judge for subjective stages, using a **different** judge model. |
| `gold/analysis_gold.template.jsonl` | 2 | Labeling template (copy to `analysis_gold.jsonl`, hand-label 30-50). |
| `rubrics/*.md` | 3 | 1-5 rubrics for root-cause / recommendation / report. |
| `fixtures/` | 1 | Committed sample dump so Tier 1 runs in CI without an LLM. |

## Tier summary

- **Tier 1 (deterministic, no labels, CI):** each stage is derivable from the
  previous, so correctness reduces to consistency checks - schema/enum validity,
  reasoning groundedness (evidence ids exist, aspect present, frequency matches
  within tolerance), strategy traceability, report-subset, completion rate.
- **Tier 2 (gold set, analysis only):** the one stage with objective answers.
  Hand-label 30-50 reviews; report sentiment accuracy + per-aspect macro-F1.
  Star rating is a noisy cross-check only.
- **Tier 3 (rubric LLM-judge):** subjective stages scored 1-5 against a rubric by
  a different/stronger judge model (mitigates self-enhancement bias). Small;
  informs the demo writeup, not CI.

## How to run (once implemented)

```bash
cd backend
# produce a dump
python run_pipeline.py --name "McDonald's" --pick 1 --dump-stages out/

python -m eval.tier1_checks out/                              # Tier 1
python -m eval.harness --name "McDonald's" --pick 1 --runs 3  # Tier 1b
python -m eval.tier2_analysis --gold eval/gold/analysis_gold.jsonl   # Tier 2
JUDGE_MODEL=<different-model> python -m eval.tier3_judge out/  # Tier 3
```

## Recommended build order

1. `common.load_dump` + `tier1_checks` + commit a `fixtures/sample_dump` +
   `tests/test_eval_tier1.py` (offline, highest value).
2. `tier2_analysis` once the gold set is labeled.
3. `harness` (latency / repro / degradation).
4. `tier3_judge` (needs a second model).
