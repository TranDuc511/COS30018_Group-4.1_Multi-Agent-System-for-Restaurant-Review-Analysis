"""Tests for orchestrator criticality normalisation and graph recovery routing.

These cover only the deterministic hard-rule and routing logic — no LLM calls.
"""

from app.core.orchestrator import OrchestratorAgent
from app.core import graph as g
from app.core import nodes
from app.core.pipeline import build_pipeline, initial_state

orchestrator = OrchestratorAgent()


# ── Criticality is suffix-insensitive (#2) ───────────────────────────────────

def test_is_critical_matches_both_name_forms():
    assert orchestrator.is_critical("analysis") is True
    assert orchestrator.is_critical("analysis_agent") is True
    assert orchestrator.is_critical("REASONING_AGENT") is True
    assert orchestrator.is_critical("strategy_agent") is False
    assert orchestrator.is_critical("report") is False


def test_hard_rule_halts_critical_and_skips_noncritical_when_exhausted():
    assert orchestrator.decide_recovery("analysis_agent", "boom", retry_count=2) == "halt"
    assert orchestrator.decide_recovery("strategy_agent", "boom", retry_count=2) == "skip"


def test_provider_failure_uses_deterministic_recovery(monkeypatch):
    class BrokenLLM:
        def invoke(self, _messages):
            raise RuntimeError("provider unavailable")

    local = OrchestratorAgent()
    monkeypatch.setattr(local, "_get_llm", lambda: BrokenLLM())

    assert local.decide_recovery("analysis_agent", "boom", retry_count=0) == "retry"
    assert local.decide_recovery("analysis_agent", "boom", retry_count=2) == "halt"
    assert local.decide_recovery("strategy_agent", "boom", retry_count=2) == "skip"


# ── Recovery routing targets the actual failed agent (#1) ────────────────────

def test_retry_routes_back_to_failed_agent():
    state = {"pipeline_status": "retry", "failed_agent": "strategy_agent"}
    assert g.route_after_error_handler(state) == "strategy_agent"


def test_skip_routes_to_next_stage():
    state = {"pipeline_status": "skip", "failed_agent": "reasoning_agent"}
    assert g.route_after_error_handler(state) == "strategy_agent"


def test_skip_on_last_stage_ends_pipeline():
    state = {"pipeline_status": "skip", "failed_agent": "report_agent"}
    assert g.route_after_error_handler(state) == "END"


def test_halt_ends_pipeline():
    state = {"pipeline_status": "halted", "failed_agent": "analysis_agent"}
    assert g.route_after_error_handler(state) == "END"


# ── error_handler_node never skips a critical agent ──────────────────────────

def test_error_handler_downgrades_skip_to_halt_for_critical_agent(monkeypatch):
    # Force the orchestrator to "decide" skip; the node must override to halt
    # because analysis is critical.
    monkeypatch.setattr(g.orchestrator, "decide_recovery", lambda *a, **k: "skip")

    state = {
        "failed_agent": "analysis_agent",
        "errors": {"analysis_agent": "schema error"},
        "retry_counts": {},
        "skipped_agents": [],
    }
    result = g.error_handler_node(state)

    assert result["pipeline_status"] == "halted"
    assert "analysis_agent" not in result["skipped_agents"]
    assert result["retry_counts"]["analysis_agent"] == 1


def test_error_handler_allows_skip_for_noncritical_agent(monkeypatch):
    monkeypatch.setattr(g.orchestrator, "decide_recovery", lambda *a, **k: "skip")

    state = {
        "failed_agent": "strategy_agent",
        "errors": {"strategy_agent": "schema error"},
        "retry_counts": {},
        "skipped_agents": [],
    }
    result = g.error_handler_node(state)

    assert result["pipeline_status"] == "skip"
    assert result["skipped_agents"] == ["strategy_agent"]


def test_chained_failures_use_current_agent_and_terminate(monkeypatch):
    reasoning_calls = 0
    recovery_calls = []

    monkeypatch.setattr(
        nodes,
        "analyse_reviews",
        lambda batch: [
            {
                "review_id": review["review_id"],
                "sentiment": "positive",
                "aspects": [],
                "status": "success",
                "error_detail": None,
            }
            for review in batch
        ],
    )

    def fake_reasoning(_results, business_id):
        nonlocal reasoning_calls
        reasoning_calls += 1
        if reasoning_calls == 1:
            return {"status": "error", "error_detail": "reasoning failed"}
        return {"status": "success", "error_detail": None, "patterns": [], "root_causes": []}

    monkeypatch.setattr(nodes, "reason_over_reviews", fake_reasoning)
    monkeypatch.setattr(
        nodes,
        "generate_recommendations",
        lambda *_args, **_kwargs: {"status": "error", "error_detail": "strategy failed"},
    )
    monkeypatch.setattr(
        nodes,
        "generate_report",
        lambda *_args, **_kwargs: {"status": "success", "error_detail": None},
    )

    def decide(failed_agent, error_detail, retry_count):
        recovery_calls.append((failed_agent, error_detail, retry_count))
        return "retry" if failed_agent == "reasoning_agent" else "skip"

    monkeypatch.setattr(g.orchestrator, "decide_recovery", decide)

    reviews = [
        {"review_id": "r1", "stars": 5, "text": "good", "date": "2024-01-01"}
    ]
    result = build_pipeline().invoke(initial_state("Test", reviews, "b1"))

    assert recovery_calls == [
        ("reasoning_agent", "reasoning failed", 0),
        ("strategy_agent", "strategy failed", 0),
    ]
    assert result["pipeline_status"] == "complete"
    assert result["failed_agent"] is None
    assert result["skipped_agents"] == ["strategy_agent"]
