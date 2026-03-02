# global router: for high risk word detection
from typing import Literal
from langgraph.constants import END

from states.states import PublicState

def router_to_info_collection(state: PublicState) -> Literal["info_completion","warning"]:
    if state.get("high_risk_words","") == True:
        # print('⚠️线上诊断终止，请及时线下就医!')
        return "warning"
    return "info_completion"
    # else:
    #     print("error")
    #     return END
    # if

def router_add_human_info(state: PublicState)-> Literal["info_refinement","human_add_info"]:
    if state.get('info_completed',"")=="信息已完整":
        return "info_refinement"
    else:
        return "human_add_info"

# def router_info_collection(state: PublicState)-> Literal["get_rag_qa","get_medicine_info",END]:
#     # print(state)
#     intent = state.get("intent","")
#     if intent == "疾病科普" or intent == "病症分析":
#         return "get_rag_qa"
#     elif intent == "药品使用":
#         return "get_medicine_info"
#     else:
#         print("无需查询数据库，结束流程")
#         return END
#     print(111)


def router_agent_to_tools(state: PublicState) -> Literal["tools",END]:
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END