from langgraph.graph import StateGraph, END

from app.core.state import PipelineState
from app.core.orchestrator import OrchestratorAgent

orchestrator = OrchestratorAgent()

# Canonical sequential order of the agent nodes. Recovery routing uses this to
# re-run the agent that actually failed, or to continue with the next stage.
AGENT_SEQUENCE = ["analysis_agent", "reasoning_agent", "strategy_agent", "report_agent"]


# ── Routing functions (conditional edges) ────────────────────────────────────

def route_after_analysis(state: PipelineState) -> str:
    results = state.get("analysis_results") or []
    errors = [r for r in results if r.get("status") == "error"]
    if results and len(errors) > len(results) * 0.5:  # >50% failed — escalate
        return "error_handler"
    return "reasoning_agent"


def route_after_reasoning(state: PipelineState) -> str:
    out = state.get("reasoning_output") or {}
    return "error_handler" if out.get("status") == "error" else "strategy_agent"


def route_after_strategy(state: PipelineState) -> str:
    out = state.get("strategy_output") or {}
    return "error_handler" if out.get("status") == "error" else "report_agent"


def route_after_report(state: PipelineState) -> str:
    out = state.get("report_output") or {}
    return "error_handler" if out.get("status") == "error" else END


def _next_agent(failed_agent: str) -> str:
    """The agent that runs after `failed_agent`, or "END" if it is the last stage."""
    try:
        idx = AGENT_SEQUENCE.index(failed_agent)
    except ValueError:
        return "END"
    return AGENT_SEQUENCE[idx + 1] if idx + 1 < len(AGENT_SEQUENCE) else "END"


def route_after_error_handler(state: PipelineState) -> str:
    status = state.get("pipeline_status", "halted")
    failed = state.get("failed_agent")
    if status == "retry" and failed in AGENT_SEQUENCE:
        return failed                 # re-run the agent that actually failed
    if status == "skip":
        return _next_agent(failed)    # continue with the next stage
    return "END"                      # halted


# ── Error handler node ────────────────────────────────────────────────────────

def _infer_failed_agent(state: PipelineState) -> str:
    """Determine the latest failed stage without trusting stale routing state."""
    for output_key, agent in (
        ("report_output", "report_agent"),
        ("strategy_output", "strategy_agent"),
        ("reasoning_output", "reasoning_agent"),
    ):
        out = state.get(output_key) or {}
        if out.get("status") == "error":
            return agent

    results = state.get("analysis_results") or []
    errors = [r for r in results if r.get("status") == "error"]
    if results and len(errors) > len(results) * 0.5:
        return "analysis_agent"

    explicit = state.get("failed_agent")
    if explicit:
        return explicit

    return "analysis_agent"  # safe default — error_handler only runs on a real failure


def error_handler_node(state: PipelineState) -> PipelineState:
    failed = _infer_failed_agent(state)
    error = state.get("errors", {}).get(failed, "unknown error")
    count = state.get("retry_counts", {}).get(failed, 0)

    decision = orchestrator.decide_recovery(failed, error, count)

    # Never silently drop a critical agent: downgrade a "skip" decision to "halt".
    if decision == "skip" and orchestrator.is_critical(failed):
        decision = "halt"

    state.setdefault("retry_counts", {})[failed] = count + 1
    state["failed_agent"] = failed

    if decision == "retry":
        state["pipeline_status"] = "retry"
    elif decision == "skip":
        state.setdefault("skipped_agents", []).append(failed)
        state["pipeline_status"] = "skip"
    else:
        state["pipeline_status"] = "halted"

    return state


# ── Build the graph ───────────────────────────────────────────────────────────

def build_graph(analysis_node, reasoning_node, strategy_node, report_node, preprocess_node):
    graph = StateGraph(PipelineState)

    graph.add_node("preprocess",      preprocess_node)
    graph.add_node("analysis_agent",  analysis_node)
    graph.add_node("reasoning_agent", reasoning_node)
    graph.add_node("strategy_agent",  strategy_node)
    graph.add_node("report_agent",    report_node)
    graph.add_node("error_handler",   error_handler_node)

    graph.set_entry_point("preprocess")
    graph.add_edge("preprocess", "analysis_agent")

    graph.add_conditional_edges("analysis_agent",  route_after_analysis)
    graph.add_conditional_edges("reasoning_agent", route_after_reasoning)
    graph.add_conditional_edges("strategy_agent",  route_after_strategy)
    graph.add_conditional_edges("report_agent",    route_after_report)

    # Dynamic recovery routing: retry -> the failed agent, skip -> next stage,
    # halt -> END.
    graph.add_conditional_edges("error_handler", route_after_error_handler, {
        "analysis_agent":  "analysis_agent",
        "reasoning_agent": "reasoning_agent",
        "strategy_agent":  "strategy_agent",
        "report_agent":    "report_agent",
        "END": END,
    })

    return graph.compile()
