"""
数据模型定义
============
框架内部流转的核心数据结构。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    """任务生命周期状态"""
    PENDING = "pending"              # 等待处理
    RUNNING = "running"              # 执行中
    COMPLETED = "completed"          # 成功完成
    FAILED = "failed"                # 执行失败
    BLOCKED = "blocked"              # 需要人工介入
    CANCELLED = "cancelled"          # 被取消


class ToolCallStatus(str, Enum):
    """工具调用状态"""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"  # 安全策略拦截


class StepType(str, Enum):
    """ReAct循环中的步骤类型"""
    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    OBSERVATION = "observation"
    FINAL_ANSWER = "final_answer"


@dataclass
class ToolCall:
    """一次工具调用的记录"""
    id: str = field(default_factory=lambda: f"tc_{uuid.uuid4().hex[:8]}")
    tool_name: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    status: ToolCallStatus = ToolCallStatus.SUCCESS
    result: Any = None
    error_message: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0


@dataclass
class ReActStep:
    """ReAct循环中的一个完整步骤 (Thought → Action → Observation)"""
    step_index: int = 0
    type: StepType = StepType.THOUGHT
    thought: str = ""
    tool_call: Optional[ToolCall] = None
    observation: str = ""
    final_answer: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConversationTurn:
    """一次完整的LLM请求-响应轮次"""
    turn_index: int = 0
    prompt: str = ""
    response: str = ""
    parsed_steps: list[ReActStep] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    token_count: int = 0


@dataclass
class TaskContext:
    """
    任务上下文 —— 整个框架的核心数据对象。
    携带任务从创建到完成的全部状态信息。
    """
    task_id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    user_request: str = ""
    status: TaskStatus = TaskStatus.PENDING
    conversation_history: list[ConversationTurn] = field(default_factory=list)
    extracted_data: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    max_steps: int = 15
    current_step_count: int = 0
    consecutive_identical_calls: int = 0
    last_tool_call: Optional[ToolCall] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: ReActStep) -> None:
        """添加一个步骤到当前轮次"""
        if not self.conversation_history:
            self.conversation_history.append(ConversationTurn())
        current_turn = self.conversation_history[-1]
        current_turn.parsed_steps.append(step)
        self.current_step_count += 1

    def to_llm_messages(self) -> list[dict]:
        """
        构建发送给LLM的消息列表。
        应用滑动窗口策略：保留摘要 + 最近3轮完整记录。
        """
        messages = []

        # 用户原始请求
        messages.append({
            "role": "user",
            "content": self.user_request
        })

        # 历史摘要（滑动窗口策略）
        if self.summary:
            messages.append({
                "role": "system",
                "content": f"【历史摘要】\n{self.summary}"
            })

        # 最近5轮的完整交互（滑动窗口策略）
        recent_turns = self.conversation_history[-5:] if len(self.conversation_history) > 5 else self.conversation_history
        for turn in recent_turns:
            if turn.response:
                messages.append({
                    "role": "assistant",
                    "content": turn.response
                })
            for step in turn.parsed_steps:
                if step.tool_call and step.observation:
                    messages.append({
                        "role": "user",
                        "content": f"<observation>\n{step.observation}\n</observation>"
                    })

        return messages


@dataclass
class ToolDefinition:
    """工具定义 —— 注册到框架中的工具元信息"""
    name: str
    description: str
    parameters_schema: dict[str, Any]
    handler: callable = field(repr=False)
    require_confirmation: bool = False


ToolResult = Any
