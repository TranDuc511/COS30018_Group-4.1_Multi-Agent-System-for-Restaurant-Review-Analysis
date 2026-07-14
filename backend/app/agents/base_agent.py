import json
import logging
import os
from abc import ABC, abstractmethod
from collections.abc import Callable

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

load_dotenv()

_CORRECTION_PROMPT = """\
You are correcting your previous output.

Original task:
{original_task}

Your previous output (invalid):
{invalid_output}

Validation error:
{validation_error}

Required JSON schema:
{schema}

Return only valid JSON that matches the schema. Do not add explanation."""


class BaseAgent(ABC):
    MAX_RETRIES = 2

    # Cumulative prompt+completion tokens across all agent instances, used by
    # eval/harness.py to report LLM cost per 100 reviews. Additive/optional:
    # if the provider's response has no `usage` field this simply stays 0.
    total_tokens_used: int = 0

    @classmethod
    def reset_token_usage(cls) -> None:
        cls.total_tokens_used = 0

    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )
        self._model = os.getenv("OPENAI_MODEL", "gemini-2.5-flash")
        self._fallback_model = os.getenv("OPENAI_FALLBACK_MODEL", "gemini-2.5-flash")

    def _record_usage(self, resp) -> None:
        usage = getattr(resp, "usage", None)
        tokens = getattr(usage, "total_tokens", None) if usage is not None else None
        if tokens:
            BaseAgent.total_tokens_used += tokens

    def _call_llm(self, messages: list[dict], model: str | None = None) -> str:
        target = model or self._model
        try:
            resp = self._client.chat.completions.create(
                model=target,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
            self._record_usage(resp)
            return resp.choices[0].message.content
        except Exception as primary_exc:
            if target == self._fallback_model:
                raise
            logger.warning("Primary model %s failed (%s), switching to fallback %s", target, primary_exc, self._fallback_model)
            resp = self._client.chat.completions.create(
                model=self._fallback_model,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
            self._record_usage(resp)
            return resp.choices[0].message.content

    def _run_with_retry(
        self,
        initial_messages: list[dict],
        schema_model: type[BaseModel],
        original_task: str,
        result_validator: Callable[[dict], None] | None = None,
    ) -> tuple[dict | None, str | None, str | None, int]:
        """Returns (result, error_detail, error_type, attempts_made)."""
        messages = list(initial_messages)
        last_raw: str | None = None
        last_error: str | None = None
        last_error_type: str | None = None
        attempt = 0

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                last_raw = self._call_llm(messages)
            except Exception as exc:
                last_error = str(exc)
                last_error_type = "api_error"
                logger.error("LLM API call failed on attempt %d: %s", attempt, last_error)
                break
            try:
                parsed = json.loads(last_raw)
                validated = schema_model.model_validate(parsed)
                result = validated.model_dump()
                if result_validator:
                    result_validator(result)
                return result, None, None, attempt
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = str(exc)
                last_error_type = "schema_validation_error"
                if attempt < self.MAX_RETRIES:
                    correction = _CORRECTION_PROMPT.format(
                        original_task=original_task,
                        invalid_output=last_raw,
                        validation_error=last_error,
                        schema=json.dumps(schema_model.model_json_schema(), indent=2),
                    )
                    messages = list(initial_messages)
                    messages.append({"role": "assistant", "content": last_raw})
                    messages.append({"role": "user", "content": correction})

        return None, last_error, last_error_type, attempt

    @abstractmethod
    def run(self, input_data: dict) -> dict:
        pass
