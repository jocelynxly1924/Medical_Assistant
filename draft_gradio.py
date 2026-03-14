import gradio as gr
import uuid
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command
from graph_draft import get_graph

graph_app = get_graph()

thread_id = str(uuid.uuid4())


# async def chat_with_assistant(message, history):
#     """聊天函数 - 返回字符串而不是整个历史记录"""
#     global thread_id
#
#     config = {"configurable": {"thread_id": thread_id}}
#
#     try:
#         state = graph_app.get_state(config)
#         print('最开始', state)
#
#         if state.next:
#             print(1)
#             input_data = Command(resume=message)
#         else:
#             print(2)
#             input_data = {"messages": [HumanMessage(content=message)]}
#
#         # 标记当前正在运行的节点
#         current_running_node = None
#         # 用于累积当前节点的流式输出
#         current_stream = ""
#         # 标记是否已经为当前对话发送过响应
#         response_sent_for_current = False
#
#         print(3)
#         async for event in graph_app.astream_events(input_data, config=config, version="v2"):
#             kind = event["event"]
#             node_name = event.get("name", "")
#
#             # 节点开始 - 更新当前运行节点
#             if kind == "on_chain_start":
#                 if node_name in ["info_completion", "info_refinement", "info_retrieval_and_answer_generation_agent"]:
#                     current_running_node = node_name
#                     current_stream = ""  # 重置流内容
#                     response_sent_for_current = False
#                     print(f"开始节点: {node_name}")
#
#             # 流式输出 - 只处理当前运行节点的输出
#             elif kind == "on_chat_model_stream":
#                 if current_running_node and current_running_node != "intent_recognition":
#                     content = event["data"]["chunk"].content
#                     if content:
#                         current_stream += content
#                         # 只输出当前节点的流式内容
#                         yield current_stream
#
#             # 节点结束 - 清理状态
#             elif kind == "on_chain_end":
#                 if node_name == current_running_node:
#                     print(f"结束节点: {node_name}")
#                     current_running_node = None
#
#                 # 处理警告节点
#                 if node_name == "warning":
#                     if event["data"].get("output", {}).get("high_risk_words"):
#                         thread_id = str(uuid.uuid4())
#                         warning_msg = "⚠️ 检测到可能存在高风险情况，建议您及时线下就医！"
#                         yield warning_msg
#                         return
#
#         # 检查是否有中断（需要用户输入）
#         current_state = graph_app.get_state(config)
#         if current_state.next:
#             tasks = current_state.tasks
#             if tasks:
#                 for task in tasks:
#                     if hasattr(task, 'interrupts') and task.interrupts:
#                         interrupt_data = task.interrupts[0].value
#                         if isinstance(interrupt_data, dict):
#                             question = interrupt_data.get('question', '请提供更多信息')
#                             # 如果没有通过流式输出过内容，才输出问题
#                             if not current_stream:
#                                 yield question
#                             return
#
#         # 如果没有流式输出，从状态中获取最后的消息
#         if not current_stream:
#             final_state = graph_app.get_state(config)
#             if final_state.values.get('messages') and isinstance(final_state.values['messages'][-1], AIMessage):
#                 last_message = final_state.values['messages'][-1]
#                 final_response = last_message.content if hasattr(last_message, 'content') else str(last_message)
#                 yield final_response
#             else:
#                 yield "抱歉，我无法回答您的问题。请输入您想要查询的症状、疾病信息或药品信息。"
#
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         yield f"处理出错: {str(e)}"



async def chat_with_assistant(message, history):
    """聊天函数 - 返回字符串而不是整个历史记录"""
    global thread_id

    config = {"configurable": {"thread_id": thread_id}}

    try:
        state = graph_app.get_state(config)
        print('最开始', state)

        if state.next:
            print(1)
            input_data = Command(resume=message)
        else:
            print(2)
            input_data = {"messages": [HumanMessage(content=message)]}

        # 标记当前正在运行的节点
        current_running_node = None
        # 用于累积当前节点的流式输出
        current_stream = ""
        # 标记是否已经处理过中断（避免重复输出）
        interrupt_handled = False
        # 标记是否有流式输出
        has_stream_output = False

        print(3)
        async for event in graph_app.astream_events(input_data, config=config, version="v2"):
            kind = event["event"]
            node_name = event.get("name", "")

            # 节点开始 - 更新当前运行节点，重置流式状态
            if kind == "on_chain_start":
                if node_name in ["info_completion", "info_refinement", "info_retrieval_and_answer_generation_agent"]:
                    current_running_node = node_name
                    current_stream = ""  # 中断恢复后重置流式内容
                    has_stream_output = False
                    print(f"开始节点: {node_name}")

            # 流式输出 - 只处理当前运行节点的输出，避免叠加
            elif kind == "on_chat_model_stream":
                if current_running_node and current_running_node != "intent_recognition":
                    content = event["data"]["chunk"].content
                    if content:
                        current_stream += content
                        has_stream_output = True
                        yield current_stream  # 实时流式输出

            # 节点结束 - 清理状态
            elif kind == "on_chain_end":
                if node_name == current_running_node:
                    print(f"结束节点: {node_name}")
                    current_running_node = None

                # 处理警告节点
                if node_name == "warning":
                    if event["data"].get("output", {}).get("high_risk_words"):
                        thread_id = str(uuid.uuid4())
                        warning_msg = "⚠️ 检测到可能存在高风险情况，建议您及时线下就医！"
                        yield warning_msg
                        return

        # 检查是否有中断（需要用户输入）
        current_state = graph_app.get_state(config)
        if current_state.next:
            tasks = current_state.tasks
            if tasks:
                for task in tasks:
                    if hasattr(task, 'interrupts') and task.interrupts:
                        interrupt_data = task.interrupts[0].value
                        if isinstance(interrupt_data, dict):
                            question = interrupt_data.get('question', '请提供更多信息')
                            # 仅当没有流式输出时，才输出中断问题（避免重复）
                            if not has_stream_output and not current_stream:
                                yield question
                            interrupt_handled = True
                return  # 中断时直接返回，避免后续兜底输出

        # 兜底输出：仅当无流式输出、无中断时才执行（核心修复：避免双重输出）
        if not has_stream_output and not interrupt_handled and not current_stream:
            final_state = graph_app.get_state(config)
            if final_state.values.get('messages') and isinstance(final_state.values['messages'][-1], AIMessage):
                last_message = final_state.values['messages'][-1]
                final_response = last_message.content if hasattr(last_message, 'content') else str(last_message)
                yield final_response
            else:
                yield "抱歉，我无法识别或回答您的问题。请输入您想要查询的症状、疾病信息或药品信息。"

    except Exception as e:
        import traceback
        traceback.print_exc()
        yield f"处理出错: {str(e)}"


def reset_thread():
    """重置对话线程"""
    global thread_id
    thread_id = str(uuid.uuid4())
    # 对于 ChatInterface，需要返回一个更新来清空聊天记录
    return gr.update(value=[])


# 创建 ChatInterface
demo = gr.ChatInterface(
    fn=chat_with_assistant,
    title="🏥 医疗助手",
    description="### 智能健康咨询助手",
    # type="messages",  # 使用 messages 格式
    examples=[
        "疾病信息咨询",
        "常见症状诊断",
        "药品信息查询",
    ],
    cache_examples=False,
    concurrency_limit=1,
    submit_btn="发送",
    stop_btn="停止",
)

# 添加重置按钮到界面
with demo:
    gr.Markdown("---")  # 添加分隔线
    with gr.Row():
        reset_btn = gr.Button("🔄 重置对话", variant="secondary", size="md")

    # 绑定重置功能
    reset_btn.click(
        fn=reset_thread,
        inputs=None,
        outputs=demo.chatbot,  # ChatInterface 的 chatbot 组件
        queue=False
    )
if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1)
    demo.launch(server_port=7868, share=False)