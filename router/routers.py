from typing import Literal
from langgraph.constants import END

from states.states import PublicState

def router_to_info_collection(state: PublicState) -> Literal["info_completion", "warning"]:
    if state.get("high_risk_words"):
        return "warning"
    return "info_completion"

def router_after_info_completion(state: PublicState) -> Literal["info_refinement", "info_completion", "warning"]:
    if state.get("high_risk_words"):
        return "warning"
    if state.get("info_completed"):
        return "info_refinement"
    return "info_completion"

def router_agent_to_tools(state: PublicState) -> Literal["tools", END]:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END
