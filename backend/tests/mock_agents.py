# tests/mock_agents.py
from app.core.state import PipelineState

def mock_preprocess(state: PipelineState) -> PipelineState:
    state["business_id"] = "fake-biz-001"
    state["reviews_df"] = "mock_dataframe"  # real one is a DataFrame
    return state

def mock_analysis_agent(state: PipelineState) -> PipelineState:
    state["analysis_results"] = [
        {"review_id": "r1", "sentiment": "negative",
         "aspects": [{"category": "wait_time", "label": "negative"}],
         "status": "success"}
    ]
    return state

def mock_reasoning_agent(state: PipelineState) -> PipelineState:
    state["reasoning_output"] = {
        "patterns": [{"description": "Long waits on weekends", "aspect": "wait_time", "frequency": 0.4}],
        "root_causes": [{"pattern": "Long waits on weekends", "cause": "Understaffing"}],
        "status": "success"
    }
    return state

def mock_strategy_agent(state: PipelineState) -> PipelineState:
    state["strategy_output"] = {
        "recommendations": [{"priority": 1, "issue": "Understaffing",
                              "action": "Hire 2 weekend staff", "category": "operations"}],
        "status": "success"
    }
    return state

def mock_report_agent(state: PipelineState) -> PipelineState:
    state["report_output"] = {"html": "<h1>Report</h1>", "status": "success"}
    state["pipeline_status"] = "complete"
    return state