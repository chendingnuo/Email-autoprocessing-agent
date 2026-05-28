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

        支持两种结构：
        1. 段落式文档（如担保书）：提取所有段落文本
        2. 表格式文档（如立项申请书）：提取表格中的字段标签和值

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
            paragraphs = []
            for p in doc.paragraphs:
                text = p.text.strip()
                if text:
                    paragraphs.append(text)

            # 2. 提取所有表格数据
            tables = []
            for ti, table in enumerate(doc.tables):
                rows = []
                for ri, row in enumerate(table.rows):
                    cells = [cell.text.strip() for cell in row.cells]
                    rows.append(cells)
                tables.append({
                    "table_index": ti,
                    "row_count": len(rows),
                    "col_count": max(len(r) for r in rows) if rows else 0,
                    "rows": rows,
                })

            # 3. 尝试识别字段名-值对（从表格中）
            fields = {}
            for table in tables:
                for row in table["rows"]:
                    if len(row) >= 2:
                        key = row[0]
                        val = row[1]
                        # 过滤：跳过表头、申明段落、过长的值
                        if key and not key.startswith("行") and len(key) < 50:
                            fields[key] = val

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
