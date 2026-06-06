/* ── Dashboard Page ── */
const Dashboard = {
    async render(container) {
        container.innerHTML = `
            <!-- 状态卡片 -->
            <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4" style="margin-bottom:28px;">
                <div class="stat-card">
                    <div class="flex items-center justify-between" style="margin-bottom:14px;">
                        <div class="w-10 h-10" style="border-radius:16px;background:#E9F9ED;color:#86D997;display:flex;align-items:center;justify-content:center;">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                            </svg>
                        </div>
                        <span id="healthDot" class="w-2.5 h-2.5 rounded-full" style="background:#9CA3B0"></span>
                    </div>
                    <div style="font-size:0.8125rem;color:#787A86;">系统状态</div>
                    <div style="font-size:22px;font-weight:700;margin-top:6px;color:#2A2A33;" id="dashHealthText">检查中...</div>
                </div>
                <div class="stat-card">
                    <div class="flex items-center justify-between" style="margin-bottom:14px;">
                        <div class="w-10 h-10" style="border-radius:16px;background:#F0EFFF;color:#8B7FFF;display:flex;align-items:center;justify-content:center;">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                            </svg>
                        </div>
                    </div>
                    <div style="font-size:0.8125rem;color:#787A86;">可用工具</div>
                    <div style="font-size:22px;font-weight:700;margin-top:6px;color:#2A2A33;" id="dashToolCount">-</div>
                </div>
                <div class="stat-card">
                    <div class="flex items-center justify-between" style="margin-bottom:14px;">
                        <div class="w-10 h-10" style="border-radius:16px;background:#E8F1FF;color:#609FFF;display:flex;align-items:center;justify-content:center;">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                            </svg>
                        </div>
                    </div>
                    <div style="font-size:0.8125rem;color:#787A86;">模型</div>
                    <div style="font-size:22px;font-weight:700;margin-top:6px;color:#2A2A33;" id="dashModelName">-</div>
                </div>
                <div class="stat-card">
                    <div class="flex items-center justify-between" style="margin-bottom:14px;">
                        <div class="w-10 h-10" style="border-radius:16px;background:#E9F9ED;color:#86D997;display:flex;align-items:center;justify-content:center;">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                            </svg>
                        </div>
                    </div>
                    <div style="font-size:0.8125rem;color:#787A86;">邮箱账号</div>
                    <div style="font-size:22px;font-weight:700;margin-top:6px;color:#2A2A33;" id="dashAccountCount">-</div>
                </div>
                <div class="stat-card">
                    <div class="flex items-center justify-between" style="margin-bottom:14px;">
                        <div class="w-10 h-10" style="border-radius:16px;background:#FFF3E0;color:#FFB74D;display:flex;align-items:center;justify-content:center;">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                            </svg>
                        </div>
                    </div>
                    <div style="font-size:0.8125rem;color:#787A86;">历史任务</div>
                    <div style="font-size:22px;font-weight:700;margin-top:6px;color:#2A2A33;" id="dashHistoryCount">-</div>
                </div>
            </div>

            <!-- 快捷操作 + 最近活动 -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6" style="margin-bottom:28px;">
                <div class="lg:col-span-2 card">
                    <h3 style="font-size:1rem;font-weight:600;color:#2A2A33;margin-bottom:18px;">快捷操作</h3>
                    <div class="grid grid-cols-1 sm:grid-cols-2" style="gap:14px;">
                        <a href="#/execute" class="quick-card-blue p-4 transition-all" onclick="event.preventDefault(); window.location.hash='#/execute'">
                            <div class="flex items-center gap-3">
                                <span class="w-10 h-10 flex items-center justify-center text-lg" style="border-radius:14px;background:rgba(96,159,255,0.2);color:#609FFF;">📋</span>
                                <div>
                                    <div style="font-weight:600;color:#2A2A33;">荣誉时数立项处理</div>
                                    <div style="font-size:0.75rem;color:#787A86;margin-top:4px;">读取邮件 → 解析附件 → 填入汇总表 → 回复确认</div>
                                </div>
                            </div>
                        </a>
                        <a href="#/execute" class="quick-card-green p-4 transition-all" onclick="event.preventDefault(); window.location.hash='#/execute'">
                            <div class="flex items-center gap-3">
                                <span class="w-10 h-10 flex items-center justify-center text-lg" style="border-radius:14px;background:rgba(134,217,151,0.25);color:#86D997;">⏰</span>
                                <div>
                                    <div style="font-weight:600;color:#2A2A33;">志愿时数导入处理</div>
                                    <div style="font-size:0.75rem;color:#787A86;margin-top:4px;">读取邮件 → 解析附件 → 填入时数模板 → 回复确认</div>
                                </div>
                            </div>
                        </a>
                    </div>
                </div>

                <!-- 最近活动 -->
                <div class="card">
                    <div class="flex items-center justify-between" style="margin-bottom:18px;">
                        <h3 style="font-size:1rem;font-weight:600;color:#2A2A33;">最近活动</h3>
                        <a href="#/history" style="font-size:0.8125rem;color:#609FFF;" onclick="window.location.hash='#/history'">查看全部 →</a>
                    </div>
                    <div id="recentActivity">
                        <div class="text-center py-6" style="font-size:0.8125rem;color:#9CA3B0;">加载中...</div>
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
                el.style.color = '#86D997';
                dot.style.background = '#86D997';
            }
        } catch { /* will show default */ }

        try {
            const tools = await API.get('/api/tools');
            document.getElementById('dashToolCount').textContent = tools.tools.length + ' 个';
        } catch {}

        try {
            const health = await API.get('/api/health');
            const modelName = health?.llm?.model || 'qwen-plus';
            document.getElementById('dashModelName').textContent = modelName;
        } catch {}

        try {
            const accounts = await API.get('/api/accounts');
            const el = document.getElementById('dashAccountCount');
            el.textContent = accounts.total + ' 个';
            if (accounts.total > 0) el.style.color = '#86D997';
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
                container.innerHTML = '<div class="text-center py-6" style="font-size:0.8125rem;color:#9CA3B0;">暂无历史记录</div>';
                return;
            }
            let html = '<div style="display:flex;flex-direction:column;gap:10px;">';
            data.tasks.forEach(t => {
                html += `
                    <div style="display:flex;align-items:flex-start;gap:12px;padding:12px 14px;border-radius:20px;background:#F7FAFF;cursor:pointer;transition:background 0.15s;" onclick="window.location.hash='#/history'" onmouseover="this.style.background='#F0F7FF'" onmouseout="this.style.background='#F7FAFF'">
                        <div style="flex-shrink:0;margin-top:1px;">${UI.statusBadge(t.status)}</div>
                        <div style="flex:1;min-width:0;">
                            <div style="color:#2A2A33;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:0.8125rem;">${UI.escapeHtml(t.request || '-')}</div>
                            <div style="font-size:0.75rem;color:#9CA3B0;margin-top:4px;">${UI.formatTime(t.created_at)}</div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        } catch {
            document.getElementById('recentActivity').innerHTML =
                '<div class="text-center py-6" style="font-size:0.8125rem;color:#9CA3B0;">加载失败</div>';
        }
    },
};
