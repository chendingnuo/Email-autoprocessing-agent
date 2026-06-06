/* ── Task Execute Page ── */
const TaskExecute = {
    pollingTimer: null,

    render(container) {
        container.innerHTML = `
            <!-- 任务输入 -->
            <div class="card" style="margin-bottom:28px;">
                <h3 style="font-size:1rem;font-weight:600;color:#2A2A33;margin-bottom:16px;">输入任务描述</h3>
                <div style="display:flex;gap:12px;align-items:flex-start;">
                    <textarea id="taskInput" rows="3"
                        class="input-field"
                        style="flex:1;resize:none;min-height:80px;"
                        placeholder="例如：处理最近收到的立项申请邮件..."></textarea>
                    <div style="flex-shrink:0;display:flex;flex-direction:column;gap:8px;">
                        <button id="executeBtn" onclick="TaskExecute.run()"
                            class="btn-primary"
                            style="padding:12px 28px;display:flex;align-items:center;gap:8px;font-weight:500;border:none;cursor:pointer;">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                            </svg>
                            执行
                        </button>
                    </div>
                </div>
                <!-- 邮箱选择行 -->
                <div style="display:flex;align-items:center;gap:12px;margin-top:16px;padding-top:16px;border-top:1px solid #F3F4F6;">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <svg class="w-4 h-4" style="color:#9CA3B0;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                        </svg>
                        <span style="font-size:0.8125rem;color:#787A86;">使用邮箱:</span>
                    </div>
                    <select id="emailAccountSelect" class="input-field" style="padding:6px 12px;font-size:0.8125rem;min-width:160px;">
                        <option value="">自动选择（默认）</option>
                    </select>
                    <span style="font-size:0.75rem;color:#9CA3B0;">选中的邮箱会作为指令传递给 Agent</span>
                </div>
                <p style="font-size:0.75rem;color:#9CA3B0;margin-top:8px;">按 Ctrl+Enter 快速执行</p>
            </div>

            <!-- 快捷任务 -->
            <div style="margin-bottom:28px;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
                    <h3 style="font-size:1rem;font-weight:600;color:#2A2A33;">快捷任务</h3>
                    <span style="font-size:0.75rem;color:#9CA3B0;">点击即填，一键执行</span>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2" style="gap:14px;">
                    <button onclick="TaskExecute.quick('处理最近收到的立项申请邮件：读取邮件和附件中的立项申请书，提取活动信息填入荣誉活动立项汇总表，然后发送确认回复')"
                        class="card-sub card-hover"
                        style="background:var(--card-bg);padding:18px;text-align:left;border:1px solid transparent;cursor:pointer;">
                        <div style="display:flex;align-items:center;gap:14px;">
                            <span style="width:42px;height:42px;border-radius:14px;background:#E8F1FF;color:#609FFF;display:flex;align-items:center;justify-content:center;font-size:1.25rem;flex-shrink:0;">📋</span>
                            <div>
                                <div style="font-weight:600;color:#2A2A33;">荣誉时数立项处理</div>
                                <div style="font-size:0.75rem;color:#787A86;margin-top:4px;">读取邮件 → 解析附件 → 填入汇总表 → 回复确认</div>
                            </div>
                        </div>
                    </button>
                    <button onclick="TaskExecute.quick('处理最近收到的志愿时数导入申请邮件：读取邮件和附件中的担保书，提取志愿者信息填入荣誉时数导入模板，然后发送确认回复')"
                        class="card-sub card-hover"
                        style="background:var(--card-bg);padding:18px;text-align:left;border:1px solid transparent;cursor:pointer;">
                        <div style="display:flex;align-items:center;gap:14px;">
                            <span style="width:42px;height:42px;border-radius:14px;background:#E9F9ED;color:#86D997;display:flex;align-items:center;justify-content:center;font-size:1.25rem;flex-shrink:0;">⏰</span>
                            <div>
                                <div style="font-weight:600;color:#2A2A33;">志愿时数导入处理</div>
                                <div style="font-size:0.75rem;color:#787A86;margin-top:4px;">读取邮件 → 解析附件 → 填入时数模板 → 回复确认</div>
                            </div>
                        </div>
                    </button>
                </div>
            </div>

            <!-- 结果区域 -->
            <div id="resultArea" class="hidden">
                <!-- 进度条 -->
                <div id="progressBarContainer" class="w-full" style="background:#F3F4F6;border-radius:999px;height:6px;margin-bottom:28px;overflow:hidden;">
                    <div class="progress-bar" style="height:6px;width:100%;border-radius:999px;"></div>
                </div>

                <!-- 结果卡片 -->
                <div class="card" style="overflow:hidden;padding:0;">
                    <!-- 结果头部 -->
                    <div style="padding:18px 24px;border-bottom:1px solid #F3F4F6;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
                        <div style="display:flex;align-items:center;gap:12px;">
                            <h3 style="font-size:1rem;font-weight:600;color:#2A2A33;">执行结果</h3>
                            <span id="taskStatusBadge" class="hidden"></span>
                        </div>
                        <div style="display:flex;align-items:center;gap:16px;font-size:0.75rem;color:#9CA3B0;" id="resultMeta">
                            <span id="taskIdLabel" class="hidden" style="font-family:monospace;"></span>
                            <span id="taskStepsLabel" class="hidden"></span>
                            <span id="taskTimeLabel" class="hidden"></span>
                        </div>
                    </div>

                    <div style="padding:24px;display:flex;flex-direction:column;gap:16px;">
                        <!-- Loading State -->
                        <div id="loadingState" class="hidden">
                            <div style="display:flex;align-items:center;gap:16px;">
                                <div class="animate-spin rounded-full h-8 w-8" style="border:2px solid;border-color:#609FFF transparent transparent transparent;"></div>
                                <div>
                                    <p style="color:#2A2A33;font-weight:500;">正在处理中...</p>
                                    <p style="color:#787A86;font-size:0.8125rem;margin-top:4px;" id="loadingHint">Agent 正在读取邮件、解析附件、查询表格...</p>
                                </div>
                            </div>
                        </div>

                        <!-- Success State -->
                        <div id="successState" class="hidden">
                            <div style="display:flex;align-items:flex-start;gap:12px;padding:16px 20px;background:#E9F9ED;border-radius:20px;">
                                <svg class="w-5 h-5" style="color:#86D997;margin-top:2px;flex-shrink:0;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                </svg>
                                <div style="flex:1;">
                                    <p style="font-weight:600;color:#2A2A33;">任务已完成</p>
                                    <div style="color:#5CB87A;font-size:0.8125rem;margin-top:4px;" class="markdown-body" id="summaryText"></div>
                                </div>
                            </div>
                        </div>

                        <!-- Error State -->
                        <div id="errorState" class="hidden">
                            <div style="display:flex;align-items:flex-start;gap:12px;padding:16px 20px;background:#FEF2F2;border-radius:20px;">
                                <svg class="w-5 h-5" style="color:#F87171;margin-top:2px;flex-shrink:0;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                                </svg>
                                <div style="flex:1;">
                                    <p style="font-weight:600;color:#991B1B;" id="errorTitle">执行出错</p>
                                    <p style="color:#DC2626;font-size:0.8125rem;margin-top:4px;" id="errorMessage"></p>
                                </div>
                            </div>
                        </div>

                        <!-- Blocked State -->
                        <div id="blockedState" class="hidden">
                            <div style="display:flex;align-items:flex-start;gap:12px;padding:16px 20px;background:#FFFBEB;border-radius:20px;">
                                <svg class="w-5 h-5" style="color:#FBBF24;margin-top:2px;flex-shrink:0;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                                </svg>
                                <div style="flex:1;">
                                    <p style="font-weight:600;color="#92400E;">需要人工介入</p>
                                    <p style="color:#B45309;font-size:0.8125rem;margin-top:4px;" id="blockedReason"></p>
                                </div>
                            </div>
                        </div>

                        <!-- Step Timeline -->
                        <div id="stepTimeline" class="hidden">
                            <h4 style="font-size:0.8125rem;font-weight:600;color:#787A86;margin-bottom:14px;">执行步骤</h4>
                            <div id="stepList" style="display:flex;flex-direction:column;gap:0;"></div>
                        </div>

                        <!-- 详情折叠 -->
                        <div>
                            <button onclick="TaskExecute.toggleDetails()" class="btn-ghost" style="display:flex;align-items:center;gap:8px;padding:8px 16px;cursor:pointer;">
                                <svg id="detailArrow" class="w-4 h-4 detail-arrow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                                </svg>
                                查看详细数据
                            </button>
                            <div id="detailPanel" class="hidden" style="margin-top:12px;">
                                <pre id="rawResult" class="custom-scrollbar" style="font-size:0.8125rem;color:#787A86;background:#F7FAFF;border-radius:20px;padding:16px;overflow-x:auto;max-height:384px;overflow-y:auto;border:1px solid #E5E7EB;"></pre>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 键盘快捷键
        const input = document.getElementById('taskInput');
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                this.run();
            }
        });

        // 加载邮箱列表到下拉框
        this.loadAccounts();
    },

    async loadAccounts() {
        try {
            const data = await API.get('/api/accounts');
            const select = document.getElementById('emailAccountSelect');
            if (!select) return;
            // 保留第一个 option（自动选择），清空其余
            select.innerHTML = '<option value="">自动选择（默认）</option>';
            (data.accounts || []).forEach(acc => {
                if (!acc.configured) return;
                const opt = document.createElement('option');
                opt.value = acc.name;
                opt.textContent = `${acc.name} (${acc.email})`;
                select.appendChild(opt);
            });
        } catch (e) {
            // 静默失败，不影响主功能
        }
    },

    quick(text) {
        document.getElementById('taskInput').value = text;
        this.run();
    },

    async run() {
        const text = document.getElementById('taskInput').value.trim();
        if (!text) return;

        // 重置 UI
        ['loadingState', 'errorState', 'successState', 'blockedState', 'stepTimeline', 'progressBarContainer'].forEach(id => {
            document.getElementById(id).classList.add('hidden');
        });
        document.getElementById('detailPanel').classList.add('hidden');
        document.getElementById('detailArrow').classList.remove('open');
        document.getElementById('resultMeta').querySelectorAll('span').forEach(s => s.classList.add('hidden'));
        document.getElementById('taskStatusBadge').classList.add('hidden');
        document.getElementById('resultArea').classList.remove('hidden');
        document.getElementById('loadingState').classList.remove('hidden');
        document.getElementById('progressBarContainer').classList.remove('hidden');
        document.getElementById('executeBtn').disabled = true;
        document.getElementById('executeBtn').classList.add('opacity-50', 'cursor-not-allowed');

        try {
            // 提交任务
            const account = document.getElementById('emailAccountSelect')?.value || '';
            const body = { request: text };
            if (account) body.account = account;
            const initData = await API.post('/api/tasks/execute', body);
            const taskId = initData.task_id;

            const idLabel = document.getElementById('taskIdLabel');
            idLabel.textContent = 'ID: ' + taskId;
            idLabel.classList.remove('hidden');
            idLabel.title = '点击复制';
            idLabel.style.cursor = 'pointer';
            idLabel.onclick = () => {
                navigator.clipboard.writeText(taskId).then(() => {
                    App.showToast('任务 ID 已复制', 'success');
                });
            };

            // 轮询
            let data;
            while (true) {
                await new Promise(r => setTimeout(r, 800));
                data = await API.get('/api/tasks/' + taskId);

                // 更新步骤数
                if (data.steps !== undefined) {
                    const stepsLabel = document.getElementById('taskStepsLabel');
                    stepsLabel.textContent = data.steps + ' 步';
                    stepsLabel.classList.remove('hidden');
                }

                if (data.status !== 'running') break;
            }

            this.displayResult(data);

        } catch (e) {
            document.getElementById('progressBarContainer').classList.add('hidden');
            document.getElementById('loadingState').classList.add('hidden');
            App.showToast('请求失败: ' + e.message, 'error');
        } finally {
            document.getElementById('executeBtn').disabled = false;
            document.getElementById('executeBtn').classList.remove('opacity-50', 'cursor-not-allowed');
        }

        // 刷新历史计数
        try {
            const hist = await API.get('/api/tasks/history?limit=1');
            document.getElementById('dashHistoryCount') && (document.getElementById('dashHistoryCount').textContent = hist.total + ' 条');
        } catch {}
    },

    displayResult(data) {
        document.getElementById('progressBarContainer').classList.add('hidden');
        document.getElementById('loadingState').classList.add('hidden');

        // 状态徽章
        const badge = document.getElementById('taskStatusBadge');
        badge.className = '';
        badge.innerHTML = '';
        badge.classList.remove('hidden');

        const statusClass = {
            completed: 'badge badge-success',
            failed: 'badge badge-error',
            blocked: 'badge badge-warning',
        };
        const statusText = {
            completed: '✓ 已完成',
            failed: '✗ 失败',
            blocked: '⚠ 需人工介入',
        };

        const cls = statusClass[data.status] || 'badge badge-muted';
        const txt = statusText[data.status] || data.status;
        badge.textContent = txt;
        badge.className = cls;

        // 步骤数
        if (data.steps !== undefined) {
            const stepsLabel = document.getElementById('taskStepsLabel');
            stepsLabel.textContent = data.steps + ' 步';
            stepsLabel.classList.remove('hidden');
        }

        // 时间
        const timeLabel = document.getElementById('taskTimeLabel');
        timeLabel.textContent = UI.formatTime(data.created_at) + ' → ' + UI.formatTime(data.completed_at);
        timeLabel.classList.remove('hidden');

        // 状态内容
        document.getElementById('successState').classList.toggle('hidden', data.status !== 'completed');
        document.getElementById('blockedState').classList.toggle('hidden', data.status !== 'blocked');
        document.getElementById('errorState').classList.toggle('hidden', data.status !== 'failed');

        if (data.status === 'completed') {
            document.getElementById('summaryText').innerHTML = this.renderMarkdown(data.summary || '任务已完成。');
            App.showToast('任务已完成', 'success');
        } else if (data.status === 'blocked') {
            document.getElementById('blockedReason').textContent = data.error || '需要人工审核处理';
            App.showToast('任务需要人工介入', 'info');
        } else if (data.status === 'failed') {
            document.getElementById('errorTitle').textContent = '任务执行失败';
            document.getElementById('errorMessage').textContent = data.error || '未知错误';
            App.showToast('任务执行失败', 'error');
        }

        // 步骤详情
        if (data.step_details && data.step_details.length > 0) {
            const timeline = document.getElementById('stepTimeline');
            const stepList = document.getElementById('stepList');
            timeline.classList.remove('hidden');

            let stepNum = 0;
            let html = '';
            data.step_details.forEach((turn) => {
                turn.steps.forEach((step) => {
                    stepNum++;
                    const isFinalWithAnswer = !!step.final_answer;
                    const isToolCall = !!step.tool_call;
                    html += `<div class="step-card" style="border-radius:20px;">`;

                    // ── 步骤标题栏 ──
                    const headerBg = isFinalWithAnswer ? 'background:#E9F9ED;' : 'background:#F7FAFF;';
                    html += `<div style="${headerBg}padding:10px 18px;border-bottom:1px solid #E5E7EB;display:flex;align-items:center;gap:8px;">
                        <span style="width:24px;height:24px;border-radius:999px;background:#E8F1FF;color:#609FFF;display:flex;align-items:center;justify-content:center;font-size:0.6875rem;font-weight:700;">${stepNum}</span>
                        <span style="font-size:0.75rem;font-weight:600;color:#787A86;">执行步骤 ${stepNum}</span>
                        ${isFinalWithAnswer ? '<span style="margin-left:auto;font-size:0.6875rem;padding:2px 10px;border-radius:999px;background:rgba(134,217,151,0.18);color:#5CB87A;font-weight:500;">最终回答</span>' : ''}
                    </div>`;

                    // ── LLM 思考 ──
                    if (step.thought) {
                        html += `
                        <div class="step-card-body" style="border-bottom:1px solid #F3F4F6;">
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                                <span style="font-size:0.8125rem;">💭</span>
                                <span style="font-size:0.6875rem;font-weight:500;color:#9CA3B0;text-transform:uppercase;letter-spacing:0.03em;">LLM 思考</span>
                            </div>
                            <div class="markdown-body" style="font-size:0.8125rem;color:#2A2A33;">
                                ${this.renderMarkdown(step.thought)}
                            </div>
                        </div>`;
                    }

                    // ── 工具调用 ──
                    if (step.tool_call) {
                        const tc = step.tool_call;
                        const isError = tc.status === 'failure' || tc.status === 'error';
                        const isBlocked = tc.status === 'blocked';
                        const bg = isError ? '#FEF2F2' : isBlocked ? '#FFFBEB' : '#FFFFFF';

                        html += `
                        <div style="background:${bg};padding:12px 18px;border-bottom:1px solid #F3F4F6;">
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                                <span style="font-size:0.8125rem;">🔧</span>
                                <span style="font-size:0.6875rem;font-weight:500;color:#9CA3B0;text-transform:uppercase;letter-spacing:0.03em;">工具调用</span>
                                <span style="margin-left:auto;font-size:0.6875rem;padding:2px 10px;border-radius:999px;font-family:monospace;${isError ? 'background:rgba(248,113,113,0.15);color:#DC2626;' : isBlocked ? 'background:rgba(251,191,36,0.18);color:#B45309;' : 'background:rgba(96,159,255,0.15);color:#609FFF;'}">${UI.escapeHtml(tc.name)}</span>
                            </div>
                            <details style="font-size:0.8125rem;">
                                <summary style="color:#9CA3B0;cursor:pointer;font-size:0.75rem;user-select:none;">📋 查看参数</summary>
                                <pre style="margin-top:8px;padding:8px;background:#F7FAFF;border-radius:14px;font-size:0.6875rem;overflow-x:auto;">${UI.escapeHtml(JSON.stringify(tc.parameters, null, 2))}</pre>
                            </details>
                            ${tc.error ? `<div style="margin-top:6px;font-size:0.75rem;color:#DC2626;">${UI.escapeHtml(tc.error)}</div>` : ''}
                        </div>`;

                        // ── 执行结果 ──
                        if (step.observation) {
                            const obs = step.observation;
                            const isLong = obs.length > 800;
                            html += `
                            <div class="step-card-body" style="border-bottom:1px solid #F3F4F6;">
                                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                                    <span style="font-size:0.8125rem;">📊</span>
                                    <span style="font-size:0.6875rem;font-weight:500;color:#9CA3B0;text-transform:uppercase;letter-spacing:0.03em;">执行结果</span>
                                </div>
                                <div class="markdown-body observation-content ${isLong ? 'observation-truncated' : ''}" style="font-size:0.8125rem;color:#2A2A33;">
                                    ${this.renderMarkdown(obs)}
                                </div>
                                ${isLong ? '<button class="mt-1 observation-toggle" style="font-size:0.75rem;color:#609FFF;border:none;background:none;cursor:pointer;" onclick="this.previousElementSibling.classList.toggle(\'observation-truncated\'); this.textContent = this.previousElementSibling.classList.contains(\'observation-truncated\') ? \'展开全部 ▼\' : \'收起 ▲\'">展开全部 ▼</button>' : ''}
                            </div>`;
                        }
                    }

                    // ── 最终回答 ──
                    if (step.final_answer) {
                        html += `
                        <div class="step-card-body" style="background:#E9F9ED;">
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                                <span style="font-size:0.8125rem;">✅</span>
                                <span style="font-size:0.6875rem;font-weight:500;color:#5CB87A;text-transform:uppercase;letter-spacing:0.03em;">最终回答</span>
                            </div>
                            <div class="markdown-body" style="font-size:0.8125rem;color:#2A2A33;">
                                ${this.renderMarkdown(step.final_answer)}
                            </div>
                        </div>`;
                    }

                    html += `</div>`;
                });
            });

            stepList.innerHTML = html;
        }

        // 原始数据
        const rawDisplay = { ...data };
        // step_details 保留在原始数据中以便调试
        document.getElementById('rawResult').textContent = JSON.stringify(rawDisplay, null, 2);
    },

    renderMarkdown(text) {
        if (!text) return '';
        if (typeof marked !== 'undefined' && marked.parse) {
            return marked.parse(text, { breaks: true });
        }
        // 降级：纯文本
        return '<pre class="text-sm whitespace-pre-wrap">' + UI.escapeHtml(text) + '</pre>';
    },

    toggleDetails() {
        const panel = document.getElementById('detailPanel');
        const arrow = document.getElementById('detailArrow');
        panel.classList.toggle('hidden');
        arrow.classList.toggle('open');
    },
};
