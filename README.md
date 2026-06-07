# 学生行政工作智能 Agent 系统

这是我们的人工智能基础课大作业项目，我们实现的是基于 **ReAct（思考-行动-观察）范式** 的高校学生组织行政邮件自动化处理智能体。  
其主要功能包括哟自动读取学生发来的行政申请邮件，解析 Word 附件，提取关键信息录入 Excel 登记表，并生成回复草稿供人工审核发送。

---

## 功能

| 功能 | 说明 |
|------|------|
| **多邮箱支持** | 同时管理 Gmail、QQ等多个账号，Agent 自动选择或手动选择 |
| **邮件自动读取** | 连接 IMAP 读取未读邮件，自动缓存并解析 Word 附件 |
| **Word 文档解析** | 解析 `.docx` 附件中的段落、表格和表单字段，提取结构化数据 |
| **Excel 登记管理** | 将提取的信息写入荣誉活动立项汇总表，支持去重检查与条件查询 |
| **Word 模板渲染** | 根据变量动态生成 Word 公文回复（暂未启用） |
| **回复草稿生成** | 根据处理结果生成确认回复，保存至邮箱草稿箱，人工审核后发送 |
| **ReAct 智能决策** | 基于 LLM 的自主推理循环，自动判断处理流程和工具调用 |
| **多邮件批量处理** | 一次读取多封邮件并逐封自动处理，引擎层确保所有邮件处理完毕后才结束，避免遗漏 |
| **Web 管理界面** | 提供浏览器操作界面，支持任务提交、结果查看、历史记录查询 |
| **Excel 数据浏览** | 网页端直接查看 Excel 表格数据，支持多文件切换和自适应表头 |
| **Markdown 结果渲染** | Agent 执行结果和步骤详情以 Markdown 渲染，步骤卡片展示 LLM 思考、工具调用与执行结果 |
| **安全防护** | 提示注入检测、路径遍历防护、敏感数据脱敏、系统提示加固 |

---

## 系统架构

```
┌──────────────────────────────────────────────────┐
│              Web 管理界面 (FastAPI)                │
│              main.py / static/                     │
└──────────────────────┬───────────────────────────┘
                       │ HTTP API
┌──────────────────────▼───────────────────────────┐
│             任务编排器 (Orchestrator)              │
│              orchestrator.py                       │
│    注册工具 → 指派引擎 → 异步执行 → 状态持久化      │
└──────────────────────┬───────────────────────────┘
                       │ ReAct Loop
┌──────────────────────▼───────────────────────────┐
│              ReAct 循环引擎 (framework/)            │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐     │
│  │LLM Client│  │  Parser  │  │  Security    │     │
│  │(DeepSeek/│  │(XML 解析)│  │(注入检测/    │     │
│  │ 通义千问) │  │(JSON修复)│  │ 数据脱敏)    │     │
│  └──────────┘  └──────────┘  └──────────────┘     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐     │
│  │ToolRegistry│ │StateMgr │  │   Logger     │     │
│  │(工具注册/  │ │(滑动窗口 │  │(控制台+文件)  │     │
│  │ 执行/模式) │ │ +持久化) │  │              │     │
│  └──────────┘  └──────────┘  └──────────────┘     │
└──────────────────────┬───────────────────────────┘
                       │ 工具调用
┌──────────────────────▼───────────────────────────┐
│                 业务工具层 (tools/)                 │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ email_tools  │  │ excel_tools  │  │doc_tools │ │
│  │· 邮件读取    │  │· 读/写/查询  │  │· Word解析│ │
│  │· 草稿保存    │  │· 去重检查    │  │· 模板渲染│ │
│  │· 附件缓存    │  │· 模式检测    │  │          │ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
└──────────────────────────────────────────────────┘
```

**工作流程：**

1. **读取邮件** — Agent 连接指定邮箱的 IMAP，读取收件箱中的未读邮件及其附件
2. **解析附件** — 解析 `.docx` 附件中的段落和表格，提取结构化信息
3. **提取数据** — 从邮件正文和附件中提取活动名称、主办单位、负责人等关键信息
4. **去重检查** — 在 Excel 登记表中检查是否已有重复记录
5. **写入表格** — 将提取的信息追加到荣誉活动立项汇总表
6. **生成回复** — 根据处理结果生成确认/驳回回复，保存至邮箱草稿箱

> 系统**不会自动发送邮件** — 回复始终保存在草稿箱，需人工登录审核后发送。

---

## 快速开始

### 前置要求

- Python 3.10+
- 一个或多个支持 IMAP 的邮箱（Gmail / QQ  等）
- LLM API 密钥（DeepSeek 或 通义千问）

### 安装
在目标文件夹打开终端或者powershell,复制仓库的地址

```bash
# 1. 克隆项目
git clone <仓库地址>
cd Email-autoprocessing-agent

# 2. 安装依赖
pip install -r requirements.txt

```

### 邮箱配置

支持多邮箱配置，编辑 `data/email_accounts.json`：

```json
{
  "accounts": [
    {
      "name": "gmail",
      "provider": "gmail",
      "email": "your-email@gmail.com",
      "password": "你的Gmail应用专用密码"
    },
    {
      "name": "qq",
      "provider": "qq",
      "email": "your-number@qq.com",
      "password": "你的QQ邮箱授权码"
    }
  ]
}
```

**支持的服务商预设：**

| 服务商 | 提供者名 | IMAP | SMTP |
|--------|---------|------|------|
| Gmail | `gmail` | imap.gmail.com:993 | smtp.gmail.com:587 |
| QQ邮箱 | `qq` | imap.qq.com:993 | smtp.qq.com:465 |
| 自定义 | `custom` | 手动填写 IMAP|手动填写SMTP |

#### QQ邮箱配置具体操作说明
- 登录QQ邮箱
- 点击右上角的设置
- 在左侧菜单栏中选择**账号与安全**
- 在账号与安全页面左侧菜单栏选择**安全设置**
- 安全设置界面滑倒底，找到**POP3/IMAP/SMTP/Exchange/CardDAV 服务**
- 开启该服务并生成**授权码**
- 用授权码替换到**data/email_accounts.example.json**文件中的password
- 在文件中填入自己的QQ邮箱号

#### Gmail邮箱配置具体操作说明
- 登录Gmail邮箱
- 点击右上角自己的头像
- 选择manage your google account
- 先开启**登录双重认证**（按照类似以下步骤进行搜索并完成设置）
- 在中间的搜索框搜索**应用专属密码**（中文界面）或**app password**（英文界面）
- 点击同名的搜索结果，按照提示完成设置生成授权码
- 用授权码替换到**data/email_accounts.example.json**文件中的password
- 在文件中填入自己的Gmail邮箱号

### LLM 配置

系统同时支持通过 `config.json`（优先级高）和 `.env` 文件配置。编辑 `.example.env` 文件：

```ini
# LLM 配置（二选一）
## 通义千问（默认）
DASHSCOPE_API_KEY=sk-你的阿里云API密钥
LLM_PROVIDER=tongyi
LLM_MODEL=qwen-plus
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

## DeepSeek
# DASHSCOPE_API_KEY=sk-你的DeepSeek密钥
# LLM_PROVIDER=deepseek
# LLM_MODEL=deepseek-v4-flash
# LLM_BASE_URL=https://api.deepseek.com/v1
```
在测试这个项目时我是用的是deepseek的API，需要的操作就是用自己的deepseekAPI密钥替换示例中内容并将文件另存为.env

也可编辑 `config.json`（会覆盖 `.env` 中的同名配置）：

```json
{
  "llm": {
    "provider": "deepseek",
    "model": "deepseek-v4-flash",
    "base_url": "https://api.deepseek.com/v1",
    "temperature": 0.1,
    "max_tokens": 4096
  },
  "engine": {
    "max_steps": 50,
    "deadlock_threshold": 3,
    "log_level": "INFO"
  }
}
```

### 运行

在本文件夹的终端或powershell运行

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

## ReAct 框架核心

`framework/` 目录实现了完整的 ReAct 引擎：

| 模块 | 说明 |
|------|------|
| **engine.py** | ReAct 循环引擎 — 迭代驱动 LLM 推理与工具执行，含死锁检测（相同调用 3 次阻断）、调用频率限制、滑动窗口上下文压缩、**多邮件强制逐封处理校验**（LLM 试图提前结束时自动拦截并提醒继续处理剩余邮件） |
| **llm_client.py** | LLM 客户端 — 封装 OpenAI 兼容 HTTP 接口，支持重试和超时 |
| **parser.py** | XML 输出解析器 — 解析 `<thought>` / `<tool_call>` / `<final_answer>` 标签，含多层 JSON 修复（转义符修复、单引号转双引号、未闭合标签容错） |
| **security.py** | 安全模块 — 15 条提示注入检测规则、工具参数校验、路径遍历防护、电话/学号/邮箱脱敏、系统提示加固 |
| **state_manager.py** | 状态管理 — 对话滑动窗口摘要（保留最近 5 轮 + 历史摘要）、任务持久化到 JSON 文件、区分"已读取"与"已处理"邮件状态追踪 |
| **tool_registry.py** | 工具注册中心 — 注册/执行/动态生成工具 Schema |
| **models.py** | 数据模型 — TaskContext、ReActStep、ToolCall 等核心类型定义 |
| **logger.py** | 日志配置 — 控制台彩色输出 + 文件日志 |

---

## 业务工具

Agent 通过 ToolRegistry 暴露 10 个工具供 LLM 调用：

| 工具名 | 说明 |
|--------|------|
| `email_read` | 读取指定邮箱的未读邮件，自动保存 .docx 附件 |
| `email_reply_draft` | 将回复保存到草稿箱（不会自动发送） |
| `excel_list_files` | 列出 data/ 目录下所有可用的 Excel 文件 |
| `excel_get_schema` | 获取 Excel 表结构（列名、行数、标题行偏移） |
| `excel_check_duplicate` | 检查指定字段是否已存在（去重） |
| `excel_insert_record` | 向表格追加记录，支持写入前去重 |
| `excel_query_records` | 按条件查询记录（字段名 + 值） |
| `doc_parse_attachment` | 解析 .docx 文件中的段落和表格 |
| `doc_render_template` | 基于 Word 模板 + 变量字典生成公文 |
| `data_store` | 将提取的业务数据持久化到任务上下文 |

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 健康检查，返回系统版本和配置状态 |
| `POST` | `/api/tasks/execute` | 提交任务（异步执行） |
| `GET` | `/api/tasks/{task_id}` | 查询任务状态/结果（含 step_details 步骤详情） |
| `POST` | `/api/tasks/{task_id}/resume` | 恢复被阻断的任务 |
| `GET` | `/api/tasks/history` | 任务历史记录（支持 `?limit=N`） |
| `GET` | `/api/excel/files` | 列出所有可用的 Excel 文件 |
| `GET` | `/api/excel/read?file=xxx` | 读取指定 Excel 文件的全部记录 |
| `GET` | `/api/accounts` | 列出所有已配置的邮箱账号 |
| `GET` | `/api/tools` | 列出 Agent 可用的所有工具 |

### 提交任务

```bash
curl -X POST http://127.0.0.1:8000/api/tasks/execute \
  -H "Content-Type: application/json" \
  -d '{"request": "处理最近收到的立项申请邮件", "account": "gmail"}'
```

### 查询结果

```bash
curl http://127.0.0.1:8000/api/tasks/task_xxxxxxxxxxxx
```

返回结果中包含 `step_details`，展示 Agent 每一步的思考、工具调用和观察结果。

---

## 项目结构

```
├── main.py                       # FastAPI Web 服务 + 管理界面
├── orchestrator.py                # 任务编排器（工具注册 + 异步执行）
├── config.py                      # 配置管理（环境变量 / 邮箱预设 / JSON 配置）
├── config.json                    # LLM 和引擎配置（覆盖 .env）
├── demo_workflow.py               # 离线演示脚本（无需 API）
├── requirements.txt               # Python 依赖
├── .example.env                   # 环境变量（不含仓库）
├── .gitignore                     # Git 忽略规则
│
├── framework/                     # ReAct 框架核心
│   ├── engine.py                  # ReAct 循环引擎（思考→行动→观察）
│   ├── llm_client.py              # LLM 客户端（DeepSeek / 通义千问）
│   ├── parser.py                  # XML 输出解析器 + JSON 修复
│   ├── security.py                # 安全模块（注入检测 / 数据脱敏）
│   ├── state_manager.py           # 状态管理（滑动窗口 + 持久化）
│   ├── tool_registry.py           # 工具注册中心
│   ├── models.py                  # 数据模型定义
│   └── logger.py                  # 日志配置
│
├── tools/                         # 业务工具层
│   ├── email_tools.py             # 邮件读取、草稿保存、附件缓存
│   ├── excel_tools.py             # Excel 读写、去重查询、模式检测
│   └── doc_tools.py               # Word 文档解析、模板渲染
│
├── static/                        # Web 前端静态资源
│   ├── index.html                 # SPA 入口（Tailwind CSS CDN）
│   ├── css/
│   │   └── style.css              # 自定义样式
│   └── js/
│       ├── app.js                 # 核心路由、API 客户端、UI 工具
│       ├── dashboard.js           # 仪表盘页面
│       ├── task-execute.js        # 任务执行（含 Markdown 步骤卡片）
│       ├── history.js             # 执行日志页面
│       ├── excel-records.js       # Excel 数据浏览页面
│       └── tools.js               # 工具管理页面
│
├── tests/                         # 单元测试
│   ├── test_parser.py             # 解析器测试（6 个用例）
│   ├── test_security.py           # 安全模块测试（7 个用例）
│   └── test_tool_registry.py      # 工具注册中心测试（9 个用例）
│
├── data/                          # 运行时数据（不含仓库）
│   ├── email_accounts.example.json# 邮箱配置模板（可安全提交）
│   ├── 荣誉活动立项汇总表.xlsx     # 立项登记 Excel
│   ├── 志愿者荣誉时数-志愿者编号导入模板.xlsx  # 志愿者时长登记模板
│   ├── tasks/                     # 任务执行历史（JSON，已 gitignore）
│   └── attachments/               # 邮件附件缓存（已 gitignore）
│
├── 志愿者时长导入回复模板.txt       # 志愿者时长回复模板
└── 立项邮件回复模板.txt            # 立项申请回复模板
```

---

## 技术栈

- **Web 框架**: FastAPI + Uvicorn
- **LLM**: DeepSeek API / 通义千问 API（OpenAI 兼容接口）
- **前端**: 原生 JavaScript、Tailwind CSS（CDN）、marked.js（Markdown 渲染）
- **数据处理**: pandas + openpyxl
- **文档处理**: python-docx
- **邮件协议**: imaplib（读取）+ smtplib（草稿）
- **测试**: pytest（22 个用例）

---

## 开发

```bash
# 运行全部测试
python -m pytest tests/ -v

# 单独测试
python tests/test_parser.py
python tests/test_security.py
python tests/test_tool_registry.py
```

---

## 注意事项

1. **邮件不会自动发送** — 系统仅将回复保存到草稿箱，需人工登录审核后发送
2. **数据表格请勿手动修改格式** — 表头行位置与代码中的 `header_row` 参数绑定
3. **敏感信息保护** — `.env` 和 `data/email_accounts.json` 包含密钥，已加入 `.gitignore`
4. **`data/tasks/` 中的任务记录含邮件内容**，已在 `.gitignore` 中排除
5. **`data/attachments/` 为附件缓存目录**，已在 `.gitignore` 中排除

---

## 许可

本项目仅供学习参考。
