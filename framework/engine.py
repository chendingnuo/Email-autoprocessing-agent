"""
ReAct循环引擎
=============
核心执行引擎，驱动思考-行动-观察的循环，管理任务从创建到完成的完整生命周期。
"""

from __future__ import annotations

import json
import logging
import time
import traceback
from typing import Any, Callable, Optional

from .llm_client import BaseLLMClient, LLMResponse
from .logger import ConversationLogger
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
        log_dir: str = "data/logs",
    ):
        self.llm = llm_client
        self.tools = tool_registry or ToolRegistry(security_manager)
        self.security = security_manager or SecurityManager()
        self.state = state_manager or StateManager()
        self.max_steps = max_steps
        self.deadlock_threshold = deadlock_threshold
        self.system_prompt_generator = system_prompt_generator
        self.log_dir = log_dir
        # 数据存储：Agent 可以用 data_store 工具持久化提取的业务数据
        self._data_store: dict[str, Any] = {}

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

        # 防御：新任务（非恢复）开始时清理引擎级残留状态
        if context is None:
            self._data_store.clear()

        # 初始化对话日志记录器
        conv_log = ConversationLogger(log_dir=self.log_dir)
        conv_log.start_task(ctx.task_id, user_request, created_at=ctx.created_at)

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

            # 记录本轮对话
            last_turn = ctx.conversation_history[-1] if ctx.conversation_history else None
            if last_turn and last_turn.response:
                conv_log.log_turn(
                    task_id=ctx.task_id,
                    turn_index=last_turn.turn_index,
                    system_prompt=last_turn.system_prompt,
                    messages=last_turn.full_messages,
                    llm_response=last_turn.response,
                    token_count=last_turn.token_count,
                    latency_ms=last_turn.latency_ms,
                )

            # 触发回调
            for cb in callbacks:
                try:
                    cb(step)
                except Exception as e:
                    logger.warning(f"回调执行失败: {e}")

            # 第二步：如果是工具调用，执行工具
            if step.type == StepType.TOOL_CALL and step.tool_call:
                self._execute_tool_step(ctx, step)
                # 记录工具调用
                tc = step.tool_call
                conv_log.log_tool_call(
                    task_id=ctx.task_id,
                    turn_index=len(ctx.conversation_history) - 1,
                    tool_name=tc.tool_name,
                    parameters=tc.parameters,
                    result=tc.result,
                    status=tc.status.value if tc.status else "unknown",
                    duration_ms=tc.duration_ms,
                    error=tc.error_message,
                )
            elif step.type == StepType.FINAL_ANSWER:
                # 记录最终回答
                conv_log.log_final_answer(
                    ctx.task_id,
                    len(ctx.conversation_history) - 1,
                    step.final_answer,
                )

                # 检查是否还有未处理的邮件（email_read 返回了多封但未全部处理）
                read_ids = ctx.metadata.get("read_email_ids", [])
                completed_ids = ctx.metadata.get("completed_email_ids", [])
                if read_ids and len(completed_ids) < len(read_ids):
                    # 死锁保护：追踪对同一组邮件连续提醒的次数
                    reminder_key = f"{','.join(sorted(str(e) for e in read_ids))}|{','.join(sorted(str(e) for e in completed_ids))}"
                    last_key = ctx.metadata.get("_reminder_key", "")
                    reminder_count = ctx.metadata.get("_reminder_count", 0)
                    if reminder_key == last_key:
                        reminder_count += 1
                    else:
                        reminder_count = 1
                    ctx.metadata["_reminder_key"] = reminder_key
                    ctx.metadata["_reminder_count"] = reminder_count

                    MAX_REMINDERS = 3
                    if reminder_count >= MAX_REMINDERS:
                        logger.warning(
                            f"[{ctx.task_id}] FINAL_ANSWER 连续被提醒 {reminder_count} 次无进展，强制完成"
                        )
                        ctx.metadata.pop("_reminder_key", None)
                        ctx.metadata.pop("_reminder_count", None)
                        # 不 continue，继续执行下面的完成逻辑
                    else:
                        unprocessed = sorted(set(str(e) for e in read_ids) - set(str(e) for e in completed_ids))
                        correction = (
                            f"【提醒】email_read 返回了 {len(read_ids)} 封邮件"
                            f"（ID: {', '.join(str(e) for e in read_ids)}），"
                            f"但你目前只处理了 {len(completed_ids)} 封"
                            f"（已完成: {', '.join(str(e) for e in completed_ids) or '无'}），"
                            f"还有 {len(unprocessed)} 封未处理"
                            f"（未处理: {', '.join(unprocessed)}）。\n\n"
                            f"请继续处理剩余邮件！每封邮件都需要完成："
                            f"提取信息 → 检查重复 → 登记数据 → 回复草稿。"
                            f"全部处理完毕后，再给出最终回答。"
                        )
                        conv_log.log_reminder(ctx.task_id, correction)
                        ctx.conversation_history.append(
                            ConversationTurn(
                                turn_index=len(ctx.conversation_history),
                                prompt="",
                                response=f"<observation>\n{correction}\n</observation>",
                            )
                        )
                        continue

                # 检测最终答案中是否包含需要人工介入的标记
                fa = step.final_answer[:2000]
                ctx.llm_final_answer = step.final_answer  # 保留 LLM 原始回答
                blocked_keywords = ["需要人工介入", "无法完成", "未能完成",
                                    "请人工处理", "请手动处理", "操作失败", "写入失败"]
                needs_intervention = any(kw in fa for kw in blocked_keywords)
                if needs_intervention:
                    self.state.block_context(
                        ctx,
                        reason=f"Agent报告需要人工介入: {fa[:300]}",
                    )
                    logger.warning(
                        f"[{ctx.task_id}] 任务需人工介入: {fa[:100]}..."
                    )
                    conv_log.complete_task(
                        ctx.task_id, "blocked", ctx.current_step_count,
                        summary=ctx.summary, error=ctx.error or "",
                    )
                else:
                    # 用基于实际执行数据的事实摘要替代 LLM 编造的 final_answer
                    factual_summary = self._generate_execution_summary(ctx)
                    self.state.complete_context(ctx, summary=factual_summary)
                    logger.info(
                        f"[{ctx.task_id}] 任务完成: {fa[:100]}..."
                    )
                    conv_log.complete_task(
                        ctx.task_id, "completed", ctx.current_step_count,
                        summary=fa,
                    )
                return ctx

            # 滑动窗口压缩
            self.state.apply_sliding_window(ctx)

        # 任务未正常结束（异常中断 / 超出最大步数）
        if ctx.status not in (TaskStatus.COMPLETED,):
            if ctx.status == TaskStatus.BLOCKED:
                conv_log.complete_task(
                    ctx.task_id, "blocked", ctx.current_step_count,
                    summary=ctx.summary, error=ctx.error or "",
                )
            else:
                conv_log.complete_task(
                    ctx.task_id, "failed", ctx.current_step_count,
                    summary=ctx.summary, error=ctx.error or "任务异常中断",
                )

        return ctx

    # ── LLM 交互 ───────────────────────────────────────

    def _build_system_prompt(self, ctx: TaskContext) -> str:
        """构建系统提示词"""
        if self.system_prompt_generator:
            return self.system_prompt_generator(self.tools, ctx)

        tool_descs = self.tools.generate_tool_descriptions()

        # 检测用户意图：只读任务 vs 处理任务
        read_only_keywords = [
            "列出", "查看", "不需要处理", "不处理", "只读",
            "摘要", "概览", "仅显示", "不用处理", "不用回复",
            "不需要做任何处理", "不回复",
        ]
        is_read_only = any(kw in ctx.user_request for kw in read_only_keywords)

        extra_rules = [
            "从邮件或附件中提取出结构化信息后，必须先调用 data_store 工具保存，"
            "否则数据在后续步骤中可能丢失。",
        ]

        if is_read_only:
            extra_rules.append(
                "注意：用户当前请求明确要求只查看/列清单，不要对邮件进行后续处理"
                "（不调用 doc_parse_attachment、不检查重复、不写入 Excel、不生成回复草稿）。"
                "只需列出邮件信息，直接给出 final_answer 即可。"
            )
        else:
            extra_rules.append(
                "如果 email_read 读取到多封邮件，必须逐封处理完所有邮件，"
                "不得只处理第一封就结束。每处理完一封，继续处理下一封，直到全部处理完毕后再给出最终回答。"
                "示例：email_read 返回了5封邮件 → 处理第1封 → 继续处理第2封 → ... → 全部处理完 → final_answer"
            )

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
            system_prompt=system_prompt,
            full_messages=messages,
        )

        try:
            # 调用LLM
            response: LLMResponse = self.llm.chat(messages, system_prompt)
            turn.response = response.content
            turn.token_count = response.token_count
            turn.model = response.model
            turn.latency_ms = response.latency_ms

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
            tb = traceback.format_exc()
            logger.error(f"[{ctx.task_id}] LLM调用异常: {e}\n{tb}")
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
                # 记录已使用的工具（去重）
                used = ctx.metadata.setdefault("used_tools", [])
                if tool_call.tool_name not in used:
                    used.append(tool_call.tool_name)
                # 自动追踪已读取的邮件ID（来自 email_read 的结果）
                if tool_call.tool_name == "email_read" and isinstance(obs, str):
                    try:
                        email_result = json.loads(obs)
                        if email_result.get("status") == "success":
                            ids = ctx.metadata.setdefault("read_email_ids", [])
                            for em in email_result.get("emails", []):
                                eid = str(em.get("id", ""))
                                if eid and eid not in ids:
                                    ids.append(eid)
                    except (json.JSONDecodeError, Exception):
                        pass
                # 自动追踪已处理的邮件ID（来自 email_reply_draft 的结果）
                if tool_call.tool_name == "email_reply_draft" and isinstance(obs, str):
                    try:
                        draft_result = json.loads(obs)
                        if draft_result.get("status") == "success":
                            mid = tool_call.parameters.get("mail_id", "")
                            if mid:
                                completed = ctx.metadata.setdefault("completed_email_ids", [])
                                if mid not in completed:
                                    completed.append(mid)
                    except (json.JSONDecodeError, Exception):
                        pass
                # 同步 data_store 到上下文，使提取的数据在滑动窗口压缩后仍可恢复
                if self._data_store:
                    ctx.extracted_data.update(self._data_store)
                    ctx.metadata.setdefault("extracted_fields", {}).update(self._data_store)
                    # 追加记录到 extracted_records（保留所有邮件的提取结果，避免同名键覆盖）
                    records = ctx.metadata.setdefault("extracted_records", [])
                    records.append(dict(self._data_store))
                    self._data_store.clear()
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
        检测两种模式：
        1. 同一工具、相同参数连续执行 => 精确死循环
        2. 同一工具出现次数超过阈值（不论参数）=> 宽泛死循环
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

        # 宽泛检测：同一工具累计出现太多次（不论参数）
        call_history = ctx.metadata.setdefault("tool_call_history", [])
        call_history.append(tc.tool_name)
        # 保留最近20次记录
        if len(call_history) > 20:
            call_history[:] = call_history[-20:]

        # 统计各工具出现次数
        from collections import Counter
        counts = Counter(call_history)
        for tool_name, count in counts.items():
            threshold = self.deadlock_threshold * 3  # 3倍阈值
            if count >= threshold:
                self.state.block_context(
                    ctx,
                    f"检测到死循环: 工具 '{tool_name}' 已连续出现 {count} 次 "
                    f"(超过阈值 {threshold})，已自动阻断",
                )
                break

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

    # ── 事实摘要 ──────────────────────────────────────

    def _generate_execution_summary(self, ctx: TaskContext) -> str:
        """
        基于实际工具执行数据生成任务摘要，而非依赖 LLM 的 final_answer。
        防止 LLM 在总结时编造未实际执行的操作。
        """
        parts = ["## 任务执行报告（基于实际执行数据）\n"]

        # 1) 提取的记录
        records = ctx.metadata.get("extracted_records", [])
        if records:
            parts.append(f"### 数据登记（共 {len(records)} 条）")
            for i, r in enumerate(records, 1):
                fields = " | ".join(f"{k}: {v}" for k, v in r.items())
                parts.append(f"{i}. {fields}")
            parts.append("")

        # 2) 回复草稿
        completed_ids = ctx.metadata.get("completed_email_ids", [])
        if completed_ids:
            ids_str = ", ".join(completed_ids)
            parts.append("### 回复草稿")
            parts.append(f"已为 {len(completed_ids)} 封邮件生成回复草稿（邮件ID: {ids_str}）")
            parts.append("")

        # 3) 已读取邮件概况
        read_ids = ctx.metadata.get("read_email_ids", [])
        if read_ids:
            parts.append(f"共读取 {len(read_ids)} 封邮件，已处理 {len(completed_ids)} 封")

        # 4) 执行操作概况
        used_tools = ctx.metadata.get("used_tools", [])
        if used_tools:
            parts.append(f"总步数: {ctx.current_step_count}")
            parts.append(f"涉及工具: {', '.join(used_tools)}")

        parts.append("\n---\n*LLM 原始回答见下方*")
        return "\n".join(parts)

    # ── 任务恢复 ───────────────────────────────────────

    def resume(self, task_id: str) -> Optional[TaskContext]:
        """恢复之前中断的任务"""
        ctx = self.state.load_context(task_id)
        if ctx and ctx.status == TaskStatus.RUNNING:
            logger.info(f"[{task_id}] 恢复执行任务")
            return self.run(user_request=ctx.user_request, context=ctx)
        return ctx
