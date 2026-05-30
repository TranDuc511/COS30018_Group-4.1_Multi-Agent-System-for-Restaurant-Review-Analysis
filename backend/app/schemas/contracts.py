from typing import Literal

from pydantic import BaseModel


class ReviewRecord(BaseModel):
    review_id: str
    business_id: str
    stars: int
    text: str
    date: str


class AgentError(BaseModel):
    status: Literal["error"] = "error"
    agent: str
    error_type: str
    error_detail: str
    retry_count: int
    recoverable: bool


# ── Analysis Agent contracts ──────────────────────────────────────────────────

class AspectLabel(BaseModel):
    category: Literal[
        "food_quality", "staff_attitude", "pricing",
        "wait_time", "ambience", "cleanliness", "other"
    ]
    label: Literal["positive", "negative", "neutral"]


class AnalysisOutput(BaseModel):
    review_id: str
    sentiment: Literal["positive", "negative", "neutral", "mixed"]
    aspects: list[AspectLabel]
    status: Literal["success", "error"]
    error_detail: str | None = None


# ── Reasoning Agent contracts ─────────────────────────────────────────────────

class Pattern(BaseModel):
    description: str
    aspect: str
    frequency: float          # proportion of reviews mentioning this aspect negatively
    evidence_review_ids: list[str]


class RootCause(BaseModel):
    pattern: str
    cause: str
    confidence: Literal["low", "medium", "high"]


class ReasoningOutput(BaseModel):
    patterns: list[Pattern]
    root_causes: list[RootCause]
    status: Literal["success", "error"]
    error_detail: str | None = None

