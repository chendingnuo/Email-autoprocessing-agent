/* ── Dashboard Page ── */
const Dashboard = {
    async render(container) {
        container.innerHTML = `
            <!-- 状态卡片 -->
            <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
                <div class="stat-card bg-white rounded-xl shadow-sm p-5 border border-gray-100">
                    <div class="flex items-center justify-between mb-3">
                        <div class="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                            </svg>
                        </div>
                        <span id="healthDot" class="w-2.5 h-2.5 rounded-full bg-gray-300"></span>
                    </div>
                    <div class="text-sm text-gray-500">系统状态</div>
                    <div class="text-lg font-semibold mt-1 text-gray-900" id="dashHealthText">检查中...</div>
                </div>
                <div class="stat-card bg-white rounded-xl shadow-sm p-5 border border-gray-100">
                    <div class="flex items-center justify-between mb-3">
                        <div class="w-9 h-9 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                            </svg>
                        </div>
                    </div>
                    <div class="text-sm text-gray-500">可用工具</div>
                    <div class="text-lg font-semibold mt-1 text-gray-900" id="dashToolCount">-</div>
                </div>
                <div class="stat-card bg-white rounded-xl shadow-sm p-5 border border-gray-100">
                    <div class="flex items-center justify-between mb-3">
                        <div class="w-9 h-9 rounded-lg bg-cyan-50 text-cyan-600 flex items-center justify-center">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                            </svg>
                        </div>
                    </div>
                    <div class="text-sm text-gray-500">模型</div>
                    <div class="text-lg font-semibold mt-1 text-gray-900" id="dashModelName">-</div>
                </div>
                <div class="stat-card bg-white rounded-xl shadow-sm p-5 border border-gray-100">
                    <div class="flex items-center justify-between mb-3">
                        <div class="w-9 h-9 rounded-lg bg-green-50 text-green-600 flex items-center justify-center">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                            </svg>
                        </div>
                    </div>
                    <div class="text-sm text-gray-500">邮箱账号</div>
                    <div class="text-lg font-semibold mt-1 text-gray-900" id="dashAccountCount">-</div>
                </div>
                <div class="stat-card bg-white rounded-xl shadow-sm p-5 border border-gray-100">
                    <div class="flex items-center justify-between mb-3">
                        <div class="w-9 h-9 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                            </svg>
                        </div>
                    </div>
                    <div class="text-sm text-gray-500">历史任务</div>
                    <div class="text-lg font-semibold mt-1 text-gray-900" id="dashHistoryCount">-</div>
                </div>
            </div>

            <!-- 快捷操作 -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                <div class="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                    <h3 class="text-base font-semibold text-gray-900 mb-4">快捷操作</h3>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <a href="#/execute" class="group p-4 bg-blue-50 rounded-xl border border-blue-100 hover:border-blue-300 transition-all" onclick="event.preventDefault(); window.location.hash='#/execute'">
                            <div class="flex items-center gap-3">
                                <span class="w-10 h-10 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center text-lg">📋</span>
                                <div>
                                    <div class="font-medium text-gray-900">荣誉时数立项处理</div>
                                    <div class="text-xs text-gray-500 mt-0.5">读取邮件 → 解析附件 → 填入汇总表 → 回复确认</div>
                                </div>
                            </div>
                        </a>
                        <a href="#/execute" class="group p-4 bg-green-50 rounded-xl border border-green-100 hover:border-green-300 transition-all" onclick="event.preventDefault(); window.location.hash='#/execute'">
                            <div class="flex items-center gap-3">
                                <span class="w-10 h-10 rounded-lg bg-green-100 text-green-600 flex items-center justify-center text-lg">⏰</span>
                                <div>
                                    <div class="font-medium text-gray-900">志愿时数导入处理</div>
                                    <div class="text-xs text-gray-500 mt-0.5">读取邮件 → 解析附件 → 填入时数模板 → 回复确认</div>
                                </div>
                            </div>
                        </a>
                    </div>
                </div>

                <!-- 最近活动 -->
                <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-base font-semibold text-gray-900">最近活动</h3>
                        <a href="#/history" class="text-xs text-blue-600 hover:text-blue-700" onclick="window.location.hash='#/history'">查看全部 →</a>
                    </div>
                    <div id="recentActivity">
                        <div class="text-center py-6 text-gray-400 text-sm">加载中...</div>
                    </div>
                </div>
            </div>
        `;

        this.loadStats();
        this.loadRecentActivity();
    },

    async loadStats() {
        try {
            const health = await API.get('/api/health');
            const el = document.getElementById('dashHealthText');
            const dot = document.getElementById('healthDot');
            if (health.status === 'ok') {
                el.textContent = health.warnings?.length ? `运行中 (${health.warnings.length}项警告)` : '正常运行';
                el.className = 'text-lg font-semibold mt-1 text-green-600';
                dot.className = 'w-2.5 h-2.5 rounded-full bg-green-500';
            }
        } catch { /* will show default */ }

        try {
            const tools = await API.get('/api/tools');
            document.getElementById('dashToolCount').textContent = tools.tools.length + ' 个';
        } catch {}

        try {
            // 模型名从 health 里没有就直接显示配置默认
            document.getElementById('dashModelName').textContent = 'qwen-plus';
        } catch {}

        try {
            const accounts = await API.get('/api/accounts');
            const el = document.getElementById('dashAccountCount');
            el.textContent = accounts.total + ' 个';
            if (accounts.total > 0) el.className = 'text-lg font-semibold mt-1 text-green-600';
        } catch {}

        try {
            const history = await API.get('/api/tasks/history?limit=1');
            document.getElementById('dashHistoryCount').textContent = history.total + ' 条';
        } catch {}
    },

    async loadRecentActivity() {
        try {
            const data = await API.get('/api/tasks/history?limit=5');
            const container = document.getElementById('recentActivity');
            if (!data.tasks || data.tasks.length === 0) {
                container.innerHTML = '<div class="text-center py-6 text-gray-400 text-sm">暂无历史记录</div>';
                return;
            }
            let html = '<div class="space-y-3">';
            data.tasks.forEach(t => {
                html += `
                    <div class="flex items-start gap-2 text-sm cursor-pointer hover:bg-gray-50 rounded-lg p-2 -mx-2 transition-colors" onclick="window.location.hash='#/history'">
                        <div class="shrink-0 mt-0.5">${UI.statusBadge(t.status)}</div>
                        <div class="flex-1 min-w-0">
                            <div class="text-gray-900 truncate">${UI.escapeHtml(t.request || '-')}</div>
                            <div class="text-xs text-gray-400 mt-0.5">${UI.formatTime(t.created_at)}</div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        } catch {
            document.getElementById('recentActivity').innerHTML =
                '<div class="text-center py-6 text-gray-400 text-sm">加载失败</div>';
        }
    },
};
