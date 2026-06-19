"""
文档工具
========
封装Word文档的解析（提取附件中的表单数据）和生成（渲染模板）功能。
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DocTools:
    """
    文档工具集。
    提供Word附件的解析和标准行政公文模板的生成功能。
    """

    def __init__(self, template_dir: str = ""):
        self.template_dir = template_dir or os.getcwd()

    def render_template(
        self,
        template_path: str,
        output_path: str,
        variables: dict[str, Any],
    ) -> str:
        """
        基于标准模板生成Word文档。

        模板中使用 {{变量名}} 作为占位符，render时会被替换。

        Args:
            template_path: 模板文件路径
            output_path: 输出文件路径
            variables: 替换变量字典，如 {"学生姓名": "张三", "学号": "2023001"}

        Returns:
            str: 操作结果
        """
        full_template = self._resolve_path(template_path)
        full_output = self._resolve_path(output_path)

        if not full_template.exists():
            return json.dumps({
                "status": "error",
                "message": f"模板文件不存在: {full_template}"
            }, ensure_ascii=False)

        try:
            from docx import Document

            doc = Document(str(full_template))

            # 替换段落中的变量
            for para in doc.paragraphs:
                self._replace_in_run(para, variables)

            # 替换表格中的变量
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            self._replace_in_run(para, variables)

            # 确保输出目录存在
            full_output.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(full_output))

            return json.dumps({
                "status": "success",
                "message": f"文档已生成: {full_output}",
                "output_path": str(full_output),
                "variables_used": list(variables.keys()),
            }, ensure_ascii=False)

        except ImportError:
            return json.dumps({
                "status": "error",
                "message": "缺少python-docx库，请执行: pip install python-docx"
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"文档生成失败: {e}"
            }, ensure_ascii=False)

    def parse_attachment(self, file_path: str) -> str:
        """
        读取并解析Word附件(.docx)，提取其中的文本内容和表单字段。

        支持两种文档结构，自动识别并选择合适的解析策略：
        1. 表格式文档（如立项申请书）：合并单元格场景下，只提取前两列的
           字段标签-值对，自动跳过声明/免责行和完全重复行。
        2. 段落式文档（如担保书）：当无表格或表格为空时，从段落文本中
           用正则提取 "标签：值" 和 "姓名 编号 时数" 模式的结构化字段。

        Args:
            file_path: Word文档的绝对路径（邮件附件保存后的路径）

        Returns:
            str: 包含文档结构化内容的JSON
        """
        full_path = Path(file_path)
        if not full_path.exists():
            return json.dumps({
                "status": "error",
                "message": f"文件不存在: {file_path}"
            }, ensure_ascii=False)

        try:
            from docx import Document

            doc = Document(str(full_path))

            # 1. 提取所有段落（过滤空段落）
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

            # 2. 提取所有表格数据
            tables = []
            for ti, table in enumerate(doc.tables):
                rows = []
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    rows.append(cells)
                tables.append({
                    "table_index": ti,
                    "row_count": len(rows),
                    "col_count": max(len(r) for r in rows) if rows else 0,
                    "rows": rows,
                })

            # 3. 提取结构化字段
            fields = {}
            if tables:
                # 表格式文档（立项申请书）：只取前两列的字段-值对
                fields = self._parse_table_doc(tables)
            elif paragraphs:
                # 段落式文档（担保书）：从段落文本中提取字段
                fields = self._parse_paragraph_doc(paragraphs)

            result = {
                "status": "success",
                "filename": full_path.name,
                "paragraphs": paragraphs,
                "tables": tables,
                "extracted_fields": fields,
                "paragraph_count": len(paragraphs),
                "table_count": len(tables),
            }
            return json.dumps(result, ensure_ascii=False)

        except ImportError:
            return json.dumps({
                "status": "error",
                "message": "缺少python-docx库，请执行: pip install python-docx"
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"解析Word文档失败: {e}"
            }, ensure_ascii=False)

    @staticmethod
    def _parse_table_doc(tables: list[dict]) -> dict[str, str]:
        """
        解析表格式文档（立项申请书）。

        合并单元格导致多列内容重复，只需取每行的 key（col[0]）和
        value（col[1]），跳过声明/免责行、空行和重复键。
        """
        fields = {}
        seen_keys = set()

        # 声明/免责段落的特征词
        skip_keywords = (
            "申明", "承诺", "声明", "负责", "承担", "记录",
            "提交", "拒绝", "责任", "影响", "平台",
        )

        for table in tables:
            for row in table["rows"]:
                if len(row) < 2:
                    continue
                key = row[0]
                val = row[1]

                # 跳过空键、长文本声明行、标题行
                if not key or len(key) > 50:
                    continue
                if any(kw in key for kw in skip_keywords):
                    continue

                # 跳过重复键（合并单元格导致的冗余）
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                # 跳过值和键完全相同（合并单元格噪声）
                if val and val != key:
                    fields[key] = val

        return fields

    @staticmethod
    def _parse_paragraph_doc(paragraphs: list[str]) -> dict[str, str]:
        """
        解析段落式文档（院系担保书）。

        从段落文本中提取两类结构化数据：
        1. "标签：值" 模式（如 "组织名称：ZJU大凉山助学志愿小组"）
        2. "姓名  志愿者编号  时数" 模式（空格分隔的三元组）
        """
        fields = {}

        for p in paragraphs:
            # 模式 1：标签：值
            if "：" in p:
                parts = p.split("：", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip()
                    if key and val and len(key) < 30:
                        fields[key] = val
                continue

            # 模式 2：姓名 编号 时数（空格分隔）
            # 例: "陈思成  330102001013765057  15h"
            # 编号特征：18位数字
            vid_match = re.search(
                r"(\S{1,6})\s+(\d{18})\s+(\d+\.?\d*\s*h?)", p
            )
            if vid_match:
                name = vid_match.group(1)
                vid = vid_match.group(2)
                hours_raw = vid_match.group(3).replace("h", "").replace("H", "").strip()
                try:
                    hours = str(float(hours_raw))
                    # 去掉末尾无意义的 .0
                    if hours.endswith(".0"):
                        hours = hours[:-2]
                except ValueError:
                    hours = hours_raw
                fields["姓名"] = name
                fields["志愿者编号"] = vid
                fields["荣誉时数"] = hours

            # 模式 3：补录原因行
            reason_match = re.search(r"补录原因[：:]\s*(.+)", p)
            if reason_match:
                fields["补录原因"] = reason_match.group(1).strip()

        return fields

    def list_templates(self, pattern: str = "*.docx") -> str:
        """
        列出模板目录中可用的模板文件。

        Args:
            pattern: 文件匹配模式

        Returns:
            str: 模板文件列表
        """
        template_dir = Path(self.template_dir)
        if not template_dir.exists():
            return json.dumps({
                "status": "error",
                "message": f"模板目录不存在: {template_dir}"
            }, ensure_ascii=False)

        templates = list(template_dir.glob(pattern))
        result = {
            "status": "success",
            "template_dir": str(template_dir),
            "templates": [
                {
                    "name": t.name,
                    "path": str(t),
                    "size_kb": round(t.stat().st_size / 1024, 1),
                }
                for t in sorted(templates)
            ],
        }
        return json.dumps(result, ensure_ascii=False)

    def _resolve_path(self, file_path: str) -> Path:
        p = Path(file_path)
        if p.is_absolute():
            return p
        return Path(self.template_dir) / p

    @staticmethod
    def _replace_in_run(para, variables: dict[str, Any]) -> None:
        """替换段落中的模板变量"""
        for run in para.runs:
            original = run.text
            for key, value in variables.items():
                placeholder = "{{" + key + "}}"
                if placeholder in original:
                    original = original.replace(placeholder, str(value))
            if original != run.text:
                run.text = original
