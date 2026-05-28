"""
ReAct循环引擎
=============
核心执行引擎，驱动思考-行动-观察的循环，管理任务从创建到完成的完整生命周期。
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Optional

from .llm_client import BaseLLMClient, LLMResponse
from .models import (
    ConversationTurn,
    ReActStep,
    StepType,
    TaskContext,
    TaskStatus,
    ToolCall,
    ToolCallStatus,
)
from .parser import ParseError, ReActParser
from .security import SecurityError, SecurityManager
from .state_manager import StateManager
from .tool_registry import ToolExecuteError, ToolRegistry

logger = logging.getLogger(__name__)


class ReActEngine:
    """
    ReAct循环引擎。
    驱动LLM进行"思考→行动→观察"的迭代循环，直到任务完成。
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        tool_registry: Optional[ToolRegistry] = None,
        security_manager: Optional[SecurityManager] = None,
        state_manager: Optional[StateManager] = None,
        max_steps: int = 15,
        deadlock_threshold: int = 3,
        system_prompt_generator: Optional[Callable] = None,
    ):
        self.llm = llm_client
        self.tools = tool_registry or ToolRegistry(security_manager)
        self.security = security_manager or SecurityManager()
        self.state = state_manager or StateManager()
        self.max_steps = max_steps
        self.deadlock_threshold = deadlock_threshold
        self.system_prompt_generator = system_prompt_generator

    # ── 主入口 ─────────────────────────────────────────

    def run(
        self,
        user_request: str,
        context: Optional[TaskContext] = None,
        callbacks: Optional[list[Callable[[ReActStep], None]]] = None,
    ) -> TaskContext:
        """
        执行一个任务的完整ReAct循环。

        Args:
            user_request: 用户的任务描述
            context: 可选的已有上下文（用于恢复任务）
            callbacks: 可选的回调列表，每个步骤完成后触发

        Returns:
            完成任务后的上下文
        """
        ctx = context or self.state.create_context(user_request)
        callbacks = callbacks or []

        logger.info(f"[{ctx.task_id}] 开始执行ReAct循环, 最大步数={self.max_steps}")

        while ctx.current_step_count < self.max_steps:
            # 检查是否需人工介入
            if ctx.status == TaskStatus.BLOCKED:
                break

            # 第一步：调用LLM获取行动决策
            step = self._llm_step(ctx)
            if not step:
                break

            ctx.add_step(step)

            # 触发回调
            for cb in callbacks:
                try:
                    cb(step)
                except Exception as e:
                    logger.warning(f"回调执行失败: {e}")

            # 第二步：如果是工具调用，执行工具
            if step.type == StepType.TOOL_CALL and step.tool_call:
                self._execute_tool_step(ctx, step)
            elif step.type == StepType.FINAL_ANSWER:
                # 任务完成
                self.state.complete_context(
                    ctx,
                    summary=step.final_answer[:2000],
                )
                logger.info(
                    f"[{ctx.task_id}] 任务完成: {step.final_answer[:100]}..."
                )
                return ctx

            # 滑动窗口压缩
            self.state.apply_sliding_window(ctx)

        # 超出最大步数
        if ctx.current_step_count >= self.max_steps:
            self.state.block_context(
                ctx, f"超出最大执行步数限制 ({self.max_steps})"
            )

        return ctx

    # ── LLM 交互 ───────────────────────────────────────

    def _build_system_prompt(self, ctx: TaskContext) -> str:
        """构建系统提示词"""
        if self.system_prompt_generator:
            return self.system_prompt_generator(self.tools, ctx)

        tool_descs = self.tools.generate_tool_descriptions()
        extra_rules = []

        if ctx.extracted_data:
            extra_rules.append(
                f"任务中已提取的数据: {json.dumps(ctx.extracted_data, ensure_ascii=False)}"
            )

        return SecurityManager.generate_secure_system_prompt(
            tool_descriptions=tool_descs,
            extra_rules=extra_rules,
        )

    def _llm_step(self, ctx: TaskContext) -> Optional[ReActStep]:
        """
        执行一次LLM调用，获取模型决策（工具调用或最终答案）。

        Returns:
            ReActStep | None: 解析后的步骤，返回None表示需要中止
        """
        system_prompt = self._build_system_prompt(ctx)
        messages = ctx.to_llm_messages()

        # 记录本轮轮次
        turn = ConversationTurn(
            turn_index=len(ctx.conversation_history),
            prompt=json.dumps(messages, ensure_ascii=False)[:200],
        )

        try:
            # 调用LLM
            response: LLMResponse = self.llm.chat(messages, system_prompt)
            turn.response = response.content
            turn.token_count = response.token_count

            logger.info(
                f"[{ctx.task_id}] 第{turn.turn_index}轮LLM调用 "
                f"({response.model}, {response.token_count}tokens, "
                f"{response.latency_ms:.0f}ms)"
            )

            # 解析输出
            steps = ReActParser.parse(response.content)
            ctx.conversation_history.append(turn)

            if steps:
                step = steps[0]
                # 提取业务数据（如果是tool_call，记录参数快照）
                if step.tool_call:
                    self._track_tool_call_pattern(ctx, step.tool_call)
                return step

        except ParseError as e:
            logger.warning(f"[{ctx.task_id}] 解析LLM输出失败: {e}")
            turn.response = f"[PARSE_ERROR] {e}"
            ctx.conversation_history.append(turn)

            # 解析失败尝试纠正
            if ctx.current_step_count < self.max_steps:
                self._handle_parse_error(ctx, e)
                return self._llm_step(ctx)
            else:
                self.state.block_context(ctx, f"持续解析失败: {e}")
                return None

        except SecurityError as e:
            logger.warning(f"[{ctx.task_id}] 安全检测拦截: {e}")
            self.state.block_context(ctx, f"安全拦截: {e}")
            return None

        except Exception as e:
            logger.error(f"[{ctx.task_id}] LLM调用异常: {e}")
            self.state.block_context(ctx, f"LLM调用异常: {e}")
            return None

        return None

    # ── 工具执行 ───────────────────────────────────────

    def _execute_tool_step(self, ctx: TaskContext, step: ReActStep) -> None:
        """执行工具调用并记录观察结果"""
        tool_call = step.tool_call
        logger.info(
            f"[{ctx.task_id}] 执行工具: {tool_call.tool_name} "
            f"参数: {json.dumps(tool_call.parameters, ensure_ascii=False)}"
        )

        try:
            executed = self.tools.execute(tool_call)
            step.tool_call = executed
            ctx.last_tool_call = executed

            if executed.status == ToolCallStatus.SUCCESS:
                obs = executed.result
                logger.info(
                    f"[{ctx.task_id}] 工具 {tool_call.tool_name} 执行成功 "
                    f"({executed.duration_ms:.0f}ms)"
                )
            elif executed.status == ToolCallStatus.BLOCKED:
                obs = f"工具调用被安全策略拦截: {executed.error_message}"
                logger.warning(f"[{ctx.task_id}] {obs}")
            else:
                obs = f"工具执行出错: {executed.error_message}"
                logger.warning(f"[{ctx.task_id}] {obs}")

            step.observation = obs

        except ToolExecuteError as e:
            obs = f"工具调用失败: {e}"
            step.observation = obs
            tool_call.status = ToolCallStatus.FAILURE
            tool_call.error_message = str(e)
            logger.warning(f"[{ctx.task_id}] {obs}")

    # ── 状态追踪 ───────────────────────────────────────

    def _track_tool_call_pattern(self, ctx: TaskContext, tc: ToolCall) -> None:
        """
        追踪工具调用模式，用于死循环检测。
        同一工具、相同参数连续执行多次且结果无变化  → 判定为死循环。
        """
        last = ctx.last_tool_call
        if (
            last
            and last.tool_name == tc.tool_name
            and last.parameters == tc.parameters
        ):
            ctx.consecutive_identical_calls += 1
            if ctx.consecutive_identical_calls >= self.deadlock_threshold:
                self.state.block_context(
                    ctx,
                    f"检测到死循环: 工具 '{tc.tool_name}' 以相同参数连续执行 "
                    f"{ctx.consecutive_identical_calls} 次，已自动阻断",
                )
        else:
            ctx.consecutive_identical_calls = 0

    def _handle_parse_error(self, ctx: TaskContext, error: ParseError) -> None:
        """处理解析错误：在上下文中注入纠正信息"""
        correction = (
            f"【格式错误纠正】你的上一轮输出格式不符合要求，具体问题: {error}\n\n"
            f"请严格按照以下格式之一重新输出，不要添加其他内容：\n\n"
            f"【需要调用工具时】\n"
            f"<thought>\n你的思考过程\n</thought>\n"
            f"<tool_call>\n{{\n"
            f'    "tool_name": "工具名",\n'
            f'    "parameters": {{"参数1": "值1", "参数2": "值2"}}\n'
            f"}}\n"
            f"</tool_call>\n\n"
            f"【任务完成时】\n"
            f"<thought>\n总结\n</thought>\n"
            f"<final_answer>\n给用户的汇报\n</final_answer>\n\n"
            f"注意：JSON字符串中的双引号必须用\\\"转义，不要使用中文引号。"
        )
        ctx.conversation_history.append(
            ConversationTurn(
                turn_index=len(ctx.conversation_history),
                prompt="",
                response=f"<observation>\n{correction}\n</observation>",
            )
        )

    # ── 任务恢复 ───────────────────────────────────────

    def resume(self, task_id: str) -> Optional[TaskContext]:
        """恢复之前中断的任务"""
        ctx = self.state.load_context(task_id)
        if ctx and ctx.status == TaskStatus.RUNNING:
            logger.info(f"[{task_id}] 恢复执行任务")
            return self.run(user_request=ctx.user_request, context=ctx)
        return ctx
