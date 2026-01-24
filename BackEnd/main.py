# main.py
import shutil
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import StreamingResponse
from io import BytesIO
import pandas as pd

import database
import ai_engine

app = FastAPI(title="财务数字人后端")

# 允许 Vue 前端跨域访问 (localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库
database.init_db()


# --- 数据模型 ---
class RecordItem(BaseModel):
    item: str
    date: str
    amount: float


class AnalysisRequest(BaseModel):
    model_name: str
    user_query: Optional[str] = "请分析这段时间的财务状况" # 默认指令
    start_date: Optional[str] = None
    end_date: Optional[str] = None

# --- 接口定义 ---
# === 接口: 获取 Ollama 中可用的模型列表 ===
@app.get("/api/models")
def get_models():
    models = ai_engine.get_available_models()
    return {"models": models}

# === 接口: 获取财务记录用于前端绘图 ===
@app.get("/api/records")
def get_records():
    return database.get_all_records()

# === 接口: 添加记录 ===
@app.post("/api/records")
def add_record(record: RecordItem):
    database.insert_record(record.item, record.date, record.amount)
    return {"status": "success"}

# === 接口: 上传知识库 ===
@app.post("/api/upload_knowledge")
async def upload_knowledge(file: UploadFile = File(...)):
    file_location = f"temp_{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    success = ai_engine.init_knowledge_base(file_location)
    os.remove(file_location)  # 清理临时文件

    if success:
        return {"message": "知识库加载成功"}
    else:
        raise HTTPException(status_code=400, detail="文件解析失败")

# === 接口: AI分析 ===
@app.post("/api/chat")
def chat_with_finance(req: AnalysisRequest):
    """
    Agent 核心接口
    """
    # 1. 确定时间范围 (如果前端没传，默认取最近30天，或者全量)
    # 这里我们逻辑是：如果没传，就分析所有。如果传了，就分析特定时间。
    if req.start_date and req.end_date:
        financial_summary = database.get_filtered_financial_summary(req.start_date, req.end_date)
    else:
        # 兼容旧逻辑，或者全量分析
        financial_summary = database.get_financial_summary_text()  # 这是你之前全量的函数，如果 database.py 里删了，就改用 get_filtered... 传很早的时间

    print(f"📊 数据摘要准备完毕，长度: {len(financial_summary)} 字符")

    # 2. 调用 AI Agent
    # 注意：我们将 user_query 透传给 AI，让它决定怎么回答
    response_text = ai_engine.run_analysis(
        model_name=req.model_name,
        data_summary=financial_summary,
        user_query=req.user_query
    )

    return {"reply": response_text}

# === 接口: 查询知识库状态 ===
@app.get("/api/knowledge/status")
def get_knowledge_status():
    exists = ai_engine.check_kb_exists()
    return {"exists": exists}

# === 接口: 删除记录 ===
@app.delete("/api/records/{record_id}")
def delete_record_endpoint(record_id: int):
    success = database.delete_record(record_id)
    if success:
        return {"status": "success", "message": f"记录 {record_id} 已删除"}
    else:
        raise HTTPException(status_code=404, detail="记录不存在或删除失败")

# === 接口: 下载 Excel 模板 ===
@app.get("/api/template")
def download_template():
    # 创建一个空的 DataFrame，只有列头
    df = pd.DataFrame(columns=["日期", "项目", "金额"])
    # 添加一行示例数据
    df.loc[0] = ["2024-01-01", "示例收入(正数)或支出(负数)", 1000]

    # 写入内存 Buffer
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)

    headers = {
        'Content-Disposition': 'attachment; filename="example.xlsx"'
    }
    return StreamingResponse(output, headers=headers,
                             media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# === 接口: 批量上传 Excel ===
@app.post("/api/records/batch_upload")
async def batch_upload(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 Excel 文件 (.xlsx, .xls)")

    try:
        contents = await file.read()
        # 使用 Pandas 读取二进制流
        df = pd.read_excel(BytesIO(contents))

        # 简单的列名校验
        required_columns = {'日期', '项目', '金额'}
        if not required_columns.issubset(df.columns):
            raise HTTPException(status_code=400, detail=f"Excel 缺少必须列: {required_columns}")

        count = database.insert_batch_from_excel(df)
        return {"status": "success", "count": count}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析文件失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)