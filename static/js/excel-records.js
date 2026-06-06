/* ── Excel 数据记录页面 ── */
const ExcelRecords = {
    currentFile: '',

    render(container) {
        container.innerHTML = `
            <!-- 文件选择 -->
            <div class="card" style="margin-bottom:28px;">
                <div style="display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px;">
                    <div style="display:flex;align-items:center;gap:12px;flex:1;">
                        <svg style="width:20px;height:20px;color:#9CA3B0;flex-shrink:0;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                        </svg>
                        <span style="font-size:0.8125rem;font-weight:500;color:#2A2A33;white-space:nowrap;">选择表格</span>
                        <select id="excelFileSelect"
                            class="input-field"
                            style="flex:1;min-width:200px;padding:8px 14px;font-size:0.8125rem;"
                            onchange="ExcelRecords.onFileChange(this.value)">
                            <option value="">-- 请选择 --</option>
                        </select>
                        <button onclick="ExcelRecords.loadFiles()"
                            class="btn-secondary" style="display:flex;align-items:center;gap:6px;padding:8px 16px;font-size:0.8125rem;cursor:pointer;white-space:nowrap;">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                            </svg>
                            刷新
                        </button>
                    </div>
                    <span id="excelRecordCount" style="font-size:0.75rem;color:#9CA3B0;white-space:nowrap;"></span>
                </div>
            </div>

            <!-- 加载状态 -->
            <div id="excelLoading" class="hidden">
                <div style="display:flex;align-items:center;justify-content:center;padding:64px 0;">
                    <div style="display:flex;align-items:center;gap:12px;">
                        <div class="animate-spin rounded-full h-6 w-6" style="border:2px solid;border-color:#609FFF transparent transparent transparent;"></div>
                        <span style="font-size:0.8125rem;color:#787A86;">正在加载数据...</span>
                    </div>
                </div>
            </div>

            <!-- 空状态 -->
            <div id="excelEmpty" class="hidden">
                <div style="text-align:center;padding:64px 0;">
                    <svg style="width:48px;height:48px;color:#D1D5DB;margin:0 auto 12px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                    </svg>
                    <p style="color:#9CA3B0;font-size:0.8125rem;">请选择一个表格文件查看数据</p>
                </div>
            </div>

            <!-- 错误状态 -->
            <div id="excelError" class="hidden">
                <div style="display:flex;align-items:flex-start;gap:12px;padding:16px 20px;background:#FEF2F2;border-radius:20px;">
                    <svg class="w-5 h-5" style="color:#F87171;margin-top:2px;flex-shrink:0;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                    </svg>
                    <div>
                        <p style="font-weight:600;color:#991B1B;">加载失败</p>
                        <p style="color:#DC2626;font-size:0.8125rem;margin-top:4px;" id="excelErrorMessage"></p>
                    </div>
                </div>
            </div>

            <!-- 数据表格 -->
            <div id="excelTableContainer" class="hidden">
                <div class="table-container">
                    <div class="overflow-x-auto custom-scrollbar">
                        <table id="excelDataTable">
                            <thead id="excelTableHead">
                                <tr></tr>
                            </thead>
                            <tbody id="excelTableBody"></tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;

        // 加载文件列表
        document.getElementById('excelEmpty').classList.remove('hidden');
        this.loadFiles();
    },

    async loadFiles() {
        const select = document.getElementById('excelFileSelect');
        if (!select) return;
        const prevValue = this.currentFile;

        try {
            const data = await API.get('/api/excel/files');
            select.innerHTML = '<option value="">-- 请选择 --</option>';
            (data.files || []).forEach(f => {
                const opt = document.createElement('option');
                opt.value = f.name;
                opt.textContent = `${f.name} (${f.size_kb} KB)`;
                select.appendChild(opt);
            });
            // 恢复之前选中的文件
            if (prevValue && [...select.options].some(o => o.value === prevValue)) {
                select.value = prevValue;
            }
        } catch (e) {
            select.innerHTML = '<option value="">加载失败</option>';
        }
    },

    onFileChange(fileName) {
        if (!fileName) {
            this.currentFile = '';
            document.getElementById('excelTableContainer').classList.add('hidden');
            document.getElementById('excelLoading').classList.add('hidden');
            document.getElementById('excelError').classList.add('hidden');
            document.getElementById('excelEmpty').classList.remove('hidden');
            document.getElementById('excelRecordCount').textContent = '';
            return;
        }
        this.currentFile = fileName;
        this.loadData(fileName);
    },

    async loadData(fileName) {
        // 显示加载
        document.getElementById('excelEmpty').classList.add('hidden');
        document.getElementById('excelError').classList.add('hidden');
        document.getElementById('excelTableContainer').classList.add('hidden');
        document.getElementById('excelLoading').classList.remove('hidden');
        document.getElementById('excelRecordCount').textContent = '加载中...';

        try {
            const data = await API.get('/api/excel/read?file=' + encodeURIComponent(fileName));
            this.renderTable(data.columns || [], data.records || []);
            document.getElementById('excelLoading').classList.add('hidden');

            const count = data.total || (data.records || []).length;
            document.getElementById('excelRecordCount').textContent = `共 ${count} 条记录`;
        } catch (e) {
            document.getElementById('excelLoading').classList.add('hidden');
            document.getElementById('excelErrorMessage').textContent = e.message || '无法读取文件数据';
            document.getElementById('excelError').classList.remove('hidden');
            document.getElementById('excelRecordCount').textContent = '加载失败';
        }
    },

    renderTable(columns, records) {
        const thead = document.getElementById('excelTableHead');
        const tbody = document.getElementById('excelTableBody');

        // 表头
        let headerHtml = '';
        columns.forEach(col => {
            headerHtml += `<th>${UI.escapeHtml(col)}</th>`;
        });
        thead.innerHTML = headerHtml;

        // 数据行
        if (records.length === 0) {
            tbody.innerHTML = `<tr><td colspan="${columns.length || 1}" style="padding:48px 16px;text-align:center;color:#9CA3B0;font-size:0.8125rem;">暂无数据</td></tr>`;
        } else {
            let bodyHtml = '';
            records.forEach((row, idx) => {
                bodyHtml += `<tr style="transition:background 0.12s ease;">`;
                columns.forEach(col => {
                    const val = row[col] !== undefined && row[col] !== null ? String(row[col]) : '';
                    bodyHtml += `<td title="${UI.escapeHtml(val)}">${UI.escapeHtml(val) || '<span style="color:#D1D5DB;">-</span>'}</td>`;
                });
                bodyHtml += '</tr>';
            });
            tbody.innerHTML = bodyHtml;
        }

        // 显示表格
        document.getElementById('excelTableContainer').classList.remove('hidden');
    },
};
