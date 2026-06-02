/* ── Tools Page ── */
const Tools = {
    render(container) {
        container.innerHTML = `
            <div id="toolsContent">
                <div class="text-center py-12 text-gray-400">加载中...</div>
            </div>
        `;
        this.loadData();
    },

    async loadData() {
        const content = document.getElementById('toolsContent');
        try {
            const data = await API.get('/api/tools');
            const tools = data.tools || [];
            if (tools.length === 0) {
                content.innerHTML = '<div class="text-center py-12 text-gray-400">暂无可用工具</div>';
                return;
            }

            let html = '<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">';
            tools.forEach(t => {
                const desc = t.description || '无描述';
                const paramCount = t.parameters ? Object.keys(t.parameters).length : 0;
                html += `
                    <div class="tool-card bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:border-blue-200 hover:shadow-sm transition-all card-hover">
                        <div class="flex items-start gap-3 mb-3">
                            <div class="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                </svg>
                            </div>
                            <div class="flex-1 min-w-0">
                                <h4 class="text-sm font-semibold text-gray-900 truncate">${UI.escapeHtml(t.name)}</h4>
                                <p class="text-xs text-gray-500 mt-1 line-clamp-2">${UI.escapeHtml(desc)}</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-2 text-xs text-gray-400">
                            <span>参数: ${paramCount} 个</span>
                            <button onclick="Tools.toggleParams(this)" class="text-blue-600 hover:text-blue-700 ml-auto ${paramCount === 0 ? 'hidden' : ''}">
                                查看参数
                            </button>
                        </div>
                        <div class="tool-params hidden mt-3 pt-3 border-t border-gray-100">
                            <pre class="text-xs text-gray-600 bg-gray-50 rounded-lg p-3 overflow-x-auto max-h-40 overflow-y-auto custom-scrollbar">${UI.escapeHtml(JSON.stringify(t.parameters || {}, null, 2))}</pre>
                        </div>
                    </div>
                `;
            });
            html += '</div>';

            html += `
                <div class="mt-6 text-center">
                    <span class="text-sm text-gray-400">共 ${tools.length} 个可用工具</span>
                </div>
            `;

            content.innerHTML = html;

        } catch {
            content.innerHTML = '<div class="text-center py-12 text-red-400">加载工具列表失败</div>';
        }
    },

    toggleParams(btn) {
        const params = btn.closest('.tool-card').querySelector('.tool-params');
        params.classList.toggle('hidden');
        btn.textContent = params.classList.contains('hidden') ? '查看参数' : '收起参数';
    },
};
