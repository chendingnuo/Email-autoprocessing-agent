# 学生行政工作智能 Agent 系统

基于 **ReAct（思考-行动-观察）范式** 的高校学生组织行政邮件自动化处理系统。  
自动读取学生发来的行政申请邮件，解析附件中的 Word 文档，提取关键信息录入 Excel 登记表，并生成回复草稿供人工审核发送。

---

## 功能

| 功能 | 说明 |
|------|------|
| **邮件自动读取** | 连接 Gmail IMAP，读取未读邮件及其 Word 附件（立项申请书等） |
| **Word 文档解析** | 解析 `.docx` 附件中的段落、表格和表单字段，提取结构化数据 |
| **Excel 登记管理** | 将提取的信息写入荣誉活动立项汇总表，支持去重检查 |
| **回复草稿生成** | 根据处理结果生成确认回复邮件，保存至 Gmail 草稿箱供人工审核 |
| **Web 管理界面** | 提供浏览器操作界面，支持任务提交、结果查看、历史记录查询 |
| **ReAct 智能决策** | 基于 LLM 的自主推理循环，自动判断处理流程和工具调用 |
| **Excel 数据浏览** | 网页端直接查看 Excel 表格数据，支持多文件切换和自适应表头 |
| **Markdown 结果渲染** | Agent 执行结果和步骤详情以 Markdown 格式渲染，步骤卡片展示 LLM 思考、工具调用与执行结果 |

---

## 系统架构

```
┌──────────────────────────────────────────────┐
│              Web 管理界面 (FastAPI)            │
│              main.py / index.html              │
└──────────────────────┬───────────────────────┘
                       │ HTTP API
┌──────────────────────▼───────────────────────┐
│             任务编排器 (Orchestrator)          │
│              orchestrator.py                   │
│    ┌──────────┼──────────────┐                │
│    ▼          ▼              ▼                │
│  邮件工具   表格工具     文档工具               │
│ email_tools excel_tools  doc_tools            │
└──────────────────────┬───────────────────────┘
                       │ ReAct Loop
┌──────────────────────▼───────────────────────┐
│           ReAct 循环引擎 (ReActEngine)         │
│    ┌──────────┬──────────┬──────────┐        │
│    │ LLM Client │ Parser  │ Security │        │
│    │ (DeepSeek) │ (XML)   │ (检测)   │        │
│    └──────────┴──────────┴──────────┘        │
│    ┌──────────┬──────────┬──────────┐        │
│    │ ToolRegistry │ StateManager │ Logger │  │
│    └──────────┴──────────┴──────────┘        │
└──────────────────────────────────────────────┘
```

**工作流程:**

1. **读取邮件** — Agent 自动连接 Gmail IMAP，读取未读邮件
2. **解析附件** — 如果邮件包含 `.docx` 附件（如立项申请书），解析其中的表格和字段
3. **提取数据** — 从邮件正文和附件中提取活动名称、主办单位、负责人等关键信息
4. **去重检查** — 在 Excel 登记表中检查是否有重复记录
5. **写入表格** — 将提取的信息追加到荣誉活动立项汇总表
6. **生成回复** — 根据处理结果生成确认/驳回回复，保存至 Gmail 草稿箱

---

## 快速开始

### 前置要求

- Python 3.10+
- Gmail 邮箱（需开启 IMAP 并生成应用专用密码）
- DeepSeek API 密钥（或兼容 OpenAI 接口的其他 LLM）

### 安装

```bash
# 1. 克隆项目
git clone <仓库地址>
cd 邮件处理agent

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API 密钥和邮箱凭据

# 4. 忽略 Excel 本地变更（避免运行时数据被 Git 追踪）
git update-index --skip-worktree data/荣誉活动立项汇总表.xlsx
git update-index --skip-worktree data/志愿者荣誉时数-志愿者编号导入模板.xlsx
```

### 配置

编辑 `.env` 文件：

```ini
# LLM 配置
DASHSCOPE_API_KEY=sk-你的API密钥       # DeepSeek API Key
LLM_PROVIDER=deepseek                   # LLM 服务商 (deepseek / tongyi)
LLM_MODEL=deepseek-v4-flash             # 模型名称

# 邮件服务器配置（Gmail）
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ACCOUNT=your-email@gmail.com      # Gmail 邮箱
EMAIL_PASSWORD=你的Gmail应用专用密码     # 应用专用密码

# Agent 配置
AGENT_LOG_LEVEL=INFO
AGENT_STORAGE_DIR=./data/tasks
AGENT_DATA_DIR=./data
AGENT_HOST=127.0.0.1
AGENT_PORT=8000
```

> **Gmail 应用专用密码获取**: https://myaccount.google.com/apppasswords  
> 需开启 Gmail 的 IMAP 访问: Gmail 设置 → 查看所有设置 → 转发和 POP/IMAP → 启用 IMAP

### 运行

```bash
python main.py
```

打开浏览器访问 `http://127.0.0.1:8000` 即可进入管理界面。

**Web 界面包含以下页面：**

| 页面 | 说明 |
|------|------|
| **仪表盘** | 系统概览与状态监控 |
| **任务执行** | 提交自然语言任务让 Agent 自动处理，实时轮询结果 |
| **执行日志** | 查看所有任务的执行历史，支持筛选和搜索 |
| **数据记录** | 以表格形式浏览 Excel 文件内容 |
| **工具管理** | 查看 Agent 可用的所有工具列表 |

> 任务执行结果中的 LLM 思考过程、工具调用参数和最终回答会以 **Markdown 格式**渲染为步骤卡片，便于阅读。

### 启动演示（无需 API）

```bash
python demo_workflow.py
```

演示脚本不调用真实 LLM，展示框架的模块结构和 ReAct 循环流程。

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/tasks/execute` | 提交任务（异步执行） |
| GET | `/api/tasks/{task_id}` | 查询任务状态和结果（含 step_details 步骤详情） |
| GET | `/api/tasks/history` | 查看任务历史记录 |
| GET | `/api/excel/files` | 列出所有可用的 Excel 文件 |
| GET | `/api/excel/read?file=xxx` | 读取指定 Excel 文件的全部记录 |
| GET | `/api/accounts` | 列出所有已配置的邮箱账号 |
| GET | `/api/tools` | 列出 Agent 可用的所有工具 |
| GET | `/` | Web 管理界面 |

### 提交任务

```bash
curl -X POST http://127.0.0.1:8000/api/tasks/execute \
  -H "Content-Type: application/json" \
  -d '{"request": "处理最近收到的立项申请邮件"}'
```

### 查询结果

```bash
curl http://127.0.0.1:8000/api/tasks/task_xxxx
```

---

## 项目结构

```
├── main.py                     # FastAPI Web 服务 + 管理界面
├── orchestrator.py              # 任务编排器（工具注册 + 执行入口）
├── config.py                    # 配置管理（环境变量 / 配置文件）
├── demo_workflow.py             # 离线演示脚本
├── requirements.txt             # Python 依赖
├── .env                         # 环境变量配置（不含仓库）
├── .env.example                 # 环境变量模板
├── .gitignore                   # Git 忽略规则
│
├── static/                      # Web 静态资源
│   ├── index.html               # SPA 入口页面
│   ├── css/
│   │   └── style.css            # 全局样式
│   └── js/
│       ├── app.js               # 核心路由、API 工具、UI 工具
│       ├── dashboard.js         # 仪表盘页面
│       ├── task-execute.js      # 任务执行页面（含 Markdown 步骤卡片）
│       ├── history.js           # 执行日志页面
│       ├── excel-records.js     # Excel 数据记录页面
│       └── tools.js             # 工具管理页面
│
├── framework/                   # ReAct 框架核心
│   ├── engine.py                # ReAct 循环引擎（思考→行动→观察）
│   ├── llm_client.py            # LLM 客户端（DeepSeek / 通义千问）
│   ├── parser.py                # ReAct 输出解析器（XML 解析）
│   ├── security.py              # 安全模块（注入检测 / 数据脱敏）
│   ├── state_manager.py         # 状态管理（滑动窗口 + 持久化）
│   ├── tool_registry.py         # 工具注册中心
│   ├── models.py                # 数据模型定义
│   └── logger.py                # 日志配置
│
├── tools/                       # 业务工具
│   ├── email_tools.py           # 邮件读取、草稿保存
│   ├── excel_tools.py           # Excel 登记表读写、去重查询
│   └── doc_tools.py             # Word 文档解析、模板渲染
│
├── tests/                       # 单元测试
│   ├── test_parser.py
│   ├── test_security.py
│   └── test_tool_registry.py
│
├── data/                        # 运行时数据（不含仓库）
│   ├── 荣誉活动立项汇总表.xlsx   # 立项登记表
│   ├── 志愿者荣誉时数-志愿者编号导入模板.xls
│   ├── tasks/                   # 任务执行历史（.gitignore）
│   └── attachments/             # 邮件附件缓存（.gitignore）
│
└── 志愿者时长导入回复模板.txt    # 回复模板
 立项邮件回复模板.txt            # 回复模板
```

---

## 技术栈

- **Web 框架**: FastAPI + Uvicorn
- **LLM**: DeepSeek API / 通义千问 API（OpenAI 兼容接口）
- **数据处理**: pandas + openpyxl
- **文档处理**: python-docx
- **邮件协议**: IMAP (读取) + SMTP (草稿)

---

## 开发

```bash
# 运行测试
python -m pytest tests/

# 单独测试
python tests/test_parser.py
python tests/test_security.py
python tests/test_tool_registry.py
```

---

## 注意事项

1. **邮件不会自动发送** — 系统仅将回复保存到 Gmail 草稿箱，需人工登录审核后发送
2. **数据表格请勿手动修改格式** — 表头行和标题行位置与代码中的 `header_row` 参数绑定
3. **.env 文件包含敏感信息**，已加入 `.gitignore`，切勿提交到 Git
4. `data/tasks/` 目录下的任务记录包含邮件内容，已在 `.gitignore` 中排除

---

## 许可

本项目仅供学习参考。
