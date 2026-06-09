"""Interactive CLI: run the full multi-agent pipeline on a real restaurant.

Flow:
    restaurant name -> fuzzy search -> pick a match -> load + sample reviews
    -> analysis -> reasoning -> strategy -> report -> print the report.

Usage (from the backend/ directory, with the venv active):
    python run_pipeline.py
    python run_pipeline.py --name "McDonald's"          # skip the name prompt
    python run_pipeline.py --name "McDonald's" --pick 1 # fully non-interactive

Requires OPENAI_API_KEY (the agents make real LLM calls). The dataset files must
be present under backend/data/raw/ (see RUN_TESTS.md / README).
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv

from app.core.pipeline import run_pipeline
from app.data import loader, preprocessor


def _choose_match(results: list[dict], pick: int | None) -> dict | None:
    print()
    for i, r in enumerate(results, start=1):
        print(
            f"{i}. {r['name']} — {r.get('address', '')}, {r.get('city', '')}, "
            f"{r.get('state', '')} (reviews={r.get('review_count', 0)}, "
            f"score={r.get('score')}, id={r['business_id']})"
        )

    if pick is not None:
        if not 1 <= pick <= len(results):
            print(f"--pick {pick} is out of range (1-{len(results)}).")
            return None
        return results[pick - 1]

    while True:
        try:
            choice = int(input(f"\nSelect a match (1-{len(results)}): "))
            if 1 <= choice <= len(results):
                return results[choice - 1]
            print(f"Please enter a number from 1 to {len(results)}.")
        except ValueError:
            print("Please enter a number.")
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return None


def _print_report(report: dict) -> None:
    print("\n" + "=" * 70)
    print(report.get("title", "Report"))
    print("=" * 70)
    print(f"Business     : {report.get('business_name', '')}")
    print(f"Sample size  : {report.get('sample_size', 0)} reviews")
    print(f"\nExecutive summary:\n  {report.get('executive_summary', '')}")

    findings = report.get("key_findings") or []
    if findings:
        print("\nKey findings:")
        for f in findings:
            print(f"  - {f}")

    causes = report.get("root_causes") or []
    if causes:
        print("\nLikely root causes:")
        for c in causes:
            print(f"  - [{c.get('confidence', '?')}] {c.get('cause', '')}")

    recs = report.get("recommendations") or []
    if recs:
        print("\nRecommendations (prioritised):")
        for r in recs:
            print(f"  {r.get('priority', '?')}. {r.get('action', '')}")
            print(f"     issue: {r.get('issue', '')} | impact: {r.get('expected_impact', '')}")

    limitations = report.get("limitations") or []
    if limitations:
        print("\nLimitations:")
        for limitation in limitations:
            print(f"  - {limitation}")
    print("=" * 70)


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run the full review-analysis pipeline.")
    parser.add_argument("--name", help="Restaurant name (skips the prompt).")
    parser.add_argument("--pick", type=int, help="Auto-select the Nth match (1-based).")
    parser.add_argument("--json", action="store_true", help="Print the raw report JSON.")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set — the agents need it to run. See RUN_TESTS.md.")
        return 1

    business_name = args.name or input("Restaurant name: ")

    print("Searching businesses...")
    results = loader.search_business(business_name)
    if not results:
        print("No matching business found.")
        return 1

    selected = _choose_match(results, args.pick)
    if selected is None:
        return 1
    print(f"\n>> Selected: {selected['name']} ({selected['business_id']})")

    print("Loading reviews...")
    df_raw = loader.load_reviews(selected["business_id"])
    if df_raw.empty:
        print("No reviews found for that business. Stopping.")
        return 1

    df_clean = preprocessor.preprocess(df_raw)
    print(f"Running pipeline on {len(df_clean)} reviews (this makes live LLM calls)...")

    final_state = run_pipeline(
        business_name=selected["name"],
        reviews=df_clean,
        business_id=selected["business_id"],
    )

    status = final_state["pipeline_status"]
    print(f"\nPipeline status: {status}")
    if final_state.get("skipped_agents"):
        print(f"Skipped stages : {final_state['skipped_agents']}")

    report = final_state.get("report_output")
    if not report or report.get("status") != "success":
        print("No successful report was produced.")
        if report:
            print(f"Report error: {report.get('error_detail')}")
        return 2

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        _print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
