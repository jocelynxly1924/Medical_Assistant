# from models.model_factory import get_llm_client
# llm = get_llm_client(model_name='q', organization='ollama')
# print(llm.invoke("hello world"))

########################################################################
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import ToolNode

from states.states import PublicState
from nodes.nodes import (intent_recognition, info_completion, warning, info_refinement, human_add_info,
                         info_retrieval_and_answer_generation_agent)

from tools.get_rag_huatuo_qa import get_rag_qa_tool
from tools.get_medicine_info import get_medicine_info_tool
from router.routers import router_to_info_collection, router_add_human_info, router_agent_to_tools

# llm_qwen = get_llm_client(model_name='qwen3-max')
# llm_ollama = OllamaLLM(model='qwen2.5:7b-instruct-q4_K_M')

tools = [get_rag_qa_tool,get_medicine_info_tool]
tool_node = ToolNode(tools)

graph = StateGraph(PublicState)

graph.add_node('intent_recognition',intent_recognition)
graph.add_node('info_completion', info_completion)
graph.add_node('human_add_info',human_add_info)
graph.add_node('warning',warning)
graph.add_node('info_refinement',info_refinement)
graph.add_node('retrieval_and_answer_agent',info_retrieval_and_answer_generation_agent)
graph.add_node("tools", tool_node)

graph.add_edge(START, 'intent_recognition')
graph.add_conditional_edges('intent_recognition', router_to_info_collection)
graph.add_conditional_edges('info_completion', router_add_human_info)
graph.add_edge('human_add_info', 'info_completion')
graph.add_edge('info_refinement', 'retrieval_and_answer_agent')
graph.add_conditional_edges('retrieval_and_answer_agent', router_agent_to_tools)
graph.add_edge('tools','retrieval_and_answer_agent')
graph.add_edge('warning',END)

app = graph.compile()

# from IPython.display import Image, display
# try:
#     display(Image(app.get_graph().draw_mermaid_png(output_file_path='./graph.png')))
# except Exception:
#     pass

response = app.invoke({
    # "messages": [HumanMessage(content="我有点咳嗽")]
    # "messages": [HumanMessage(content="哮喘有哪些症状")]
    "messages": [HumanMessage(content=input("您好！请问有什么要提问的吗？\n"))]
})

# print(response["messages"])
clr = '\033[32m'
reset = '\033[0m'
print(f'\n{clr}【流程已结束】{reset}')






