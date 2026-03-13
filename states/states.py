from langgraph.graph import MessagesState
from typing import AsyncGenerator

class PublicState(MessagesState):
    query: str = ""
    intent: str = ""
    info_completed: bool = False
    high_risk_words: bool = False
    full_info: str = ""
    query_refined: str = ""
    rag_times: int = 0
    web_times: int = 0
    source: str = ""
    streaming_content: str = ""

