from typing import TypedDict, Optional, List, Dict, Any

class PipelineState(TypedDict):
    # Input
    business_name: str
    business_id: Optional[str]

    # Data layer (Member 2 fills these)
    reviews_df: Optional[Any]           # pandas DataFrame

    # Agent outputs (Members 3 & 4 fill these)
    analysis_results: Optional[List[Dict]]   # list of per-review JSON
    reasoning_output: Optional[Dict]
    strategy_output:  Optional[Dict]
    report_output:    Optional[Dict]

    # Error handling (YOU manage these)
    retry_counts:    Dict[str, int]     # { "analysis": 0, "reasoning": 0, ... }
    skipped_agents:  List[str]
    errors:          Dict[str, str]     # { "analysis": "error detail" }

    # Pipeline control (YOU manage these)
    pipeline_status:  str               # "running" | "halted" | "complete"
    failed_agent:     Optional[str]     # set when an agent returns error status