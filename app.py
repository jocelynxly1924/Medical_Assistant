from flask import Flask, render_template, request, jsonify, session
import uuid
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from graph_draft import get_graph

app = Flask(__name__)
app.secret_key = 'secret-key-in-production-mode'

graph_app = get_graph()

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
    config = {"configurable": {"thread_id": thread_id}}
    
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
        
        session['thread_id'] = str(uuid.uuid4())
        
        return jsonify({
            'response': ai_response,
            'finished': True
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
    app.run(debug=True, port=5001)
