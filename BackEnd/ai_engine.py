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
import main
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# --- 全局配置与常量定义 ---
OLLAMA_URL = "http://127.0.0.1:11434"  # 本地 Ollama 服务地址
DB_PATH = os.path.join(os.getcwd(), "faiss_index")  # 向量数据库本地持久化路径

# --- 1. 动态初始化 Embedding 模型(若采用API则不初始化 Embedding 模型) ---
def check_ollama_alive():
    try:
        # 发送 1 秒超时的请求，如果没开 Ollama 会立刻报错拦截
        res = requests.get(OLLAMA_URL, timeout=1)
        return res.status_code == 200
    except:
        return False

# 动态初始化 embeddings
if check_ollama_alive():
    try:
        embeddings = OllamaEmbeddings(model="bge-m3", base_url=OLLAMA_URL)
        print("✅ 检测到本地 Ollama，知识库 (RAG) 功能已激活。")
    except Exception as e:
        embeddings = None
        print(f"⚠️ Ollama 异常: {e}")
else:
    embeddings = None
    print("⚠️ 未检测到本地 Ollama 服务。知识库向量检索功能已禁用，但不影响使用 API 进行数据分析。")

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
【财务数据摘要】(事实依据):
{data_summary}

【参考知识库】(仅作参考):
{context}

【对话历史】(上下文背景):
{history_str}

【当前用户指令】:
{user_query}

请基于数据和上下文，以财务顾问身份回答：
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

def run_analysis(model_name, data_summary, user_query, chat_history=[], use_custom_api=False, api_key=None,
                 api_base=None):
    """
        Agent 模式分析函数
        :param model_name: 模型名称
        :param data_summary: 财务数据摘要
        :param user_query: 用户问题
        :param chat_history: 历史对话记录 (List[Dict])
        """
    global vector_store
    # --- 格式化历史记录 ---
    recent_history = chat_history[-6:]
    history_str = "无（这是第一轮对话）"
    if recent_history:
        history_str = ""
        for msg in recent_history:
            role = "用户" if msg['role'] == 'user' else "AI顾问"
            content = msg['content']
            history_str += f"{role}: {content}\n"

    print(f"🚀 Agent 启动 | 模型: {model_name} | 云端API: {use_custom_api}")

    try:
        # 知识库装载
        if vector_store is None:
            load_existing_db()

        # --- 动态初始化 LLM ---
        if use_custom_api and api_key:
            # 走云端 API
            print("🌐 使用第三方云端大模型接口...")
            llm = ChatOpenAI(
                model_name=model_name,
                api_key=api_key,
                base_url=api_base if api_base else "https://api.openai.com/v1",
                temperature=0.6,
                timeout=60,
                max_retries=2
            )
        else:
            # 走本地 Ollama
            print("🖥️ 使用本地 Ollama 大模型...")
            llm = OllamaLLM(
                model=model_name,
                base_url=OLLAMA_URL,
                num_ctx=4096,
                timeout=120,
                temperature=0.6
            )
        # 构建输入参数
        input_args = {
            "user_query": user_query,
            "data_summary": data_summary,
            "history_str": history_str,
            "input": user_query
        }

        # --- 3. 运行 Chain  ---
        if vector_store:
            retriever = vector_store.as_retriever(search_kwargs={"k": 2})
            prompt = ChatPromptTemplate.from_messages([
                ("system", AGENT_SYSTEM_PROMPT),
                ("human", AGENT_USER_TEMPLATE)
            ])
            question_answer_chain = create_stuff_documents_chain(llm, prompt)
            rag_chain = create_retrieval_chain(retriever, question_answer_chain)

            res = rag_chain.invoke(input_args)
            return res["answer"]
        else:
            prompt = ChatPromptTemplate.from_messages([
                ("system", AGENT_SYSTEM_PROMPT),
                ("human", AGENT_USER_TEMPLATE.replace("{context}", "无"))
            ])
            chain = prompt | llm
            # 清洗文本
            res = chain.invoke(input_args)
            # 兼容处理提取文本
            if hasattr(res, 'content'):
                return res.content  # ChatOpenAI 返回格式
            return res  # Ollama 返回格式

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"思考出错: {str(e)}"

def check_kb_exists():
    """
    检查知识库文件夹是否存在。
    用于前端判断显示状态。
    """
    return os.path.exists(DB_PATH) and os.path.isdir(DB_PATH)