"""
工具注册中心单元测试
====================
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from framework.tool_registry import ToolRegistry, ToolExecuteError, tool
from framework.models import ToolDefinition, ToolCall, ToolCallStatus


def test_register_and_get():
    """测试工具注册和查询"""
    registry = ToolRegistry()

    def mock_handler(limit: int = 10):
        return f"读取 {limit} 封邮件"

    tool_def = ToolDefinition(
        name="email_read",
        description="读取未处理邮件",
        parameters_schema={
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "读取数量"}},
            "required": [],
        },
        handler=mock_handler,
    )
    registry.register(tool_def)

    retrieved = registry.get("email_read")
    assert retrieved is not None
    assert retrieved.name == "email_read"
    assert retrieved.handler(limit=5) == "读取 5 封邮件"
    print("✓ test_register_and_get PASS")


def test_register_from_callable():
    """测试从函数自动注册"""
    registry = ToolRegistry()

    def query_records(file_path: str, field: str = "学号"):
        return f"查询 {file_path} 中 {field} 字段"

    registry.register_from_callable(
        name="excel_query",
        description="查询Excel记录",
        fn=query_records,
    )

    tool_def = registry.get("excel_query")
    assert tool_def is not None
    assert "file_path" in tool_def.parameters_schema["required"]
    assert "field" not in tool_def.parameters_schema["required"]
    assert tool_def.handler(file_path="test.xlsx") == "查询 test.xlsx 中 学号 字段"
    print("✓ test_register_from_callable PASS")


def test_duplicate_registration():
    """重复注册应报错"""
    registry = ToolRegistry()

    def handler_a():
        return "a"

    def handler_b():
        return "b"

    registry.register_from_callable("same_tool", "工具A", handler_a)
    try:
        registry.register_from_callable("same_tool", "工具B", handler_b)
        assert False, "应该报错"
    except ValueError:
        print("✓ test_duplicate_registration PASS")


def test_execute_success():
    """测试工具执行成功"""
    registry = ToolRegistry()

    def add_student(name: str, student_id: str):
        return f"已添加学生: {name}({student_id})"

    registry.register_from_callable("add_student", "添加学生", add_student)

    tc = ToolCall(
        tool_name="add_student",
        parameters={"name": "张三", "student_id": "2023001"},
    )
    result = registry.execute(tc)
    assert result.status == ToolCallStatus.SUCCESS
    assert "张三" in result.result
    print("✓ test_execute_success PASS")


def test_execute_unknown_tool():
    """执行未知工具应报错"""
    registry = ToolRegistry()
    tc = ToolCall(tool_name="non_existent", parameters={})

    try:
        registry.execute(tc)
        assert False, "应该报错"
    except ToolExecuteError:
        print("✓ test_execute_unknown_tool PASS")


def test_execute_missing_required_param():
    """缺少必填参数应报错"""
    registry = ToolRegistry()

    def send_email(to: str, content: str):
        return f"发送给 {to}"

    registry.register_from_callable("send_email", "发送邮件", send_email)

    tc = ToolCall(tool_name="send_email", parameters={"content": "你好"})
    try:
        registry.execute(tc)
        assert False, "应该报错"
    except ToolExecuteError:
        print("✓ test_execute_missing_required_param PASS")


def test_execute_error_handler():
    """工具执行时handler异常应被捕获"""
    registry = ToolRegistry()

    def failing_handler():
        raise RuntimeError("模拟错误")

    registry.register_from_callable("failing", "会失败的工具", failing_handler)

    tc = ToolCall(tool_name="failing", parameters={})
    result = registry.execute(tc)
    assert result.status == ToolCallStatus.FAILURE
    assert "模拟错误" in result.error_message
    print("✓ test_execute_error_handler PASS")


def test_generate_tool_descriptions():
    """测试工具描述生成"""
    registry = ToolRegistry()

    registry.register_from_callable(
        "email_read", "读取收件箱中未处理的邮件", lambda limit=10: None
    )
    registry.register_from_callable(
        "email_reply", "生成回复草稿", lambda mail_id, content: None
    )

    desc = registry.generate_tool_descriptions()
    assert "email_read" in desc
    assert "email_reply" in desc
    assert "limit" in desc
    print("✓ test_generate_tool_descriptions PASS")


def test_decorator():
    """测试装饰器注册"""
    from framework.tool_registry import get_registry

    # 清理
    registry = get_registry()

    @tool(name="test_decorator_tool", description="装饰器注册测试")
    def my_tool(query: str, limit: int = 5):
        return f"查询: {query}, 限制: {limit}"

    tool_def = registry.get("test_decorator_tool")
    assert tool_def is not None
    assert tool_def.name == "test_decorator_tool"
    assert "query" in tool_def.parameters_schema["required"]
    assert "limit" not in tool_def.parameters_schema["required"]

    tc = ToolCall(
        tool_name="test_decorator_tool",
        parameters={"query": "张三"},
    )
    result = registry.execute(tc)
    assert result.status == ToolCallStatus.SUCCESS
    print("✓ test_decorator PASS")


if __name__ == "__main__":
    test_register_and_get()
    test_register_from_callable()
    test_duplicate_registration()
    test_execute_success()
    test_execute_unknown_tool()
    test_execute_missing_required_param()
    test_execute_error_handler()
    test_generate_tool_descriptions()
    test_decorator()
    print("\n✅ 所有工具注册中心测试通过")
