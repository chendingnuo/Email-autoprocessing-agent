/* ── Excel 数据记录页面 ── */
const ExcelRecords = {
    currentFile: '',

    render(container) {
        container.innerHTML = `
            <!-- 文件选择 -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 mb-6">
                <div class="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
                    <div class="flex items-center gap-3 w-full sm:w-auto">
                        <svg class="w-5 h-5 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                        </svg>
                        <span class="text-sm font-medium text-gray-700">选择表格</span>
                        <select id="excelFileSelect"
                            class="flex-1 sm:flex-none text-sm border border-gray-200 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none bg-white min-w-[240px]"
                            onchange="ExcelRecords.onFileChange(this.value)">
                            <option value="">-- 请选择 --</option>
                        </select>
                        <button onclick="ExcelRecords.loadFiles()"
                            class="px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors border border-blue-100 flex items-center gap-1.5">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                            </svg>
                            刷新
                        </button>
                    </div>
                    <span id="excelRecordCount" class="text-xs text-gray-400"></span>
                </div>
            </div>

            <!-- 加载状态 -->
            <div id="excelLoading" class="hidden">
                <div class="flex items-center justify-center py-16">
                    <div class="flex items-center gap-3">
                        <div class="animate-spin rounded-full h-6 w-6 border-2 border-blue-500 border-t-transparent"></div>
                        <span class="text-sm text-gray-500">正在加载数据...</span>
                    </div>
                </div>
            </div>

            <!-- 空状态 -->
            <div id="excelEmpty" class="hidden">
                <div class="text-center py-16">
                    <svg class="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                    </svg>
                    <p class="text-gray-400 text-sm">请选择一个表格文件查看数据</p>
                </div>
            </div>

            <!-- 错误状态 -->
            <div id="excelError" class="hidden">
                <div class="flex items-start gap-3 p-4 bg-red-50 rounded-lg border border-red-100">
                    <svg class="w-5 h-5 text-red-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                    </svg>
                    <div>
                        <p class="font-medium text-red-800">加载失败</p>
                        <p class="text-red-600 text-sm mt-1" id="excelErrorMessage"></p>
                    </div>
                </div>
            </div>

            <!-- 数据表格 -->
            <div id="excelTableContainer" class="hidden">
                <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                    <div class="overflow-x-auto custom-scrollbar">
                        <table class="w-full text-sm" id="excelDataTable">
                            <thead id="excelTableHead">
                                <tr class="bg-gray-50 border-b border-gray-100"></tr>
                            </thead>
                            <tbody id="excelTableBody" class="divide-y divide-gray-50"></tbody>
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
            headerHtml += `<th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">${UI.escapeHtml(col)}</th>`;
        });
        thead.innerHTML = headerHtml;

        // 数据行
        if (records.length === 0) {
            tbody.innerHTML = `<tr><td colspan="${columns.length || 1}" class="px-4 py-12 text-center text-gray-400">暂无数据</td></tr>`;
        } else {
            let bodyHtml = '';
            records.forEach((row, idx) => {
                bodyHtml += `<tr class="${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'} hover:bg-blue-50/50 transition-colors">`;
                columns.forEach(col => {
                    const val = row[col] !== undefined && row[col] !== null ? String(row[col]) : '';
                    bodyHtml += `<td class="px-4 py-2.5 text-sm text-gray-700 whitespace-nowrap max-w-[300px] truncate" title="${UI.escapeHtml(val)}">${UI.escapeHtml(val) || '<span class="text-gray-300">-</span>'}</td>`;
                });
                bodyHtml += '</tr>';
            });
            tbody.innerHTML = bodyHtml;
        }

        // 显示表格
        document.getElementById('excelTableContainer').classList.remove('hidden');
    },
};
