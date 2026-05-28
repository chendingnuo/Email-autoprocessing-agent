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


# ── 主页 ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Web管理界面"""
    return HTMLResponse(INDEX_HTML)


# ── 静态Web界面 ─────────────────────────────────────

INDEX_HTML = """
<!DOCTYPE html>
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
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
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
                <div class="text-sm text-gray-500">历史任务</div>
                <div class="text-lg font-semibold mt-1" id="historyCount">-</div>
            </div>
        </div>

        <script>
        // 独立初始化脚本 — 不与主脚本共享作用域
        (function(){ fetch('/api/health').then(function(r){ return r.json(); }).then(function(health){
            var el=document.getElementById('healthStatus');
            if(health.status==='ok'){ el.textContent='正常运行'; el.className='text-lg font-semibold mt-1 text-green-600'; }
            else{ el.textContent='异常'; el.className='text-lg font-semibold mt-1 text-red-600'; }
            if(health.warnings&&health.warnings.length) el.textContent+=' ('+health.warnings.length+' 项警告)';
        }).catch(function(){ document.getElementById('healthStatus').textContent='无法连接'; });
        fetch('/api/tools').then(function(r){ return r.json(); }).then(function(t){ document.getElementById('toolCount').textContent=t.tools.length+' 个'; }).catch(function(){});
        fetch('/api/tasks/history?limit=1').then(function(r){ return r.json(); }).then(function(h){ document.getElementById('historyCount').textContent=h.total+' 条'; }).catch(function(){});
        })();
        </script>

        <!-- Tab 切换 -->
        <div class="flex gap-1 mb-6 border-b border-gray-200">
            <button id="tabExecute" onclick="switchTab('execute')" class="px-5 py-3 text-sm font-medium border-b-2 border-blue-600 text-blue-600 transition-colors">任务执行</button>
            <button id="tabHistory" onclick="switchTab('history')" class="px-5 py-3 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700 transition-colors">历史记录</button>
        </div>

        <!-- 任务执行页 -->
        <div id="pageExecute">
            <!-- 任务输入 -->
            <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100 mb-8">
                <h2 class="text-lg font-semibold text-gray-900 mb-3">执行任务</h2>
                <div class="flex gap-3">
                    <input
                        id="taskInput"
                        type="text"
                        class="flex-1 px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                        placeholder="例如：处理最近收到的立项申请邮件..."
                        onkeydown="if(event.key==='Enter') executeTask()"
                    >
                    <button
                        onclick="executeTask()"
                        class="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                    >
                        执行
                    </button>
                </div>
            </div>

            <!-- 快捷任务 -->
            <div class="mb-8">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-lg font-semibold text-gray-900">快捷任务</h2>
                    <span class="text-xs text-gray-400">点击即填，一键执行</span>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <button onclick="quickTask('处理最近收到的立项申请邮件：读取邮件和附件中的立项申请书，提取活动信息填入荣誉活动立项汇总表，然后发送确认回复')"
                        class="group text-left p-5 bg-white rounded-xl border border-gray-100 hover:border-blue-200 hover:shadow-sm transition-all">
                        <div class="flex items-center gap-3">
                            <span class="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-xl shrink-0">📋</span>
                            <div>
                                <div class="font-medium text-gray-900">荣誉时数立项处理</div>
                                <div class="text-sm text-gray-400 group-hover:text-gray-500 mt-0.5">读取邮件 → 解析附件 → 填入立项汇总表 → 回复确认</div>
                            </div>
                        </div>
                    </button>
                    <button onclick="quickTask('处理最近收到的志愿时数导入申请邮件：读取邮件和附件中的担保书，提取志愿者信息填入荣誉时数导入模板，然后发送确认回复')"
                        class="group text-left p-5 bg-white rounded-xl border border-gray-100 hover:border-green-200 hover:shadow-sm transition-all">
                        <div class="flex items-center gap-3">
                            <span class="w-10 h-10 rounded-lg bg-green-50 text-green-600 flex items-center justify-center text-xl shrink-0">⏰</span>
                            <div>
                                <div class="font-medium text-gray-900">志愿时数导入处理</div>
                                <div class="text-sm text-gray-400 group-hover:text-gray-500 mt-0.5">读取邮件 → 解析附件 → 填入时数模板 → 回复确认</div>
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
                            <h2 class="text-lg font-semibold text-gray-900">执行结果</h2>
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
                                    <p class="text-gray-700 font-medium">正在处理中...</p>
                                    <p class="text-gray-400 text-sm mt-1">Agent 正在读取邮件、解析附件、查询表格...</p>
                                </div>
                            </div>
                        </div>

                        <div id="errorState" class="hidden">
                            <div class="flex items-start gap-3 p-4 bg-red-50 rounded-lg border border-red-100">
                                <svg class="w-6 h-6 text-red-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                                </svg>
                                <div>
                                    <p class="font-medium text-red-800" id="errorTitle">执行出错</p>
                                    <p class="text-red-600 text-sm mt-1" id="errorMessage"></p>
                                </div>
                            </div>
                        </div>

                        <div id="successState" class="hidden">
                            <div class="flex items-start gap-3 p-4 bg-green-50 rounded-lg border border-green-100 mb-4">
                                <svg class="w-6 h-6 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                </svg>
                                <div>
                                    <p class="font-medium text-green-800">任务已完成</p>
                                    <p class="text-green-600 text-sm mt-1" id="summaryText"></p>
                                </div>
                            </div>
                        </div>

                        <div id="blockedState" class="hidden">
                            <div class="flex items-start gap-3 p-4 bg-yellow-50 rounded-lg border border-yellow-100 mb-4">
                                <svg class="w-6 h-6 text-yellow-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                                </svg>
                                <div>
                                    <p class="font-medium text-yellow-800">需要人工介入</p>
                                    <p class="text-yellow-600 text-sm mt-1" id="blockedReason"></p>
                                </div>
                            </div>
                        </div>

                        <div class="mt-4">
                            <button onclick="toggleDetails()" class="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition-colors">
                                <svg id="detailArrow" class="w-4 h-4 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                                </svg>
                                查看详细数据
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
                    <h2 class="text-lg font-semibold text-gray-900">历史记录</h2>
                    <button onclick="loadHistory()" class="text-sm text-blue-600 hover:text-blue-700">刷新</button>
                </div>
                <div class="p-6">
                    <div id="historyLoading" class="text-center py-8 text-gray-400">加载中...</div>
                    <div id="historyEmpty" class="hidden text-center py-8 text-gray-400">暂无历史记录</div>
                    <div id="historyList" class="hidden space-y-2"></div>
                </div>
            </div>
        </div>

        <!-- 页脚 -->
        <div class="mt-10 text-center text-xs text-gray-300">
            荣誉时数管理系统 v2.0
        </div>
    </div>

    <style>
        .rotate-180 { transform: rotate(180deg); }
        #detailArrow { transition: transform 0.2s ease; }
    </style>

    <script>
        function $(id) { return document.getElementById(id); }
        function show(id) { $(id).classList.remove('hidden'); }
        function hide(id) { $(id).classList.add('hidden'); }
        function setText(id, text) { $(id).textContent = text; }

        function formatTime(isoStr) {
            if (!isoStr) return '-';
            try {
                const d = new Date(isoStr);
                return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
            } catch(e) { return isoStr; }
        }

        // Tab switch
        let currentTab = 'execute';
        function switchTab(tab) {
            currentTab = tab;
            ['execute', 'history'].forEach(function(t) {
                var page = document.getElementById('page' + t.charAt(0).toUpperCase() + t.slice(1));
                var btn = document.getElementById('tab' + t.charAt(0).toUpperCase() + t.slice(1));
                if (t === tab) {
                    page.classList.remove('hidden');
                    btn.className = 'px-5 py-3 text-sm font-medium border-b-2 border-blue-600 text-blue-600 transition-colors';
                } else {
                    page.classList.add('hidden');
                    btn.className = 'px-5 py-3 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700 transition-colors';
                }
            });
            if (tab === 'history') loadHistory();
        }


        // History
        async function loadHistory() {
            hide('historyEmpty');
            show('historyLoading');
            hide('historyList');
            try {
                const resp = await fetch('/api/tasks/history?limit=50');
                const data = await resp.json();
                hide('historyLoading');
                if (!data.tasks || data.tasks.length === 0) {
                    show('historyEmpty');
                    return;
                }
                show('historyList');
                var list = document.getElementById('historyList');
                var html = '';
                data.tasks.forEach(function(t) {
                    var badgeHtml = '';
                    if (t.status === 'completed') badgeHtml = '<span class="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">完成</span>';
                    else if (t.status === 'failed') badgeHtml = '<span class="px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">失败</span>';
                    else if (t.status === 'blocked') badgeHtml = '<span class="px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-700">需介入</span>';
                    else if (t.status === 'running') badgeHtml = '<span class="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">运行中</span>';
                    else badgeHtml = '<span class="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">' + t.status + '</span>';
                    var summary = t.summary || t.error || '-';
                    html += '<div class="flex items-start gap-3 p-3 bg-white rounded-lg border border-gray-100 cursor-pointer hover:border-blue-300 transition-all mb-2" onclick="showTaskDetail(\\'' + t.task_id + '\\')">' +
                        '<div class="shrink-0 mt-0.5">' + badgeHtml + '</div>' +
                        '<div class="flex-1 min-w-0">' +
                            '<div class="text-sm text-gray-900 truncate">' + t.request + '</div>' +
                            '<div class="text-xs text-gray-400 mt-0.5 truncate">' + summary + '</div>' +
                        '</div>' +
                        '<div class="shrink-0 text-xs text-gray-400">' + formatTime(t.created_at) + '</div>' +
                    '</div>';
                });
                list.innerHTML = html;
            } catch(e) {
                hide('historyLoading');
                show('historyEmpty');
                document.getElementById('historyEmpty').textContent = '加载失败: ' + e.message;
            }
        }

        async function showTaskDetail(taskId) {
            try {
                const resp = await fetch('/api/tasks/' + taskId);
                const data = await resp.json();
                switchTab('execute');
                var badge = document.getElementById('taskStatusBadge');
                show('taskStatusBadge');
                var badgeText = '', badgeCls = '';
                if (data.status === 'completed') { badgeText = '✓ 已完成'; badgeCls = 'bg-green-100 text-green-700'; }
                else if (data.status === 'failed') { badgeText = '✗ 失败'; badgeCls = 'bg-red-100 text-red-700'; }
                else if (data.status === 'blocked') { badgeText = '⚠ 需人工介入'; badgeCls = 'bg-yellow-100 text-yellow-700'; }
                else { badgeText = data.status; badgeCls = 'bg-gray-100 text-gray-700'; }
                badge.textContent = badgeText;
                badge.className = 'px-3 py-1 rounded-full text-sm font-medium ' + badgeCls;
                show('taskIdLabel');
                setText('taskIdLabel', 'ID: ' + taskId);
                show('taskStepsLabel');
                setText('taskStepsLabel', (data.steps || 0) + ' 步');
                show('taskTimeLabel');
                setText('taskTimeLabel', formatTime(data.created_at) + ' → ' + formatTime(data.completed_at));
                hide('loadingState');
                hide('progressBar');
                hide('successState');
                hide('blockedState');
                hide('errorState');
                if (data.status === 'completed') {
                    show('successState');
                    setText('summaryText', data.summary || '任务已完成。');
                } else if (data.status === 'blocked') {
                    show('blockedState');
                    setText('blockedReason', data.error || '需要人工审核处理');
                } else if (data.status === 'failed') {
                    show('errorState');
                    setText('errorTitle', '任务执行失败');
                    setText('errorMessage', data.error || '未知错误');
                }
                setText('rawResult', JSON.stringify(data, null, 2));
                show('resultArea');
                hide('detailPanel');
            } catch(e) {
                alert('加载任务详情失败: ' + e.message);
            }
        }

        // Task execution
        async function executeTask() {
            var text = document.getElementById('taskInput').value.trim();
            if (!text) return;
            await runTask(text);
        }

        function quickTask(text) {
            document.getElementById('taskInput').value = text;
            runTask(text);
        }

        async function runTask(text) {
            hide('loadingState');
            hide('errorState');
            hide('successState');
            hide('blockedState');
            hide('detailPanel');
            document.getElementById('detailArrow').classList.remove('rotate-180');
            document.getElementById('resultArea').classList.remove('hidden');
            show('loadingState');
            show('progressBar');
            hide('taskStatusBadge');
            hide('taskIdLabel');
            hide('taskStepsLabel');
            hide('taskTimeLabel');

            try {
                const resp = await fetch('/api/tasks/execute', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({request: text})
                });
                const initData = await resp.json();
                var taskId = initData.task_id;
                show('taskIdLabel');
                setText('taskIdLabel', 'ID: ' + taskId);

                var data;
                while (true) {
                    await new Promise(function(r) { setTimeout(r, 800); });
                    const statusResp = await fetch('/api/tasks/' + taskId);
                    data = await statusResp.json();
                    if (data.steps !== undefined) {
                        show('taskStepsLabel');
                        setText('taskStepsLabel', data.steps + ' 步');
                    }
                    if (data.status !== 'running') break;
                }

                hide('loadingState');
                hide('progressBar');

                var badge = document.getElementById('taskStatusBadge');
                show('taskStatusBadge');
                var badgeText = '', badgeCls = '';
                if (data.status === 'completed') { badgeText = '✓ 已完成'; badgeCls = 'bg-green-100 text-green-700'; }
                else if (data.status === 'failed') { badgeText = '✗ 失败'; badgeCls = 'bg-red-100 text-red-700'; }
                else if (data.status === 'blocked') { badgeText = '⚠ 需人工介入'; badgeCls = 'bg-yellow-100 text-yellow-700'; }
                else { badgeText = data.status; badgeCls = 'bg-gray-100 text-gray-700'; }
                badge.textContent = badgeText;
                badge.className = 'px-3 py-1 rounded-full text-sm font-medium ' + badgeCls;

                show('taskStepsLabel');
                setText('taskStepsLabel', data.steps + ' 步');
                show('taskTimeLabel');
                setText('taskTimeLabel', formatTime(data.created_at) + ' → ' + formatTime(data.completed_at));

                if (data.status === 'completed') {
                    show('successState');
                    setText('summaryText', data.summary || '任务已完成。');
                } else if (data.status === 'blocked') {
                    show('blockedState');
                    setText('blockedReason', data.error || '需要人工审核处理');
                } else if (data.status === 'failed') {
                    show('errorState');
                    setText('errorTitle', '任务执行失败');
                    setText('errorMessage', data.error || '未知错误');
                }

                setText('rawResult', JSON.stringify(data, null, 2));

            } catch(e) {
                hide('progressBar');
                hide('loadingState');
                show('errorState');
                setText('errorTitle', '请求失败');
                setText('errorMessage', e.message || '无法连接到服务器');
                setText('rawResult', '');
            }

            // Refresh history count
            try {
                const hist = await (await fetch('/api/tasks/history?limit=1')).json();
                document.getElementById('historyCount').textContent = hist.total + ' 条';
            } catch(e) {}
        }

        function toggleDetails() {
            var panel = document.getElementById('detailPanel');
            var arrow = document.getElementById('detailArrow');
            if (panel.classList.contains('hidden')) {
                show('detailPanel');
                arrow.classList.add('rotate-180');
            } else {
                hide('detailPanel');
                arrow.classList.remove('rotate-180');
            }
        }
    </script>
</body>
</html>
"""
# ── 入口 ─────────────────
if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════╗
    ║   荣誉时数管理系统                               ║
    ╚══════════════════════════════════════════════╝
    """)

    warnings = config.validate()
    if warnings:
        print("⚠ 配置警告:")
        for w in warnings:
            print(f"   • {w}")
        print()

    host = os.getenv("AGENT_HOST", "127.0.0.1")
    port = int(os.getenv("AGENT_PORT", "8000"))

    print(f"🌐 Web管理界面: http://{host}:{port}")
    print(f"📡 API服务: http://{host}:{port}/api")
    print()
    uvicorn.run(app, host=host, port=port, log_level="info")
