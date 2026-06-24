from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.pipeline import run_pipeline
from app.data.loader import load_reviews, search_business
from app.data.preprocessor import preprocess
from app.schemas.contracts import ReportOutput

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
    sample_size: Optional[int] = None  # reserved for P3-1; env var controls cap today


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

    # 1. Resolve the best-matching business.
    matches = search_business(request.restaurant_name, top_n=1)
    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f"No business found matching '{request.restaurant_name}'",
        )
    best = matches[0]
    business_id: str = best["business_id"]
    business_name: str = best["name"]

    # 2. Load and preprocess reviews.
    df = load_reviews(business_id)
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
