import gradio as gr
import uuid
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from graph_draft import get_graph

# 初始化图应用
graph_app = get_graph()

# 每个用户会话有独立的thread_id，用于保存对话状态
thread_id = str(uuid.uuid4())


def chat_with_assistant(message, history):
    """
    与医疗助手对话的核心函数

    参数:
        message: 用户当前输入的消息
        history: 对话历史（Gradio自动维护，格式为消息列表）

    返回:
        tuple: (更新后的对话历史, 清空了的输入框)
    """
    global thread_id

    # 配置：使用thread_id来区分不同的对话会话
    config = {"configurable": {"thread_id": thread_id}}

    # 先把用户消息添加到历史
    history = history or []
    history.append({"role": "user", "content": message})

    # 立即返回用户消息，让界面先显示用户输入
    yield history, ""  # yield：生成器，逐步输出内容
    # 使用yield的原因：
    # 先显示用户消息：yield history, "" ：history → 更新对话区域，显示用户刚发的消息；“”：清空对话框
    # 再逐步生成回复：后面还有代码会继续 yield，把助手的回复逐字或逐段地显示出来

    try:
        # 获取当前状态
        state = graph_app.get_state(config)

        # 判断是否需要继续之前的对话（有中断点）还是开始新对话
        if state.next:
            # 有中断点，说明是在等待用户回答问题
            response = graph_app.invoke(Command(resume=message), config=config)
        else:
            # 新对话，创建新的消息
            response = graph_app.invoke(
                {"messages": [HumanMessage(content=message)]},
                config=config
            )

        # 检测高风险词汇，如果检测到则重置对话
        if response.get('high_risk_words'):
            thread_id = str(uuid.uuid4())  # 重置thread_id
            history.append({"role": "assistant", "content": "⚠️ 检测到可能存在高风险情况，建议您及时线下就医！"})
            yield history, ""
            return

        # 获取当前状态，检查是否还有中断点（需要更多信息）
        current_state = graph_app.get_state(config)

        if current_state.next:
            # 有中断点，说明需要用户提供更多信息
            tasks = current_state.tasks
            if tasks:
                for task in tasks:
                    if hasattr(task, 'interrupts') and task.interrupts:
                        # 从中断数据中获取问题
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

        # 对话完成，获取最终回复
        if response.get('messages'):
            last_message = response['messages'][-1]
            ai_response = last_message.content if hasattr(last_message, 'content') else str(last_message)
        else:
            ai_response = '处理完成'

        # 对话结束，重置thread_id以便下次新对话
        thread_id = str(uuid.uuid4())

        history.append({"role": "assistant", "content": ai_response})
        yield history, ""

    except Exception as e:
        history.append({"role": "assistant", "content": f"处理出错: {str(e)}"})
        yield history, ""


def reset_conversation():
    """重置对话，开始新的会话"""
    global thread_id
    thread_id = str(uuid.uuid4())
    return [], ""  # 返回空列表清空聊天历史，空字符串清空输入框


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
