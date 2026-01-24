#  智财云 AI 财务分析系统 (ZhiCaiYun AI Financial System)

这是一个基于 **本地大模型 (Ollama)**、**RAG (检索增强生成)** 和 **魔珐星云 (Magic Nebula) 数字人** 技术构建的智能财务分析平台。系统不仅提供传统的财务收支管理功能，还能通过 AI 审计师角色，结合企业内部知识库（如审计准则），对特定时间段的财务状况进行语音播报和深度分析。本系统使用的思考分析模型均为本地部署，因此无需担心 **数据泄露** 的问题。 

## ✨ 核心功能

1.  **📊 经营状况仪表盘**
    *   收支趋势图（支持按周、月、自定义时间段筛选）。
    *   智能数字展示（大额数字自动转“万”单位，点击可查看精确值）。
    *   核心指标卡片（总收入、总支出、净利润）。
2.  **📝 数据录入与管理**
    *   支持单条数据的增删改查。
    *   **Excel 批量导入**：支持下载模板，快速导入大量历史数据。
    *   支持按 ID、日期、金额进行排序。
3.  **🧠 知识库管理 (RAG)**
    *   支持上传 PDF/TXT 格式的财务准则或审计文件。
    *   系统自动进行文本切分与向量化索引（使用 `bge-m3` 模型）。
4.  **🤖 AI 数字人审计师 (Agent 模式)**
    *   **交互式咨询**：类似于聊天室的交互体验，支持上下文多轮对话。
    *   **多模态输出**：AI 生成的分析建议由 3D 数字人实时语音播报。
    *   **精准分析**：支持指定时间段（如“近30天”）进行针对性分析。
    *   **模型切换**：支持在前端动态切换本地不同的 LLM 模型（如 Qwen2.5, Yi 等）。

---

## 🛠️ 环境搭建与部署指南

若要在新机器上部署本系统，请按以下步骤操作。

### 第一步：基础环境准备 (Prerequisites)

请确保目标机器已安装以下软件：
1.  **Python 3.10+** (用于后端服务)
2.  **Node.js 18+ & npm** (用于前端 Vue 项目)
3.  **Ollama** (用于运行本地大模型) -> [下载地址](https://ollama.com/)

### 第二步：配置 AI 模型 (Ollama)

本系统依赖 Ollama 提供推理和向量化能力。请打开终端（CMD/Terminal）执行以下命令拉取模型：

```bash
# 1. 拉取大语言模型 (推荐 Qwen2.5)
ollama pull qwen2.5:7b

# 2. 拉取向量嵌入模型 (用于 RAG 知识库)
ollama pull bge-m3
```

> **注意**：
> 1、请确保 Ollama 服务在后台运行（默认端口 11434）。<br>
> 2、该系统支持模型切换，并且支持模型自动读取。如需使用模型切换功能请自行从ollama拉去模型（例如：Yi:6b)

---

### 第三步：后端部署 (Python FastAPI)

1.  **进入后端目录**（存放 `main.py`, `ai_engine.py` 的文件夹）。
2.  **创建虚拟环境（推荐）**：
    ```bash
    python -m venv venv
    # Windows 激活:
    venv\Scripts\activate
    # Mac/Linux 激活:
    source venv/bin/activate
    ```
3.  **安装依赖**：
    请创建一个 `requirements.txt` 文件并填入以下内容，然后运行 `pip install -r requirements.txt`。
    
    *requirements.txt 内容示例:*
    ```text
    fastapi
    uvicorn
    python-multipart
    pandas
    openpyxl
    langchain
    langchain-community
    langchain-ollama
    faiss-cpu
    pypdf
    requests
    ```
4.  **启动后端服务**：
    ```bash
    python main.py
    ```
    *若看到 `Uvicorn running on http://0.0.0.0:8000` 即表示启动成功。*

---

### 第四步：前端部署 (Vue 3 + Vite)

1.  **进入前端目录**（包含 `package.json` 的文件夹）。
2.  **安装依赖**：
    ```bash
    npm install
    ```
3.  **配置数字人密钥**：
    打开 `src/stores/app.ts`，找到以下代码段，填入你在魔珐星云官网申请的 Key：
    ```typescript
    avatar: {
      appId: '在此处粘贴你的 AppID', 
      appSecret: '在此处粘贴你的 AppSecret',
      // ...
    }
    ```
4.  **启动前端**：
    ```bash
    npm run dev
    ```
5.  **访问系统**：
    打开浏览器访问 `http://localhost:5173`。

---

## 📂 目录结构说明

```text
Project/
├── backend/                # 后端代码
│   ├── main.py             # FastAPI 入口与接口定义
│   ├── ai_engine.py        # LangChain RAG 与 Ollama 调用逻辑
│   ├── database.py         # SQLite 数据库操作与 Excel 处理
│   └── finance_system.db   # (自动生成) 数据库文件
│
└── frontend/               # 前端代码
    ├── public/             # 静态资源 (bg.png, logo.png)
    ├── src/
    │   ├── components/
    │   │   ├── AvatarAnalysis.vue  # AI 分析师交互主界面
    │   │   ├── Dashboard.vue       # 收支图表
    │   │   ├── RecordManager.vue   # 数据录入
    │   │   └── ...
    │   ├── stores/         # 状态管理 (包含 AppID 配置)
    │   ├── services/       # API 请求封装
    │   └── App.vue         # 布局入口
    └── index.html          # 网页入口
```

## ⚠️ 常见问题排查

1.  **无法连接数字人？**
    *   检查 `src/stores/app.ts` 中的 AppID 和 Secret 是否正确。
    *   检查网络是否通畅（需要连接魔珐星云公网服务器）。
2.  **AI 分析报错 500？**
    *   检查后端控制台报错信息。
    *   确认 Ollama 是否正在运行 (`ollama list` 查看模型是否存在)。
    *   确认是否拉取了 `bge-m3` 向量模型。
    *   注意检查关闭vpn
3.  **知识库无法上传？**
    *   确认上传的是 `.pdf` 或 `.txt` 文件。
    *   确认后端安装了 `pypdf` 和 `faiss-cpu` 库。

---

## 📄 开源协议 (License)

本项目代码遵循 **[MIT License](https://opensource.org/licenses/MIT)** 开源协议。

您可以免费：
*   ✅ 使用本项目的源代码进行学习、测试或商业用途。
*   ✅ 修改源代码以满足您的需求。
*   ✅ 分发本项目的副本。

**但在使用过程中请注意以下事项：**

### 1. 第三方组件版权说明
本项目集成了 **魔珐星云 (Magic Nebula)** 的数字人 SDK。
*   **SDK 版权**：数字人驱动相关的 SDK 文件（如 `xmovAvatar` 相关 JS 库）版权归 **上海魔珐信息科技有限公司** 所有。
*   **使用限制**：本项目的开源协议**不包含**魔珐星云 SDK 的授权。如需在商业产品中使用数字人功能，请务必前往 [魔珐星云官网](https://www.xingyun3d.com/) 申请合法的 AppID 和 Secret，并遵守其服务条款。
*   **敬告**：本项目的APP ID APP Secret均为本人测试账号的id。API信息将于2026-2-1删去。如需使用数字人驱动功能，请自行前往[魔珐星云官网](https://www.xingyun3d.com/) 申请合法的 AppID 和 Secret，并遵守其服务条款。

### 2. 模型使用说明
本项目默认使用的 AI 模型（Qwen2.5, Yi, BGE-M3 等）均由 Ollama 运行。
*   请遵守各个模型原作者（如 Alibaba Cloud, 01.AI 等）发布的开源协议和使用规范。

### 3. 免责声明
*   **AI 幻觉风险**：本系统中的财务分析建议由 AI 大模型生成，**仅供参考**，不构成任何专业的投资建议或审计结论。
*   **数据安全**：请勿将真实的、包含敏感隐私的财务数据上传至未受保护的测试环境。开发者不对因使用本软件造成的任何数据丢失或财务损失承担责任。

---

**© 2026 智财云 AI 财务分析系统**
