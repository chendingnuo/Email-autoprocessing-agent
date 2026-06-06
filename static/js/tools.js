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
                content.innerHTML = '<div class="text-center py-12" style="color:#9CA3B0;font-size:0.8125rem;">暂无可用工具</div>';
                return;
            }

            let html = '<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">';
            tools.forEach(t => {
                const desc = t.description || '无描述';
                const paramCount = t.parameters ? Object.keys(t.parameters).length : 0;
                html += `
                    <div class="tool-card">
                        <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:14px;">
                            <div style="width:40px;height:40px;border-radius:14px;background:#E8F1FF;color:#609FFF;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                </svg>
                            </div>
                            <div style="flex:1;min-width:0;">
                                <h4 style="font-size:0.8125rem;font-weight:600;color:#2A2A33;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${UI.escapeHtml(t.name)}</h4>
                                <p style="font-size:0.75rem;color:#787A86;margin-top:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">${UI.escapeHtml(desc)}</p>
                            </div>
                        </div>
                        <div style="display:flex;align-items:center;gap:8px;font-size:0.75rem;color:#9CA3B0;">
                            <span>参数: ${paramCount} 个</span>
                            <button onclick="Tools.toggleParams(this)" class="${paramCount === 0 ? 'hidden' : ''}" style="color:#609FFF;margin-left:auto;border:none;background:none;cursor:pointer;font-size:0.75rem;">
                                查看参数
                            </button>
                        </div>
                        <div class="tool-params hidden" style="margin-top:12px;padding-top:12px;border-top:1px solid #F3F4F6;">
                            <pre class="custom-scrollbar" style="font-size:0.75rem;color:#787A86;background:#F7FAFF;border-radius:16px;padding:12px;overflow-x:auto;max-height:160px;overflow-y:auto;">${UI.escapeHtml(JSON.stringify(t.parameters || {}, null, 2))}</pre>
                        </div>
                    </div>
                `;
            });
            html += '</div>';

            html += `
                <div class="mt-6 text-center">
                    <span style="font-size:0.8125rem;color:#9CA3B0;">共 ${tools.length} 个可用工具</span>
                </div>
            `;

            content.innerHTML = html;

        } catch {
            content.innerHTML = '<div class="text-center py-12" style="color:#F87171;font-size:0.8125rem;">加载工具列表失败</div>';
        }
    },

    toggleParams(btn) {
        const params = btn.closest('.tool-card').querySelector('.tool-params');
        params.classList.toggle('hidden');
        btn.textContent = params.classList.contains('hidden') ? '查看参数' : '收起参数';
    },
};
