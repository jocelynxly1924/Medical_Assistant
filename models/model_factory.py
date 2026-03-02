import os
from langchain_openai import ChatOpenAI

def get_embedding_client(model_name='bge-m3', organization='ollama'):
    if organization == 'ollama':
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(model='bge-m3:latest')
    elif organization == 'dashscope':
        return ChatOpenAI(model = model_name,
                          api_key=os.environ['DASHSCOPE_API_KEY'],
                          base_url='https://dashscope.aliyuncs.com/compatible-mode/v1')
    else:
        return ValueError(f'{organization} is not supported!')

def get_llm_client(model_name, organization='dashscope'):
    if organization == 'ollama':
        from langchain_ollama import OllamaLLM
        return OllamaLLM(model='qwen2.5:7b-instruct-q4_K_M')
    elif organization == 'dashscope':
        return ChatOpenAI(model = model_name,
                      api_key=os.environ['DASHSCOPE_API_KEY'],
                      base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
                      )

if __name__ == '__main__':
    embedding_client = get_embedding_client(model_name='bge-m3', organization='ollama')
    llm_client = get_llm_client(model_name='qwen2.5',organization='ollama')
    llm_client2 = get_llm_client(model_name='qwen-max',organization='dashscope')
    print(embedding_client)
    print(llm_client.invoke("hello world"))
    print(llm_client2.invoke("hello world"))