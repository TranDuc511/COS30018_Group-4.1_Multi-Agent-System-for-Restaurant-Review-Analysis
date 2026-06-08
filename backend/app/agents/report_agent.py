"""Report Generator Agent — builds the final human-readable report.

Supports a deterministic mode (use_llm=False) used by the tests and offline runs,
and an LLM-backed mode (use_llm=True) that uses the configured OpenAI models.
"""

import json
import os
from typing import Any

from dotenv import load_dotenv
from pydantic import ValidationError

from app.schemas.contracts import ReportGeneratorInput, ReportOutput

_REPORT_TITLE = "Restaurant Review Analysis Report"

_BASE_LIMITATIONS = [
    "Analysis is based on a random sample of up to 100 reviews and may not represent every customer.",
    "Sentiment and aspect labels are produced automatically and may contain classification errors.",
]

_SYSTEM_PROMPT = """\
You are a business analyst writing a concise report for a restaurant owner.
Given upstream analysis, reasoning, and recommendation outputs, produce a clear report.

Return a JSON object with:
- title: "Restaurant Review Analysis Report"
- business_name: the restaurant name
- sample_size: number of reviews analysed
- executive_summary: a short plain-English summary
- key_findings: list of the most important findings
- root_causes: list of likely root causes
- recommendations: prioritised actions
- limitations: list of caveats about the analysis
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


def _build_key_findings(patterns: list[dict]) -> list[str]:
    if not patterns:
        return ["No major recurring pattern was provided by upstream agents."]
    return [p.get("description", "") for p in patterns if p.get("description")]


def _build_executive_summary(business_name: str, sample_size: int, recommendations: list[dict]) -> str:
    if not recommendations:
        return (
            f"This report summarises {sample_size} sampled reviews for {business_name}. "
            "No prioritised recommendations were produced by the upstream agents."
        )
    actions = "; ".join(r.get("action", "") for r in recommendations if r.get("action"))
    return (
        f"Based on {sample_size} sampled reviews for {business_name}, the priority actions are: "
        f"{actions}"
    )


def _build_limitations(sample_size: int) -> list[str]:
    limitations = list(_BASE_LIMITATIONS)
    if sample_size == 0:
        limitations.append(
            "No review records were available for this restaurant, so the findings are limited."
        )
    return limitations


def _deterministic_report(payload: dict) -> dict:
    business_name = payload.get("business_name", "")
    sample_size = payload.get("sample_size", 0)
    reasoning_summary = payload.get("reasoning_summary") or {}
    recommendations = payload.get("recommendations") or []
    patterns = reasoning_summary.get("patterns") or []
    root_causes = reasoning_summary.get("root_causes") or []

    return {
        "title": _REPORT_TITLE,
        "business_name": business_name,
        "sample_size": sample_size,
        "executive_summary": _build_executive_summary(business_name, sample_size, recommendations),
        "key_findings": _build_key_findings(patterns),
        "root_causes": root_causes,
        "recommendations": recommendations,
        "limitations": _build_limitations(sample_size),
        "status": "success",
        "error_detail": None,
    }


def _llm_report(payload: dict) -> dict:
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
            data.setdefault("title", _REPORT_TITLE)
            data.setdefault("status", "success")
            data.setdefault("error_detail", None)
            validated = ReportOutput.model_validate(data)
            return validated.model_dump()
        except Exception as exc:  # noqa: BLE001 - fall through to fallback model
            last_error = exc

    return _error(f"LLM report generation failed: {last_error}")


def generate_report(payload: dict, use_llm: bool = True) -> dict:
    try:
        ReportGeneratorInput.model_validate(payload)
    except ValidationError as exc:
        return _error(f"Invalid report generator input: {exc}")

    if use_llm:
        _load_environment()
        if not os.getenv("OPENAI_API_KEY"):
            return _error("OPENAI_API_KEY is not set.")
        return _llm_report(payload)

    return _deterministic_report(payload)
