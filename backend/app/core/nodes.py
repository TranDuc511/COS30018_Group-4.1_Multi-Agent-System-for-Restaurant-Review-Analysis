"""Real agent node wrappers for the LangGraph pipeline.

Each node takes and returns a :class:`PipelineState`. These are the production
node implementations shared by:

- ``app/core/pipeline.py`` (the runnable pipeline / future FastAPI endpoint),
- ``backend/run_pipeline.py`` (the CLI runner),
- ``tests/test_e2e_pipeline.py`` (the end-to-end test).

Keeping them in one place means the API, the CLI, and the tests all exercise the
exact same wiring.
"""

import os
from typing import Any

from app.agents.analysis_agent import analyse_reviews
from app.agents.reasoning_agent import reason_over_reviews
from app.agents.report_agent import generate_report
from app.agents.strategy_agent import generate_recommendations
from app.core.state import PipelineState

# Number of reviews sent to the analysis LLM per request. Batching keeps the
# total request count low so we stay within Groq's per-minute rate limits.
ANALYSIS_BATCH_SIZE = int(os.getenv("ANALYSIS_BATCH_SIZE", 10))


def _reviews_as_records(reviews: Any) -> list[dict]:
    """Normalise the review container in state to a list of plain dicts.

    Accepts a pandas DataFrame (real data path) or an already-materialised list
    of dicts (tests / in-memory samples).
    """
    if reviews is None:
        return []
    # Avoid importing pandas just to type-check; duck-type on to_dict.
    to_dict = getattr(reviews, "to_dict", None)
    if callable(to_dict):
        return reviews.to_dict(orient="records")
    return list(reviews)


def passthrough_preprocess_node(state: PipelineState) -> PipelineState:
    """No-op preprocess node for callers that load + clean data *before* the graph.

    The CLI runner and API do search/load/preprocess up front and inject the
    finished reviews into ``state['reviews_df']``, so the graph's preprocess step
    just passes the state through.
    """
    return state


def analysis_node(state: PipelineState) -> PipelineState:
    records = _reviews_as_records(state.get("reviews_df"))
    reviews = [
        {
            "review_id": str(r["review_id"]),
            "stars": int(r["stars"]),
            "text": str(r["text"]),
            "date": str(r["date"]),
        }
        for r in records
    ]

    results = []
    for start in range(0, len(reviews), ANALYSIS_BATCH_SIZE):
        batch = reviews[start : start + ANALYSIS_BATCH_SIZE]
        results.extend(analyse_reviews(batch))

    state["analysis_results"] = results
    return state


def reasoning_node(state: PipelineState) -> PipelineState:
    analysis_results = state.get("analysis_results") or []
    cleaned = [
        {
            "review_id": a["review_id"],
            "sentiment": a["sentiment"],
            "aspects": a["aspects"],
        }
        for a in analysis_results
        if a.get("status") == "success"
    ]
    state["reasoning_output"] = reason_over_reviews(
        cleaned, business_id=state.get("business_id", "unknown")
    )
    return state


def strategy_node(state: PipelineState) -> PipelineState:
    reasoning = state.get("reasoning_output") or {}
    payload = {
        "patterns": reasoning.get("patterns", []),
        "root_causes": reasoning.get("root_causes", []),
    }
    state["strategy_output"] = generate_recommendations(payload, use_llm=True)
    return state


def report_node(state: PipelineState) -> PipelineState:
    reasoning = state.get("reasoning_output") or {}
    strategy = state.get("strategy_output") or {}
    payload = {
        "business_name": state.get("business_name", ""),
        "sample_size": len(state.get("analysis_results") or []),
        "analysis_summary": {},
        "reasoning_summary": {
            "patterns": reasoning.get("patterns", []),
            "root_causes": reasoning.get("root_causes", []),
        },
        "recommendations": strategy.get("recommendations", []),
    }
    out = generate_report(payload, use_llm=True)
    state["report_output"] = out
    if out.get("status") == "success":
        state["pipeline_status"] = "complete"
    return state
