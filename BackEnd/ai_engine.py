import os
import time
import requests
import traceback  # <--- 新增：用于打印详细报错
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# 全局配置
OLLAMA_URL = "http://127.0.0.1:11434"
DB_PATH = os.path.join(os.getcwd(), "faiss_index")

# --- 1. 安全初始化 Embedding ---
# 尝试连接 Ollama，如果连不上或模型不对，不要让程序直接启动失败，而是运行时报错
try:
    embeddings = OllamaEmbeddings(
        model="bge-m3",  # 确保你终端里运行过 `ollama pull bge-m3`
        base_url=OLLAMA_URL
    )
except Exception as e:
    print(f"⚠️ Embedding 初始化警告: {e}")
    embeddings = None

vector_store = None

AGENT_SYSTEM_PROMPT = """
你叫“智财云AI审计师”，是魔珐星云企业的数字财务专家。
你的任务是根据用户的提问和提供的财务数据摘要进行分析。
【核心原则 - 必须严格遵守】:
1. **数据优先**：你的分析必须基于【财务数据摘要】中的数字。如果数据表现良好，不要强行批评。
2. **知识库仅作参考**：【参考知识库】是你的理论后台（如审计准则），仅当数据出现异常或用户询问合规性时才引用。**严禁**大段背诵知识库内容。
3. **角色代入**：你现在正通过数字人的语音与用户对话，请使用口语化、亲切但专业的语气。不要使用 markdown 格式（如 **粗体**、## 标题），因为语音合成无法朗读这些符号。
4. **简洁性**：回答控制在 100-200 字以内，直接说重点。
5. **切勿** 在回答中使用markdown来生成文本。生成文本应为纯text，仅保留必要的排版
"""

AGENT_USER_TEMPLATE = """
【财务数据摘要】(这是你分析的事实依据):
{data_summary}

【参考知识库】(仅作为判断标准，不要复述):
{context}

【用户指令】:
{user_query}

请以财务顾问的身份回答用户指令：
"""


NO_RAG_PROMPT = """
你是一位专业的财务审计师。请根据以下的【财务数据摘要】进行分析。
如果数据为空，请礼貌地提示用户先录入数据。

【财务数据摘要】:
{input}

请给出分析或建议（中文）：
"""


def get_available_models():
    """查询 Ollama 获取所有可用模型"""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            all_models = [model['name'] for model in data['models']]
            # 过滤掉 embedding 模型
            exclude_keywords = ['embed', 'bge', 'nomic', 'bert']
            llm_models = []
            for m in all_models:
                if not any(k in m.lower() for k in exclude_keywords):
                    llm_models.append(m)
            return llm_models
    except Exception as e:
        print(f"❌ Ollama 连接失败 (获取模型列表): {e}")
    return ["qwen2.5:7b"]  # 兜底


def init_knowledge_base(file_path):
    global vector_store
    print(f"📂 处理知识库文件: {file_path}")
    docs = []
    try:
        if file_path.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
            docs = loader.load()
        elif file_path.endswith('.txt'):
            loader = TextLoader(file_path, encoding='utf-8')
            docs = loader.load()

        if docs:
            splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20)
            splits = splitter.split_documents(docs)
            if embeddings:
                vector_store = FAISS.from_documents(splits, embeddings)
                vector_store.save_local(DB_PATH)
                return True
            else:
                print("❌ Embedding 模型未就绪，无法建立索引")
                return False
    except Exception as e:
        print(f"❌ 知识库处理失败: {e}")
        traceback.print_exc()
        return False
    return False


def load_existing_db():
    global vector_store
    if os.path.exists(DB_PATH) and embeddings:
        try:
            vector_store = FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)
            print("✅ 已加载本地知识库索引")
        except Exception as e:
            print(f"⚠️ 加载本地索引失败: {e}")


def run_analysis(model_name, data_summary, user_query):
    """
    Agent 模式分析函数
    :param model_name: 模型名称
    :param data_summary: 也就是 database.py 生成的那段文本
    :param user_query: 用户具体问的问题（例如：帮我分析下上个月的利润）
    """
    global vector_store

    print(f"🚀 Agent 启动 | 模型: {model_name}")

    try:
        # 1. 确保知识库加载
        if vector_store is None:
            load_existing_db()

        # 2. 初始化 LLM
        llm = OllamaLLM(
            model=model_name,
            base_url=OLLAMA_URL,
            num_ctx=4096,  # 如果显存够，Agent 模式建议大一点
            timeout=120,
            temperature=0.7  # 稍微增加一点创造性，让对话更自然
        )

        # 3. 构建 RAG Chain
        if vector_store:
            # 检索器：只取最相关的 2 条，减少干扰
            retriever = vector_store.as_retriever(search_kwargs={"k": 2})

            # 组合 Prompt
            # System Prompt 放在 ChatPromptTemplate 的 messages 列表头
            prompt = ChatPromptTemplate.from_messages([
                ("system", AGENT_SYSTEM_PROMPT),
                ("human", AGENT_USER_TEMPLATE)
            ])

            # 使用 create_stuff_documents_chain 会自动把检索到的 docs 填充给 {context}
            question_answer_chain = create_stuff_documents_chain(llm, prompt)
            rag_chain = create_retrieval_chain(retriever, question_answer_chain)

            # 执行
            res = rag_chain.invoke({
                "input": user_query,  # 这里的 input 会被检索器用来搜文档
                "user_query": user_query,  # 传给 Prompt 模板
                "data_summary": data_summary  # 传给 Prompt 模板
            })
            return res["answer"]

        else:
            # 无知识库模式 (纯 LLM)
            prompt = ChatPromptTemplate.from_messages([
                ("system", AGENT_SYSTEM_PROMPT),
                ("human", "【财务数据摘要】:\n{data_summary}\n\n【用户指令】:\n{user_query}")
            ])
            chain = prompt | llm
            res = chain.invoke({
                "data_summary": data_summary,
                "user_query": user_query
            })
            return res

    except Exception as e:
        traceback.print_exc()
        return f"大脑思考时出现错误: {str(e)}"

def check_kb_exists():
    """检查知识库是否存在"""
    # DB_PATH 是之前定义的 faiss_index 目录路径
    return os.path.exists(DB_PATH) and os.path.isdir(DB_PATH)