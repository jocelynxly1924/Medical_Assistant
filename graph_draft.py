from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from states.states import PublicState
from nodes.nodes import (intent_recognition, info_completion, warning,
                         info_refinement, info_retrieval_and_answer_generation_agent)
from tools.get_rag_huatuo_qa import get_rag_qa_tool
from tools.get_medicine_info import get_medicine_info_tool
from router.routers import router_to_info_collection, router_after_info_completion, router_agent_to_tools

def get_graph():
    tools = [get_rag_qa_tool, get_medicine_info_tool]
    tool_node = ToolNode(tools)

    graph = StateGraph(PublicState)

    graph.add_node('intent_recognition', intent_recognition)
    graph.add_node('info_completion', info_completion)
    graph.add_node('warning', warning)
    graph.add_node('info_refinement', info_refinement)
    graph.add_node('retrieval_and_answer_agent', info_retrieval_and_answer_generation_agent)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, 'intent_recognition')
    graph.add_conditional_edges('intent_recognition', router_to_info_collection)
    graph.add_conditional_edges('info_completion', router_after_info_completion)
    graph.add_edge('info_refinement', 'retrieval_and_answer_agent')
    graph.add_conditional_edges('retrieval_and_answer_agent', router_agent_to_tools)
    graph.add_edge('tools', 'retrieval_and_answer_agent')
    graph.add_edge('warning', END)

    # from IPython.display import Image, display
    # try:
    #     display(Image(app.get_graph().draw_mermaid_png(output_file_path='./graph.png')))
    # except Exception:
    #     pass
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)

if __name__ == '__main__':
    from langchain_core.messages import HumanMessage
    from langgraph.types import Command
    import uuid
    
    app = get_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    initial_input = input("您好！请问有什么要提问的吗？\n")
    response = app.invoke(
        {"messages": [HumanMessage(content=initial_input)]},
        config=config
    )
    
    while True:
        if response.get('high_risk_words'):
            print("⚠️ 检测到高风险，请线下就医！")
            break
        
        state = app.get_state(config)
        if state.next:
            user_input = input("请输入: ")
            response = app.invoke(Command(resume=user_input), config=config)
        else:
            break
    
    print("\n【流程已结束】")
