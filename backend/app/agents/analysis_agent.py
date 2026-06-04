import json

from app.agents.base_agent import BaseAgent
from app.schemas.contracts import AgentError, AnalysisOutput

_SYSTEM_PROMPT = """\
You are a restaurant review analyst. Given a single review, return a JSON object with:

- review_id: the review's ID (string)
- sentiment: overall sentiment — one of "positive", "negative", "neutral", "mixed"
- aspects: list of aspects explicitly mentioned or clearly implied in the review, each with:
  - category: one of "food_quality", "staff_attitude", "pricing", "wait_time", "ambience", "cleanliness", "other"
  - label: sentiment for that aspect — one of "positive", "negative", "neutral"
- status: "success"
- error_detail: null

Only include aspects that are actually present in the review. Return only valid JSON."""


class AnalysisAgent(BaseAgent):
    def run(self, input_data: dict) -> dict:
        original_task = (
            f"Analyse the following restaurant review and return structured JSON:\n"
            f"{json.dumps(input_data, indent=2)}"
        )
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": original_task},
        ]

        result, error, error_type, attempts = self._run_with_retry(messages, AnalysisOutput, original_task)

        if result is not None:
            return result

        return AgentError(
            agent="analysis_agent",
            error_type=error_type or "unknown_error",
            error_detail=error or "Unknown error",
            retry_count=attempts,
            recoverable=False,
        ).model_dump()


def analyse_review(review: dict) -> dict:
    return AnalysisAgent().run(review)
