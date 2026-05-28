"""
任务编排器
=========
连接配置、框架、工具三者，提供面向使用者的统一入口。
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from typing import Any, Optional

from config import AppConfig, PROVIDER_PRESETS, load_email_accounts
from framework.engine import ReActEngine
from framework.llm_client import TongyiQianwenClient, OpenAIClient
from framework.logger import setup_logger
from framework.models import TaskContext, TaskStatus
from framework.security import SecurityManager
from framework.state_manager import StateManager
from framework.tool_registry import ToolRegistry, get_registry, tool

from tools.email_tools import EmailTools
from tools.excel_tools import ExcelTools
from tools.doc_tools import DocTools

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    任务编排器。
    封装完整的初始化流程，对外暴露简单的 execute() 接口。
    """

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig()
        self._setup_logging()

        # 多邮箱账号实例表
        self._email_instances: dict[str, Any] = {}

        # 初始化各组件
        self.security = SecurityManager()
        self.tools = self._init_tools()
        self.state = StateManager(
            storage_dir=self.config.engine.storage_dir
        )
        self.llm = self._init_llm()
        self.engine = self._init_engine()

        # 注册工具到ReAct引擎
        self._register_tools()

        logger.info("编排器初始化完成")

        # 打印配置警告
        warnings = self.config.validate()
        if warnings:
            for w in warnings:
                logger.warning(f"配置警告: {w}")

    def execute(self, user_request: str, **kwargs) -> dict[str, Any]:
        """
        执行一个任务的完整流程（同步，直接返回结果）。
        """
        try:
            self.security.sanitize_user_input(user_request)
        except Exception as e:
            return {
                "status": "blocked",
                "error": str(e),
                "task_id": None,
            }
        ctx = self.engine.run(user_request, **kwargs)
        return self._format_result(ctx)

    def execute_async(self, user_request: str) -> str:
        """
        异步执行任务，立即返回 task_id。
        """
        try:
            self.security.sanitize_user_input(user_request)
        except Exception as e:
            ctx = self.state.create_context(user_request)
            ctx.status = TaskStatus.FAILED
            ctx.error = str(e)
            ctx.summary = f"安全拦截: {e}"
            self.state.save_context(ctx)
            return ctx.task_id

        ctx = self.state.create_context(user_request)
        thread = threading.Thread(
            target=self._run_async,
            args=(ctx,),
            daemon=True,
        )
        thread.start()
        return ctx.task_id

    def _run_async(self, ctx: TaskContext) -> None:
        """后台线程执行体"""
        try:
            self.engine.run(
                user_request=ctx.user_request,
                context=ctx,
            )
        except Exception as e:
            ctx.status = TaskStatus.FAILED
            ctx.error = f"{type(e).__name__}: {e}"
            import traceback
            ctx.summary = traceback.format_exc()[:500]
            self.state.save_context(ctx)

    def get_result(self, task_id: str) -> dict[str, Any]:
        return self._get_task_result(task_id)

    def get_status(self, task_id: str) -> dict[str, Any]:
        return self._get_task_result(task_id)

    def _get_task_result(self, task_id: str) -> dict[str, Any]:
        ctx = self.state.get_context(task_id)
        if not ctx:
            ctx = self.state.load_context(task_id)
        if ctx:
            return self._format_result(ctx)
        return {"status": "not_found"}

    def resume(self, task_id: str) -> dict[str, Any]:
        """恢复一个中断的任务"""
        ctx = self.engine.resume(task_id)
        if ctx:
            return self._format_result(ctx)
        return {"status": "not_found", "error": f"任务 {task_id} 不存在"}

    def list_email_accounts(self) -> list[dict[str, str]]:
        """列出所有已配置的邮箱账号"""
        result = []
        for name, inst in self._email_instances.items():
            result.append({
                "name": name,
                "email": inst.email_account,
                "configured": bool(inst.imap_server and inst.email_account),
            })
        return result

    # ── 内部初始化 ─────────────────────────────────────

    def _setup_logging(self) -> None:
        setup_logger(
            name="agent",
            level=getattr(logging, self.config.engine.log_level.upper(), logging.INFO),
            log_file=self.config.engine.log_file,
        )

    def _init_llm(self):
        cfg = self.config.llm
        if cfg.provider == "tongyi":
            return TongyiQianwenClient(
                api_key=cfg.api_key,
                model=cfg.model,
                base_url=cfg.base_url,
                timeout=cfg.timeout,
                max_retries=cfg.max_retries,
            )
        else:
            base_url = cfg.base_url
            if cfg.provider == "deepseek" and "deepseek" not in base_url:
                base_url = "https://api.deepseek.com/v1"
            return OpenAIClient(
                api_key=cfg.api_key,
                model=cfg.model,
                base_url=base_url,
                timeout=cfg.timeout,
                max_retries=cfg.max_retries,
            )

    def _init_tools(self):
        """初始化所有业务工具，并构建多邮箱实例表"""
        # 构建多邮箱实例
        all_accounts = load_email_accounts(self.config.data_dir)

        for acct_name, acct_cfg in all_accounts.items():
            inst = EmailTools(
                imap_server=acct_cfg.imap_server,
                imap_port=acct_cfg.imap_port,
                smtp_server=acct_cfg.smtp_server,
                smtp_port=acct_cfg.smtp_port,
                email_account=acct_cfg.email,
                email_password=acct_cfg.password,
            )
            self._email_instances[acct_name] = inst
            logger.info(
                f"邮箱账号已加载: [{acct_name}] {acct_cfg.email} ({acct_cfg.provider})"
            )

        default_inst = self._email_instances.get("default")

        return {
            "email": default_inst,
            "excel": ExcelTools(default_dir=self.config.data_dir),
            "doc": DocTools(template_dir=os.path.join(self.config.data_dir, "templates")),
        }

    def _init_engine(self):
        return ReActEngine(
            llm_client=self.llm,
            security_manager=self.security,
            state_manager=self.state,
            max_steps=self.config.engine.max_steps,
            deadlock_threshold=self.config.engine.deadlock_threshold,
        )

    def _register_tools(self):
        """将业务工具注册到ReAct引擎的工具注册中心"""
        tool_registry = self.engine.tools

        default_email = self.tools["email"]
        excel_tools = self.tools["excel"]
        doc_tools = self.tools["doc"]

        # ── 构建可用邮箱列表 ───────────────────────────
        account_list_str = ", ".join(
            f"{name}({inst.email_account})"
            for name, inst in self._email_instances.items()
        )

        def _email_dispatch(account, method_name, *args, **kwargs):
            inst = self._email_instances.get(account) or default_email
            if inst is None:
                return json.dumps({
                    "status": "error",
                    "message": f"邮箱 '{account}' 未配置。可用邮箱: {account_list_str}",
                }, ensure_ascii=False)
            method = getattr(inst, method_name)
            return method(*args, **kwargs)

        # ── 邮件工具 ───────────────────────────────────

        tool_registry.register_from_callable(
            name="email_read",
            description=(
                "读取指定邮箱收件箱中的邮件（含附件）。"
                "优先读取未读邮件，如果没有未读邮件则自动返回最近的邮件。"
                "返回邮件列表，包含发件人、主题、正文预览、附件信息（文件名和保存路径）。"
                "如有附件（.docx），附件保存在 saved_path 字段中，可后续调用 doc_parse_attachment 解析。\n\n"
                f"可用邮箱: {account_list_str}\n"
                "account 参数指定用哪个邮箱读取，不传则使用默认邮箱。"
            ),
            fn=lambda account="default", limit=10: _email_dispatch(
                account, "read_unread", limit=limit
            ),
        )

        tool_registry.register_from_callable(
            name="email_reply_draft",
            description=(
                "生成回复邮件并保存到草稿箱。"
                "根据 account 参数决定用哪个邮箱回复（默认用主邮箱）。"
                "参数mail_id是原邮件ID，subject是回复主题，content是回复正文。\n\n"
                "根据处理结果生成回复内容：\n"
                " - 立项处理成功：回复确认收到立项申请，告知已登记\n"
                " - 志愿时数导入成功：回复确认时数已登记\n"
                " - 发现重复：回复告知已收到过相同申请，无需重复提交\n\n"
                "保存后需人工登录对应邮箱审核发送。\n\n"
                f"可用邮箱: {account_list_str}"
            ),
            fn=lambda account="default", mail_id="", subject="", content="": _email_dispatch(
                account, "reply_draft", mail_id=mail_id, subject=subject, content=content
            ),
        )

        # ── Excel工具 ──────────────────────────────────

        tool_registry.register_from_callable(
            name="excel_list_files",
            description=(
                "列出 data/ 目录下所有可用的 Excel 表格文件。请在操作文件前先调用此工具查看有哪些可用文件。"
                "当前主要表格：荣誉活动立项汇总表.xlsx（立项登记）、志愿者荣誉时数-志愿者编号导入模板.xls（志愿时数导入）。"
            ),
            fn=lambda: excel_tools.list_files(),
        )

        tool_registry.register_from_callable(
            name="excel_get_schema",
            description=(
                "获取指定Excel表格的结构（列名、行数等）。"
                "参数excel_path是文件名（不需要 data/ 前缀）。"
                "注意：荣誉活动立项汇总表.xlsx 的标题在第1行、表头在第2行，请使用 header_row=1；"
                "志愿者荣誉时数导入模板.xls 的标题在第1行、说明在第2行、表头在第3行，请使用 header_row=2。"
            ),
            fn=lambda excel_path, header_row=0: excel_tools.get_schema(
                file_path=excel_path, header_row=header_row
            ),
        )

        tool_registry.register_from_callable(
            name="excel_check_duplicate",
            description=(
                "在指定表格中检查是否存在重复记录（根据关键字段匹配）。"
                "参数excel_path是文件名，fields是待匹配的字段-值字典。"
                "例如：检查立项表中是否已有同名的活动，fields={'活动名称': '校园清洁'}。"
                "返回 duplicate_found 或 no_duplicate。"
                "重要：立项申请请始终使用 excel_path='荣誉活动立项汇总表.xlsx'，不要使用 test_output.xlsx 或其他测试文件。"
            ),
            fn=lambda excel_path, fields, header_row=0: excel_tools.check_duplicate(
                file_path=excel_path, fields=fields, header_row=header_row
            ),
        )

        tool_registry.register_from_callable(
            name="excel_insert_record",
            description=(
                "在指定的本地登记表格末尾追加一条记录。"
                "参数excel_path是文件名（不需要 data/ 前缀），record是包含字段键值对的字典。"
                "参数 dedup_fields 是可选的用于去重的字段列表。"
                "如果提供 dedup_fields，插入前会自动检查这些字段是否已存在相同记录。"
                "如出现重复会返回 duplicate 状态，需要告知发件人。"
                "插入成功后请调用 email_reply_draft 发送确认回复。"
                "注意：荣誉活动立项汇总表.xlsx 使用 header_row=1；志愿者荣誉时数导入模板.xls 使用 header_row=2。"
                "重要：立项申请请始终使用 excel_path='荣誉活动立项汇总表.xlsx'，不要使用 test_output.xlsx 或其他测试文件。"
            ),
            fn=lambda excel_path, record, dedup_fields=None, header_row=0: excel_tools.insert_record(
                file_path=excel_path, record=record,
                dedup_fields=dedup_fields, header_row=header_row
            ),
        )

        tool_registry.register_from_callable(
            name="excel_query_records",
            description="在指定表格中按条件查询记录。参数excel_path是文件名，field是查询字段，value是查询值。",
            fn=lambda excel_path, field, value: excel_tools.query_records(
                file_path=excel_path, field=field, value=value
            ),
        )

        # ── 文档解析工具 ──────────────────────────────

        tool_registry.register_from_callable(
            name="doc_parse_attachment",
            description=(
                "解析Word附件(.docx)，提取其中的文本段落、表格数据和表单字段。"
                "参数 file_path 是邮件附件保存的绝对路径（来自 email_read 返回的 saved_path 字段）。"
                "返回文档的段落内容、表格结构、以及提取的字段-值对。"
                "用于解析立项申请书或担保书等Word文档附件。"
            ),
            fn=lambda file_path: doc_tools.parse_attachment(file_path=file_path),
        )

        # ── 文档生成工具 ──────────────────────────────

        tool_registry.register_from_callable(
            name="doc_render_template",
            description="基于标准模板生成Word行政公文。参数template_path是模板路径，output_path是输出路径，variables是替换变量字典。",
            fn=lambda template_path, output_path, variables: doc_tools.render_template(
                template_path=template_path,
                output_path=output_path,
                variables=variables,
            ),
            require_confirmation=True,
        )

        logger.info(f"已注册 {len(tool_registry.list_tools())} 个工具")

    @staticmethod
    def _format_result(ctx: TaskContext) -> dict[str, Any]:
        return {
            "task_id": ctx.task_id,
            "status": ctx.status.value,
            "steps": ctx.current_step_count,
            "summary": ctx.summary or "",
            "error": ctx.error,
            "extracted_data": ctx.extracted_data,
            "created_at": ctx.created_at.isoformat(),
            "completed_at": ctx.completed_at.isoformat() if ctx.completed_at else None,
        }


# ── 快捷入口 ─────────────────────────────────────────

def create_orchestrator(config_path: str = "") -> Orchestrator:
    """便捷工厂函数"""
    config = AppConfig.from_file(config_path) if config_path else AppConfig()
    return Orchestrator(config)
