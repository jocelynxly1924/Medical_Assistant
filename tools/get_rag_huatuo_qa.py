import time

from langchain_core.messages import ToolMessage
from langchain_ollama import OllamaEmbeddings
import os
from states.states import PublicState
from langchain_chroma import Chroma
from langchain_core.tools import tool

def get_retriever(repository_name = 'Huatuo_lite_respiratory_full'):
    embedding_client = OllamaEmbeddings(model="bge-m3:latest")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 获取项目根目录（tools的上一级）
    project_root = os.path.dirname(current_dir)
    # 正确的数据路径
    persist_directory = os.path.join(project_root, 'data', repository_name)
    # print(persist_directory)

    vector_store = Chroma(collection_name=repository_name,
                          embedding_function=embedding_client,
                          persist_directory=persist_directory, )
    retriever = vector_store.as_retriever(search_kwargs={'k': 3})
    return retriever

def get_source(docs):
    source = '————————————————————————————————————\n\n数据来源：Huatuo Lite数据库 \n 参考案例：\n'
    for i, doc in enumerate(docs):
        query = doc.page_content
        answer = doc.metadata['answer']
        source += f"{i+1}.用户问题：{query}\n医生回答：{answer}\n"
    source += '\n本建议仅为AI基于有限信息的分析结果，不作为最终医疗依据。您的健康至关重要，具体的诊疗方案请务必咨询专业医生。'
    print(source)
    return source


@tool
def get_rag_qa_tool(query: str):

    """从Huatuo数据库中调取医疗诊断问答对，以获取疾病具体信息、症状、治疗方法、注意事项等信息。

    Args:
        query: 需要查询的语句

    Returns:
        从Huatuo医疗问答对数据库中获取的查询结果
        """

    yellow = '\033[93m'
    reset = '\033[0m'
    print(f"{yellow}正在查询HuaTuo数据库……{reset}")

    retriever = get_retriever(repository_name='Huatuo_lite_respiratory_full')
    docs = retriever.invoke(query)
    print(f"查询到内容：\n{docs}")
    # get_source(docs)
    source = get_source(docs)
    return {
        'rag_retrieved_docs': docs,
        'source': source
    }

if __name__=='__main__':

    # print(get_rag_qa_tool.invoke({'query':"咳嗽五天没好怎么办"}))
    retriever_500 = get_retriever(repository_name = 'Huatuo_lite_respiratory_demo')
    retriever_5000 = get_retriever(repository_name = 'Huatuo_lite_respiratory_full')

    start_time = time.time()
    print(retriever_500.invoke("咳嗽五天没好怎么办"))
    end_time = time.time()
    print(f"ChromaDB 500 索引时间：{end_time - start_time}秒")

    start_time = time.time()
    print(retriever_5000.invoke("咳嗽五天没好怎么办"))
    end_time = time.time()
    print(f"ChromaDB 5000 索引时间：{end_time - start_time}秒")

    print(get_rag_qa_tool.invoke({'query':"咳嗽五天没好怎么办"}))

