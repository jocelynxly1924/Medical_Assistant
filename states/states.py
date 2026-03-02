from langgraph.graph import MessagesState
from typing import Literal

class PublicState(MessagesState):
    current_node: Literal["intent_recognition","info_completion", "start",'warning']
    query: str
    intent: str
    info_completed: str
    high_risk_words: bool
    full_info: str
    query_refined: str
    rag_retrieved_docs: str
    web_retrieved_docs: str
    rag_times: int
    web_times: int
    final_response: str


# class InfoCompletionState(MessagesState):
#     query: str
#     intent: str
#     info_completion: str