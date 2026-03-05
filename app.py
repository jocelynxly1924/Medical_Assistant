from flask import Flask, render_template, request, jsonify, session, g
import uuid
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from graph_draft import get_graph
from extensions import socketio

app = Flask(__name__)
app.secret_key = 'secret-key-in-production-mode'

# 初始化 SocketIO
socketio.init_app(app, cors_allowed_origins="*")

graph_app = get_graph()

# 在每个请求前将 thread_id 存入上下文变量
@app.before_request
def before_request():
    if 'thread_id' not in session:
        session['thread_id'] = str(uuid.uuid4())
    pass

# WebSocket 连接事件
@socketio.on('connect')
def handle_connect():
    thread_id = session.get('thread_id')
    if thread_id:
        # 将当前客户端加入以 thread_id 命名的房间
        socketio.server.enter_room(request.sid, thread_id)
        print(f"Client {request.sid} joined room {thread_id}")

@socketio.on('disconnect')
def handle_disconnect():
    thread_id = session.get('thread_id')
    if thread_id:
        socketio.server.leave_room(request.sid, thread_id)


@app.route('/')
def index():
    if 'thread_id' not in session:
        session['thread_id'] = str(uuid.uuid4())
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message', '').strip()

    if not user_input:
        return jsonify({'error': '请输入消息'}), 400

    thread_id = session.get('thread_id')
    print(f"DEBUG: 当前会话 thread_id = {thread_id}")

    config = {
        "configurable": {"thread_id": thread_id},
        "thread_id_for_tools": thread_id  # 确保这个键被正确设置
    }

    print(f"DEBUG: 创建的 config = {config}")

    try:
        state = graph_app.get_state(config)
        
        if state.next:
            response = graph_app.invoke(Command(resume=user_input), config=config)
        else:
            response = graph_app.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config
            )
        
        if response.get('high_risk_words'):
            session['thread_id'] = str(uuid.uuid4())
            return jsonify({
                'response': '⚠️ 检测到可能存在高风险情况，建议您及时线下就医！',
                'finished': True
            })
        
        current_state = graph_app.get_state(config)
        
        if current_state.next:
            print(f"DEBUG: state.next = {current_state.next}")
            print(f"DEBUG: state.values = {current_state.values}")
            print(f"DEBUG: state.tasks = {current_state.tasks}")
            
            tasks = current_state.tasks
            if tasks:
                for task in tasks:
                    print(f"DEBUG: task = {task}")
                    print(f"DEBUG: task.interrupts = {task.interrupts if hasattr(task, 'interrupts') else 'no interrupts attr'}")
                    if hasattr(task, 'interrupts') and task.interrupts:
                        interrupt_data = task.interrupts[0].value
                        print(f"DEBUG: interrupt_data = {interrupt_data}")
                        if isinstance(interrupt_data, dict):
                            question = interrupt_data.get('question', '请提供更多信息')
                        else:
                            question = str(interrupt_data) if interrupt_data else '请提供更多信息'
                        return jsonify({
                            'response': question,
                            'finished': False
                        })
            return jsonify({
                'response': '请提供更多信息',
                'finished': False
            })
        
        if response.get('messages'):
            last_message = response['messages'][-1]
            ai_response = last_message.content if hasattr(last_message, 'content') else str(last_message)
        else:
            ai_response = '处理完成'
        
        rag_used = response.get('rag_times', 0) > 0
        
        session['thread_id'] = str(uuid.uuid4())
        
        return jsonify({
            'response': ai_response,
            'finished': True,
            'rag_used': rag_used
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'处理出错: {str(e)}'}), 500

@app.route('/reset', methods=['POST'])
def reset():
    session['thread_id'] = str(uuid.uuid4())
    return jsonify({'status': 'success', 'message': '对话已重置'})

if __name__ == '__main__':
    # app.run(debug=True, port=5001)
    socketio.run(app, debug=True, port=5001, allow_unsafe_werkzeug=True)
