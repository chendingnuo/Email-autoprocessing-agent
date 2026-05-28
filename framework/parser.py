"""
ReAct输出解析器
===============
负责解析LLM返回的XML标签格式输出，将其转换为结构化的步骤数据。

支持的标签格式：
  <thought>...</thought>
  <tool_call>{JSON}</tool_call>
  <final_answer>...</final_answer>

增强容错：自动修复常见的LLM JSON格式问题。
"""

from __future__ import annotations

import json
import re
from typing import Optional

from .models import ReActStep, StepType, ToolCall


class ParseError(Exception):
    """解析错误"""
    pass


def _repair_json(raw: str) -> str:
    """
    安全修复LLM生成的常见JSON格式错误。
    逐个尝试修复策略，不破坏已有正确内容。
    """
    s = raw.strip()

    # 1. 去掉Markdown代码块标记
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)

    # 2. 直接尝试解析
    try:
        json.loads(s)
        return s
    except json.JSONDecodeError:
        pass

    # 3. 修复JSON字符串值中未转义的反斜杠
    #    如 "path": "data\活动报名表.xlsx" -> "path": "data\\活动报名表.xlsx"
    def _escape_backslashes(m):
        before = m.group(1)
        val = m.group(2)
        # 把不在有效转义序列里的反斜杠转义（如 \活 -> \\活）
        val = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', val)
        return f'"{before}": "{val}"'

    s = re.sub(r'"([^"]+)":\s*"([^"]*)"', _escape_backslashes, s)

    try:
        json.loads(s)
        return s
    except json.JSONDecodeError:
        pass

    # 4. 修复结构层的单引号为双引号
    #    仅修复 "key": 'value' 或 'key': "value" 形式的
    lines = s.split("\n")
    fixed_lines = []
    for line in lines:
        stripped = line.strip()
        if ":" in stripped and ("'" in stripped):
            parts = stripped.split(":", 1)
            key_part = parts[0].strip().strip("'\"").strip()
            val_part = parts[1].strip().rstrip(",").strip("'\"").strip()
            has_comma = stripped.rstrip().endswith(",")
            comma = "," if has_comma else ""
            fixed_lines.append(f'  "{key_part}": "{val_part}"{comma}')
        else:
            fixed_lines.append(line)
    s = "\n".join(fixed_lines)

    try:
        json.loads(s)
        return s
    except json.JSONDecodeError:
        pass

    # 全部修复失败，返回原始内容让json.loads报原始的错
    return raw


class ReActParser:
    """
    ReAct格式输出解析器。
    将LLM输出的XML标签文本解析为结构化的ReActStep对象。
    """

    THOUGHT_PATTERN = re.compile(
        r"<thought>\s*(.*?)\s*</thought>", re.DOTALL
    )
    TOOL_CALL_PATTERN = re.compile(
        r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL
    )
    FINAL_ANSWER_PATTERN = re.compile(
        r"<final_answer>\s*(.*?)\s*</final_answer>", re.DOTALL
    )

    # 容错模式：标签未闭合
    LOOSE_TOOL_CALL_PATTERN = re.compile(
        r"<tool_call>\s*(.*?)(?:</tool_call>|$)", re.DOTALL
    )
    LOOSE_FINAL_ANSWER_PATTERN = re.compile(
        r"<final_answer>\s*(.*?)(?:</final_answer>|$)", re.DOTALL
    )

    @classmethod
    def parse(cls, llm_output: str) -> list[ReActStep]:
        """
        解析LLM的完整输出，提取其中所有XML标签步骤。

        Args:
            llm_output: LLM返回的原始文本

        Returns:
            list[ReActStep]: 解析出的步骤列表

        Raises:
            ParseError: 当输出格式不符合预期时
        """
        steps = []
        step_index = 0

        # 1. 提取 <thought>
        thought_match = cls.THOUGHT_PATTERN.search(llm_output)
        thought_text = thought_match.group(1).strip() if thought_match else ""

        # 2. 提取 <tool_call>
        tool_call = None
        tool_call_match = cls.TOOL_CALL_PATTERN.search(llm_output)
        if not tool_call_match:
            tool_call_match = cls.LOOSE_TOOL_CALL_PATTERN.search(llm_output)

        if tool_call_match:
            raw_json = tool_call_match.group(1).strip()
            raw_json = raw_json.replace("&lt;", "<").replace("&gt;", ">")

            # 先尝试直接解析，让 _repair_json 做自动修复
            repaired = _repair_json(raw_json)

            try:
                parsed = json.loads(repaired)
                tool_name = parsed.get("tool_name", "") or parsed.get("tool", "")
                params = parsed.get("parameters", {})
                if not tool_name:
                    raise ParseError("tool_call 中缺少 tool_name 字段")
                tool_call = ToolCall(
                    tool_name=tool_name,
                    parameters=params if isinstance(params, dict) else {},
                )
            except json.JSONDecodeError as e:
                raise ParseError(
                    f"tool_call 参数JSON解析失败: {e}\n"
                    f"原始内容: {tool_call_match.group(1).strip()[:300]}"
                )

        # 3. 提取 <final_answer>
        final_answer_text = ""
        final_answer_match = cls.FINAL_ANSWER_PATTERN.search(llm_output)
        if not final_answer_match:
            final_answer_match = cls.LOOSE_FINAL_ANSWER_PATTERN.search(llm_output)
        if final_answer_match:
            final_answer_text = final_answer_match.group(1).strip()

        # 4. 构造步骤
        if thought_text or tool_call or final_answer_text:
            step = ReActStep(
                step_index=step_index,
                type=StepType.THOUGHT,
                thought=thought_text,
                tool_call=tool_call,
                final_answer=final_answer_text,
            )
            if tool_call:
                step.type = StepType.TOOL_CALL
            if final_answer_text and not tool_call:
                step.type = StepType.FINAL_ANSWER
            steps.append(step)

        # 5. 校验
        if not steps:
            if llm_output.strip():
                snippet = llm_output[:100].replace("\n", " ")
                raise ParseError(
                    f"LLM输出未包含有效的XML标签 "
                    f"(<thought>/<tool_call>/<final_answer>)。"
                    f"输出开头: {snippet}..."
                )
            else:
                raise ParseError("LLM返回了空输出")

        has_tc = any(s.tool_call is not None for s in steps)
        has_fa = any(s.final_answer for s in steps)
        if has_tc and has_fa:
            raise ParseError(
                "LLM输出同时包含 <tool_call> 和 <final_answer> 标签，"
                "一次只能输出其中一个。"
            )

        tc_count = sum(1 for s in steps if s.tool_call is not None)
        if tc_count > 1:
            raise ParseError(
                f"LLM输出包含 {tc_count} 个 <tool_call> 标签，"
                "一次只能输出一个。"
            )

        return steps

    @classmethod
    def validate_output_format(cls, llm_output: str) -> tuple[bool, Optional[str]]:
        try:
            cls.parse(llm_output)
            return True, None
        except ParseError as e:
            return False, str(e)
