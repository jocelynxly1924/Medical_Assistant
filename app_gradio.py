import gradio as gr
import uuid
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from graph_draft import get_graph
import time
# from gradio import ShowProgress

# 初始化图应用
graph_app = get_graph()

# 每个用户会话有独立的thread_id，用于保存对话状态
thread_id = str(uuid.uuid4())


def chat_with_assistant(message, history):
    """
    与医疗助手对话的核心函数
    """
    global thread_id

    config = {"configurable": {"thread_id": thread_id}}

    # 先把用户消息添加到历史
    history = history or []
    history.append({"role": "user", "content": message})
    # yield history, ""  # 这句虽然能让输出的消息实时显示，但是会让processing&加载时间模块失效。
    # print("历史：", history)

    try:
        # 获取当前状态
        state = graph_app.get_state(config)

        # 判断是否需要继续之前的对话（有中断点）还是开始新对话
        if state.next:
            # 有中断点，说明是在等待用户回答问题
            # 修改: 处理流式响应
            response = graph_app.invoke(Command(resume=message), config=config)
        else:
            # 新对话，创建新的消息
            response = graph_app.invoke(
                {"messages": [HumanMessage(content=message)]},
                config=config
            )

        # 检测高风险词汇
        if response.get('high_risk_words'):
            thread_id = str(uuid.uuid4())
            history.append({"role": "assistant", "content": "⚠️ 检测到可能存在高风险情况，建议您及时线下就医！"})
            yield history, ""
            return

        # 获取当前状态，检查是否还有中断点
        current_state = graph_app.get_state(config)

        if current_state.next:
            # 有中断点，说明需要用户提供更多信息
            tasks = current_state.tasks
            if tasks:
                for task in tasks:
                    if hasattr(task, 'interrupts') and task.interrupts:
                        interrupt_data = task.interrupts[0].value
                        if isinstance(interrupt_data, dict):
                            question = interrupt_data.get('question', '请提供更多信息')

                            # ***模拟流式输出显示追问***
                            history.append({"role": "assistant", "content": ""})
                            accumulated_response = ""
                            # 逐字显示追问（模拟流式效果）
                            for char in question:
                                accumulated_response += char
                                history[-1]["content"] = accumulated_response
                                yield history, ""
                                import time
                                time.sleep(0.02)  # 控制显示速度
                            yield history, ""
                            return

            # 兜底
            history.append({"role": "assistant", "content": "请提供更多信息"})
            yield history, ""
            return

        # 对话完成，获取最终回复
        if response.get('messages'):
            print('回复', response)
            last_message = response['messages'][-1]
            ai_response = last_message.content if hasattr(last_message, 'content') else str(last_message)
        else:
            ai_response = '处理完成'

        # 对话结束，重置thread_id
        thread_id = str(uuid.uuid4())

        # ***流式显示最终回答***
        history.append({"role": "assistant", "content": ""})
        accumulated_response = ""
        for char in ai_response:
            accumulated_response += char
            history[-1]["content"] = accumulated_response
            yield history, ""
            import time
            time.sleep(0.02)  # 控制显示速度

        print("历史结束", history)

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
        show_label=False,
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
    user_input.submit(
        fn=chat_with_assistant,
        inputs=[user_input, chatbot],
        outputs=[chatbot, user_input],
        queue=True,  # 启用队列
        show_progress="full"  # 显示完整进度
    )
    send_btn.click(
        chat_with_assistant,
        [user_input, chatbot],
        [chatbot, user_input],
        queue=True,
        show_progress = "full")
    # 重置按钮清空对话和输入框
    reset_btn.click(reset_conversation, None, [chatbot, user_input])

# 启动应用
if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1, )
    demo.launch(server_port=7868, share=False)  # share=False 本地运行
