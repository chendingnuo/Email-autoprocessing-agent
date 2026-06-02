/* ── History Page ── */
const History = {
    allTasks: [],
    filterStatus: 'all',
    searchQuery: '',
    pageSize: 10,
    currentPage: 1,

    render(container) {
        container.innerHTML = `
            <!-- 过滤栏 -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 mb-6">
                <div class="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
                    <div class="flex gap-1 flex-wrap" id="statusFilter">
                        <button data-status="all" class="filter-btn px-3 py-1.5 rounded-lg text-sm font-medium bg-blue-100 text-blue-700" onclick="History.setFilter('all')">全部</button>
                        <button data-status="completed" class="filter-btn px-3 py-1.5 rounded-lg text-sm font-medium text-gray-500 hover:bg-gray-100" onclick="History.setFilter('completed')">已完成</button>
                        <button data-status="failed" class="filter-btn px-3 py-1.5 rounded-lg text-sm font-medium text-gray-500 hover:bg-gray-100" onclick="History.setFilter('failed')">失败</button>
                        <button data-status="blocked" class="filter-btn px-3 py-1.5 rounded-lg text-sm font-medium text-gray-500 hover:bg-gray-100" onclick="History.setFilter('blocked')">需介入</button>
                        <button data-status="running" class="filter-btn px-3 py-1.5 rounded-lg text-sm font-medium text-gray-500 hover:bg-gray-100" onclick="History.setFilter('running')">运行中</button>
                    </div>
                    <div class="flex gap-2 w-full sm:w-auto">
                        <div class="relative flex-1 sm:flex-initial">
                            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                            </svg>
                            <input id="historySearch" type="text" placeholder="搜索任务..."
                                class="pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none w-full sm:w-48"
                                oninput="History.setSearch(this.value)">
                        </div>
                        <button onclick="History.loadData()" class="px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors border border-blue-100">
                            刷新
                        </button>
                    </div>
                </div>
            </div>

            <!-- 列表 -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-100">
                <div id="historyContent">
                    <div class="text-center py-12 text-gray-400" id="historyLoading">加载中...</div>
                </div>

                <!-- 分页 -->
                <div id="pagination" class="hidden px-6 py-4 border-t border-gray-100 flex items-center justify-between">
                    <span class="text-sm text-gray-400" id="pageInfo"></span>
                    <div class="flex gap-2">
                        <button id="prevPage" onclick="History.prevPage()" class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed">上一页</button>
                        <button id="nextPage" onclick="History.nextPage()" class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed">下一页</button>
                    </div>
                </div>
            </div>
        `;

        this.loadData();
    },

    setFilter(status) {
        this.filterStatus = status;
        this.currentPage = 1;
        document.querySelectorAll('.filter-btn').forEach(el => {
            const isActive = el.dataset.status === status;
            el.className = isActive
                ? 'filter-btn px-3 py-1.5 rounded-lg text-sm font-medium bg-blue-100 text-blue-700'
                : 'filter-btn px-3 py-1.5 rounded-lg text-sm font-medium text-gray-500 hover:bg-gray-100';
        });
        this.renderList();
    },

    setSearch(query) {
        this.searchQuery = query.trim().toLowerCase();
        this.currentPage = 1;
        this.renderList();
    },

    async loadData() {
        const content = document.getElementById('historyContent');
        try {
            const data = await API.get('/api/tasks/history?limit=200');
            this.allTasks = data.tasks || [];
            this.renderList();
        } catch {
            content.innerHTML = '<div class="text-center py-12 text-red-400">加载失败，请重试</div>';
        }
    },

    getFilteredTasks() {
        let tasks = this.allTasks;
        if (this.filterStatus !== 'all') {
            tasks = tasks.filter(t => t.status === this.filterStatus);
        }
        if (this.searchQuery) {
            tasks = tasks.filter(t =>
                (t.request && t.request.toLowerCase().includes(this.searchQuery)) ||
                (t.summary && t.summary.toLowerCase().includes(this.searchQuery)) ||
                (t.task_id && t.task_id.toLowerCase().includes(this.searchQuery))
            );
        }
        return tasks;
    },

    renderList() {
        const content = document.getElementById('historyContent');
        const pagination = document.getElementById('pagination');
        const filtered = this.getFilteredTasks();
        const total = filtered.length;
        const totalPages = Math.max(1, Math.ceil(total / this.pageSize));
        if (this.currentPage > totalPages) this.currentPage = totalPages;

        if (total === 0) {
            content.innerHTML = '<div class="text-center py-12 text-gray-400">暂无匹配的历史记录</div>';
            pagination.classList.add('hidden');
            return;
        }

        const start = (this.currentPage - 1) * this.pageSize;
        const pageTasks = filtered.slice(start, start + this.pageSize);

        let html = '<div class="divide-y divide-gray-50">';
        pageTasks.forEach(t => {
            html += `
                <div class="history-item px-6 py-4 hover:bg-gray-50 transition-colors cursor-pointer" onclick="History.toggleDetail(this, '${t.task_id}')">
                    <div class="flex items-start gap-3">
                        <div class="shrink-0 mt-0.5">${UI.statusBadge(t.status)}</div>
                        <div class="flex-1 min-w-0">
                            <div class="text-sm text-gray-900 truncate">${UI.escapeHtml(t.request || '-')}</div>
                            <div class="text-xs text-gray-400 mt-1">
                                <span>${UI.formatTime(t.created_at)}</span>
                                <span class="mx-1">·</span>
                                <span>${t.steps || 0} 步</span>
                                ${t.summary ? `<span class="mx-1">·</span><span class="text-gray-500">${UI.escapeHtml(t.summary.slice(0, 80))}${t.summary.length > 80 ? '...' : ''}</span>` : ''}
                            </div>
                        </div>
                        <svg class="w-4 h-4 text-gray-300 mt-1 transition-transform detail-arrow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                        </svg>
                    </div>
                    <div class="history-detail hidden mt-3 pl-0">
                        <div class="bg-white rounded-lg border border-gray-200 overflow-hidden" id="detail-${t.task_id}">
                            <div class="text-center py-8 text-sm text-gray-400">加载中...</div>
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        content.innerHTML = html;

        // 分页
        pagination.classList.remove('hidden');
        document.getElementById('pageInfo').textContent = `共 ${total} 条，第 ${this.currentPage}/${totalPages} 页`;
        document.getElementById('prevPage').disabled = this.currentPage <= 1;
        document.getElementById('nextPage').disabled = this.currentPage >= totalPages;
    },

    async toggleDetail(el, taskId) {
        const detail = el.querySelector('.history-detail');
        const arrow = el.querySelector('.detail-arrow');
        const isOpening = detail.classList.contains('hidden');

        detail.classList.toggle('hidden');
        arrow.classList.toggle('open');

        if (isOpening) {
            const container = document.getElementById('detail-' + taskId);
            try {
                const data = await API.get('/api/tasks/' + taskId);
                if (data.step_details && data.step_details.length > 0) {
                    let html = '<div class="divide-y divide-gray-100">';

                    // 摘要信息
                    html += `
                        <div class="px-4 py-3 bg-gray-50 flex items-center gap-4 text-xs text-gray-500">
                            <span>状态: ${data.status}</span>
                            <span>${data.steps || 0} 步</span>
                            ${data.created_at ? `<span>${UI.formatTime(data.created_at)}</span>` : ''}
                            ${data.completed_at ? `<span>→ ${UI.formatTime(data.completed_at)}</span>` : ''}
                        </div>`;

                    // 步骤卡片
                    let stepNum = 0;
                    data.step_details.forEach((turn) => {
                        turn.steps.forEach((step) => {
                            stepNum++;
                            const isFinal = !!step.final_answer;
                            html += `<div class="px-4 py-3">`;
                            html += `<div class="text-xs font-semibold text-gray-500 mb-2">步骤 ${stepNum}</div>`;

                            if (step.thought) {
                                html += `
                                <div class="mb-2">
                                    <div class="text-xs text-gray-400 mb-0.5">💭 思考</div>
                                    <div class="text-sm text-gray-700 markdown-body">${History.renderMarkdown(step.thought)}</div>
                                </div>`;
                            }

                            if (step.tool_call) {
                                const tc = step.tool_call;
                                html += `
                                <div class="mb-2">
                                    <div class="text-xs text-gray-400 mb-0.5">🔧 工具: <span class="font-mono text-blue-600">${UI.escapeHtml(tc.name)}</span></div>
                                    <details class="text-xs">
                                        <summary class="text-gray-400 cursor-pointer hover:text-gray-600">查看参数</summary>
                                        <pre class="mt-1 p-2 bg-gray-100 rounded overflow-x-auto">${UI.escapeHtml(JSON.stringify(tc.parameters, null, 2))}</pre>
                                    </details>
                                </div>`;

                                if (step.observation) {
                                    const obs = step.observation;
                                    const shortObs = obs.length > 500 ? obs.slice(0, 500) + '...' : obs;
                                    html += `
                                    <div class="mb-2">
                                        <div class="text-xs text-gray-400 mb-0.5">📊 结果</div>
                                        <div class="text-sm text-gray-700 markdown-body max-h-40 overflow-y-auto">${History.renderMarkdown(obs)}</div>
                                    </div>`;
                                }
                            }

                            if (step.final_answer) {
                                html += `
                                <div class="mb-2">
                                    <div class="text-xs text-green-600 mb-0.5">✅ 最终回答</div>
                                    <div class="text-sm text-gray-700 markdown-body">${History.renderMarkdown(step.final_answer)}</div>
                                </div>`;
                            }

                            html += `</div>`;
                        });
                    });

                    // 原始 JSON（折叠）
                    html += `
                        <div class="px-4 py-3 bg-gray-50 border-t border-gray-100">
                            <details>
                                <summary class="text-xs text-gray-400 cursor-pointer hover:text-gray-600 select-none">查看原始数据</summary>
                                <pre class="mt-2 text-xs text-gray-600 overflow-x-auto max-h-40 overflow-y-auto">${UI.escapeHtml(JSON.stringify({task_id: data.task_id, status: data.status, steps: data.steps, summary: data.summary, error: data.error}, null, 2))}</pre>
                            </details>
                        </div>`;

                    html += '</div>';
                    container.innerHTML = html;
                } else {
                    // 无步骤详情，显示概要信息
                    const display = {
                        task_id: data.task_id,
                        status: data.status,
                        steps: data.steps,
                        summary: data.summary,
                        error: data.error,
                        extracted_data: data.extracted_data,
                        created_at: data.created_at,
                        completed_at: data.completed_at,
                    };
                    container.innerHTML = `<pre class="text-xs text-gray-600 p-4 overflow-x-auto max-h-60 overflow-y-auto">${UI.escapeHtml(JSON.stringify(display, null, 2))}</pre>`;
                }
            } catch {
                container.innerHTML = '<div class="text-center py-8 text-sm text-red-400">加载失败</div>';
            }
        }
    },

    renderMarkdown(text) {
        if (!text) return '';
        if (typeof marked !== 'undefined' && marked.parse) {
            return marked.parse(text, { breaks: true });
        }
        return '<pre class="text-sm whitespace-pre-wrap">' + UI.escapeHtml(text) + '</pre>';
    },

    prevPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.renderList();
        }
    },

    nextPage() {
        const totalPages = Math.max(1, Math.ceil(this.getFilteredTasks().length / this.pageSize));
        if (this.currentPage < totalPages) {
            this.currentPage++;
            this.renderList();
        }
    },
};
