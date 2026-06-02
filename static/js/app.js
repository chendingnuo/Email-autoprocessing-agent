/* ── App Core ── */
const App = {
    currentPage: 'dashboard',

    init() {
        this.initRouter();
        this.initSidebar();
        this.loadSidebarStatus();
        this.initToast();
    },

    // ── Router ──
    initRouter() {
        window.addEventListener('hashchange', () => this.route());
        // 初始路由
        if (!window.location.hash || window.location.hash === '#/') {
            window.location.hash = '#/dashboard';
        } else {
            this.route();
        }
    },

    route() {
        const hash = window.location.hash.replace('#/', '') || 'dashboard';
        const page = hash.split('?')[0];
        this.switchPage(page);
    },

    switchPage(page) {
        this.currentPage = page;

        // 更新侧边栏
        document.querySelectorAll('.nav-link').forEach(el => {
            el.classList.toggle('active', el.dataset.page === page);
        });

        // 页面标题
        const titles = {
            dashboard: ['仪表盘', '系统概览与状态监控'],
            execute: ['任务执行', '提交自然语言任务让Agent自动处理'],
            history: ['执行日志', '查看所有任务的执行历史'],
            'excel-records': ['数据记录', '查看 Excel 表格数据'],
            tools: ['工具管理', '查看Agent可用的所有工具'],
        };
        const [title, subtitle] = titles[page] || ['未知页面', ''];
        document.getElementById('pageTitle').textContent = title;
        document.getElementById('pageSubtitle').textContent = subtitle;

        // 渲染页面
        const container = document.getElementById('pageContainer');
        switch (page) {
            case 'dashboard': Dashboard.render(container); break;
            case 'execute': TaskExecute.render(container); break;
            case 'history': History.render(container); break;
            case 'excel-records': ExcelRecords.render(container); break;
            case 'tools': Tools.render(container); break;
            default: container.innerHTML = '<p class="text-gray-400">页面不存在</p>';
        }
    },

    // ── Sidebar ──
    initSidebar() {
        document.querySelectorAll('.nav-link').forEach(el => {
            el.addEventListener('click', (e) => {
                // hashchange 事件会处理页面切换
            });
        });
    },

    async loadSidebarStatus() {
        try {
            const data = await API.get('/api/health');
            const dot = document.getElementById('sidebarStatus');
            const text = document.getElementById('sidebarStatusText');
            if (data.status === 'ok') {
                dot.className = 'w-2 h-2 rounded-full bg-green-500';
                text.textContent = data.warnings?.length ? `运行中 (${data.warnings.length}项警告)` : '系统正常';
                text.className = 'text-sm text-green-600';
            }
        } catch {
            document.getElementById('sidebarStatus').className = 'w-2 h-2 rounded-full bg-red-400';
            document.getElementById('sidebarStatusText').textContent = '无法连接';
            document.getElementById('sidebarStatusText').className = 'text-sm text-red-400';
        }
    },

    // ── Toast ──
    initToast() {
        this.toastTimer = null;
    },

    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        const icon = document.getElementById('toastIcon');
        const msg = document.getElementById('toastMessage');

        const icons = {
            success: '<svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
            error: '<svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>',
            info: '<svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
        };

        icon.innerHTML = icons[type] || icons.info;
        msg.textContent = message;
        toast.classList.remove('hidden');
        toast.style.transform = 'translateX(120%)';
        toast.style.transition = 'transform 0.3s ease';
        requestAnimationFrame(() => { toast.style.transform = 'translateX(0)'; });

        clearTimeout(this.toastTimer);
        this.toastTimer = setTimeout(() => this.hideToast(), 4000);
    },

    hideToast() {
        const toast = document.getElementById('toast');
        toast.style.transform = 'translateX(120%)';
        setTimeout(() => toast.classList.add('hidden'), 300);
    },
};

// ── API 工具 ──
const API = {
    async get(url) {
        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return resp.json();
    },
    async post(url, body) {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return resp.json();
    },
};

// ── 通用UI工具 ──
const UI = {
    formatTime(isoStr) {
        if (!isoStr) return '-';
        try {
            const d = new Date(isoStr);
            return d.toLocaleString('zh-CN', {
                month: '2-digit', day: '2-digit',
                hour: '2-digit', minute: '2-digit',
            });
        } catch { return isoStr; }
    },

    formatFullTime(isoStr) {
        if (!isoStr) return '-';
        try {
            const d = new Date(isoStr);
            return d.toLocaleString('zh-CN', {
                year: 'numeric', month: '2-digit', day: '2-digit',
                hour: '2-digit', minute: '2-digit', second: '2-digit',
            });
        } catch { return isoStr; }
    },

    statusBadge(status) {
        const map = {
            completed: '<span class="status-badge bg-green-100 text-green-700">✓ 已完成</span>',
            failed: '<span class="status-badge bg-red-100 text-red-700">✗ 失败</span>',
            blocked: '<span class="status-badge bg-yellow-100 text-yellow-700">⚠ 需人工介入</span>',
            running: '<span class="status-badge bg-blue-100 text-blue-700">● 运行中</span>',
        };
        return map[status] || `<span class="status-badge bg-gray-100 text-gray-700">${status}</span>`;
    },

    escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },
};

// ── 启动 ──
document.addEventListener('DOMContentLoaded', () => App.init());
