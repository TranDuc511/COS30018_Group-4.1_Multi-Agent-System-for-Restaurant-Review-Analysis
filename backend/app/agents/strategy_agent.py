"""Strategic Agent — converts patterns and root causes into prioritised actions.

Supports a deterministic mode (use_llm=False) used by the tests and offline runs,
and an LLM-backed mode (use_llm=True) that uses the configured OpenAI models.
"""

import json
import os
from typing import Any

from dotenv import load_dotenv
from pydantic import ValidationError

from app.schemas.contracts import StrategicAgentInput, StrategyOutput

_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}

# Maps a review aspect to the business area a recommendation belongs to.
_ASPECT_CATEGORY = {
    "food_quality": "food",
    "staff_attitude": "service",
    "pricing": "pricing",
    "wait_time": "operations",
    "ambience": "ambience",
    "cleanliness": "facilities",
    "other": "general",
}

_SYSTEM_PROMPT = """\
You are a restaurant operations strategist. Given recurring review patterns and
their likely root causes, produce prioritised, concrete business actions.

Return a JSON object with:
- recommendations: list ordered most-important first, each with:
  - priority: integer starting at 1
  - issue: the underlying problem being addressed
  - action: a concrete, specific action the owner can take
  - category: business area (e.g. "operations", "pricing", "service", "food")
  - expected_impact: the improvement expected from the action
- status: "success"
- error_detail: null

Return only valid JSON."""


def _load_environment() -> None:
    load_dotenv()


def _candidate_models() -> list[str]:
    return [
        os.getenv("OPENAI_MODEL", "gpt-5.4"),
        os.getenv("OPENAI_FALLBACK_MODEL", "gpt-5.4-mini"),
    ]


def _completion_options() -> dict[str, Any]:
    return {"response_format": {"type": "json_object"}, "temperature": 0}


def _error(detail: str) -> dict:
    return {"recommendations": [], "status": "error", "error_detail": detail}


def _match_pattern(patterns: list[dict], target: str) -> dict | None:
    for pattern in patterns:
        if pattern.get("description") == target:
            return pattern
    return None


def _deterministic_recommendations(patterns: list[dict], root_causes: list[dict]) -> dict:
    ranked = []
    for root_cause in root_causes:
        match = _match_pattern(patterns, root_cause.get("pattern"))
        aspect = match.get("aspect", "other") if match else "other"
        frequency = match.get("frequency", 0.0) if match else 0.0
        ranked.append(
            {
                "issue": root_cause.get("cause", ""),
                "aspect": aspect,
                "category": _ASPECT_CATEGORY.get(aspect, "general"),
                "frequency": frequency,
                "confidence": root_cause.get("confidence", "low"),
            }
        )

    ranked.sort(
        key=lambda r: (_CONFIDENCE_RANK.get(r["confidence"], 0), r["frequency"]),
        reverse=True,
    )

    recommendations = []
    for priority, item in enumerate(ranked, start=1):
        aspect_label = item["aspect"].replace("_", " ")
        recommendations.append(
            {
                "priority": priority,
                "issue": item["issue"],
                "action": f"Address {aspect_label}: {item['issue']}",
                "category": item["category"],
                "expected_impact": f"Reduce {aspect_label} complaints",
            }
        )

    return {"recommendations": recommendations, "status": "success", "error_detail": None}


def _llm_recommendations(payload: dict) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
    user_prompt = json.dumps(payload, indent=2)
    last_error: Exception | None = None

    for model in _candidate_models():
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                **_completion_options(),
            )
            data = json.loads(response.choices[0].message.content)
            validated = StrategyOutput.model_validate(
                {
                    "recommendations": data.get("recommendations", []),
                    "status": "success",
                    "error_detail": None,
                }
            )
            return validated.model_dump()
        except Exception as exc:  # noqa: BLE001 - fall through to fallback model
            last_error = exc

    return _error(f"LLM recommendation generation failed: {last_error}")


def generate_recommendations(payload: dict, use_llm: bool = True) -> dict:
    try:
        StrategicAgentInput.model_validate(payload)
    except ValidationError as exc:
        return _error(f"Invalid strategic agent input: {exc}")

    patterns = payload.get("patterns", [])
    root_causes = payload.get("root_causes", [])

    if use_llm:
        _load_environment()
        if not os.getenv("OPENAI_API_KEY"):
            return _error("OPENAI_API_KEY is not set.")
        return _llm_recommendations(payload)

    return _deterministic_recommendations(patterns, root_causes)
