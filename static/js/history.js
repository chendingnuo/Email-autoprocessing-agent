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
            <div class="card" style="margin-bottom:28px;">
                <div style="display:flex;flex-wrap:wrap;gap:16px;align-items:flex-start;justify-content:space-between;">
                    <div style="display:flex;gap:4px;flex-wrap:wrap;" id="statusFilter">
                        <button data-status="all" class="filter-btn active" onclick="History.setFilter('all')">全部</button>
                        <button data-status="completed" class="filter-btn" onclick="History.setFilter('completed')">已完成</button>
                        <button data-status="failed" class="filter-btn" onclick="History.setFilter('failed')">失败</button>
                        <button data-status="blocked" class="filter-btn" onclick="History.setFilter('blocked')">需介入</button>
                        <button data-status="running" class="filter-btn" onclick="History.setFilter('running')">运行中</button>
                    </div>
                    <div style="display:flex;gap:8px;width:100%;max-width:320px;">
                        <div class="input-field" style="display:flex;align-items:center;gap:8px;padding:0;flex:1;overflow:hidden;">
                            <svg style="width:16px;height:16px;color:#9CA3B0;margin-left:12px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                            </svg>
                            <input id="historySearch" type="text" placeholder="搜索任务..."
                                style="border:none;outline:none;flex:1;padding:8px 12px 8px 0;font-size:0.8125rem;background:transparent;"
                                oninput="History.setSearch(this.value)">
                        </div>
                        <button onclick="History.loadData()" class="btn-secondary" style="padding:8px 16px;font-size:0.8125rem;cursor:pointer;white-space:nowrap;">
                            刷新
                        </button>
                    </div>
                </div>
            </div>

            <!-- 列表 -->
            <div class="card" style="padding:0;overflow:hidden;">
                <div id="historyContent">
                    <div class="text-center py-12" style="color:#9CA3B0;font-size:0.8125rem;" id="historyLoading">加载中...</div>
                </div>

                <!-- 分页 -->
                <div id="pagination" class="hidden" style="padding:16px 24px;border-top:1px solid #F3F4F6;display:flex;align-items:center;justify-content:space-between;">
                    <span style="font-size:0.8125rem;color:#9CA3B0;" id="pageInfo"></span>
                    <div style="display:flex;gap:8px;">
                        <button id="prevPage" onclick="History.prevPage()" class="btn-ghost" style="padding:8px 16px;font-size:0.8125rem;cursor:pointer;">上一页</button>
                        <button id="nextPage" onclick="History.nextPage()" class="btn-ghost" style="padding:8px 16px;font-size:0.8125rem;cursor:pointer;">下一页</button>
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
            el.classList.toggle('active', el.dataset.status === status);
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
            content.innerHTML = '<div class="text-center py-12" style="color:#F87171;font-size:0.8125rem;">加载失败，请重试</div>';
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
            content.innerHTML = '<div class="text-center py-12" style="color:#9CA3B0;font-size:0.8125rem;">暂无匹配的历史记录</div>';
            pagination.classList.add('hidden');
            return;
        }

        const start = (this.currentPage - 1) * this.pageSize;
        const pageTasks = filtered.slice(start, start + this.pageSize);

        let html = '';
        pageTasks.forEach(t => {
            html += `
                <div class="history-item" onclick="History.toggleDetail(this, '${t.task_id}')">
                    <div style="display:flex;align-items:flex-start;gap:12px;">
                        <div style="flex-shrink:0;margin-top:1px;">${UI.statusBadge(t.status)}</div>
                        <div style="flex:1;min-width:0;">
                            <div style="font-size:0.8125rem;color:#2A2A33;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${UI.escapeHtml(t.request || '-')}</div>
                            <div style="font-size:0.75rem;color:#9CA3B0;margin-top:4px;">
                                <span>${UI.formatTime(t.created_at)}</span>
                                <span style="margin:0 4px;">·</span>
                                <span>${t.steps || 0} 步</span>
                                ${t.summary ? `<span style="margin:0 4px;">·</span><span style="color:#787A86;">${UI.escapeHtml(t.summary.slice(0, 80))}${t.summary.length > 80 ? '...' : ''}</span>` : ''}
                            </div>
                        </div>
                        <svg class="w-4 h-4 detail-arrow" style="color:#D1D5DB;margin-top:4px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                        </svg>
                    </div>
                    <div class="history-detail hidden" style="margin-top:12px;">
                        <div style="border-radius:20px;border:1px solid #E5E7EB;overflow:hidden;" id="detail-${t.task_id}">
                            <div class="text-center py-8" style="font-size:0.8125rem;color:#9CA3B0;">加载中...</div>
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
        document.getElementById('prevPage').style.opacity = this.currentPage <= 1 ? '0.3' : '1';
        document.getElementById('nextPage').style.opacity = this.currentPage >= totalPages ? '0.3' : '1';
        document.getElementById('prevPage').style.cursor = this.currentPage <= 1 ? 'not-allowed' : 'pointer';
        document.getElementById('nextPage').style.cursor = this.currentPage >= totalPages ? 'not-allowed' : 'pointer';
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
                        <div style="padding:12px 16px;background:#F7FAFF;display:flex;align-items:center;gap:16px;font-size:0.75rem;color:#787A86;">
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
                            html += `<div style="padding:14px 16px;">`;
                            html += `<div style="font-size:0.75rem;font-weight:600;color:#787A86;margin-bottom:8px;">步骤 ${stepNum}</div>`;

                            if (step.thought) {
                                html += `
                                <div style="margin-bottom:8px;">
                                    <div style="font-size:0.75rem;color:#9CA3B0;margin-bottom:4px;">💭 思考</div>
                                    <div class="markdown-body" style="font-size:0.8125rem;color:#2A2A33;">${History.renderMarkdown(step.thought)}</div>
                                </div>`;
                            }

                            if (step.tool_call) {
                                const tc = step.tool_call;
                                html += `
                                <div style="margin-bottom:8px;">
                                    <div style="font-size:0.75rem;color:#9CA3B0;margin-bottom:4px;">🔧 工具: <span style="font-family:monospace;color:#609FFF;">${UI.escapeHtml(tc.name)}</span></div>
                                    <details style="font-size:0.75rem;">
                                        <summary style="color:#9CA3B0;cursor:pointer;">查看参数</summary>
                                        <pre style="margin-top:4px;padding:8px;background:#F7FAFF;border-radius:14px;overflow-x:auto;">${UI.escapeHtml(JSON.stringify(tc.parameters, null, 2))}</pre>
                                    </details>
                                </div>`;

                                if (step.observation) {
                                    const obs = step.observation;
                                    const shortObs = obs.length > 500 ? obs.slice(0, 500) + '...' : obs;
                                    html += `
                                    <div style="margin-bottom:8px;">
                                        <div style="font-size:0.75rem;color:#9CA3B0;margin-bottom:4px;">📊 结果</div>
                                        <div class="markdown-body" style="font-size:0.8125rem;color:#2A2A33;max-height:160px;overflow-y:auto;">${History.renderMarkdown(obs)}</div>
                                    </div>`;
                                }
                            }

                            if (step.final_answer) {
                                html += `
                                <div style="margin-bottom:8px;">
                                    <div style="font-size:0.75rem;color:#5CB87A;margin-bottom:4px;">✅ 最终回答</div>
                                    <div class="markdown-body" style="font-size:0.8125rem;color:#2A2A33;">${History.renderMarkdown(step.final_answer)}</div>
                                </div>`;
                            }

                            html += `</div>`;
                        });
                    });

                    // 原始 JSON（折叠）
                    html += `
                        <div style="padding:12px 16px;background:#F7FAFF;border-top:1px solid #F3F4F6;">
                            <details>
                                <summary style="font-size:0.75rem;color:#9CA3B0;cursor:pointer;user-select:none;">查看原始数据</summary>
                                <pre style="margin-top:8px;font-size:0.6875rem;color:#787A86;overflow-x:auto;max-height:160px;overflow-y:auto;">${UI.escapeHtml(JSON.stringify({task_id: data.task_id, status: data.status, steps: data.steps, summary: data.summary, error: data.error}, null, 2))}</pre>
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
                    container.innerHTML = `<pre style="font-size:0.75rem;color:#787A86;padding:16px;overflow-x:auto;max-height:240px;overflow-y:auto;">${UI.escapeHtml(JSON.stringify(display, null, 2))}</pre>`;
                }
            } catch {
                container.innerHTML = '<div class="text-center py-8" style="font-size:0.8125rem;color:#F87171;">加载失败</div>';
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
