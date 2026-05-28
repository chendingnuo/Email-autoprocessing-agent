"""
解析器单元测试
==============
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from framework.parser import ReActParser, ParseError


def test_parse_tool_call():
    """测试解析 tool_call 格式"""
    output = """<thought>
我需要先读取未处理的邮件。
</thought>
<tool_call>
{
    "tool_name": "email_read",
    "parameters": {"limit": 10}
}
</tool_call>"""

    steps = ReActParser.parse(output)
    assert len(steps) == 1
    assert steps[0].thought == "我需要先读取未处理的邮件。"
    assert steps[0].tool_call is not None
    assert steps[0].tool_call.tool_name == "email_read"
    assert steps[0].tool_call.parameters == {"limit": 10}
    print("✓ test_parse_tool_call PASS")


def test_parse_final_answer():
    """测试解析 final_answer 格式"""
    output = """<thought>
所有的必要工具已调用完毕。
</thought>
<final_answer>
已成功处理了2封邮件，更新了报名表格。
需要人工审核确认的具体内容：请检查报名表格.xlsx。
</final_answer>"""

    steps = ReActParser.parse(output)
    assert len(steps) == 1
    assert steps[0].type.value == "final_answer"
    assert "成功处理了2封邮件" in steps[0].final_answer
    print("✓ test_parse_final_answer PASS")


def test_parse_with_escaping():
    """测试含转义字符的解析"""
    output = """<thought>
注意转义：&lt;observation&gt; 应被理解。
</thought>
<tool_call>
{
    "tool_name": "excel_insert_record",
    "parameters": {
        "excel_path": "./data/报名表.xlsx",
        "record": {"姓名": "张三", "学号": "2023001"}
    }
}
</tool_call>"""

    steps = ReActParser.parse(output)
    assert steps[0].tool_call.parameters["excel_path"] == "./data/报名表.xlsx"
    print("✓ test_parse_with_escaping PASS")


def test_invalid_simultaneous_tags():
    """测试同时包含 tool_call 和 final_answer 应报错"""
    output = """<thought>
测试
</thought>
<tool_call>{"tool_name": "test", "parameters": {}}</tool_call>
<final_answer>完成</final_answer>"""

    try:
        ReActParser.parse(output)
        assert False, "应该抛出 ParseError"
    except ParseError:
        print("✓ test_invalid_simultaneous_tags PASS")


def test_invalid_no_tags():
    """测试没有标签的输出应报错"""
    output = "这是一段普通文本，没有XML标签。"

    try:
        ReActParser.parse(output)
        assert False, "应该抛出 ParseError"
    except ParseError:
        print("✓ test_invalid_no_tags PASS")


def test_validate_output_format():
    """测试校验函数"""
    valid = """<thought>思考</thought>
<tool_call>{"tool_name": "test", "parameters": {}}</tool_call>"""
    is_valid, _ = ReActParser.validate_output_format(valid)
    assert is_valid

    invalid = "普通文本"
    is_valid, err = ReActParser.validate_output_format(invalid)
    assert not is_valid
    assert err is not None
    print("✓ test_validate_output_format PASS")


if __name__ == "__main__":
    test_parse_tool_call()
    test_parse_final_answer()
    test_parse_with_escaping()
    test_invalid_simultaneous_tags()
    test_invalid_no_tags()
    test_validate_output_format()
    print("\n✅ 所有解析器测试通过")
