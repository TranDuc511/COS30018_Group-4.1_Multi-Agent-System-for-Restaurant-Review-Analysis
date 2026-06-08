# tests/test_graph.py
from app.core.graph import build_graph
from app.core.state import PipelineState
from tests.mock_agents import *

def test_happy_path():
    graph = build_graph(
        analysis_node=mock_analysis_agent,
        reasoning_node=mock_reasoning_agent,
        strategy_node=mock_strategy_agent,
        report_node=mock_report_agent,
        preprocess_node=mock_preprocess,
    )
    initial_state: PipelineState = {
        "business_name": "McDonald's",
        "business_id": None, "reviews_df": None,
        "analysis_results": None, "reasoning_output": None,
        "strategy_output": None, "report_output": None,
        "retry_counts": {}, "skipped_agents": [],
        "errors": {}, "pipeline_status": "running", "failed_agent": None,
    }
    result = graph.invoke(initial_state)
    assert result["pipeline_status"] == "complete"
    assert result["report_output"]["status"] == "success"