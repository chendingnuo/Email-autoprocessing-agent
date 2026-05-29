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
from orchestrator import create_orchestrator

logger = logging.getLogger(__name__)

# 初始化
config = AppConfig()
orchestrator = create_orchestrator()

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
        {"request": "处理今天的活动申请邮件"}
    """
    body = await request.json()
    user_request = body.get("request", "")
    if not user_request:
        raise HTTPException(status_code=400, detail="缺少 request 字段")

    task_id = orchestrator.execute_async(user_request)
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


# ── 数据查询 API ─────────────────────────────────────

@app.get("/api/data/activities")
async def query_activities():
    """查询荣誉活动立项汇总表中的已登记活动记录"""
    try:
        import pandas as pd
        import os
        path = os.path.join(config.data_dir, "荣誉活动立项汇总表.xlsx")
        df = pd.read_excel(path, sheet_name="Sheet1", dtype=str, header=1)
        df = df.fillna("")
        records = df.to_dict(orient="records")
        return {
            "status": "success",
            "total": len(records),
            "columns": list(df.columns),
            "records": records,
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "records": []}


@app.get("/api/data/volunteers")
async def query_volunteers():
    """查询志愿者荣誉时数导入模板中的已导入记录"""
    try:
        import pandas as pd
        import os
        path = os.path.join(config.data_dir, "志愿者荣誉时数-志愿者编号导入模板.xlsx")
        df = pd.read_excel(path, sheet_name="Sheet1", dtype=str, header=2)
        df = df.fillna("")
        records = df.to_dict(orient="records")
        return {
            "status": "success",
            "total": len(records),
            "columns": list(df.columns),
            "records": records,
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "records": []}


# ── 主页 ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Web管理界面"""
    return HTMLResponse(INDEX_HTML)


# ── 静态Web界面 ─────────────────────────────────────

INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>荣誉时数管理系统</title>
    <script src="https://cdn.tailwindcss.com" async></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="max-w-6xl mx-auto p-6">
        <!-- 头部 -->
        <header class="mb-8">
            <h1 class="text-3xl font-bold text-gray-900">荣誉时数管理系统</h1>
            <p class="text-gray-500 mt-1">学生组织荣誉时数立项申请与志愿时数导入自动化处理</p>
        </header>

        <!-- 状态卡片 -->
        <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
            <div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
                <div class="text-sm text-gray-500">系统状态</div>
                <div class="text-lg font-semibold mt-1" id="healthStatus">检查中...</div>
            </div>
            <div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
                <div class="text-sm text-gray-500">可用工具</div>
                <div class="text-lg font-semibold mt-1" id="toolCount">-</div>
            </div>
            <div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
                <div class="text-sm text-gray-500">模型</div>
                <div class="text-lg font-semibold mt-1" id="modelName">-</div>
            </div>
            <div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
                <div class="text-sm text-gray-500">邮箱账号</div>
                <div class="text-lg font-semibold mt-1" id="accountCount">-</div>
            </div>
            <div class="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
                <div class="text-sm text-gray-500">历史任务</div>
                <div class="text-lg font-semibold mt-1" id="historyCount">-</div>
            </div>
        </div>

        <script>
        (function(){
            fetch('/api/health').then(function(r){ return r.json(); }).then(function(health){
                var el=document.getElementById("healthStatus");
                if(health.status==="ok"){ el.textContent="\u6b63\u5e38\u8fd0\u884c"; el.className="text-lg font-semibold mt-1 text-green-600"; }
                else{ el.textContent="\u5f02\u5e38"; el.className="text-lg font-semibold mt-1 text-red-600"; }
                if(health.warnings&&health.warnings.length) el.textContent+=" ("+health.warnings.length+" \u9879\u8b66\u544a)";
            }).catch(function(){ document.getElementById("healthStatus").textContent="\u65e0\u6cd5\u8fde\u63a5"; });
            fetch("/api/tools").then(function(r){ return r.json(); }).then(function(t){ document.getElementById("toolCount").textContent=t.tools.length+" \u4e2a"; }).catch(function(){});
            fetch("/api/accounts").then(function(r){ return r.json(); }).then(function(a){
                var el=document.getElementById("accountCount");
                el.textContent=a.total+" \u4e2a";
                if(a.total>0){ el.className="text-lg font-semibold mt-1 text-green-600"; }
            }).catch(function(){ document.getElementById("accountCount").textContent="-"; });
            fetch("/api/tasks/history?limit=1").then(function(r){ return r.json(); }).then(function(h){ document.getElementById("historyCount").textContent=h.total+" \u6761"; }).catch(function(){});
        })();
        </script>

        <!-- Tab 切换 -->
        <div class="flex gap-1 mb-6 border-b border-gray-200">
            <button id="tabExecute" onclick="switchTab(\'execute\')" class="px-5 py-3 text-sm font-medium border-b-2 border-blue-600 text-blue-600 transition-colors">\u4efb\u52a1\u6267\u884c</button>
            <button id="tabHistory" onclick="switchTab(\'history\')" class="px-5 py-3 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700 transition-colors">\u5386\u53f2\u8bb0\u5f55</button>\n            <button id="tabData" onclick="switchTab(\'data\')" class="px-5 py-3 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700 transition-colors">\u6570\u636e\u67e5\u8be2</button>
        </div>

        <!-- 任务执行页 -->
        <div id="pageExecute">
            <!-- 任务输入 -->
            <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100 mb-8">
                <h2 class="text-lg font-semibold text-gray-900 mb-3">\u6267\u884c\u4efb\u52a1</h2>
                <div class="flex gap-3">
                    <input id="taskInput" type="text" class="flex-1 px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" placeholder="\u4f8b\u5982\uff1a\u5904\u7406\u6700\u8fd1\u6536\u5230\u7684\u7acb\u9879\u7533\u8bf7\u90ae\u4ef6..." onkeydown="if(event.key===\"Enter\") executeTask()">
                    <button onclick="executeTask()" class="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium">\u6267\u884c</button>
                </div>
            </div>

            <!-- 快捷任务 -->
            <div class="mb-8">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-lg font-semibold text-gray-900">\u5feb\u6377\u4efb\u52a1</h2>
                    <span class="text-xs text-gray-400">\u70b9\u51fb\u5373\u586b\uff0c\u4e00\u952e\u6267\u884c</span>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <button onclick="quickTask(\'\u5904\u7406\u6700\u8fd1\u6536\u5230\u7684\u7acb\u9879\u7533\u8bf7\u90ae\u4ef6\uff1a\u8bfb\u53d6\u90ae\u4ef6\u548c\u9644\u4ef6\u4e2d\u7684\u7acb\u9879\u7533\u8bf7\u4e66\uff0c\u63d0\u53d6\u6d3b\u52a8\u4fe1\u606f\u586b\u5165\u8363\u8a89\u6d3b\u52a8\u7acb\u9879\u6c47\u603b\u8868\uff0c\u7136\u540e\u53d1\u9001\u786e\u8ba4\u56de\u590d\')"
                        class="group text-left p-5 bg-white rounded-xl border border-gray-100 hover:border-blue-200 hover:shadow-sm transition-all">
                        <div class="flex items-center gap-3">
                            <span class="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-xl shrink-0">\U0001F4CB</span>
                            <div>
                                <div class="font-medium text-gray-900">\u8363\u8a89\u65f6\u6570\u7acb\u9879\u5904\u7406</div>
                                <div class="text-sm text-gray-400 group-hover:text-gray-500 mt-0.5">\u8bfb\u53d6\u90ae\u4ef6 \u2192 \u89e3\u6790\u9644\u4ef6 \u2192 \u586b\u5165\u7acb\u9879\u6c47\u603b\u8868 \u2192 \u56de\u590d\u786e\u8ba4</div>
                            </div>
                        </div>
                    </button>
                    <button onclick="quickTask(\'\u5904\u7406\u6700\u8fd1\u6536\u5230\u7684\u5fd7\u613f\u65f6\u6570\u5bfc\u5165\u7533\u8bf7\u90ae\u4ef6\uff1a\u8bfb\u53d6\u90ae\u4ef6\u548c\u9644\u4ef6\u4e2d\u7684\u62c5\u4fdd\u4e66\uff0c\u63d0\u53d6\u5fd7\u613f\u8005\u4fe1\u606f\u586b\u5165\u8363\u8a89\u65f6\u6570\u5bfc\u5165\u6a21\u677f\uff0c\u7136\u540e\u53d1\u9001\u786e\u8ba4\u56de\u590d\')"
                        class="group text-left p-5 bg-white rounded-xl border border-gray-100 hover:border-green-200 hover:shadow-sm transition-all">
                        <div class="flex items-center gap-3">
                            <span class="w-10 h-10 rounded-lg bg-green-50 text-green-600 flex items-center justify-center text-xl shrink-0">\u23f0</span>
                            <div>
                                <div class="font-medium text-gray-900">\u5fd7\u613f\u65f6\u6570\u5bfc\u5165\u5904\u7406</div>
                                <div class="text-sm text-gray-400 group-hover:text-gray-500 mt-0.5">\u8bfb\u53d6\u90ae\u4ef6 \u2192 \u89e3\u6790\u9644\u4ef6 \u2192 \u586b\u5165\u65f6\u6570\u6a21\u677f \u2192 \u56de\u590d\u786e\u8ba4</div>
                            </div>
                        </div>
                    </button>
                </div>
            </div>

            <!-- 结果区域 -->
            <div id="resultArea" class="hidden">
                <div id="progressBar" class="w-full bg-gray-200 rounded-full h-2 mb-4 hidden">
                    <div class="bg-blue-500 h-2 rounded-full animate-pulse" style="width: 100%"></div>
                </div>
                <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                    <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                        <div class="flex items-center gap-3">
                            <h2 class="text-lg font-semibold text-gray-900">\u6267\u884c\u7ed3\u679c</h2>
                            <span id="taskStatusBadge" class="px-3 py-1 rounded-full text-sm font-medium hidden"></span>
                        </div>
                        <div class="flex items-center gap-2 text-sm text-gray-400">
                            <span id="taskIdLabel" class="hidden"></span>
                            <span id="taskStepsLabel" class="hidden"></span>
                            <span id="taskTimeLabel" class="hidden"></span>
                        </div>
                    </div>
                    <div class="p-6">
                        <div id="loadingState" class="hidden">
                            <div class="flex items-center gap-4">
                                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                                <div>
                                    <p class="text-gray-700 font-medium">\u6b63\u5728\u5904\u7406\u4e2d...</p>
                                    <p class="text-gray-400 text-sm mt-1">Agent \u6b63\u5728\u8bfb\u53d6\u90ae\u4ef6\u3001\u89e3\u6790\u9644\u4ef6\u3001\u67e5\u8be2\u8868\u683c...</p>
                                </div>
                            </div>
                        </div>
                        <div id="errorState" class="hidden">
                            <div class="flex items-start gap-3 p-4 bg-red-50 rounded-lg border border-red-100">
                                <svg class="w-6 h-6 text-red-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                                </svg>
                                <div>
                                    <p class="font-medium text-red-800" id="errorTitle">\u6267\u884c\u51fa\u9519</p>
                                    <p class="text-red-600 text-sm mt-1" id="errorMessage"></p>
                                </div>
                            </div>
                        </div>
                                                <div id="successState" class="hidden">
                            <div class="flex items-center gap-2 p-3 bg-green-50 rounded-lg border border-green-100">
                                <svg class="w-5 h-5 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                </svg>
                                <span class="font-medium text-green-800 text-sm">✓ 已完成</span>
                                <span id="taskStepsDisplay" class="text-green-600 text-sm ml-auto hidden"></span>
                            </div>
                        </div>
                        <div id="hintState" class="hidden">
                            <div class="p-4 bg-gray-50 rounded-lg mt-3">
                                <p class="text-sm font-medium text-gray-700 mb-2">⏳ 待人工确认</p>
                                <div id="hintContent" class="text-sm text-gray-600 leading-relaxed"></div>
                            </div>
                        </div>
                        <div id="replyState" class="hidden">
                            <div class="p-4 bg-white rounded-lg border border-gray-200 mt-3">
                                <p class="text-sm font-medium text-gray-700 mb-2">🤖 Agent 回复</p>
                                <div id="replyContent" class="text-sm text-gray-800 leading-relaxed"></div>
                            </div>
                        </div>
                        <div id="blockedState" class="hidden">
                            <div class="flex items-start gap-3 p-4 bg-yellow-50 rounded-lg border border-yellow-100 mb-4">
                                <svg class="w-6 h-6 text-yellow-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                                </svg>
                                <div>
                                    <p class="font-medium text-yellow-800">\u9700\u8981\u4eba\u5de5\u4ecb\u5165</p>
                                    <p class="text-yellow-600 text-sm mt-1" id="blockedReason"></p>
                                </div>
                            </div>
                        </div>
                        <div class="mt-4">
                            <button onclick="toggleDetails()" class="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition-colors">
                                <svg id="detailArrow" class="w-4 h-4 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                                </svg>
                                \u67e5\u770b\u8be6\u7ec6\u6570\u636e
                            </button>
                            <div id="detailPanel" class="hidden mt-3">
                                <pre id="rawResult" class="text-sm text-gray-600 bg-gray-50 rounded-lg p-4 overflow-x-auto max-h-96 overflow-y-auto border border-gray-200"></pre>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 历史记录页 -->
        <div id="pageHistory" class="hidden">
            <div class="bg-white rounded-xl shadow-sm border border-gray-100">
                <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                    <h2 class="text-lg font-semibold text-gray-900">\u5386\u53f2\u8bb0\u5f55</h2>
                    <button onclick="loadHistory()" class="text-sm text-blue-600 hover:text-blue-700">\u5237\u65b0</button>
                </div>
                <div class="p-6">
                    <div id="historyLoading" class="text-center py-8 text-gray-400">\u52a0\u8f7d\u4e2d...</div>
                    <div id="historyEmpty" class="hidden text-center py-8 text-gray-400">\u6682\u65e0\u5386\u53f2\u8bb0\u5f55</div>
                    <div id="historyList" class="hidden space-y-2"></div>
                </div>
            </div>
        </div>

        <!-- 数据查询页 -->
        <div id="pageData" class="hidden">
            <div class="flex items-center justify-between mb-6">
                <h2 class="text-lg font-semibold text-gray-900">数据查询</h2>
                <div class="flex gap-2">
                    <select id="dataTableSelector" onchange="loadData()" class="px-4 py-2 border border-gray-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500">
                        <option value="activities">荣誉活动立项汇总表</option>
                        <option value="volunteers">志愿者时数导入模板</option>
                    </select>
                    <button onclick="loadData()" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium">刷新</button>
                </div>
            </div>

            <div id="dataLoading" class="text-center py-12 text-gray-400">加载中...</div>
            <div id="dataEmpty" class="hidden text-center py-12">
                <p class="text-gray-400 text-lg">暂无记录</p>
                <p class="text-gray-300 text-sm mt-1">数据将在任务执行后自动填充</p>
            </div>
            <div id="dataError" class="hidden text-center py-8">
                <p class="text-red-500" id="dataErrorMessage"></p>
            </div>
            <div id="dataTableWrap" class="hidden">
                <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                    <div class="px-6 py-3 border-b border-gray-100 flex items-center justify-between bg-gray-50">
                        <span class="text-sm text-gray-600">共 <span id="dataTotalCount" class="font-semibold text-gray-900">0</span> 条记录</span>
                        <div class="flex items-center gap-3">
                            <input id="dataSearchInput" type="text" placeholder="搜索关键字..." oninput="filterDataTable()" class="px-3 py-1.5 border border-gray-200 rounded text-sm outline-none focus:ring-2 focus:ring-blue-500 w-48">
                            <span id="dataFilterCount" class="text-xs text-gray-400 hidden"></span>
                        </div>
                    </div>
                    <div class="overflow-x-auto">
                        <table id="dataTable" class="w-full text-sm">
                            <thead id="dataTableHead" class="bg-gray-50 text-gray-600"></thead>
                            <tbody id="dataTableBody" class="divide-y divide-gray-100"></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- 页脚 -->
        <div class="mt-10 text-center text-xs text-gray-300">
            \u8363\u8a89\u65f6\u6570\u7ba1\u7406\u7cfb\u7edf v2.0
        </div>
    </div>

    <style>
        .rotate-180 { transform: rotate(180deg); }
        #detailArrow { transition: transform 0.2s ease; }
    </style>

    <script>
        function $(id) { return document.getElementById(id); }
        function show(id) { $(id).classList.remove(\'hidden\'); }
        function hide(id) { $(id).classList.add(\'hidden\'); }
        var NL = String.fromCharCode(10);
        function setText(id, text) { $(id).textContent = text; }
        function setHtml(id, html) { $(id).innerHTML = html; }

        function renderMarkdown(text) {
            if (!text) return '';
            var t = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            t = t.replace(/[*]{2}(.+?)[*]{2}/g, '<strong>$1</strong>');
            t = t.replace(/`(.+?)`/g, '<code class="px-1 py-0.5 bg-gray-100 rounded text-xs font-mono">$1</code>');
            var lines = t.split(NL);
            var html = '';
            var inUl = false, inOl = false;
            for (var i = 0; i < lines.length; i++) {
                var line = lines[i];
                if (!line.trim()) {
                    if (inUl) { html += '</ul>'; inUl = false; }
                    if (inOl) { html += '</ol>'; inOl = false; }
                    html += '<div class="h-2"></div>';
                    continue;
                }
                if (/^[*-] /.test(line)) {
                    if (inOl) { html += '</ol>'; inOl = false; }
                    if (!inUl) { html += '<ul class="list-disc pl-5 my-1 space-y-0.5">'; inUl = true; }
                    html += '<li>' + line.replace(/^[*-] /, '') + '</li>';
                    continue;
                }
                if (/^[0-9]+[.)] /.test(line)) {
                    if (inUl) { html += '</ul>'; inUl = false; }
                    if (!inOl) { html += '<ol class="list-decimal pl-5 my-1 space-y-0.5">'; inOl = true; }
                    html += '<li>' + line.replace(/^[0-9]+[.)] /, '') + '</li>';
                    continue;
                }
                if (inUl) { html += '</ul>'; inUl = false; }
                if (inOl) { html += '</ol>'; inOl = false; }
                var trimmed = line.trim();
                if (/^# /.test(trimmed)) {
                    html += '<div class="font-semibold text-gray-900 mt-2 mb-1">' + trimmed.replace(/^# /, '') + '</div>';
                } else if (/^## /.test(trimmed)) {
                    html += '<div class="font-semibold text-gray-800 mt-2 mb-1">' + trimmed.replace(/^## /, '') + '</div>';
                } else if (/^### /.test(trimmed)) {
                    html += '<div class="font-semibold text-gray-700 mt-1 mb-1">' + trimmed.replace(/^### /, '') + '</div>';
                } else {
                    html += line + '<br>';
                }
            }
            if (inUl) html += '</ul>';
            if (inOl) html += '</ol>';
            return html;
        }

        function extractHint(summary) {
            if (!summary) return '';
            var idx = summary.indexOf('待人工确认');
            if (idx === -1) idx = summary.indexOf('待确认事项');
            if (idx === -1) idx = summary.indexOf('待处理事项');
            if (idx !== -1) return summary.substring(idx);
            var lines = summary.split(NL);
            var hintLines = [];
            var inHint = false;
            for (var i = 0; i < lines.length; i++) {
                if (lines[i].indexOf('⏳') > -1 || lines[i].indexOf('⚠') > -1 || lines[i].indexOf('需要人工') > -1 || lines[i].indexOf('请登录') > -1) {
                    inHint = true;
                }
                if (inHint) hintLines.push(lines[i]);
            }
            return hintLines.join(NL);
        }

        function formatTime(isoStr) {
            if (!isoStr) return \'-\';
            try {
                var d = new Date(isoStr);
                return d.toLocaleString(\'zh-CN\', { month: \'2-digit\', day: \'2-digit\', hour: \'2-digit\', minute: \'2-digit\' });
            } catch(e) { return isoStr; }
        }

        var currentTab = \'execute\';
        function switchTab(tab) {
            currentTab = tab;
            [\'execute\', \'history\', \'data\'].forEach(function(t) {
                var page = document.getElementById(\'page\' + t.charAt(0).toUpperCase() + t.slice(1));
                var btn = document.getElementById(\'tab\' + t.charAt(0).toUpperCase() + t.slice(1));
                if (t === tab) {
                    page.classList.remove(\'hidden\');
                    btn.className = \'px-5 py-3 text-sm font-medium border-b-2 border-blue-600 text-blue-600 transition-colors\';
                } else {
                    page.classList.add(\'hidden\');
                    btn.className = \'px-5 py-3 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700 transition-colors\';
                }
            });
            if (tab === \'history\') loadHistory();\n            if (tab === \'data\') loadData();
        }

        async function loadHistory() {
            hide(\'historyEmpty\');
            show(\'historyLoading\');
            hide(\'historyList\');
            try {
                var resp = await fetch(\'/api/tasks/history?limit=50\');
                var data = await resp.json();
                hide(\'historyLoading\');
                if (!data.tasks || data.tasks.length === 0) {
                    show(\'historyEmpty\');
                    return;
                }
                show(\'historyList\');
                var list = document.getElementById(\'historyList\');
                var html = \'\';
                data.tasks.forEach(function(t) {
                    var badgeHtml = \'\';
                    if (t.status === \'completed\') badgeHtml = \'<span class="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">\u5b8c\u6210</span>\';
                    else if (t.status === \'failed\') badgeHtml = \'<span class="px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">\u5931\u8d25</span>\';
                    else if (t.status === \'blocked\') badgeHtml = \'<span class="px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-700">\u9700\u4ecb\u5165</span>\';
                    else if (t.status === \'running\') badgeHtml = \'<span class="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">\u8fd0\u884c\u4e2d</span>\';
                    else badgeHtml = \'<span class="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">\' + t.status + \'</span>\';
                    var summary = t.summary || t.error || \'-\';
                    html += \'<div class="flex items-start gap-3 p-3 bg-white rounded-lg border border-gray-100 cursor-pointer hover:border-blue-300 transition-all mb-2" onclick="showTaskDetail(\\\'\' + t.task_id + \'\\\')">\' +
                        \'<div class="shrink-0 mt-0.5">\' + badgeHtml + \'</div>\' +
                        \'<div class="flex-1 min-w-0">\' +
                            \'<div class="text-sm text-gray-900 truncate">\' + t.request + \'</div>\' +
                            \'<div class="text-xs text-gray-400 mt-0.5 truncate">\' + summary + \'</div>\' +
                        \'</div>\' +
                        \'<div class="shrink-0 text-xs text-gray-400">\' + formatTime(t.created_at) + \'</div>\' +
                    \'</div>\';
                });
                list.innerHTML = html;
            } catch(e) {
                hide(\'historyLoading\');
                show(\'historyEmpty\');
                document.getElementById(\'historyEmpty\').textContent = \'\u52a0\u8f7d\u5931\u8d25: \' + e.message;
            }
        }

        async function showTaskDetail(taskId) {
            try {
                var resp = await fetch(\'/api/tasks/\' + taskId);
                var data = await resp.json();
                switchTab(\'execute\');
                var badge = document.getElementById(\'taskStatusBadge\');
                show(\'taskStatusBadge\');
                var badgeText = \'\', badgeCls = \'\';
                if (data.status === \'completed\') { badgeText = \'\u2713 \u5df2\u5b8c\u6210\'; badgeCls = \'bg-green-100 text-green-700\'; }
                else if (data.status === \'failed\') { badgeText = \'\u2717 \u5931\u8d25\'; badgeCls = \'bg-red-100 text-red-700\'; }
                else if (data.status === \'blocked\') { badgeText = \'\u26a0 \u9700\u4eba\u5de5\u4ecb\u5165\'; badgeCls = \'bg-yellow-100 text-yellow-700\'; }
                else { badgeText = data.status; badgeCls = \'bg-gray-100 text-gray-700\'; }
                badge.textContent = badgeText;
                badge.className = \'px-3 py-1 rounded-full text-sm font-medium \' + badgeCls;
                show(\'taskIdLabel\');
                setText(\'taskIdLabel\', \'ID: \' + taskId);
                show(\'taskStepsLabel\');
                setText(\'taskStepsLabel\', (data.steps || 0) + \' \u6b65\');
                show(\'taskTimeLabel\');
                setText(\'taskTimeLabel\', formatTime(data.created_at) + \' \u2192 \' + formatTime(data.completed_at));
                hide(\'loadingState\');
                hide(\'progressBar\');
                hide(\'successState\');
                hide(\'hintState\');
                hide(\'replyState\');
                hide(\'blockedState\');
                hide(\'errorState\');
                if (data.status === \'completed\') {
                    show(\'successState\');
                    show(\'replyState\');
                    show(\'taskStepsDisplay\');
                    setText(\'taskStepsDisplay\', data.steps + \' \u6b65\');
                    setHtml(\'replyContent\', renderMarkdown(data.summary || \'\u4efb\u52a1\u5df2\u5b8c\u6210\u3002\'));
                    var hint = extractHint(data.summary);
                    if (hint) {
                        show(\'hintState\');
                        setHtml(\'hintContent\', renderMarkdown(hint));
                    }
                } else if (data.status === \'blocked\') {
                    show(\'blockedState\');
                    setText(\'blockedReason\', data.error || \'\u9700\u8981\u4eba\u5de5\u5ba1\u6838\u5904\u7406\');
                } else if (data.status === \'failed\') {
                    show(\'errorState\');
                    setText(\'errorTitle\', \'\u4efb\u52a1\u6267\u884c\u5931\u8d25\');
                    setText(\'errorMessage\', data.error || \'\u672a\u77e5\u9519\u8bef\');
                }
                setText(\'rawResult\', JSON.stringify(data, null, 2));
                show(\'resultArea\');
                hide(\'detailPanel\');
            } catch(e) {
                alert(\'\u52a0\u8f7d\u4efb\u52a1\u8be6\u60c5\u5931\u8d25: \' + e.message);
            }
        }

        async function executeTask() {
            var text = document.getElementById(\'taskInput\').value.trim();
            if (!text) return;
            await runTask(text);
        }

        function quickTask(text) {
            document.getElementById(\'taskInput\').value = text;
            runTask(text);
        }

        async function runTask(text) {
            hide(\'loadingState\');
            hide(\'errorState\');
            hide(\'successState\');
            hide(\'hintState\');
            hide(\'replyState\');
            hide(\'blockedState\');
            hide(\'detailPanel\');
            document.getElementById(\'detailArrow\').classList.remove(\'rotate-180\');
            document.getElementById(\'resultArea\').classList.remove(\'hidden\');
            show(\'loadingState\');
            show(\'progressBar\');
            hide(\'taskStatusBadge\');
            hide(\'taskIdLabel\');
            hide(\'taskStepsLabel\');
            hide(\'taskTimeLabel\');

            try {
                var resp = await fetch(\'/api/tasks/execute\', {
                    method: \'POST\',
                    headers: {\'Content-Type\': \'application/json\'},
                    body: JSON.stringify({request: text})
                });
                var initData = await resp.json();
                var taskId = initData.task_id;
                show(\'taskIdLabel\');
                setText(\'taskIdLabel\', \'ID: \' + taskId);

                var data;
                while (true) {
                    await new Promise(function(r) { setTimeout(r, 800); });
                    var statusResp = await fetch(\'/api/tasks/\' + taskId);
                    data = await statusResp.json();
                    if (data.steps !== undefined) {
                        show(\'taskStepsLabel\');
                        setText(\'taskStepsLabel\', data.steps + \' \u6b65\');
                    }
                    if (data.status !== \'running\') break;
                }

                hide(\'loadingState\');
                hide(\'progressBar\');

                var badge = document.getElementById(\'taskStatusBadge\');
                show(\'taskStatusBadge\');
                var badgeText = \'\', badgeCls = \'\';
                if (data.status === \'completed\') { badgeText = \'\u2713 \u5df2\u5b8c\u6210\'; badgeCls = \'bg-green-100 text-green-700\'; }
                else if (data.status === \'failed\') { badgeText = \'\u2717 \u5931\u8d25\'; badgeCls = \'bg-red-100 text-red-700\'; }
                else if (data.status === \'blocked\') { badgeText = \'\u26a0 \u9700\u4eba\u5de5\u4ecb\u5165\'; badgeCls = \'bg-yellow-100 text-yellow-700\'; }
                else { badgeText = data.status; badgeCls = \'bg-gray-100 text-gray-700\'; }
                badge.textContent = badgeText;
                badge.className = \'px-3 py-1 rounded-full text-sm font-medium \' + badgeCls;

                show(\'taskStepsLabel\');
                setText(\'taskStepsLabel\', data.steps + \' \u6b65\');
                show(\'taskTimeLabel\');
                setText(\'taskTimeLabel\', formatTime(data.created_at) + \' \u2192 \' + formatTime(data.completed_at));

                if (data.status === \'completed\') {
                    show(\'successState\');
                    show(\'replyState\');
                    show(\'taskStepsDisplay\');
                    setText(\'taskStepsDisplay\', data.steps + \' \u6b65\');
                    setHtml(\'replyContent\', renderMarkdown(data.summary || \'\u4efb\u52a1\u5df2\u5b8c\u6210\u3002\'));
                    var hint = extractHint(data.summary);
                    if (hint) {
                        show(\'hintState\');
                        setHtml(\'hintContent\', renderMarkdown(hint));
                    }
                } else if (data.status === \'blocked\') {
                    show(\'blockedState\');
                    setText(\'blockedReason\', data.error || \'\u9700\u8981\u4eba\u5de5\u5ba1\u6838\u5904\u7406\');
                } else if (data.status === \'failed\') {
                    show(\'errorState\');
                    setText(\'errorTitle\', \'\u4efb\u52a1\u6267\u884c\u5931\u8d25\');
                    setText(\'errorMessage\', data.error || \'\u672a\u77e5\u9519\u8bef\');
                }

                setText(\'rawResult\', JSON.stringify(data, null, 2));

            } catch(e) {
                hide(\'progressBar\');
                hide(\'loadingState\');
                show(\'errorState\');
                setText(\'errorTitle\', \'\u8bf7\u6c42\u5931\u8d25\');
                setText(\'errorMessage\', e.message || \'\u65e0\u6cd5\u8fde\u63a5\u5230\u670d\u52a1\u5668\');
                setText(\'rawResult\', \'\');
            }

            try {
                var hist = await (await fetch(\'/api/tasks/history?limit=1\')).json();
                document.getElementById(\'historyCount\').textContent = hist.total + \' \u6761\';
            } catch(e) {}
        }

        function toggleDetails() {
            var panel = document.getElementById(\'detailPanel\');
            var arrow = document.getElementById(\'detailArrow\');
            if (panel.classList.contains(\'hidden\')) {
                show(\'detailPanel\');
                arrow.classList.add(\'rotate-180\');
            } else {
                hide(\'detailPanel\');
                arrow.classList.remove(\'rotate-180\');
            }
        }
    
        // ── 数据查询 ───────────────────────

        var _dataCache = null;

        async function loadData() {
            var table = document.getElementById('dataTableSelector').value;
            hide('dataError');
            hide('dataEmpty');
            hide('dataTableWrap');
            show('dataLoading');

            try {
                var resp = await fetch('/api/data/' + table);
                var data = await resp.json();
                hide('dataLoading');

                if (data.status === 'error') {
                    show('dataError');
                    document.getElementById('dataErrorMessage').textContent = data.message || '加载失败';
                    return;
                }

                if (!data.records || data.records.length === 0) {
                    show('dataEmpty');
                    return;
                }

                _dataCache = data;
                document.getElementById('dataTotalCount').textContent = data.total;
                renderDataTable(data.records, data.columns);
                show('dataTableWrap');
                document.getElementById('dataFilterCount').classList.add('hidden');

            } catch(e) {
                hide('dataLoading');
                show('dataError');
                document.getElementById('dataErrorMessage').textContent = '请求失败: ' + e.message;
            }
        }

        function renderDataTable(records, columns) {
            var thead = document.getElementById('dataTableHead');
            var tbody = document.getElementById('dataTableBody');

            var headerHtml = '<tr>';
            headerHtml += '<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">#</th>';
            columns.forEach(function(col) {
                headerHtml += '<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">' + col + '</th>';
            });
            headerHtml += '</tr>';
            thead.innerHTML = headerHtml;

            var bodyHtml = '';
            records.forEach(function(row, idx) {
                bodyHtml += '<tr class="hover:bg-gray-50 transition-colors">';
                bodyHtml += '<td class="px-4 py-3 text-sm text-gray-400">' + (idx + 1) + '</td>';
                columns.forEach(function(col) {
                    var val = row[col] || '';
                    bodyHtml += '<td class="px-4 py-3 text-sm text-gray-700 max-w-xs truncate" title="' + val.replace(/"/g, '&quot;') + '">' + val + '</td>';
                });
                bodyHtml += '</tr>';
            });
            tbody.innerHTML = bodyHtml;
        }

        function filterDataTable() {
            if (!_dataCache || !_dataCache.records) return;
            var keyword = document.getElementById('dataSearchInput').value.trim().toLowerCase();
            var filtered = _dataCache.records;

            if (keyword) {
                filtered = _dataCache.records.filter(function(row) {
                    return Object.values(row).some(function(val) {
                        return String(val).toLowerCase().indexOf(keyword) > -1;
                    });
                });
            }

            renderDataTable(filtered, _dataCache.columns);
            var fc = document.getElementById('dataFilterCount');
            if (keyword) {
                fc.classList.remove('hidden');
                fc.textContent = filtered.length + ' / ' + _dataCache.records.length + ' 条';
            } else {
                fc.classList.add('hidden');
            }
        }

    </script>
</body>
</html>"""

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

    print(f"\U0001F310 Web\u7ba1\u7406\u754c\u9762: http://{host}:{port}")
    print(f"\U0001F4E1 API\u670d\u52a1: http://{host}:{port}/api")
    print()
    uvicorn.run(app, host=host, port=port, log_level="info")
