"""
工具注册中心
===========
管理所有可用工具的注册、查找与执行。采用插件式设计，
开发者只需定义工具函数并用装饰器注册即可。
"""

from __future__ import annotations

import functools
import inspect
import time
from typing import Any, Callable, Optional

from .models import ToolCall, ToolCallStatus, ToolDefinition
from .security import SecurityManager


class ToolExecuteError(Exception):
    """工具执行错误"""
    pass


class ToolRegistry:
    """
    工具注册中心。
    维护工具注册表，提供工具查找、执行、文档生成等功能。
    """

    def __init__(self, security_manager: Optional[SecurityManager] = None):
        self._tools: dict[str, ToolDefinition] = {}
        self.security = security_manager or SecurityManager()

    # ── 注册 ─────────────────────────────────────────────

    def register(self, tool_def: ToolDefinition) -> ToolDefinition:
        """注册一个工具"""
        if tool_def.name in self._tools:
            raise ValueError(f"工具 '{tool_def.name}' 已注册")
        self._tools[tool_def.name] = tool_def
        return tool_def

    def register_from_callable(
        self,
        name: str,
        description: str,
        fn: Callable,
        require_confirmation: bool = False,
    ) -> ToolDefinition:
        """
        从可调用对象自动注册工具。
        函数签名中的类型注解会被用于生成参数schema。
        """
        sig = inspect.signature(fn)
        properties = {}
        required_params = []

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            param_type = "string"
            if param.annotation is not inspect.Parameter.empty:
                type_map = {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object",
                }
                param_type = type_map.get(param.annotation, "string")

            properties[param_name] = {
                "type": param_type,
                "description": f"参数 {param_name}",
            }
            if param.default is inspect.Parameter.empty:
                required_params.append(param_name)

        schema = {
            "type": "object",
            "properties": properties,
            "required": required_params,
        }

        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters_schema=schema,
            handler=fn,
            require_confirmation=require_confirmation,
        )
        return self.register(tool_def)

    def unregister(self, name: str) -> None:
        """注销一个工具"""
        self._tools.pop(name, None)

    # ── 查询 ─────────────────────────────────────────────

    def get(self, name: str) -> Optional[ToolDefinition]:
        """获取工具定义"""
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        """列出所有已注册的工具"""
        return list(self._tools.values())

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    # ── 执行 ─────────────────────────────────────────────

    def execute(self, tool_call: ToolCall) -> ToolCall:
        """
        执行一次工具调用。

        Args:
            tool_call: 工具调用记录（包含工具名和参数）

        Returns:
            执行完毕的ToolCall（填充了result/status等信息）

        Raises:
            ToolExecuteError: 工具未找到或执行出错
        """
        tool_def = self.get(tool_call.tool_name)
        if not tool_def:
            raise ToolExecuteError(
                f"未知工具: '{tool_call.tool_name}'。"
                f"可用工具: {', '.join(self._tools.keys())}"
            )

        # 安全校验
        is_safe, reason = self.security.validate_tool_call(
            tool_call.tool_name, tool_call.parameters
        )
        if not is_safe:
            tool_call.status = ToolCallStatus.BLOCKED
            tool_call.error_message = f"安全策略拦截: {reason}"
            return tool_call

        # 参数校验
        self._validate_parameters(tool_def, tool_call.parameters)

        # 执行
        tool_call.start_time = time.time()
        try:
            result = tool_def.handler(**tool_call.parameters)
            tool_call.result = result
            tool_call.status = ToolCallStatus.SUCCESS
            # 将结果转为字符串用于observation
            if isinstance(result, str):
                tool_call.result = result
            elif isinstance(result, (dict, list)):
                import json
                tool_call.result = json.dumps(result, ensure_ascii=False, indent=2)
            else:
                tool_call.result = str(result)
        except Exception as e:
            tool_call.status = ToolCallStatus.FAILURE
            tool_call.error_message = f"{type(e).__name__}: {str(e)}"
            tool_call.result = f"执行出错: {tool_call.error_message}"

        tool_call.end_time = time.time()
        tool_call.duration_ms = (tool_call.end_time - tool_call.start_time) * 1000

        return tool_call

    def _validate_parameters(
        self, tool_def: ToolDefinition, params: dict[str, Any]
    ) -> None:
        """校验参数是否符合schema要求"""
        schema = tool_def.parameters_schema
        required = schema.get("required", [])
        for field_name in required:
            if field_name not in params or params[field_name] is None:
                raise ToolExecuteError(
                    f"工具 '{tool_def.name}' 缺少必填参数: '{field_name}'"
                )

    # ── LLM Prompt 工具描述 ─────────────────────────────

    def generate_tool_descriptions(self) -> str:
        """
        生成供LLM使用的工具描述文本（嵌入系统提示词）。
        """
        lines = []
        for tool in self._tools.values():
            lines.append(
                f"{tool.name}: {tool.description}"
            )
            # 添加参数说明
            props = tool.parameters_schema.get("properties", {})
            if props:
                param_lines = []
                for pname, pinfo in props.items():
                    required = pname in tool.parameters_schema.get("required", [])
                    req_mark = " (必填)" if required else " (可选)"
                    param_lines.append(f"    - {pname}: {pinfo.get('description', '')}{req_mark}")
                lines.extend(param_lines)

        return "\n".join(lines)


# ── 装饰器用法 ─────────────────────────────────────────

_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """获取全局工具注册中心"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    require_confirmation: bool = False,
):
    """
    工具注册装饰器。

    Usage:
        @tool(name="email_read", description="读取未处理邮件")
        def email_read(limit: int = 10):
            ...
    """
    def decorator(fn: Callable):
        tool_name = name or fn.__name__
        tool_desc = description or fn.__doc__ or f"工具 {tool_name}"
        registry = get_registry()
        registry.register_from_callable(
            name=tool_name,
            description=tool_desc,
            fn=fn,
            require_confirmation=require_confirmation,
        )

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        return wrapper
    return decorator
