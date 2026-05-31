/* ── Task Execute Page ── */
const TaskExecute = {
    pollingTimer: null,

    render(container) {
        container.innerHTML = `
            <!-- 任务输入 -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
                <h3 class="text-base font-semibold text-gray-900 mb-3">输入任务描述</h3>
                <div class="flex gap-3 items-start">
                    <textarea id="taskInput" rows="3"
                        class="flex-1 px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none text-sm"
                        placeholder="例如：处理最近收到的立项申请邮件..."></textarea>
                    <button id="executeBtn" onclick="TaskExecute.run()"
                        class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium shrink-0 flex items-center gap-2">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                        </svg>
                        执行
                    </button>
                </div>
                <p class="text-xs text-gray-400 mt-2">按 Ctrl+Enter 快速执行</p>
            </div>

            <!-- 快捷任务 -->
            <div class="mb-6">
                <div class="flex items-center justify-between mb-3">
                    <h3 class="text-base font-semibold text-gray-900">快捷任务</h3>
                    <span class="text-xs text-gray-400">点击即填，一键执行</span>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <button onclick="TaskExecute.quick('处理最近收到的立项申请邮件：读取邮件和附件中的立项申请书，提取活动信息填入荣誉活动立项汇总表，然后发送确认回复')"
                        class="group text-left p-4 bg-white rounded-xl border border-gray-100 hover:border-blue-200 hover:shadow-sm transition-all card-hover">
                        <div class="flex items-center gap-3">
                            <span class="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-xl shrink-0">📋</span>
                            <div>
                                <div class="font-medium text-gray-900">荣誉时数立项处理</div>
                                <div class="text-xs text-gray-400 mt-0.5">读取邮件 → 解析附件 → 填入汇总表 → 回复确认</div>
                            </div>
                        </div>
                    </button>
                    <button onclick="TaskExecute.quick('处理最近收到的志愿时数导入申请邮件：读取邮件和附件中的担保书，提取志愿者信息填入荣誉时数导入模板，然后发送确认回复')"
                        class="group text-left p-4 bg-white rounded-xl border border-gray-100 hover:border-green-200 hover:shadow-sm transition-all card-hover">
                        <div class="flex items-center gap-3">
                            <span class="w-10 h-10 rounded-lg bg-green-50 text-green-600 flex items-center justify-center text-xl shrink-0">⏰</span>
                            <div>
                                <div class="font-medium text-gray-900">志愿时数导入处理</div>
                                <div class="text-xs text-gray-400 mt-0.5">读取邮件 → 解析附件 → 填入时数模板 → 回复确认</div>
                            </div>
                        </div>
                    </button>
                </div>
            </div>

            <!-- 结果区域 -->
            <div id="resultArea" class="hidden">
                <!-- 进度条 -->
                <div id="progressBarContainer" class="w-full bg-gray-100 rounded-full h-1.5 mb-6 hidden">
                    <div class="progress-bar h-1.5 rounded-full" style="width: 100%"></div>
                </div>

                <!-- 结果卡片 -->
                <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                    <!-- 结果头部 -->
                    <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between flex-wrap gap-2">
                        <div class="flex items-center gap-3">
                            <h3 class="text-base font-semibold text-gray-900">执行结果</h3>
                            <span id="taskStatusBadge" class="hidden"></span>
                        </div>
                        <div class="flex items-center gap-4 text-xs text-gray-400" id="resultMeta">
                            <span id="taskIdLabel" class="hidden font-mono"></span>
                            <span id="taskStepsLabel" class="hidden"></span>
                            <span id="taskTimeLabel" class="hidden"></span>
                        </div>
                    </div>

                    <div class="p-6 space-y-4">
                        <!-- Loading State -->
                        <div id="loadingState" class="hidden">
                            <div class="flex items-center gap-4">
                                <div class="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent"></div>
                                <div>
                                    <p class="text-gray-700 font-medium">正在处理中...</p>
                                    <p class="text-gray-400 text-sm mt-0.5" id="loadingHint">Agent 正在读取邮件、解析附件、查询表格...</p>
                                </div>
                            </div>
                        </div>

                        <!-- Success State -->
                        <div id="successState" class="hidden">
                            <div class="flex items-start gap-3 p-4 bg-green-50 rounded-lg border border-green-100">
                                <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                </svg>
                                <div class="flex-1">
                                    <p class="font-medium text-green-800">任务已完成</p>
                                    <p class="text-green-600 text-sm mt-1" id="summaryText"></p>
                                </div>
                            </div>
                        </div>

                        <!-- Error State -->
                        <div id="errorState" class="hidden">
                            <div class="flex items-start gap-3 p-4 bg-red-50 rounded-lg border border-red-100">
                                <svg class="w-5 h-5 text-red-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                                </svg>
                                <div class="flex-1">
                                    <p class="font-medium text-red-800" id="errorTitle">执行出错</p>
                                    <p class="text-red-600 text-sm mt-1" id="errorMessage"></p>
                                </div>
                            </div>
                        </div>

                        <!-- Blocked State -->
                        <div id="blockedState" class="hidden">
                            <div class="flex items-start gap-3 p-4 bg-yellow-50 rounded-lg border border-yellow-100">
                                <svg class="w-5 h-5 text-yellow-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                                </svg>
                                <div class="flex-1">
                                    <p class="font-medium text-yellow-800">需要人工介入</p>
                                    <p class="text-yellow-600 text-sm mt-1" id="blockedReason"></p>
                                </div>
                            </div>
                        </div>

                        <!-- Step Timeline -->
                        <div id="stepTimeline" class="hidden">
                            <h4 class="text-sm font-semibold text-gray-700 mb-3">执行步骤</h4>
                            <div id="stepList" class="space-y-0"></div>
                        </div>

                        <!-- 详情折叠 -->
                        <div>
                            <button onclick="TaskExecute.toggleDetails()" class="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition-colors">
                                <svg id="detailArrow" class="w-4 h-4 detail-arrow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                                </svg>
                                查看详细数据
                            </button>
                            <div id="detailPanel" class="hidden mt-3">
                                <pre id="rawResult" class="text-sm text-gray-600 bg-gray-50 rounded-lg p-4 overflow-x-auto max-h-96 overflow-y-auto border border-gray-200 custom-scrollbar"></pre>
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
            const initData = await API.post('/api/tasks/execute', { request: text });
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
            completed: 'bg-green-100 text-green-700',
            failed: 'bg-red-100 text-red-700',
            blocked: 'bg-yellow-100 text-yellow-700',
        };
        const statusText = {
            completed: '✓ 已完成',
            failed: '✗ 失败',
            blocked: '⚠ 需人工介入',
        };

        const cls = statusClass[data.status] || 'bg-gray-100 text-gray-700';
        const txt = statusText[data.status] || data.status;
        badge.textContent = txt;
        badge.className = 'px-3 py-1 rounded-full text-sm font-medium ' + cls;

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
            document.getElementById('summaryText').textContent = data.summary || '任务已完成。';
            App.showToast('任务已完成', 'success');
        } else if (data.status === 'blocked') {
            document.getElementById('blockedReason').textContent = data.error || '需要人工审核处理';
            App.showToast('任务需要人工介入', 'info');
        } else if (data.status === 'failed') {
            document.getElementById('errorTitle').textContent = '任务执行失败';
            document.getElementById('errorMessage').textContent = data.error || '未知错误';
            App.showToast('任务执行失败', 'error');
        }

        // 步骤时间线
        if (data.steps && data.steps > 0) {
            const timeline = document.getElementById('stepTimeline');
            const stepList = document.getElementById('stepList');
            timeline.classList.remove('hidden');
            let html = '';
            for (let i = 1; i <= data.steps; i++) {
                const isLast = i === data.steps;
                html += `
                    <div class="step-line ${isLast ? '' : ''}">
                        <div class="step-dot"></div>
                        <div class="pb-4 text-sm">
                            <span class="text-gray-500">步骤 ${i}</span>
                            <span class="text-gray-300 mx-1">·</span>
                            <span class="text-gray-400">${data.status === 'completed' ? '完成' : data.status === 'failed' ? '失败' : '-'}</span>
                        </div>
                    </div>
                `;
            }
            stepList.innerHTML = html;
        }

        // 原始数据
        document.getElementById('rawResult').textContent = JSON.stringify(data, null, 2);
    },

    toggleDetails() {
        const panel = document.getElementById('detailPanel');
        const arrow = document.getElementById('detailArrow');
        panel.classList.toggle('hidden');
        arrow.classList.toggle('open');
    },
};
