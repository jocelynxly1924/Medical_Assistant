from pyexpat.errors import messages

from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, RemoveMessage
from oauthlib.uri_validate import query

from models.model_factory import get_llm_client
from prompts.prompts import (template_intent_recognition_lite, template_info_completion,
                             template_summarization, template_final_answer, template_retrieval_and_answer)
from states.states import PublicState
# from tools.high_risk_word_detection import high_risk_word_detection
from tools.high_risk_word_detection import input_detection
from tools.get_medicine_info import get_medicine_info_tool
from tools.get_rag_huatuo_qa import get_rag_qa_tool

tool_list = [get_medicine_info_tool, get_rag_qa_tool]
llm = get_llm_client(model_name='qwen3-max')
llm_with_tools = get_llm_client(model_name='qwen3-max').bind_tools(tool_list)

def warning(state: PublicState):
    print("⚠️线上诊断终止，请及时线下就医!")

def intent_recognition(state: PublicState):
    user_message = state["messages"][-1].content
    system_prompt = template_intent_recognition_lite.format(query=user_message)
    response = llm.invoke([SystemMessage(content=system_prompt)]).content
    # print(response)
    if input_detection(response, user_message):
        return{
            'high_risk_words': True
        }
    return {
        "current_node": "intent_recognition",
        "query": user_message,
        "intent": response,
        "full_info": f"用户：{user_message}\n",
        'rag_times':0,
        'web_times':0
    }

def info_completion(state: PublicState):
    """诱导用户补充信息直至完整"""
    # print(state)
    conversation_history = state["full_info"]
    intent = state['intent']
    prompt = template_info_completion.format(intent=intent,
                                             history=conversation_history)
    response_full = llm.invoke([SystemMessage(content=prompt)])
    response = response_full.content

    if "信息已完整" in response:
        # print("信息已完整！")
        return {
            "info_completed": response,
            "current_node": "info_completion",
        }
    else:
        return{
            'messages': response_full,
            'full_info': state['full_info'] + f"助手：{response}\n",
            "current_node": "info_completion",
        }

    # else:
    #
    #         # conversation_history += f"助手: {response}\n"
    #         # state["messages"].append(response_full)
    #         #
    #         additional_info = input(f"{response}\n")
    #         # conversation_history += f"用户: {additional_info}\n"
    #         # state["messages"].append(HumanMessage(content=additional_info))
    #
    #         if input_detection(intent, additional_info):
    #             return{
    #                 'high_risk_words': True
    #             }
    #
    #         prompt = template_info_completion.format(query=conversation_history,
    #                                                  intent=intent,
    #                                                  history=conversation_history)
    #         response_full = llm.invoke([SystemMessage(content=prompt)])
    #         response = response_full.content
    #         # print(conversation_history)
    #         if "信息已完整" in response:
    #             return {
    #                 "current_node": "info_completion",
    #                 'full_info': conversation_history,
    #             }
def human_add_info(state: PublicState):
    human_message = input(f"{state['messages'][-1].content}\n")
    if input_detection(state['intent'], human_message):
        return{
            'high_risk_words': True
        }
    return {
        'messages': human_message,
        'full_info': state['full_info'] + f"用户: {human_message}\n",
    }


def info_refinement(state: PublicState):
    messages = state["messages"]
    # print("消息提炼", state)
    if len(messages) == 1:
        # print("仅一个消息，无需提炼")
        return{'query_refined': state["query"]}
    else:
        # history = ''
        # for msg in state['messages']:
        #     role = ''
        #     if isinstance(msg, HumanMessage):
        #         role = '用户'
        #     elif isinstance(msg, AIMessage):
        #         role = '助手'
        #     history += f"{role}: {msg.content}\n"
        history = state['full_info']
        # print("总结前：\n",history)
        prompt = template_summarization.format(history = history)
        response = llm.invoke(prompt).content
        # print("总结后：\n",response)
        print("您的输入信息汇总：\n",response)
        # 清空message内容：
        # print(messages)
        return {
            'messages': [RemoveMessage(id=m.id)for m in messages] + [HumanMessage(content=response)],
            'query_refined': response
        }

def info_retrieval_and_answer_generation_agent(state: PublicState):
    # print(state)
    rag_times = state['rag_times']
    web_times = state['web_times']
    if rag_times < 2 and web_times < 2:
        prompt= template_retrieval_and_answer
        response = llm_with_tools.invoke([SystemMessage(content=prompt)] + state['messages'])
    else:
        prompt = template_final_answer
        response = llm.invoke([SystemMessage(content=prompt)] + state['messages'])

    if response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']

            if tool_name == 'get_medicine_info_tool':
                web_times += 1
            elif tool_name == 'get_rag_qa_tool':
                rag_times += 1
    if response.content:
        color = '\033[93m'
        reset = '\033[0m'
        print(f"\n{color}最终回答：{reset}\n\n", response.content)
    return {
        'messages': response,
        'web_times': web_times,
        'rag_times': rag_times,
        # "final_response": response,
    }



# def final_response(state: PublicState):
#     query_full = state["query_refined"]
#     rag_retrieved_info = state.get("rag_retrieved_docs","")
#     web_retrieved_info = state.get("web_retrieved_docs","")
#     prompt = template_final_answer.format(query=query_full,
#                                           rag_retrieved_info=rag_retrieved_info,
#                                           web_retrieved_info=web_retrieved_info)
#     response = llm.invoke(prompt).content
#     print("最终回答：\n",response)
#     return {
#         "final_response": response,
#     }


