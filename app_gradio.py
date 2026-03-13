import gradio as gr
import uuid
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from graph_draft import get_graph

graph_app = get_graph()

thread_id = str(uuid.uuid4())


async def chat_with_assistant(message, history):
    global thread_id

    config = {"configurable": {"thread_id": thread_id}}

    history = history or []
    history.append({"role": "user", "content": message})

    try:
        state = graph_app.get_state(config)

        if state.next:
            input_data = Command(resume=message)
        else:
            input_data = {"messages": [HumanMessage(content=message)]}

        current_streaming_content = ""
        current_node = None
        assistant_message_added = False

        async for event in graph_app.astream_events(input_data, config=config, version="v2"):
            kind = event["event"]

            if kind == "on_chain_start":
                current_node = event.get("name", "")
                if current_node in ["info_completion", "info_refinement", "info_retrieval_and_answer_generation_agent"]:
                    if not assistant_message_added:
                        history.append({"role": "assistant", "content": ""})
                        assistant_message_added = True
                    current_streaming_content = ""

            elif kind == "on_chat_model_stream":
                if current_node and current_node != "intent_recognition":
                    content = event["data"]["chunk"].content
                    if content:
                        current_streaming_content += content
                        if assistant_message_added:
                            history[-1]["content"] = current_streaming_content
                            yield history, ""

            elif kind == "on_chain_end":
                node_name = event.get("name", "")
                if node_name == "warning":
                    if event["data"].get("output", {}).get("high_risk_words"):
                        thread_id = str(uuid.uuid4())
                        history.append(
                            {"role": "assistant", "content": "⚠️ 检测到可能存在高风险情况，建议您及时线下就医！"})
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

                            if not assistant_message_added:
                                history.append({"role": "assistant", "content": ""})

                            history[-1]["content"] = question
                            yield history, ""
                            return

            if not assistant_message_added:
                history.append({"role": "assistant", "content": "请提供更多信息"})
            yield history, ""
            return

        if current_streaming_content and assistant_message_added:
            history[-1]["content"] = current_streaming_content
        else:
            final_state = graph_app.get_state(config)
            if final_state.values.get('messages'):
                last_message = final_state.values['messages'][-1]
                ai_response = last_message.content if hasattr(last_message, 'content') else str(last_message)
                if not assistant_message_added:
                    history.append({"role": "assistant", "content": ai_response})
                else:
                    history[-1]["content"] = ai_response

        thread_id = str(uuid.uuid4())
        yield history, ""

    except Exception as e:
        import traceback
        traceback.print_exc()
        history.append({"role": "assistant", "content": f"处理出错: {str(e)}"})
        yield history, ""


def reset_conversation():
    global thread_id
    thread_id = str(uuid.uuid4())
    return [], ""


with gr.Blocks(title="医疗助手") as demo:
    gr.Markdown("# 🏥 医疗助手\n### 智能健康咨询助手")

    chatbot = gr.Chatbot(
        label="对话",
        height=500,
        show_label=False,
    )

    with gr.Row():
        user_input = gr.Textbox(
            label="输入框",
            placeholder="请输入您的问题...",
            show_label=False,
            scale=4
        )
        send_btn = gr.Button("发送", variant="primary", scale=1)
        reset_btn = gr.Button("重置对话", variant="secondary", scale=1)

    user_input.submit(
        fn=chat_with_assistant,
        inputs=[user_input, chatbot],
        outputs=[chatbot, user_input],
        queue=True,
        show_progress="full"
    )
    send_btn.click(
        chat_with_assistant,
        [user_input, chatbot],
        [chatbot, user_input],
        queue=True,
        show_progress="full"
    )
    reset_btn.click(reset_conversation, None, [chatbot, user_input])

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1)
    demo.launch(server_port=7868, share=False)
