from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, RemoveMessage
from langgraph.types import interrupt

from extensions import socketio
from models.model_factory import get_llm_client
from prompts.prompts import (template_intent_recognition_lite, template_info_completion,
                             template_summarization, template_final_answer, template_retrieval_and_answer)
from states.states import PublicState
from tools.high_risk_word_detection import input_detection
from tools.get_medicine_info import get_medicine_info_tool
from tools.get_rag_huatuo_qa import get_rag_qa_tool

tool_list = [get_medicine_info_tool, get_rag_qa_tool]
llm = get_llm_client(model_name='qwen3-max')
llm_with_tools = llm.bind_tools(tool_list)

def warning(state: PublicState):
    return {
        'messages': [AIMessage(content="⚠️ 检测到可能存在高风险情况，建议您及时线下就医！")],
        'high_risk_words': True
    }

def intent_recognition(state: PublicState):
    user_message = state["messages"][-1].content
    system_prompt = template_intent_recognition_lite.format(query=user_message)
    intent = llm.invoke([SystemMessage(content=system_prompt)]).content
    
    if input_detection(intent, user_message):
        return {'high_risk_words': True}
    
    return {
        "query": user_message,
        "intent": intent,
        "full_info": f"用户：{user_message}\n",
        'rag_times': 0,
        'web_times': 0
    }

def info_completion(state: PublicState):
    conversation_history = state.get("full_info", "")
    intent = state.get('intent', '')
    
    prompt = template_info_completion.format(intent=intent, history=conversation_history)
    response = llm.invoke([SystemMessage(content=prompt)])
    
    if "信息已完整" in response.content:
        return {"info_completed": True}
    
    user_answer = interrupt({
        'question': response.content,
        'full_info': conversation_history + f"助手：{response.content}\n"
    })
    
    if input_detection(intent, user_answer):
        return {'high_risk_words': True}
    
    return {
        'full_info': conversation_history + f"助手：{response.content}\n用户：{user_answer}\n",
        'messages': [response]
    }

def info_refinement(state: PublicState):
    messages = state["messages"]
    # print("消息提炼", state)
    if len(messages) == 1:
        print("仅一个消息，无需提炼")
        return{'query_refined': state["query"]}
    else:
        history = state['full_info']
        # print("总结前：\n",history)
        prompt = template_summarization.format(history = history)
        response = llm.invoke(prompt).content
        print("您的输入信息汇总：\n",response)
        return {
            'messages': [RemoveMessage(id=m.id)for m in messages] + [HumanMessage(content=response)],
            'query_refined': response
        }

def info_retrieval_and_answer_generation_agent(state: PublicState):
    rag_times = state.get('rag_times', 0)
    web_times = state.get('web_times', 0)

    if rag_times < 2 and web_times < 2:
        prompt = template_retrieval_and_answer
        print('我的状态：', state)
        response = llm_with_tools.invoke([SystemMessage(content=prompt)] + state['messages'],) # 传递 config
        # # ========== 核心修复：优化 tool_calls 检测逻辑 ==========
        # # 1. 从 config 中提取 thread_id
        # thread_id = None
        # if config and isinstance(config, dict):
        #     thread_id = config.get("configurable", {}).get("thread_id")
        # print("现在的thread id：", thread_id)
        #
        # # 2. 修复：兼容 LLM 响应的不同格式 + 延迟检测（确保 tool_calls 已生成）
        # # 方案1：先尝试直接获取，失败则从 response.additional_kwargs 提取（LLM 响应的备用存储位置）
        # tool_calls = None
        # # 优先从属性获取
        # if hasattr(response, 'tool_calls') and response.tool_calls:
        #     tool_calls = response.tool_calls
        # # 备用：从 additional_kwargs 提取（很多 LLM 会把 tool_calls 存在这里）
        # elif hasattr(response, 'additional_kwargs') and 'tool_calls' in response.additional_kwargs:
        #     tool_calls = response.additional_kwargs['tool_calls']
        #
        # # 3. 检测到工具调用就发送消息
        # if tool_calls:
        #     for tool_call in tool_calls:
        #         if tool_call.get('name') == 'get_rag_qa_tool':
        #             if thread_id:
        #                 print("检测到调用 get_rag_qa_tool，发送 SocketIO 状态消息")
        #                 socketio.emit(
        #                     'status',
        #                     {'message': '正在查询 HuaTuo 知识库……'},
        #                     room=thread_id,
        #                     namespace='/'
        #                 )
        #             break
        # # ========== 核心修复结束 ==========

    else:
        prompt = template_final_answer
        response = llm.invoke([SystemMessage(content=prompt)] + state['messages'])
    
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call['name'] == 'get_medicine_info_tool':
                web_times += 1
            elif tool_call['name'] == 'get_rag_qa_tool':
                rag_times += 1
    
    if response.content:
        print(f"\n最终回答：\n\n{response.content}")
    
    return {
        'messages': [response],
        'web_times': web_times,
        'rag_times': rag_times,
    }


