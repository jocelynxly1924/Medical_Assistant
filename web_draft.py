from flask import Flask, request, render_template_string, session
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command
import uuid

from graph_draft import app as graph_app

flask_app = Flask(__name__)
flask_app.secret_key = 'your-secret-key-here'

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>医疗助手</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
        }
        .chat-box {
            border: 1px solid #ddd;
            border-radius: 5px;
            height: 400px;
            overflow-y: auto;
            padding: 15px;
            margin-bottom: 15px;
            background: #fafafa;
        }
        .user-msg {
            background: #3498db;
            color: white;
            padding: 10px 15px;
            border-radius: 15px;
            margin: 10px 0 10px auto;
            max-width: 70%;
            width: fit-content;
            text-align: right;
        }
        .ai-msg {
            background: #ecf0f1;
            color: #2c3e50;
            padding: 10px 15px;
            border-radius: 15px;
            margin: 10px 0;
            max-width: 70%;
            width: fit-content;
            white-space: pre-wrap;
        }
        .ai-question {
            background: #fff3cd;
            color: #856404;
            padding: 10px 15px;
            border-radius: 15px;
            margin: 10px 0;
            max-width: 70%;
            width: fit-content;
            border-left: 4px solid #ffc107;
        }
        .input-area {
            display: flex;
            gap: 10px;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        button {
            padding: 12px 30px;
            background: #27ae60;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background: #219a52;
        }
        .clear-btn {
            background: #e74c3c;
            margin-top: 10px;
        }
        .clear-btn:hover {
            background: #c0392b;
        }
        .status {
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-top: 10px;
        }
        .full-info {
            margin-top: 20px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
            font-size: 12px;
            color: #666;
            max-height: 100px;
            overflow-y: auto;
        }
        .full-info-title {
            font-weight: bold;
            margin-bottom: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏥 医疗助手</h1>

        <div class="chat-box" id="chatBox">
            {% for msg in messages %}
                {% if msg.role == 'user' %}
                    <div class="user-msg">{{ msg.content }}</div>
                {% elif msg.role == 'question' %}
                    <div class="ai-question">❓ {{ msg.content }}</div>
                {% else %}
                    <div class="ai-msg">{{ msg.content }}</div>
                {% endif %}
            {% endfor %}
        </div>

        <form method="post" class="input-area">
            <input type="text" name="question" placeholder="{% if waiting_for_input %}请补充信息...{% else %}请输入您的问题...{% endif %}" required autofocus>
            <button type="submit">发送</button>
        </form>

        <div class="status">
            {% if waiting_for_input %}
                ⏳ 等待补充信息...
            {% else %}
                准备就绪
            {% endif %}
        </div>

        <form action="/clear" method="get" style="text-align: center;">
            <button type="submit" class="clear-btn">清空对话</button>
        </form>

        {% if full_info %}
        <div class="full-info">
            <div class="full-info-title">📋 已收集信息：</div>
            <pre>{{ full_info }}</pre>
        </div>
        {% endif %}
    </div>

    <script>
        var chatBox = document.getElementById('chatBox');
        chatBox.scrollTop = chatBox.scrollHeight;
    </script>
</body>
</html>
'''

user_sessions = {}

@flask_app.route('/', methods=['GET', 'POST'])
def index():
    user_id = session.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
        session['user_id'] = user_id
        user_sessions[user_id] = {
            'messages': [],
            'thread_id': str(uuid.uuid4()),
            'waiting_for_input': False,
            'full_info': '',
            'intent': ''
        }

    user_data = user_sessions.get(user_id, {
        'messages': [],
        'thread_id': str(uuid.uuid4()),
        'waiting_for_input': False,
        'full_info': '',
        'intent': ''
    })

    if request.method == 'POST':
        question = request.form.get('question', '').strip()
        if question:
            user_data['messages'].append({'role': 'user', 'content': question})

            config = {"configurable": {"thread_id": user_data['thread_id']}}

            if user_data['waiting_for_input']:
                # 恢复中断的流程
                user_data['waiting_for_input'] = False

                try:
                    # 直接使用 Command(resume) 恢复，让 LangGraph 处理状态
                    response = graph_app.invoke(
                        Command(resume=question),
                        config=config
                    )

                    # 从响应中获取更新后的 full_info
                    if 'full_info' in response:
                        user_data['full_info'] = response['full_info']
                    if 'intent' in response:
                        user_data['intent'] = response['intent']

                    # 检查是否还有中断
                    current_state = graph_app.get_state(config)
                    if current_state and hasattr(current_state, 'tasks'):
                        for task in current_state.tasks:
                            if hasattr(task, 'interrupts') and task.interrupts:
                                for interrupt_data in task.interrupts:
                                    if isinstance(interrupt_data, dict) and 'question' in interrupt_data:
                                        user_data['messages'].append({'role': 'question', 'content': interrupt_data['question']})
                                        user_data['waiting_for_input'] = True
                                        break

                    if not user_data['waiting_for_input']:
                        last_msg = response["messages"][-1]
                        if isinstance(last_msg, AIMessage):
                            answer = last_msg.content
                        else:
                            answer = str(last_msg.content) if hasattr(last_msg, 'content') else str(last_msg)
                        user_data['messages'].append({'role': 'assistant', 'content': answer})

                except Exception as e:
                    user_data['messages'].append({'role': 'assistant', 'content': f"处理出错: {str(e)}"})

            else:
                # 新对话
                try:
                    response = graph_app.invoke(
                        {"messages": [HumanMessage(content=question)]},
                        config=config
                    )

                    # 从响应中获取 full_info 和 intent
                    if 'full_info' in response:
                        user_data['full_info'] = response['full_info']
                    if 'intent' in response:
                        user_data['intent'] = response['intent']

                    # 检查是否有中断
                    current_state = graph_app.get_state(config)
                    has_interrupt = False
                    if current_state and hasattr(current_state, 'tasks'):
                        for task in current_state.tasks:
                            if hasattr(task, 'interrupts') and task.interrupts:
                                for interrupt_data in task.interrupts:
                                    if isinstance(interrupt_data, dict) and 'question' in interrupt_data:
                                        user_data['messages'].append({'role': 'question', 'content': interrupt_data['question']})
                                        user_data['waiting_for_input'] = True
                                        has_interrupt = True
                                        break

                    if not has_interrupt:
                        last_msg = response["messages"][-1]
                        if isinstance(last_msg, AIMessage):
                            answer = last_msg.content
                        else:
                            answer = str(last_msg.content) if hasattr(last_msg, 'content') else str(last_msg)
                        user_data['messages'].append({'role': 'assistant', 'content': answer})

                except Exception as e:
                    user_data['messages'].append({'role': 'assistant', 'content': f"处理出错: {str(e)}"})

            user_sessions[user_id] = user_data

    return render_template_string(HTML,
                                  messages=user_data['messages'],
                                  waiting_for_input=user_data['waiting_for_input'],
                                  full_info=user_data.get('full_info', ''))

@flask_app.route('/clear')
def clear():
    user_id = session.get('user_id')
    if user_id and user_id in user_sessions:
        del user_sessions[user_id]
    session.pop('user_id', None)
    return render_template_string(HTML, messages=[], waiting_for_input=False, full_info='')

if __name__ == '__main__':
    flask_app.run(debug=True, port=5000)
