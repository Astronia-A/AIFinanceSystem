# main.py
import shutil
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pyarrow import nulls
from fastapi.responses import StreamingResponse
from io import BytesIO
import pandas as pd
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import database
import ai_engine

# 初始化 FastAPI 应用实例
app = FastAPI(title="财务数字人后端", description="基于本地大模型的AI财务分析系统后端API")

# --- 中间件配置 ---
# 配置跨域资源共享 (CORS)
# 允许前端从不同端口访问后端 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 后续可将 "*" 替换为具体的域名或 IP
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法 (GET, POST, etc.)
    allow_headers=["*"],  # 允许所有请求头
)

# --- 系统初始化 ---
# 在应用启动时初始化数据库连接和表结构
database.init_db()

# --- 数据模型 (Pydantic Schema) ---
class RecordItem(BaseModel):
    """
    财务记录数据模型
    用于单条记录的添加验证
    """
    item: str  # 收支项目名称
    date: str  # 日期 (格式: YYYY-MM-DD)
    amount: float  # 金额 (正数为收入，负数为支出)

class AnalysisRequest(BaseModel):
    """
        AI 分析请求数据模型
        定义前端发送给 AI 的参数结构
    """
    model_name: str
    user_query: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = None
    # 第三方 API 支持字段
    use_custom_api: bool = False  # 是否使用自定义API
    api_key: Optional[str] = None  # API 密钥
    api_base: Optional[str] = None  # 自定义 API 代理地址 (如: https://api.deepseek.com/v1)

# --- 接口定义 ---
@app.get("/api/models")
def get_models():
    """
    获取可用模型列表
    调用 AI 引擎查询 Ollama 服务中已安装的大模型
    """
    models = ai_engine.get_available_models()
    return {"models": models}


@app.get("/api/records")
def get_records():
    """
    获取所有财务记录
    用于前端图表展示和数据列表渲染
    """
    return database.get_all_records()

@app.get("/api/knowledge/status")
def get_knowledge_status():
    """
        获取ollama是否运行
        用于决定是本地运行大模型还是采用API交流
    """
    exists = ai_engine.check_kb_exists()
    ollama_alive = ai_engine.check_ollama_alive() # 获取存活状态
    return {
        "exists": exists,
        "ollama_active": ollama_alive
    }

@app.post("/api/records")
def add_record(record: RecordItem):
    """
    添加单条财务记录
    接收 JSON 数据并写入数据库
    """
    database.insert_record(record.item, record.date, record.amount)
    return {"status": "success"}

@app.post("/api/upload_knowledge")
async def upload_knowledge(file: UploadFile = File(...)):
    """
    上传并处理知识库文件 (RAG)
    流程:
    1. 接收文件并暂存到本地
    2. 调用 AI 引擎进行向量化处理
    3. 清理临时文件
    """
    # 定义临时文件路径
    file_location = f"temp_{file.filename}"

    # 将上传的文件流写入本地临时文件
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    # 初始化知识库 (向量化)
    success = ai_engine.init_knowledge_base(file_location)

    # 处理完毕后删除临时文件，释放空间
    os.remove(file_location)

    if success:
        return {"message": "知识库加载成功"}
    else:
        raise HTTPException(status_code=400, detail="文件解析失败")


@app.post("/api/chat")
def chat_with_finance(req: AnalysisRequest):
    """
    AI 财务分析核心接口 (Agent)
    流程:
    1. 根据请求的时间范围从数据库获取财务数据摘要
    2. 将数据摘要、用户问题、选定的模型传递给 AI 引擎
    3. 返回 AI 生成的分析结果
    """
    # 1. 确定时间范围
    if req.start_date and req.end_date:
        financial_summary = database.get_filtered_financial_summary(req.start_date, req.end_date)
    else:
        financial_summary = database.get_financial_summary_text()

    # 如果前端没传 history 或者传了 null，这里将其转为空列表 []
    safe_history = req.history if req.history is not None else []
    print(f"📊 收到请求 | 历史消息数: {len(safe_history)} | 当前问题: {req.user_query}")

    # 3. 调用 AI Agent
    response_text = ai_engine.run_analysis(
        model_name=req.model_name,
        data_summary=financial_summary,
        user_query=req.user_query,
        chat_history=safe_history,
        # 用户采用了API调用模型存储的信息
        use_custom_api=req.use_custom_api,  # <--- 新增
        api_key=req.api_key,  # <--- 新增
        api_base=req.api_base  # <--- 新增
    )

    return {"reply": response_text}


@app.get("/api/knowledge/status")
def get_knowledge_status():
    """
    查询知识库状态
    检查向量数据库是否存在，用于前端判断是否需要提示用户上传文档
    """
    exists = ai_engine.check_kb_exists()
    return {"exists": exists}


@app.delete("/api/records/{record_id}")
def delete_record_endpoint(record_id: int):
    """
    删除指定 ID 的财务记录
    """
    success = database.delete_record(record_id)
    if success:
        return {"status": "success", "message": f"记录 {record_id} 已删除"}
    else:
        raise HTTPException(status_code=404, detail="记录不存在或删除失败")


@app.get("/api/template")
def download_template():
    """
    下载 Excel 导入模板
    生成包含标准表头的示例 Excel 文件流，供前端下载
    """
    # 构建仅包含表头的 DataFrame，并插入一行示例数据作为指引
    df = pd.DataFrame(columns=["日期", "项目", "金额"])
    df.loc[0] = ["2024-01-01", "示例收入(正数)或支出(负数)", 1000]
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)
    # 设置响应头，触发浏览器下载行为
    headers = {
        'Content-Disposition': 'attachment; filename="example.xlsx"'
    }
    return StreamingResponse(output, headers=headers,
                             media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.post("/api/records/batch_upload")
async def batch_upload(file: UploadFile = File(...)):
    """
    批量上传 Excel 财务记录
    流程:
    1. 校验文件后缀 (.xlsx, .xls)
    2. 使用 Pandas 读取内存中的文件流
    3. 校验 Excel 列名完整性
    4. 批量插入数据库
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 Excel 文件 (.xlsx, .xls)")

    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        required_columns = {'日期', '项目', '金额'}
        if not required_columns.issubset(df.columns):
            raise HTTPException(status_code=400, detail=f"Excel 缺少必须列: {required_columns}")
        count = database.insert_batch_from_excel(df)
        return {"status": "success", "count": count}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析文件失败: {str(e)}")


if os.path.exists("dist"):
    # 挂载 assets 文件夹 (JS/CSS等静态资源)
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")

    # 捕获所有其他非 API 请求，全部返回 index.html
    @app.get("/{full_path:path}")
    async def serve_vue_app(full_path: str):
        # 如果请求的刚好是根目录，或者页面路由，返回前端入口文件
        # 如果请求了某个具体的静态文件(如 favicon.ico)，返回该文件
        file_path = os.path.join("dist", full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse("dist/index.html")
else:
    print("⚠️ 警告: 未找到前端 dist 文件夹。系统将仅提供 API 服务。")

if __name__ == "__main__":
    import uvicorn
    # 启动应用服务
    uvicorn.run(app, host="127.0.0.1", port=8000)