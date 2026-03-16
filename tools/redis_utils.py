import redis
import os
from typing import Optional

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

QUERY_INFO_KEY = "medical_assistant:refined_info"

_redis_client = None


def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )
    return _redis_client


def save_refined_info(info: str, user_id: str = "default", expire_seconds: int = 600) -> bool:
    try:
        client = get_redis_client()
        key = f"{QUERY_INFO_KEY}:{user_id}"
        client.set(key, info, ex=expire_seconds)
        return True
    except Exception as e:
        print(f"[Redis] 保存refined_info失败: {e}")
        return False


def get_latest_refined_info(user_id: str = "default") -> Optional[str]:
    try:
        client = get_redis_client()
        key = f"{QUERY_INFO_KEY}:{user_id}"
        info = client.get(key)
        return info
    except Exception as e:
        print(f"[Redis] 获取refined_info失败: {e}")
        return None


def clear_refined_info(user_id: str = "default") -> bool:
    try:
        client = get_redis_client()
        key = f"{QUERY_INFO_KEY}:{user_id}"
        client.delete(key)
        return True
    except Exception as e:
        print(f"[Redis] 清除refined_info失败: {e}")
        return False
