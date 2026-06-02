"""
学生行政工作智能Agent系统 - 主入口
=================================
启动FastAPI Web服务，提供HTTP API和Web管理界面。
"""

from __future__ import annotations

import json
import logging
import os
import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# 将项目根目录加入Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import AppConfig
from orchestrator import Orchestrator

logger = logging.getLogger(__name__)

# 初始化 — 优先加载 config.json（可覆盖 .env 中的默认值）
_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
if os.path.exists(_config_path):
    config = AppConfig.from_file(_config_path)
    logger.info(f"已加载配置文件: {_config_path}")
else:
    config = AppConfig()
    logger.info("未找到 config.json，使用环境变量默认配置")

orchestrator = Orchestrator(config)

app = FastAPI(
    title="学生行政工作智能Agent系统",
    description="基于ReAct范式的高校学生组织行政邮件自动化处理系统",
    version="1.0.0",
)


# ── API 路由 ─────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """健康检查"""
    warnings = config.validate()
    return {
        "status": "ok",
        "version": "1.0.0",
        "warnings": warnings,
    }


@app.post("/api/tasks/execute")
async def execute_task(request: Request):
    """
    执行一个任务（异步）。
    立即返回 task_id，前端通过轮询 /api/tasks/{task_id} 获取结果。

    Request body:
        {"request": "处理今天的活动申请邮件", "account": "gmail"}
    """
    body = await request.json()
    user_request = body.get("request", "")
    if not user_request:
        raise HTTPException(status_code=400, detail="缺少 request 字段")

    account = body.get("account", "") or ""
    task_id = orchestrator.execute_async(user_request, account=account)
    return {"task_id": task_id, "status": "running"}


@app.get("/api/tasks/history")
async def list_task_history(limit: int = 20):
    """获取历史任务记录列表（放在通配路由前以避免被捕获）"""
    summaries = orchestrator.state.list_task_summaries(limit=limit)
    return {"tasks": summaries, "total": len(summaries)}


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """查询任务状态和完整结果"""
    result = orchestrator.get_status(task_id)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="任务不存在")
    return result


@app.post("/api/tasks/{task_id}/resume")
async def resume_task(task_id: str):
    """恢复一个中断的任务"""
    result = orchestrator.resume(task_id)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="任务不存在")
    return result


@app.get("/api/tools")
async def list_tools():
    """列出所有可用工具"""
    tools = orchestrator.engine.tools.list_tools()
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters_schema,
            }
            for t in tools
        ]
    }


@app.get("/api/accounts")
async def list_accounts():
    """列出所有已配置的邮箱账号"""
    accounts = orchestrator.list_email_accounts()
    return {"accounts": accounts, "total": len(accounts)}


# ── Excel 数据查询 ─────────────────────────────────────

def _get_excel_header_row(filename: str) -> int:
    """根据文件名判断正确的 header_row（0-indexed）"""
    if "荣誉活动立项汇总表" in filename:
        return 1  # 第1行标题，第2行表头
    if "志愿者荣誉时数" in filename:
        return 2  # 第1行标题，第2行说明，第3行表头
    return 0


@app.get("/api/excel/files")
async def list_excel_files():
    """列出所有可用的 Excel 文件"""
    result = json.loads(orchestrator.tools["excel"].list_files())
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    return {"files": result.get("files", []), "total": result.get("total", 0)}


@app.get("/api/excel/read")
async def read_excel_data(file: str):
    """读取指定 Excel 文件的全部记录"""
    import pandas as pd
    from pathlib import Path

    data_dir = Path(orchestrator.config.data_dir)
    header_row = _get_excel_header_row(file)
    full_path = data_dir / file

    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"文件不存在: {file}")

    try:
        df = pd.read_excel(full_path, dtype=str, header=header_row)
        records = df.fillna("").to_dict(orient="records")
        return {
            "file": file,
            "columns": list(df.columns),
            "records": records,
            "total": len(records),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取失败: {e}")


# ── 静态文件 ─────────────────────────────────────────

_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        """Web管理界面"""
        index_path = os.path.join(_static_dir, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                return HTMLResponse(f.read())
        return HTMLResponse("<h1>static/index.html 未找到</h1>")
else:
    @app.get("/", response_class=HTMLResponse)
    async def index():
        return HTMLResponse("<h1>static 目录未找到</h1>")

# ── 入口 ─────────────────
if __name__ == "__main__":
    print("""
    \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
    \u2551   \u8363\u8a89\u65f6\u6570\u7ba1\u7406\u7cfb\u7edf                              \u2551
    \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d
    """)

    warnings = config.validate()
    if warnings:
        print("\u26a0 \u914d\u7f6e\u8b66\u544a:")
        for w in warnings:
            print(f"   \u2022 {w}")
        print()

    host = os.getenv("AGENT_HOST", "127.0.0.1")
    port = int(os.getenv("AGENT_PORT", "8000"))

    print(f"  Web\u7ba1\u7406\u754c\u9762: http://{host}:{port}")
    print(f"  API\u670d\u52a1: http://{host}:{port}/api")
    print()
    uvicorn.run(app, host=host, port=port, log_level="info")
