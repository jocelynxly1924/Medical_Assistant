import redis
import json
from typing import Optional, List
from langchain_core.messages import HumanMessage

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

def save_conversation_history(user_id: str, query_refined: str) -> bool:
    """
    保存对话历史到Redis
    累积保存提炼后的用户查询问题（query_refined）
    
    参数:
        user_id: 用户唯一标识
        query_refined: 提炼后的用户查询问题
    
    返回:
        bool: 是否保存成功
    """
    try:
        key = f"conversation_history:{user_id}"
        
        existing_data = redis_client.get(key)
        if existing_data:
            history_data = json.loads(existing_data)
            queries = history_data.get("queries", [])
        else:
            queries = []
        
        queries.append(query_refined)
        
        history_data = {"queries": queries}
        redis_client.set(key, json.dumps(history_data, ensure_ascii=False))
        print(f"已保存历史查询，当前共{len(queries)}条记录")
        return True
    except Exception as e:
        print(f"保存对话历史失败: {e}")
        return False

def get_conversation_history(user_id: str) -> Optional[str]:
    """
    从Redis获取历史对话信息
    返回所有提炼后的用户查询问题的合并字符串
    
    参数:
        user_id: 用户唯一标识
    
    返回:
        Optional[str]: 合并后的历史查询信息，如果不存在则返回None
    """
    try:
        key = f"conversation_history:{user_id}"
        data = redis_client.get(key)
        if data:
            history_data = json.loads(data)
            queries = history_data.get("queries", [])
            if queries:
                return "\n".join([f"{i+1}. {q}" for i, q in enumerate(queries)])
        return None
    except Exception as e:
        print(f"获取对话历史失败: {e}")
        return None

def clear_conversation_history(user_id: str) -> bool:
    """
    清除用户的对话历史
    
    参数:
        user_id: 用户唯一标识
    
    返回:
        bool: 是否清除成功
    """
    try:
        key = f"conversation_history:{user_id}"
        redis_client.delete(key)
        return True
    except Exception as e:
        print(f"清除对话历史失败: {e}")
        return False
