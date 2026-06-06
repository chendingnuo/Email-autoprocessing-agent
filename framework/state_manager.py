"""
状态管理器
=========
负责任务上下文的维护、滑动窗口摘要生成、以及任务状态持久化。
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Optional

from .models import TaskContext, TaskStatus

logger = logging.getLogger(__name__)


class StateManager:
    """
    状态管理器。
    管理任务上下文的生命周期：创建、更新、摘要、持久化。
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self._contexts: dict[str, TaskContext] = {}
        self.storage_dir = storage_dir
        if storage_dir:
            os.makedirs(storage_dir, exist_ok=True)

    # ── 上下文管理 ─────────────────────────────────────

    def create_context(self, user_request: str, **kwargs) -> TaskContext:
        """创建新的任务上下文"""
        ctx = TaskContext(user_request=user_request, **kwargs)
        ctx.status = TaskStatus.RUNNING
        self._contexts[ctx.task_id] = ctx
        logger.info(f"[{ctx.task_id}] 任务已创建: {user_request[:80]}...")
        return ctx

    def get_context(self, task_id: str) -> Optional[TaskContext]:
        """获取任务上下文"""
        return self._contexts.get(task_id)

    def update_context(self, ctx: TaskContext) -> None:
        """更新任务上下文"""
        self._contexts[ctx.task_id] = ctx
        self._persist(ctx)

    def save_context(self, ctx: TaskContext) -> None:
        """保存任务上下文（兼容 orchestrator 的调用）"""
        self.update_context(ctx)

    def complete_context(
        self, ctx: TaskContext, summary: str = "", error: Optional[str] = None
    ) -> TaskContext:
        """完成任务上下文"""
        ctx.status = TaskStatus.COMPLETED if not error else TaskStatus.FAILED
        ctx.completed_at = datetime.now()
        ctx.error = error
        if summary:
            ctx.summary = summary
        self.update_context(ctx)
        logger.info(
            f"[{ctx.task_id}] 任务{'完成' if not error else '失败'}: "
            f"共 {ctx.current_step_count} 步"
        )
        return ctx

    def block_context(self, ctx: TaskContext, reason: str) -> TaskContext:
        """将任务标记为需要人工介入"""
        ctx.status = TaskStatus.BLOCKED
        ctx.error = reason
        self.update_context(ctx)
        logger.warning(f"[{ctx.task_id}] 任务需人工介入: {reason}")
        return ctx

    # ── 滑动窗口摘要 ───────────────────────────────────

    def generate_summary(self, ctx: TaskContext) -> str:
        """
        生成历史步骤的轻量摘要。
        用于滑动窗口策略：保留关键业务数据，丢弃冗余执行细节。
        """
        parts = []
        # 关键业务数据（通过 data_store 保存的）
        if ctx.extracted_data:
            parts.append(f"已提取数据: {json.dumps(ctx.extracted_data, ensure_ascii=False)}")
        # 已完成的步骤概览
        if ctx.current_step_count > 0:
            parts.append(f"已完成 {ctx.current_step_count} 步执行")
        # 已处理的邮件
        processed_ids = ctx.metadata.get("processed_email_ids", [])
        if processed_ids:
            parts.append(f"已处理邮件: {', '.join(str(e) for e in processed_ids)}")
        # 已执行过的工具列表（去重）
        used_tools = ctx.metadata.get("used_tools", [])
        if used_tools:
            parts.append(f"已使用工具: {', '.join(used_tools)}")
        # 最近一次工具调用
        if ctx.last_tool_call:
            status = "成功" if ctx.last_tool_call.status.name == "SUCCESS" else "失败"
            parts.append(
                f"最后操作: {ctx.last_tool_call.tool_name}"
                f"({status})"
            )
        parts.append(f"任务目标: {ctx.user_request[:100]}")
        return " | ".join(parts) if parts else ctx.user_request[:100]

    def apply_sliding_window(self, ctx: TaskContext) -> None:
        """
        对上下文应用滑动窗口策略：
        1. 更新摘要（将历史压缩为轻量摘要）
        2. 保留最近3轮完整交互
        """
        if len(ctx.conversation_history) > 5:
            ctx.summary = self.generate_summary(ctx)
            # 保留最近5轮完整交互（给复杂任务更多上下文）
            ctx.conversation_history = ctx.conversation_history[-5:]

    # ── 持久化 ─────────────────────────────────────────

    def _persist(self, ctx: TaskContext) -> None:
        """持久化任务上下文到磁盘"""
        if not self.storage_dir:
            return
        try:
            path = os.path.join(self.storage_dir, f"{ctx.task_id}.json")
            data = {
                "task_id": ctx.task_id,
                "user_request": ctx.user_request,
                "status": ctx.status.value,
                "current_step_count": ctx.current_step_count,
                "summary": ctx.summary,
                "extracted_data": ctx.extracted_data,
                "error": ctx.error,
                "created_at": ctx.created_at.isoformat(),
                "completed_at": ctx.completed_at.isoformat() if ctx.completed_at else None,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"持久化任务 {ctx.task_id} 失败: {e}")

    def load_context(self, task_id: str) -> Optional[TaskContext]:
        """从磁盘恢复任务上下文"""
        if not self.storage_dir:
            return None
        path = os.path.join(self.storage_dir, f"{task_id}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ctx = TaskContext(
                task_id=data["task_id"],
                user_request=data["user_request"],
                status=TaskStatus(data["status"]),
                current_step_count=data["current_step_count"],
                summary=data.get("summary", ""),
                extracted_data=data.get("extracted_data", {}),
                error=data.get("error"),
                created_at=datetime.fromisoformat(data["created_at"]),
                completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            )
            self._contexts[task_id] = ctx
            return ctx
        except Exception as e:
            logger.warning(f"恢复任务 {task_id} 失败: {e}")
            return None

    def list_task_summaries(self, limit: int = 20) -> tuple[list[dict], int]:
        """
        列出最近的已完成任务摘要列表（用于前端历史记录）。

        Args:
            limit: 最大返回条数

        Returns:
            tuple: (按创建时间降序排列的任务摘要列表, 总任务数)
        """
        if not self.storage_dir or not os.path.exists(self.storage_dir):
            return [], 0

        summaries = []
        try:
            for filename in os.listdir(self.storage_dir):
                if not filename.endswith(".json"):
                    continue
                path = os.path.join(self.storage_dir, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    summaries.append({
                        "task_id": data.get("task_id", ""),
                        "request": data.get("user_request", "")[:100] + ("..." if len(data.get("user_request", "")) > 100 else ""),
                        "status": data.get("status", "unknown"),
                        "steps": data.get("current_step_count", 0),
                        "summary": data.get("summary", "")[:200],
                        "error": data.get("error", ""),
                        "created_at": data.get("created_at", ""),
                        "completed_at": data.get("completed_at", ""),
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"列出历史任务失败: {e}")

        total = len(summaries)

        # 按 created_at 降序排列（ISO 8601 字符串可直接比较）
        summaries.sort(
            key=lambda s: s.get("created_at") or "",
            reverse=True,
        )
        return summaries[:limit], total
