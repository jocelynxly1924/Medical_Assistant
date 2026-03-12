import gradio as gr
import uuid
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from graph_draft import get_graph

graph_app = get_graph()

thread_id = str(uuid.uuid4())
user_id = str(uuid.uuid4())


def chat_with_assistant(message, history):
    """
    与医疗助手对话的核心函数

    参数:
        message: 用户当前输入的消息
        history: 对话历史（Gradio自动维护，格式为消息列表）

    返回:
        tuple: (更新后的对话历史, 清空了的输入框)
    """
    global thread_id, user_id

    config = {"configurable": {"thread_id": thread_id}}

    history = history or []
    history.append({"role": "user", "content": message})

    yield history, ""
    print("历史：",history)

    try:
        state = graph_app.get_state(config)

        if state.next:
            response = graph_app.invoke(Command(resume=message), config=config)
        else:
            all_agent_responses = []
            
            for chunk in graph_app.stream(
                {"messages": [HumanMessage(content=message)], "user_id": user_id},
                config=config,
                stream_mode="updates"
            ):
                for node_name, node_output in chunk.items():
                    if node_name == 'retrieval_and_answer_agent':
                        if node_output.get('messages'):
                            last_message = node_output['messages'][-1]
                            if hasattr(last_message, 'content') and last_message.content:
                                all_agent_responses.append(last_message.content)
                                
                                content = last_message.content
                                lines = content.split('\n')
                                
                                for line in lines:
                                    line = line.strip()
                                    if not line:
                                        continue
                                    
                                    if line.startswith('思考：'):
                                        history.append({"role": "assistant", "content": f"🤔 {line}"})
                                        yield history, ""
                                    elif line.startswith('行动：'):
                                        history.append({"role": "assistant", "content": f"⚡ {line}"})
                                        yield history, ""
                                    elif line.startswith('观察：'):
                                        history.append({"role": "assistant", "content": f"👁️ {line}"})
                                        yield history, ""
                                    elif line.startswith('🔍 查询：'):
                                        history.append({"role": "assistant", "content": line})
                                        yield history, ""
                    
                    if node_name == 'save_history':
                        print("历史已保存到Redis")

            if all_agent_responses:
                last_response = all_agent_responses[-1]
                if '回答：' in last_response:
                    lines = last_response.split('\n')
                    final_answer_lines = []
                    in_answer = False
                    for line in lines:
                        line = line.strip()
                        if line.startswith('回答：'):
                            in_answer = True
                            final_answer_lines.append(f"💬 最终回答：\n{line[3:].strip()}")
                        elif in_answer and line:
                            final_answer_lines.append(line)
                    
                    if final_answer_lines:
                        final_answer = "\n".join(final_answer_lines)
                        history.append({"role": "assistant", "content": final_answer})
                        yield history, ""

            final_state = graph_app.get_state(config)
            response = final_state.values

        if response.get('high_risk_words'):
            thread_id = str(uuid.uuid4())
            user_id = str(uuid.uuid4())
            history.append({"role": "assistant", "content": "⚠️ 检测到可能存在高风险情况，建议您及时线下就医！"})
            yield history, ""
            return

        current_state = graph_app.get_state(config)

        if current_state.next:
            tasks = current_state.tasks
            if tasks:
                for task in tasks:
                    if hasattr(task, 'interrupts') and task.interrupts:
                        interrupt_data = task.interrupts[0].value
                        if isinstance(interrupt_data, dict):
                            question = interrupt_data.get('question', '请提供更多信息')
                        else:
                            question = str(interrupt_data) if interrupt_data else '请提供更多信息'
                        history.append({"role": "assistant", "content": question})
                        yield history, ""
                        return
            history.append({"role": "assistant", "content": "请提供更多信息"})
            yield history, ""
            return

        thread_id = str(uuid.uuid4())

        print("历史结束",history)

    except Exception as e:
        history.append({"role": "assistant", "content": f"处理出错: {str(e)}"})
        yield history, ""


def reset_conversation():
    """重置对话，开始新的会话"""
    global thread_id, user_id
    thread_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    return [], ""


# 创建Gradio界面
with gr.Blocks(title="医疗助手") as demo:
    gr.Markdown("# 🏥 医疗助手\n### 智能健康咨询助手")

    # 聊天界面
    chatbot = gr.Chatbot(
        label="对话",
        height=500,
        show_label=False
    )

    with gr.Row():
        # 用户输入框
        user_input = gr.Textbox(
            label="输入框",
            placeholder="请输入您的问题...",
            show_label=False,
            scale=4
        )
        # 发送按钮
        send_btn = gr.Button("发送", variant="primary", scale=1)
        # 重置按钮
        reset_btn = gr.Button("重置对话", variant="secondary", scale=1)

    # 设置交互逻辑
    # 返回值同时更新聊天框和输入框（输入框清空）
    user_input.submit(chat_with_assistant, [user_input, chatbot], [chatbot, user_input])
    send_btn.click(chat_with_assistant, [user_input, chatbot], [chatbot, user_input])
    # 重置按钮清空对话和输入框
    reset_btn.click(reset_conversation, None, [chatbot, user_input])

# 启动应用
if __name__ == "__main__":
    demo.launch(server_port=7860)
