from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, RemoveMessage, ToolMessage
from langgraph.types import interrupt

from models.model_factory import get_llm_client
from prompts.prompts import (template_intent_recognition_lite, template_info_completion,
                             template_summarization, template_final_answer, template_retrieval_and_answer)
from states.states import PublicState
from tools.high_risk_word_detection import input_detection
from tools.get_medicine_info import get_medicine_info_tool
from tools.get_rag_huatuo_qa import get_rag_qa_tool
import json
import uuid
import re

tool_list = [get_medicine_info_tool, get_rag_qa_tool]
llm = get_llm_client(model_name='qwen3-max')
llm_streaming = get_llm_client(model_name='qwen3-max', streaming=True)
llm_with_tools = llm.bind_tools(tool_list)
llm_with_tools_streaming = llm_streaming.bind_tools(tool_list)


def warning(state: PublicState):
    return {
        'messages': [AIMessage(content="⚠️ 检测到可能存在高风险情况，建议您及时线下就医！")],
        'high_risk_words': True
    }


def intent_recognition(state: PublicState):
    print("开始状态：", state)
    user_message = state["messages"][-1].content

    system_prompt = template_intent_recognition_lite.format(query=user_message)
    intent = llm.invoke([SystemMessage(content=system_prompt)]).content
    print("[node]意图识别结果：", intent)

    if input_detection(intent, user_message):
        return {'high_risk_words': True}

    # 移除上一次执行图残留的human message
    if state.get('intent', '') == '其他类别':
        return {'messages': [RemoveMessage(id=state['messages'][-2].id)],
                "query": user_message,
                "intent": intent,
                "full_info": f"用户：{user_message}\n",
                'rag_times': 0,
                'web_times': 0
                }

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
    
    # 检查当前阶段（状态机模式）
    stage = state.get("info_completion_stage", "generate")
    
    if stage == "generate":
        # 阶段1：生成问题
        prompt = template_info_completion.format(intent=intent, history=conversation_history)
        
        # 先使用非流式LLM判断是否信息完整
        full_response = llm.invoke([SystemMessage(content=prompt)]).content
        
        if "信息已完整" in full_response:
            # 信息已完整，直接返回，不进行流式输出
            return {"info_completed": True}
        
        # 信息不完整，需要追问，进行流式输出
        full_response = ""
        for chunk in llm_streaming.stream([SystemMessage(content=prompt)]):
            if chunk.content:
                full_response += chunk.content
        
        # 保存问题，进入下一阶段
        return {
            "pending_question": full_response,
            "info_completion_stage": "interrupt"
        }
    
    elif stage == "interrupt":
        # 阶段2：中断等待用户输入
        full_response = state.get("pending_question", "")
        user_answer = interrupt({
            'question': full_response,
            'full_info': conversation_history + f"助手：{full_response}\n"
        })
        
        if input_detection(intent, user_answer):
            return {'high_risk_words': True}
        
        # 恢复后更新对话历史，添加AI问题和用户回答到messages，重置阶段
        return {
            'full_info': conversation_history + f"助手：{full_response}\n用户：{user_answer}\n",
            'pending_question': "",
            'info_completion_stage': "generate",
            'messages': [
                AIMessage(content=full_response),
                HumanMessage(content=user_answer)
            ]
        }


def info_refinement(state: PublicState):
    messages = state["messages"]
    if len(messages) == 1:
        # 仅一个消息，无需提炼
        print("仅一个消息，无需提炼")
        return {'query_refined': state["query"]}
    else:
        history = state['full_info']
        prompt = template_summarization.format(history=history)

        # 使用同步的LLM调用
        full_response = llm.invoke(prompt).content

        return {
            'messages': [RemoveMessage(id=m.id) for m in messages] + [HumanMessage(content=full_response)],
            'query_refined': full_response
        }


async def info_retrieval_and_answer_generation_agent(state: PublicState):
    rag_times = state.get('rag_times', 0)
    web_times = state.get('web_times', 0)

    if rag_times < 2 and web_times < 2:
        prompt = template_retrieval_and_answer
        print('我的状态：', state)

        response = await llm_with_tools.ainvoke([SystemMessage(content=prompt)] + state['messages'])
    else:
        prompt = template_final_answer

        full_response = ""
        async for chunk in llm_streaming.astream([SystemMessage(content=prompt)] + state['messages']):
            if chunk.content:
                full_response += chunk.content

        response = AIMessage(content=full_response)

    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call['name'] == 'get_medicine_info_tool':
                web_times += 1
            elif tool_call['name'] == 'get_rag_qa_tool':
                rag_times += 1

    if response.content:
        source = ''
        for msg in reversed(state["messages"]):
            if isinstance(msg, ToolMessage):
                tool_message_content = msg.content
                print("*** ToolMessage content (前200字符):", tool_message_content[:200])
                try:
                    source_start = tool_message_content.find("'source': '")
                    if source_start != -1:
                        source_start += len("'source': '")
                        source_end = tool_message_content.rfind("'}")
                        if source_end != -1 and source_end > source_start:
                            source = tool_message_content[source_start:source_end]
                            source = source.replace('\\n', '\n')
                            print('提取到的 source (前100字符):', source[:100])
                            break

                    source_start = tool_message_content.find('"source": "')
                    if source_start != -1:
                        source_start += len('"source": "')
                        source_end = tool_message_content.rfind('"}')
                        if source_end != -1 and source_end > source_start:
                            source = tool_message_content[source_start:source_end]
                            source = source.replace('\\n', '\n')
                            print('提取到的 source (前100字符):', source[:100])
                            break
                except Exception as e:
                    print(f"解析 ToolMessage content 失败: {e}")
                    continue

        if source:
            response.content = response.content + '\n\n' + source
        print(f"\n最终回答：\n\n{response.content}")
        print("结束状态：", state)

    return {
        'messages': [response],
        'web_times': web_times,
        'rag_times': rag_times,
    }
