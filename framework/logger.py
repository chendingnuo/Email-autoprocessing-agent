"""
日志配置模块
===========
统一的日志配置，支持控制台输出、系统级文件日志、以及每个任务的完整对话记录。
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# ── 系统级日志 ─────────────────────────────────────────


def setup_logger(
    name: str = "agent",
    level: int = logging.INFO,
    log_file: str | None = None,
    format_string: str | None = None,
) -> logging.Logger:
    """
    配置并返回根日志记录器，使所有模块的 logger.info/warning/error
    都能正常输出到控制台和日志文件。

    关键设计：将 handler 挂载到根 logger (""），利用 Python logger 层次
    传播机制，让 framework.engine、tools.email_tools 等子 logger 的
    消息都能被捕获。
    """
    fmt = format_string or (
        "[%(asctime)s] %(levelname)-8s | %(name)s | %(message)s"
    )
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    root = logging.getLogger()
    root.setLevel(level)

    # 避免重复添加 handler（但允许后续调用追加文件 handler）
    has_console = any(
        isinstance(h, logging.StreamHandler) and h.stream == sys.stdout
        for h in root.handlers
    )
    has_file = any(isinstance(h, logging.FileHandler) for h in root.handlers)

    # 控制台输出（只加一次）
    if not has_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    # 文件输出（可选，允许后续调用添加）
    if log_file and not has_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    return root


# 全局缺省日志配置
_default_logger = setup_logger()


# ── 对话日志 ───────────────────────────────────────────


class ConversationLogger:
    """
    对话日志记录器。
    为每个任务生成独立的 Markdown（人类可读）和 JSON Lines（结构化）日志文件。

    输出文件：
        <log_dir>/<task_id>.md      — Markdown 格式
        <log_dir>/<task_id>.jsonl   — JSON Lines 格式
    """

    def __init__(self, log_dir: str = "data/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._md_cache: dict[str, list[str]] = {}
        self._jsonl_cache: dict[str, list[dict]] = {}

    # ── 公开 API ─────────────────────────────────────

    def start_task(self, task_id: str, user_request: str,
                   created_at: Optional[datetime] = None) -> None:
        """创建任务日志文件，写入头部信息"""
        timestamp = (created_at or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
        md_lines = [
            f"# 任务执行日志\n",
            f"**Task ID:** `{task_id}`\n",
            f"**创建时间:** {timestamp}\n",
            f"**用户请求:**\n",
            f"\n> {user_request}\n",
            f"\n---\n",
        ]
        self._write_md(task_id, "\n".join(md_lines))
        self._write_jsonl(task_id, {
            "type": "task_start",
            "task_id": task_id,
            "user_request": user_request,
            "timestamp": timestamp,
        })

    def log_turn(
        self,
        task_id: str,
        turn_index: int,
        system_prompt: str,
        messages: list[dict],
        llm_response: str,
        token_count: int = 0,
        latency_ms: float = 0,
    ) -> None:
        """记录一轮完整的 LLM 交互"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ── Markdown ──
        md = [
            f"\n## Turn {turn_index + 1} | {ts} | {token_count} tokens | {latency_ms:.0f}ms\n",
            f"\n### System Prompt\n",
            f"\n```\n{system_prompt}\n```\n",
            f"\n### Messages Sent\n",
            f"\n```json\n{json.dumps(messages, ensure_ascii=False, indent=2)}\n```\n",
            f"\n### LLM Response\n",
            f"\n{llm_response}\n",
            f"\n---\n",
        ]
        self._write_md(task_id, "\n".join(md))

        # ── JSONL ──
        self._write_jsonl(task_id, {
            "type": "turn",
            "turn": turn_index + 1,
            "timestamp": ts,
            "system_prompt": system_prompt,
            "messages": messages,
            "response": llm_response,
            "token_count": token_count,
            "latency_ms": latency_ms,
        })

    def log_tool_call(
        self,
        task_id: str,
        turn_index: int,
        tool_name: str,
        parameters: dict[str, Any],
        result: Any,
        status: str = "success",
        duration_ms: float = 0,
        error: str = "",
    ) -> None:
        """记录一次工具调用及其结果"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result_str = self._truncate(str(result), 8000)

        # ── Markdown ──
        status_icon = {"success": "✅", "failure": "❌", "timeout": "⏱️", "blocked": "🚫"}.get(status, "❓")
        md = [
            f"\n### 🔧 工具调用: {tool_name} ({status_icon}) | {ts} | {duration_ms:.0f}ms\n",
            f"\n**参数:**\n",
            f"\n```json\n{json.dumps(parameters, ensure_ascii=False, indent=2)}\n```\n",
            f"\n**结果:**\n",
            f"\n```\n{result_str}\n```\n",
        ]
        if error:
            md.append(f"\n**错误:** {error}\n")
        md.append("\n---\n")
        self._write_md(task_id, "\n".join(md))

        # ── JSONL ──
        self._write_jsonl(task_id, {
            "type": "tool_call",
            "turn": turn_index + 1,
            "timestamp": ts,
            "tool_name": tool_name,
            "parameters": parameters,
            "result": result_str,
            "status": status,
            "duration_ms": duration_ms,
            "error": error,
        })

    def log_final_answer(self, task_id: str, turn_index: int, answer: str) -> None:
        """记录最终回答"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        md = [
            f"\n## ✅ 最终回答 | Turn {turn_index + 1} | {ts}\n",
            f"\n{answer}\n",
        ]
        self._write_md(task_id, "\n".join(md))
        self._write_jsonl(task_id, {
            "type": "final_answer",
            "turn": turn_index + 1,
            "timestamp": ts,
            "content": answer,
        })

    def log_reminder(self, task_id: str, correction: str) -> None:
        """记录引擎注入的系统提醒"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        md = [
            f"\n### ⚠️ 系统提醒 | {ts}\n",
            f"\n{correction}\n",
            f"\n---\n",
        ]
        self._write_md(task_id, "\n".join(md))
        self._write_jsonl(task_id, {
            "type": "reminder",
            "timestamp": ts,
            "content": correction,
        })

    def complete_task(
        self,
        task_id: str,
        status: str,
        steps: int,
        summary: str = "",
        error: str = "",
    ) -> None:
        """写入任务完成标记并刷新缓冲区"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_icon = {
            "completed": "✅ 已完成",
            "failed": "❌ 失败",
            "blocked": "⚠️ 需人工介入",
        }.get(status, f"📌 {status}")

        md = [
            f"\n---\n",
            f"\n## {status_icon} | {ts} | 共 {steps} 步\n",
        ]
        if summary:
            md.append(f"\n**摘要:**\n\n{summary}\n")
        if error:
            md.append(f"\n**错误:** {error}\n")
        self._write_md(task_id, "\n".join(md))
        self._write_jsonl(task_id, {
            "type": "task_complete",
            "task_id": task_id,
            "status": status,
            "steps": steps,
            "summary": summary,
            "error": error,
            "timestamp": ts,
        })

        # 刷新缓冲区到磁盘
        self._flush_md(task_id)
        self._flush_jsonl(task_id)

    # ── 内部实现 ─────────────────────────────────────

    def _write_md(self, task_id: str, content: str) -> None:
        """缓存 Markdown 内容"""
        if task_id not in self._md_cache:
            self._md_cache[task_id] = []
        self._md_cache[task_id].append(content)

    def _write_jsonl(self, task_id: str, entry: dict) -> None:
        """缓存 JSONL 条目"""
        if task_id not in self._jsonl_cache:
            self._jsonl_cache[task_id] = []
        self._jsonl_cache[task_id].append(entry)

    def _flush_md(self, task_id: str) -> None:
        """将 Markdown 缓冲区写入磁盘"""
        if task_id in self._md_cache:
            md_path = self.log_dir / f"{task_id}.md"
            try:
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write("".join(self._md_cache[task_id]))
            except Exception:
                pass
            del self._md_cache[task_id]

    def _flush_jsonl(self, task_id: str) -> None:
        """将 JSONL 缓冲区写入磁盘"""
        if task_id in self._jsonl_cache:
            jl_path = self.log_dir / f"{task_id}.jsonl"
            try:
                with open(jl_path, "w", encoding="utf-8") as f:
                    for entry in self._jsonl_cache[task_id]:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception:
                pass
            del self._jsonl_cache[task_id]

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        """截断过长文本"""
        if len(text) <= max_len:
            return text
        return text[:max_len] + f"\n\n... [已截断，原长 {len(text)} 字符]"
