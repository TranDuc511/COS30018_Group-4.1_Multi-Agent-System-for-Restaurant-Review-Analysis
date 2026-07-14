import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

load_dotenv()


class OrchestratorAgent:
    # Critical agents are stored WITHOUT the "_agent" suffix. Matching is
    # suffix-insensitive, so "analysis", "analysis_agent" and "ANALYSIS"
    # all resolve to the same agent. If a critical agent fails it must halt
    # the pipeline rather than be skipped.
    CRITICAL_AGENTS = {"analysis", "reasoning"}
    MAX_RECOVERY_RETRIES = 2

    def __init__(self):
        # LLM client is created lazily so importing/instantiating the
        # orchestrator (e.g. when building the graph) does not require
        # credentials. It is only built when an LLM decision is needed.
        self._llm = None

    def _get_llm(self) -> ChatOpenAI:
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gemini-2.5-flash"),
                base_url=os.getenv("OPENAI_BASE_URL"),
                temperature=0,
            )
        return self._llm

    @staticmethod
    def _normalize(agent: str) -> str:
        return (agent or "").strip().lower().removesuffix("_agent")

    def is_critical(self, agent: str) -> bool:
        return self._normalize(agent) in self.CRITICAL_AGENTS

    def decide_recovery(self, failed_agent: str, error_detail: str, retry_count: int) -> str:
        """Choose a recovery strategy: retry | skip | halt."""
        critical = self.is_critical(failed_agent)

        # Hard rules first — no need to call the LLM.
        if retry_count >= self.MAX_RECOVERY_RETRIES:
            return "halt" if critical else "skip"

        prompt = f"""
You are supervising an AI pipeline that analyses restaurant reviews.
An agent has failed. Decide the recovery strategy.

Failed agent: {failed_agent}
Error: {error_detail}
Retries already attempted: {retry_count}
Is this a critical agent (failure = no meaningful output): {critical}

Choose exactly ONE:
- retry  : error looks recoverable, retry count is low
- skip   : agent is non-critical, pipeline can continue with partial data
- halt   : critical failure, cannot produce a useful report

Respond with ONLY one word: retry, skip, or halt
"""
        try:
            response = self._get_llm().invoke([HumanMessage(content=prompt)])
        except Exception:
            return "retry"
        decision = response.content.strip().lower()

        # Safety fallback if the LLM returns something unexpected.
        if decision not in ("retry", "skip", "halt"):
            return "retry"
        return decision
