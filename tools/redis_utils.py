import redis
import os
import json
from typing import Optional, List, Any, Dict, Set
import numpy as np
from contextvars import ContextVar

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

QUERY_INFO_KEY = "medical_assistant:refined_info"
KNOWLEDGE_CACHE_KEY = "medical_assistant:knowledge_cache"
SESSION_USED_KEYS = "medical_assistant:session_used_keys"

RAG_CACHE_EXPIRE = 86400
MEDICINE_CACHE_EXPIRE = 604800
SESSION_EXPIRE = 3600

SEMANTIC_SIMILARITY_THRESHOLD = 0.9

_redis_client = None
_embedding_client = None

current_session_id: ContextVar[str] = ContextVar('current_session_id', default='default')


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


def get_embedding_client():
    global _embedding_client
    if _embedding_client is None:
        from langchain_ollama import OllamaEmbeddings
        _embedding_client = OllamaEmbeddings(model="bge-m3:latest")
    return _embedding_client


def _compute_similarity(text1: str, text2: str) -> float:
    embedding_client = get_embedding_client()
    emb1 = embedding_client.embed_query(text1)
    emb2 = embedding_client.embed_query(text2)
    emb1_np = np.array(emb1)
    emb2_np = np.array(emb2)
    similarity = np.dot(emb1_np, emb2_np) / (np.linalg.norm(emb1_np) * np.linalg.norm(emb2_np))
    return float(similarity)


def _find_similar_rag_cache(query: str, threshold: float = SEMANTIC_SIMILARITY_THRESHOLD) -> Optional[Dict[str, Any]]:
    try:
        client = get_redis_client()
        pattern = f"{KNOWLEDGE_CACHE_KEY}:rag:*"
        keys = client.keys(pattern)
        
        if not keys:
            return None
        
        for key in keys:
            cached_query = key.replace(f"{KNOWLEDGE_CACHE_KEY}:rag:", "")
            similarity = _compute_similarity(query, cached_query)
            if similarity >= threshold:
                print(f"[Redis] RAG语义缓存命中: '{query[:30]}...' 与 '{cached_query[:30]}...' 相似度 {similarity:.3f}")
                cached = client.get(key)
                if cached:
                    return json.loads(cached)
        return None
    except Exception as e:
        print(f"[Redis] 语义相似度匹配失败: {e}")
        return None


def _get_session_used_keys(session_id: str) -> Set[str]:
    try:
        client = get_redis_client()
        key = f"{SESSION_USED_KEYS}:{session_id}"
        used_keys = client.smembers(key)
        return set(used_keys) if used_keys else set()
    except Exception as e:
        print(f"[Redis] 获取会话已用keys失败: {e}")
        return set()


def _add_to_session_used_keys(session_id: str, cache_key: str) -> bool:
    try:
        client = get_redis_client()
        key = f"{SESSION_USED_KEYS}:{session_id}"
        client.sadd(key, cache_key)
        client.expire(key, SESSION_EXPIRE)
        return True
    except Exception as e:
        print(f"[Redis] 添加会话已用key失败: {e}")
        return False


def clear_session_used_keys(session_id: str) -> bool:
    try:
        client = get_redis_client()
        key = f"{SESSION_USED_KEYS}:{session_id}"
        client.delete(key)
        return True
    except Exception as e:
        print(f"[Redis] 清除会话已用keys失败: {e}")
        return False


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


def _build_rag_cache_key(query: str) -> str:
    return f"{KNOWLEDGE_CACHE_KEY}:rag:{query}"


def _build_medicine_cache_key(medicine_name: str, target_field: str) -> str:
    return f"{KNOWLEDGE_CACHE_KEY}:medicine:{medicine_name}的{target_field}"


def _find_similar_medicine_cache(medicine_name: str, target_fields: List[str], threshold: float = SEMANTIC_SIMILARITY_THRESHOLD) -> List[Dict[str, Any]]:
    try:
        client = get_redis_client()
        pattern = f"{KNOWLEDGE_CACHE_KEY}:medicine:{medicine_name}的*"
        keys = client.keys(pattern)
        
        if not keys:
            return []
        
        results = []
        for target_field in target_fields:
            current_query = f"{medicine_name}的{target_field}"
            
            for key in keys:
                cached_query = key.replace(f"{KNOWLEDGE_CACHE_KEY}:medicine:", "")
                similarity = _compute_similarity(current_query, cached_query)
                if similarity >= threshold:
                    print(f"[Redis] 药品语义缓存命中: '{current_query}' 与 '{cached_query}' 相似度 {similarity:.3f}")
                    cached = client.get(key)
                    if cached:
                        results.append(json.loads(cached))
                    break
        
        return results
    except Exception as e:
        print(f"[Redis] 药品语义相似度匹配失败: {e}")
        return []


def get_rag_cache(query: str, session_id: str = None) -> Optional[Dict[str, Any]]:
    try:
        client = get_redis_client()
        key = _build_rag_cache_key(query)
        
        effective_session_id = session_id or current_session_id.get()
        
        if effective_session_id and effective_session_id != 'default':
            used_keys = _get_session_used_keys(effective_session_id)
            if key in used_keys:
                print(f"[Redis] RAG缓存已在本轮使用过，跳过: {query[:30]}...")
                return None
        
        cached = client.get(key)
        if cached:
            print(f"[Redis] RAG缓存命中: '{query[:30]}...' 与 '{query[:30]}...' 相似度 1.000")
            if effective_session_id and effective_session_id != 'default':
                _add_to_session_used_keys(effective_session_id, key)
            return json.loads(cached)
        
        similar_result = _find_similar_rag_cache(query)
        if similar_result:
            if effective_session_id and effective_session_id != 'default':
                _add_to_session_used_keys(effective_session_id, key)
            return similar_result
        
        return None
    except Exception as e:
        print(f"[Redis] 获取RAG缓存失败: {e}")
        return None


def set_rag_cache(query: str, result: Dict[str, Any]) -> bool:
    try:
        client = get_redis_client()
        key = _build_rag_cache_key(query)
        client.set(key, json.dumps(result, ensure_ascii=False), ex=RAG_CACHE_EXPIRE)
        print(f"[Redis] RAG缓存已保存: {query[:30]}...")
        return True
    except Exception as e:
        print(f"[Redis] 保存RAG缓存失败: {e}")
        return False


def get_medicine_cache(medicine_name: str, target_fields: List[str], session_id: str = None) -> tuple:
    """
    返回: (cached_results, missing_fields)
    - cached_results: 缓存命中的结果列表
    - missing_fields: 未命中的字段列表（需要爬虫检索）
    """
    try:
        client = get_redis_client()
        effective_session_id = session_id or current_session_id.get()
        
        results = []
        found_fields = set()
        
        for target_field in target_fields:
            key = _build_medicine_cache_key(medicine_name, target_field)
            current_query = f"{medicine_name}的{target_field}"
            
            if effective_session_id and effective_session_id != 'default':
                used_keys = _get_session_used_keys(effective_session_id)
                if key in used_keys:
                    print(f"[Redis] 药品缓存已在本轮使用过，跳过: {current_query}")
                    continue
            
            cached = client.get(key)
            if cached:
                print(f"[Redis] 药品缓存命中: '{current_query}' 与 '{current_query}' 相似度 1.000")
                if effective_session_id and effective_session_id != 'default':
                    _add_to_session_used_keys(effective_session_id, key)
                results.append(json.loads(cached))
                found_fields.add(target_field)
        
        missing_fields = [f for f in target_fields if f not in found_fields]
        
        if missing_fields:
            similar_results = _find_similar_medicine_cache(medicine_name, missing_fields)
            for result in similar_results:
                if 'medicine_info' in result and 'content' in result['medicine_info']:
                    for field in result['medicine_info']['content'].keys():
                        found_fields.add(field)
            results.extend(similar_results)
        
        final_missing_fields = [f for f in target_fields if f not in found_fields]
        
        return results, final_missing_fields
    except Exception as e:
        print(f"[Redis] 获取药品缓存失败: {e}")
        return [], target_fields


def set_medicine_cache_by_field(medicine_name: str, field: str, content: str, source: str) -> bool:
    try:
        client = get_redis_client()
        key = _build_medicine_cache_key(medicine_name, field)
        result = {
            'medicine_info': {
                'name': medicine_name,
                'content': {field: content}
            },
            'source': source
        }
        client.set(key, json.dumps(result, ensure_ascii=False), ex=MEDICINE_CACHE_EXPIRE)
        print(f"[Redis] 药品缓存已保存: {medicine_name}的{field}")
        return True
    except Exception as e:
        print(f"[Redis] 保存药品缓存失败: {e}")
        return False
