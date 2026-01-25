# ai_engine.py
"""
AI 引擎核心模块
功能：
1. 管理与 Ollama 本地大模型的连接与交互
2. 处理 RAG (检索增强生成) 逻辑：包括知识库的构建(Embedding)与检索
3. 定义 Prompt 模板与 Agent 行为规范
"""

import os
import time
import requests
import traceback
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# --- 全局配置与常量定义 ---
OLLAMA_URL = "http://127.0.0.1:11434"  # 本地 Ollama 服务地址
DB_PATH = os.path.join(os.getcwd(), "faiss_index")  # 向量数据库本地持久化路径

# --- 1. 安全初始化 Embedding 模型 ---
try:
    embeddings = OllamaEmbeddings(
        model="bge-m3",
        base_url=OLLAMA_URL
    )
except Exception as e:
    print(f"⚠️ Embedding 初始化警告: {e}")
    embeddings = None

# 全局向量数据库实例
vector_store = None

# --- Prompt 提示词工程 ---

# 系统预设: 定义 AI 的角色、行为准则和输出格式
AGENT_SYSTEM_PROMPT = """
你叫“智财云AI审计师”，是魔珐星云企业的数字财务专家。
你的任务是根据用户的提问和提供的财务数据摘要进行分析。
【核心原则 - 必须严格遵守】:
1. **数据优先**：你的分析必须基于【财务数据摘要】中的数字。如果数据表现良好，不要强行批评。
2. **知识库仅作参考**：【参考知识库】是你的理论后台（如审计准则），仅当数据出现异常或用户询问合规性时才引用。**严禁**大段背诵知识库内容。
3. **角色代入**：你现在正通过数字人的语音与用户对话，请使用口语化、亲切但专业的语气。**切勿** 使用 markdown 格式（如 **粗体**、## 标题），因为语音合成无法朗读这些符号。
4. **简洁性**：回答控制在 100-200 字以内，直接说重点。你不得与用户展开无关互动，如调侃等行为。
6. **回答相关性**：你的回答需严格遵守用户的指令。但是你也应该铭记自身作为数字财务专家的身份。用户发送无关指令（如你好、天气怎么样等等）需礼貌提示用户自身作为数字财务专家可提供专业分析
"""

# 用户 RAG 模板: 结合 财务数据 + 知识库上下文 + 用户问题
AGENT_USER_TEMPLATE = """
【财务数据摘要】(这是你分析的事实依据):
{data_summary}

【参考知识库】(仅作为判断标准，不要复述):
{context}

【用户指令】:
{user_query}

请以财务顾问的身份回答用户指令：
"""

# 无 RAG 兜底模板: 仅基于财务数据分析，不涉及知识库
NO_RAG_PROMPT = """
你是一位专业的财务审计师。请根据以下的【财务数据摘要】进行分析。
如果数据为空，请礼貌地提示用户先录入数据。

【财务数据摘要】:
{input}

请给出分析或建议（中文）：
"""


def get_available_models():
    """
    查询 Ollama 服务获取所有已安装的可用模型。
    逻辑：
    1. 调用 Ollama API 获取模型列表
    2. 过滤掉 Embedding 模型 (如 bge, nomic, bert 等)，只保留 LLM
    3. 如果连接失败，返回默认兜底模型 'qwen2.5:7b'
    Returns:
        list: 可用的 LLM 模型名称列表
    """
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            all_models = [model['name'] for model in data['models']]
            # 过滤Embedding 模型
            exclude_keywords = ['embed', 'bge', 'nomic', 'bert']
            llm_models = []
            for m in all_models:
                if not any(k in m.lower() for k in exclude_keywords):
                    llm_models.append(m)
            return llm_models
    except Exception as e:
        print(f"❌ Ollama 连接失败 (获取模型列表): {e}")
    return ["Qwen2.5:7b"]  # 兜底


def init_knowledge_base(file_path):
    """
    初始化/重建知识库 (RAG 核心步骤)。
    流程：
    1. 加载文件 (PDF 或 TXT)
    2. 文本分块 (RecursiveCharacterTextSplitter)
    3. 向量化 (Embedding) 并建立 FAISS 索引
    4. 持久化保存到本地磁盘
    Args:
        file_path (str): 上传文件的本地临时路径
    Returns:
        bool: 是否成功建立索引
    """
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
            # 文本切分
            splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20)
            splits = splitter.split_documents(docs)
            if embeddings:
                # 生成向量并创建索引
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
    """
    加载已存在的本地 FAISS 向量索引。
    通常在 Agent 启动分析前调用，避免重复计算。
    """
    global vector_store
    if os.path.exists(DB_PATH) and embeddings:
        try:
            # allow_dangerous_deserialization=True 是为了允许加载本地 pickle 文件
            vector_store = FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)
            print("✅ 已加载本地知识库索引")
        except Exception as e:
            print(f"⚠️ 加载本地索引失败: {e}")


def run_analysis(model_name, data_summary, user_query):
    """
    Agent 核心分析函数。
    逻辑：
    1. 尝试加载知识库
    2. 初始化指定的大语言模型 (LLM)
    3. 判断是否存在知识库：
       - 存在 (RAG模式): 检索相关文档 -> 结合数据与问题 -> 生成回答
       - 不存在 (纯LLM模式): 仅根据财务数据和问题 -> 生成回答
    Args:
        model_name (str): 选用的 Ollama 模型名称
        data_summary (str): 数据库生成的财务统计摘要文本
        user_query (str): 用户的具体问题或指令
    Returns:
        str: AI 生成的分析结果
    """
    global vector_store
    print(f"🚀 Agent 启动 | 模型: {model_name}")
    try:
        # 1. 确保知识库已尝试加载
        if vector_store is None:
            load_existing_db()
        # 2. 初始化 LLM 配置
        llm = OllamaLLM(
            model=model_name,
            base_url=OLLAMA_URL,
            num_ctx=4096,  # 上下文窗口大小，需根据显存调整
            timeout=120,
            temperature=0.7
        )

        # 3. 构建 RAG Chain (检索增强生成)
        if vector_store:
            # 定义检索器：只取相关性最高的 2 个片段，避免上下文过长
            retriever = vector_store.as_retriever(search_kwargs={"k": 2})
            # 组合 Prompt：System + Human
            prompt = ChatPromptTemplate.from_messages([
                ("system", AGENT_SYSTEM_PROMPT),
                ("human", AGENT_USER_TEMPLATE)
            ])
            # create_stuff_documents_chain 会自动将检索到的文档填充至 {context} 变量
            question_answer_chain = create_stuff_documents_chain(llm, prompt)
            rag_chain = create_retrieval_chain(retriever, question_answer_chain)
            # 执行链式调用
            res = rag_chain.invoke({
                "input": user_query,  # 用于检索器搜索文档
                "user_query": user_query,  # 传递给 Prompt
                "data_summary": data_summary  # 传递给 Prompt
            })
            return res["answer"]
        else:
            # 无知识库模式 (纯 LLM 分析)
            prompt = ChatPromptTemplate.from_messages([
                ("system", AGENT_SYSTEM_PROMPT),
                ("human", "【财务数据摘要】:\n{data_summary}\n\n【用户指令】:\n{user_query}")
            ])
            # 使用 LCEL 语法构建简单链
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
    """
    检查知识库文件夹是否存在。
    用于前端判断显示状态。
    """
    # DB_PATH 是之前定义的 faiss_index 目录路径
    return os.path.exists(DB_PATH) and os.path.isdir(DB_PATH)