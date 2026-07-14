import json
import time
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.pipeline import build_pipeline, initial_state, run_pipeline
from app.data.loader import MAX_REVIEWS, load_reviews, search_business
from app.data.preprocessor import preprocess
from app.schemas.contracts import ReportOutput

# Agent stages, in execution order, used by the streaming progress endpoint to
# announce the next running stage as each node completes.
_AGENT_SEQUENCE = ["analysis_agent", "reasoning_agent", "strategy_agent", "report_agent"]

app = FastAPI(title="COS30018 Restaurant Review Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class ReportRequest(BaseModel):
    restaurant_name: str
    business_id: Optional[str] = None  # when set, skip search and use this business directly
    sample_size: Optional[int] = Field(default=None, ge=1, le=MAX_REVIEWS)


class BusinessMatch(BaseModel):
    business_id: str
    name: str
    address: str
    city: str
    state: str
    review_count: int
    score: float


class ReportResponse(ReportOutput):
    analysis_summary: dict[str, Any] = {}
    reasoning_summary: dict[str, Any] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_analysis_summary(analysis_results: list[dict]) -> dict[str, Any]:
    sentiment_counts: dict[str, int] = {
        "positive": 0, "negative": 0, "neutral": 0, "mixed": 0
    }
    aspect_counts: dict[str, dict[str, int]] = {}

    for result in analysis_results:
        if result.get("status") != "success":
            continue
        s = result.get("sentiment", "neutral")
        if s in sentiment_counts:
            sentiment_counts[s] += 1
        for aspect in result.get("aspects", []):
            cat = aspect.get("category", "other")
            label = aspect.get("label", "neutral")
            if cat not in aspect_counts:
                aspect_counts[cat] = {"positive": 0, "negative": 0, "neutral": 0}
            aspect_counts[cat][label] = aspect_counts[cat].get(label, 0) + 1

    return {"sentiment_counts": sentiment_counts, "aspect_counts": aspect_counts}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/businesses/search", response_model=list[BusinessMatch])
def search_businesses(name: str, top_n: int = 3):
    """Fuzzy-search businesses by name. Returns top matches for the frontend
    to display a confirmation UI before running the full pipeline."""
    matches = search_business(name, top_n=top_n)
    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f"No businesses found matching '{name}'",
        )
    return matches


@app.post("/api/reports", response_model=ReportResponse)
def create_report(request: ReportRequest):
    """Run the full multi-agent pipeline for a restaurant and return the report."""

    # 1. Resolve the business. If the caller already picked one (business_id),
    #    use it directly; otherwise fall back to the best fuzzy match.
    if request.business_id:
        business_id: str = request.business_id
        business_name: str = request.restaurant_name
    else:
        matches = search_business(request.restaurant_name, top_n=1)
        if not matches:
            raise HTTPException(
                status_code=404,
                detail=f"No business found matching '{request.restaurant_name}'",
            )
        best = matches[0]
        business_id = best["business_id"]
        business_name = best["name"]

    # 2. Load and preprocess reviews.
    df = load_reviews(business_id, request.sample_size)
    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No reviews found for '{business_name}'",
        )
    df = preprocess(df)

    # 3. Run the pipeline.
    state = run_pipeline(business_name, df, business_id)

    # 4. Surface pipeline failures as HTTP errors.
    if state.get("pipeline_status") == "halted":
        errors = state.get("errors") or {}
        detail = "; ".join(f"{k}: {v}" for k, v in errors.items()) or "Pipeline halted"
        raise HTTPException(status_code=500, detail=detail)

    report = state.get("report_output")
    if not report or report.get("status") != "success":
        detail = (report or {}).get("error_detail") or "Pipeline produced no valid report"
        raise HTTPException(status_code=500, detail=detail)

    # 5. Augment with computed summaries that the frontend expects.
    analysis_results = state.get("analysis_results") or []
    reasoning = state.get("reasoning_output") or {}

    return {
        **report,
        "analysis_summary": _build_analysis_summary(analysis_results),
        "reasoning_summary": {"patterns": reasoning.get("patterns", [])},
    }


@app.get("/api/reports/stream")
def stream_report(
    restaurant_name: str,
    business_id: Optional[str] = None,
    sample_size: Optional[int] = Query(default=None, ge=1, le=MAX_REVIEWS),
):
    """Run the pipeline and stream per-stage progress events (Server-Sent Events).

    Emits one ``stage_start`` and one ``stage_end`` (with ``duration_ms``) per
    stage so the frontend can show a live timeline and spot the slowest step.
    The final ``done`` event carries the full report payload.
    """

    def sse(payload: dict[str, Any]) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def event_stream():
        try:
            # ── Data stages (run outside the graph, timed individually) ──────
            yield sse({"type": "stage_start", "stage": "search_business"})
            t0 = time.perf_counter()
            if business_id:
                # Caller already picked a business — no fuzzy search needed.
                best = {"business_id": business_id, "name": restaurant_name}
            else:
                matches = search_business(restaurant_name, top_n=1)
                if not matches:
                    yield sse({"type": "error", "stage": "search_business",
                               "detail": f"No business found matching '{restaurant_name}'"})
                    return
                best = matches[0]
            yield sse({"type": "stage_end", "stage": "search_business",
                       "duration_ms": round((time.perf_counter() - t0) * 1000),
                       "info": best["name"]})

            yield sse({"type": "stage_start", "stage": "load_reviews"})
            t0 = time.perf_counter()
            df = load_reviews(best["business_id"], sample_size)
            if df.empty:
                yield sse({"type": "error", "stage": "load_reviews",
                           "detail": f"No reviews found for '{best['name']}'"})
                return
            yield sse({"type": "stage_end", "stage": "load_reviews",
                       "duration_ms": round((time.perf_counter() - t0) * 1000),
                       "info": f"{len(df)} reviews"})

            yield sse({"type": "stage_start", "stage": "preprocess"})
            t0 = time.perf_counter()
            df = preprocess(df)
            yield sse({"type": "stage_end", "stage": "preprocess",
                       "duration_ms": round((time.perf_counter() - t0) * 1000),
                       "info": f"{len(df)} cleaned"})

            # ── Agent stages (driven through the graph, one event per node) ──
            graph = build_pipeline()
            state = initial_state(best["name"], df, best["business_id"])

            yield sse({"type": "stage_start", "stage": "analysis_agent"})
            last = time.perf_counter()
            final_state: dict[str, Any] | None = None

            for chunk in graph.stream(state, stream_mode="updates"):
                for node_name, update in chunk.items():
                    if isinstance(update, dict):
                        final_state = update
                    if node_name in _AGENT_SEQUENCE:
                        yield sse({"type": "stage_end", "stage": node_name,
                                   "duration_ms": round((time.perf_counter() - last) * 1000)})
                        last = time.perf_counter()
                        idx = _AGENT_SEQUENCE.index(node_name)
                        if idx + 1 < len(_AGENT_SEQUENCE):
                            yield sse({"type": "stage_start",
                                       "stage": _AGENT_SEQUENCE[idx + 1]})
                    elif node_name == "error_handler":
                        yield sse({"type": "notice", "stage": "error_handler",
                                   "detail": "recovery handler ran"})

            # ── Final report ────────────────────────────────────────────────
            final_state = final_state or {}
            report = final_state.get("report_output")
            if not report or report.get("status") != "success":
                detail = (report or {}).get("error_detail") or "Pipeline produced no valid report"
                yield sse({"type": "error", "stage": "report_agent", "detail": detail})
                return

            analysis_results = final_state.get("analysis_results") or []
            reasoning = final_state.get("reasoning_output") or {}
            full_report = {
                **report,
                "analysis_summary": _build_analysis_summary(analysis_results),
                "reasoning_summary": {"patterns": reasoning.get("patterns", [])},
            }
            yield sse({"type": "done", "report": full_report})
        except Exception as exc:  # surface any unexpected failure to the client
            yield sse({"type": "error", "detail": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
