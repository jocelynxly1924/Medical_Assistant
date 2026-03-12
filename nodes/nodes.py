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
import re

tool_list = [get_medicine_info_tool, get_rag_qa_tool]
llm = get_llm_client(model_name='qwen3-max')
llm_with_tools = llm.bind_tools(tool_list)

def warning(state: PublicState):
    return {
        'messages': [AIMessage(content="⚠️ 检测到可能存在高风险情况，建议您及时线下就医！")],
        'high_risk_words': True
    }

def intent_recognition(state: PublicState):
    print("开始状态：",state)
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

# def info_refinement(state: PublicState):
#     history = state['full_info']
#     prompt = template_summarization.format(history=history)
#     summary = llm.invoke(prompt).content
#
#     print("您的输入信息汇总：\n", summary)
#
#     return {
#         'messages': [HumanMessage(content=summary)],
#         'query_refined': summary
#     }

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
    
    # 检查是否有ToolMessage，避免重复打印
    has_tool_message = any(isinstance(msg, ToolMessage) for msg in state["messages"])
    
    # 只在第一次执行时打印状态
    if not has_tool_message:
        print('我的状态：', state)
    
    if rag_times < 2 and web_times < 2:
        prompt = template_retrieval_and_answer
        response = llm_with_tools.invoke([SystemMessage(content=prompt)] + state['messages'])
    else:
        prompt = template_final_answer
        response = llm.invoke([SystemMessage(content=prompt)] + state['messages'])
    
    # 标记是否有工具调用
    has_tool_calls = bool(response.tool_calls)
    
    # 处理响应内容
    if response.content:
        # 提取并输出思考、行动、观察信息
        lines = response.content.split('\n')
        has_answer = False
        
        # 过滤掉空行和重复内容
        processed_lines = []
        for line in lines:
            stripped_line = line.strip()
            if stripped_line and stripped_line not in processed_lines:
                processed_lines.append(stripped_line)
        
        for line in processed_lines:
            if line.startswith('思考：'):
                print(f"🤔 {line}")
            elif line.startswith('行动：'):
                print(f"⚡ {line}")
            elif line.startswith('观察：'):
                print(f"👁️ {line}")
            elif line.startswith('回答：'):
                print(f"\n\n💬 最终回答：")
                # 提取回答内容
                answer_content = line[3:].strip()
                print(answer_content)
                has_answer = True
            elif line and has_answer:
                # 只打印最终回答相关的内容
                print(f"📝 {line}")
    
    # 处理工具调用计数和实时输出
    tool_results = []
    if has_tool_calls:
        print(f"\n🔄 等待工具执行结果...\n")
        
        for tool_call in response.tool_calls:
            if tool_call['name'] == 'get_medicine_info_tool':
                web_times += 1
                tool_info = f"🔍 查询：调用 get_medicine_info_tool 查询 {tool_call['args']['medicine_name']} 的 {tool_call['args']['target_fields']}"
                print(tool_info)
                # 在消息中添加工具调用信息，以便前端捕获
                if response.content:
                    response.content += f"\n{tool_info}"
                else:
                    response.content = tool_info
            elif tool_call['name'] == 'get_rag_qa_tool':
                rag_times += 1
                tool_info = f"🔍 查询：调用 get_rag_qa_tool 查询 {tool_call['args']['query']}"
                print(tool_info)
                # 在消息中添加工具调用信息，以便前端捕获
                if response.content:
                    response.content += f"\n{tool_info}"
                else:
                    response.content = tool_info
    
    # 处理source信息和观察信息
    sources = []
    if has_tool_message:
        # 收集所有ToolMessage的source信息
        for msg in reversed(state["messages"]):
            if isinstance(msg, ToolMessage):
                tool_message_content = msg.content
                print("*** ToolMessage content (前200字符):", tool_message_content[:200])
                print(f"\n👁️ 观察：工具执行完成，获取到相关信息")
                try:
                    # 提取source信息
                    source_start = tool_message_content.find("'source': '")
                    if source_start != -1:
                        source_start += len("'source': '")
                        source_end = tool_message_content.rfind("'}")
                        if source_end != -1 and source_end > source_start:
                            source = tool_message_content[source_start:source_end]
                            source = source.replace('\\n', '\n')
                            sources.append(source)
                            # 实时输出source信息
                            print("\n📚 数据来源：")
                            print(source)
                            continue
                    
                    source_start = tool_message_content.find('"source": "')
                    if source_start != -1:
                        source_start += len('"source": "')
                        source_end = tool_message_content.rfind('"}')
                        if source_end != -1 and source_end > source_start:
                            source = tool_message_content[source_start:source_end]
                            source = source.replace('\\n', '\n')
                            sources.append(source)
                            continue
                except Exception as e:
                    print(f"解析 ToolMessage content 失败: {e}")
    
    # 将所有source信息添加到最终回答后
    if sources:
        combined_source = '\n\n'.join([source for source in sources])
        if response.content:
            response.content += f"\n\n{combined_source}"
        else:
            response.content = combined_source
    
    # 只在最后打印一次结束状态
    print("结束状态：", state)

    return {
        'messages': [response],
        'web_times': web_times,
        'rag_times': rag_times,
    }
