from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaEmbeddings
import json
import os
import time
from tools.get_rag_huatuo_qa import get_retriever


# # 获取当前文件所在目录
# current_dir = os.path.dirname(os.path.abspath(__file__))
# # 假设文件在项目根目录的data文件夹中
# json_path = os.path.join(current_dir, 'data', 'respiratory_symptoms.jsonl')

def get_document_from_jsonl(file_path = 'data/respiratory_symptoms.jsonl'):
    documents_respiratory = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            data = json.loads(line)

            doc = Document(
                page_content=data['question'],
                metadata={
                    'answer': data['answer'],
                    'label': data['label'],
                    'disease': data['related_diseases']
                }
            )
            documents_respiratory.append(doc)
    return documents_respiratory

# 先测试小批量
# documents = documents[0:24]
# print(documents)

def json_to_chromadb(documents):
    embedding_client = OllamaEmbeddings(model="bge-m3:latest")

    vector_store = Chroma(collection_name='Huatuo_lite_respiratory_demo',
                          embedding_function=embedding_client,
                          persist_directory='data/Huatuo_lite_respiratory_demo', )
    vector_store.add_documents(documents)


if __name__ == '__main__':
    # documents = get_document_from_jsonl()
    # documents = documents[0:24]
    # json_to_chromadb(documents)
    retriever = get_retriever()
    start_time = time.time()
    print(retriever.invoke("咳嗽五天没好怎么办"))
    end_time = time.time()
    print(f"ChromaDB 索引时间：{end_time - start_time}秒")
