"""
Excel表格处理工具
================
封装对本地Excel/CSV登记表格的读写操作。
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ExcelTools:
    """
    Excel表格工具集。
    提供对本地学生工作登记表格的查询、插入、更新操作。
    """

    def __init__(self, default_dir: str = ""):
        self.default_dir = default_dir or os.getcwd()

    @staticmethod
    def _get_sheet_name(full_path: Path, preferred: str = "Sheet1") -> str:
        """
        获取Excel文件中的实际工作表名。
        优先使用 preferred，如果不存在则返回第一个工作表。
        """
        try:
            import openpyxl
            wb = openpyxl.load_workbook(full_path, read_only=True)
            names = wb.sheetnames
            wb.close()
            if preferred in names:
                return preferred
            if names:
                return names[0]
        except Exception:
            pass
        return preferred

    def read_records(self, file_path: str, sheet_name: str = "Sheet1") -> str:
        """
        读取指定表格的所有记录。

        Args:
            file_path: Excel文件路径（相对或绝对）
            sheet_name: 工作表名称

        Returns:
            str: 记录列表的JSON字符串
        """
        full_path = self._resolve_path(file_path)
        if not full_path.exists():
            return json.dumps({
                "status": "error",
                "message": f"文件不存在: {full_path}"
            }, ensure_ascii=False)

        try:
            import pandas as pd
            df = pd.read_excel(full_path, sheet_name=sheet_name, dtype=str)
            records = df.fillna("").to_dict(orient="records")

            return json.dumps({
                "status": "success",
                "total": len(records),
                "columns": list(df.columns),
                "records": records,
                "file_path": str(full_path),
            }, ensure_ascii=False)

        except ImportError:
            return self._read_excel_fallback(full_path, sheet_name)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"读取表格失败: {e}"
            }, ensure_ascii=False)

    def insert_record(
        self, file_path: str, record: dict[str, Any],
        dedup_fields: Optional[list[str]] = None,
        header_row: int = 0,
    ) -> str:
        """
        在指定表格末尾追加一条记录（支持去重检查）。

        Args:
            file_path: Excel文件路径
            record: 要插入的记录，如 {"学号": "2023001", "姓名": "张三"}
            dedup_fields: 用于去重检查的字段列表，如 ["活动名称", "主办单位"]
                          如果提供，会在插入前检查这些字段是否匹配已有记录
            header_row: 表头所在的行号（0-indexed，默认0）
                        如果文件有标题行（如第1行是标题、第2行是表头），则 header_row=1

        Returns:
            str: 操作结果
        """
        full_path = self._resolve_path(file_path)
        file_exists = full_path.exists()

        try:
            import pandas as pd

            # 将记录转换为DataFrame
            new_row = pd.DataFrame([record])

            # ── 读取现有文件 ─────────────────────────────
            pre_header_rows = []  # 标题行（表头之前的行）
            existing_data = None   # 现有数据

            if file_exists:
                # 自动检测工作表名（兼容非 Sheet1 命名的文件）
                sheet_name = self._get_sheet_name(full_path, "Sheet1")
                # 读取所有行（不设header，保留原始结构）
                all_data = pd.read_excel(
                    full_path, sheet_name=sheet_name, dtype=str, header=None
                )

                if len(all_data) > header_row:
                    # 分离：标题行 + 表头行 + 数据行
                    pre_header_rows = [list(all_data.iloc[i]) for i in range(header_row)]
                    header_values = [str(v) if pd.notna(v) else "" for v in all_data.iloc[header_row]]
                    existing_data = all_data.iloc[header_row + 1:].copy()
                    existing_data.columns = header_values
                    existing_data = existing_data.reset_index(drop=True)
                elif len(all_data) == header_row:
                    # 只有标题行，没有表头和数据
                    pre_header_rows = [list(all_data.iloc[i]) for i in range(header_row)]
                    header_values = list(record.keys())
                    existing_data = pd.DataFrame(columns=header_values)
                else:
                    # 文件行数少于header_row，异常情况
                    pre_header_rows = [list(all_data.iloc[i]) for i in range(len(all_data))]
                    header_values = list(record.keys())
                    existing_data = pd.DataFrame(columns=header_values)
            else:
                header_values = list(record.keys())

            # ── 去重检查 ─────────────────────────────────
            if dedup_fields and existing_data is not None and len(existing_data) > 0:
                for _, existing_row in existing_data.iterrows():
                    is_dup = True
                    for field in dedup_fields:
                        existing_val = str(existing_row.get(field, "")).strip()
                        new_val = str(record.get(field, "")).strip()
                        if existing_val != new_val:
                            is_dup = False
                            break
                    if is_dup:
                        match_info = {f: record.get(f, "") for f in dedup_fields}
                        return json.dumps({
                            "status": "duplicate",
                            "message": f"发现重复记录！字段 {dedup_fields} 完全匹配。",
                            "matched_fields": match_info,
                            "action_required": "该记录已存在，无需重复录入。如需更新请联系管理员。",
                        }, ensure_ascii=False)

            # ── 自动补全字段（代码层面保证数据完整性）─────
            # 1. 序号：自动按已有行数递增
            if "序号" in new_row.columns:
                existing_count = len(existing_data) if existing_data is not None else 0
                seq = existing_count + 1
                new_row["序号"] = seq
                record["序号"] = seq

            # 2. 立项通过日期：若未填则自动使用当天日期
            if "立项通过日期" in new_row.columns:
                val = str(new_row["立项通过日期"].iloc[0]).strip()
                if not val or val in ("nan", ""):
                    from datetime import date
                    today_str = date.today().strftime("%Y-%m-%d")
                    new_row["立项通过日期"] = today_str
                    record["立项通过日期"] = today_str

            # 3. 是否已发送回件：生成回复草稿即视为"是"
            if "是否已发送回件" in new_row.columns:
                new_row["是否已发送回件"] = "是"
                record["是否已发送回件"] = "是"

            # ── 合并数据 ─────────────────────────────────
            if existing_data is not None:
                # 对齐列
                for col in new_row.columns:
                    if col not in existing_data.columns:
                        existing_data[col] = ""
                for col in existing_data.columns:
                    if col not in new_row.columns:
                        new_row[col] = ""
                df = pd.concat([existing_data, new_row], ignore_index=True)
            else:
                df = new_row
                header_values = list(record.keys())

            # ── 写回文件（保留标题行） ──────────────────
            full_path.parent.mkdir(parents=True, exist_ok=True)

            if pre_header_rows:
                # 用 openpyxl 写入以保留 pre-header 行
                import openpyxl
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = sheet_name if file_exists else "Sheet1"

                # 写标题行
                for r_idx, row in enumerate(pre_header_rows, 1):
                    for c_idx, val in enumerate(row, 1):
                        if pd.notna(val) and val != "nan":
                            ws.cell(row=r_idx, column=c_idx, value=val)

                # 写表头行
                hr = header_row + 1
                for c_idx, h in enumerate(header_values, 1):
                    ws.cell(row=hr, column=c_idx, value=h)

                # 写数据行
                for r_idx, (_, data_row) in enumerate(df.iterrows(), hr + 1):
                    for c_idx, h in enumerate(header_values, 1):
                        val = data_row.get(h, "")
                        if pd.notna(val) and str(val) != "nan":
                            ws.cell(row=r_idx, column=c_idx, value=str(val))

                wb.save(full_path)
                wb.close()
            else:
                # 没有标题行，直接用 pandas 写
                out_sheet = sheet_name if file_exists else "Sheet1"
                df.to_excel(full_path, sheet_name=out_sheet, index=False)

            return json.dumps({
                "status": "success",
                "message": f"记录已插入: {json.dumps(record, ensure_ascii=False)}",
                "file_path": str(full_path),
                "record_count": len(df),
            }, ensure_ascii=False)

        except ImportError:
            return json.dumps({
                "status": "error",
                "message": "缺少pandas库，请执行: pip install pandas openpyxl"
            }, ensure_ascii=False)
        except Exception as e:
            import traceback
            return json.dumps({
                "status": "error",
                "message": f"插入记录失败: {e}\n{traceback.format_exc()[:500]}"
            }, ensure_ascii=False)

    def query_records(
        self, file_path: str, field: str, value: str, sheet_name: str = "Sheet1"
    ) -> str:
        """
        按条件查询记录。

        Args:
            file_path: Excel文件路径
            field: 查询字段名
            value: 查询值
            sheet_name: 工作表名称

        Returns:
            str: 匹配记录的JSON字符串
        """
        full_path = self._resolve_path(file_path)
        if not full_path.exists():
            return json.dumps({
                "status": "error",
                "message": f"文件不存在: {full_path}"
            }, ensure_ascii=False)

        try:
            import pandas as pd
            df = pd.read_excel(full_path, sheet_name=sheet_name, dtype=str)

            if field not in df.columns:
                return json.dumps({
                    "status": "error",
                    "message": f"字段 '{field}' 不存在。可用字段: {list(df.columns)}"
                }, ensure_ascii=False)

            matches = df[df[field].astype(str).str.contains(value, na=False)]
            records = matches.fillna("").to_dict(orient="records")

            return json.dumps({
                "status": "success",
                "total": len(records),
                "records": records,
            }, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"查询失败: {e}"
            }, ensure_ascii=False)

    def get_schema(self, file_path: str, header_row: int = 0) -> str:
        """
        获取表格的结构信息（列名、行数等）。

        对于带标题行的表格（如 荣誉活动立项汇总表.xlsx），
        标题行在第1行，表头在第2行，应使用 header_row=1。
        对于 志愿者荣誉时数导入模板.xls，标题在第1行，
        说明在第2行，表头在第3行，应使用 header_row=2。

        Args:
            file_path: Excel文件路径
            header_row: 表头所在的行号（0-indexed，默认0即第1行）

        Returns:
            str: 表结构信息的JSON字符串
        """
        full_path = self._resolve_path(file_path)
        if not full_path.exists():
            return json.dumps({
                "status": "error",
                "message": f"文件不存在: {full_path}"
            }, ensure_ascii=False)

        try:
            import pandas as pd
            sheet_name = self._get_sheet_name(full_path, "Sheet1")
            df = pd.read_excel(full_path, sheet_name=sheet_name, dtype=str, header=header_row)
            schema = {
                "status": "success",
                "columns": list(df.columns),
                "row_count": len(df),
                "column_count": len(df.columns),
                "file_path": str(full_path),
                "file_exists": True,
                "header_row": header_row,
                "sheet_name": sheet_name,
                "note": "如果列名不准确（如'Unnamed'开头），请尝试调整header_row参数",
            }
            return json.dumps(schema, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"读取表结构失败: {e}"
            }, ensure_ascii=False)

    def list_files(self, pattern: str = "*.[xX][lL][sS]*") -> str:
        """
        列出数据目录中所有可用的Excel文件。

        Args:
            pattern: 文件匹配模式，默认 *.xlsx

        Returns:
            str: 文件列表的JSON字符串
        """
        data_dir = Path(self.default_dir)
        if not data_dir.exists():
            return json.dumps({
                "status": "error",
                "message": f"数据目录不存在: {data_dir}"
            }, ensure_ascii=False)

        files = []
        for f in sorted(data_dir.glob(pattern)):
            stats = f.stat()
            # 返回相对于data_dir的路径，避免LLM拼接出 data/data/xxx.xlsx
            try:
                rel_path = str(f.relative_to(data_dir))
            except ValueError:
                rel_path = f.name
            files.append({
                "name": f.name,
                "path": rel_path,
                "size_kb": round(stats.st_size / 1024, 1),
                "modified": str(stats.st_mtime),
            })

        return json.dumps({
            "status": "success",
            "data_dir": str(data_dir),
            "total": len(files),
            "files": files,
        }, ensure_ascii=False)

    def check_duplicate(
        self, file_path: str, fields: dict[str, str],
        header_row: int = 0,
    ) -> str:
        """
        检查指定表格中是否存在与给定字段完全匹配的重复记录。

        Args:
            file_path: Excel文件名（如 荣誉活动立项汇总表.xlsx）
            fields: 要匹配的字段-值字典，如 {"活动名称": "xxx", "主办单位": "yyy"}
            header_row: 表头所在行号（0-indexed，默认0）

        Returns:
            str: 包含检查结果的JSON
        """
        full_path = self._resolve_path(file_path)
        if not full_path.exists():
            return json.dumps({
                "status": "error",
                "message": f"文件不存在: {full_path}"
            }, ensure_ascii=False)

        try:
            import pandas as pd
            sheet_name = self._get_sheet_name(full_path, "Sheet1")
            df = pd.read_excel(full_path, sheet_name=sheet_name, dtype=str, header=header_row)

            for _, existing_row in df.iterrows():
                is_dup = True
                for field, value in fields.items():
                    existing_val = str(existing_row.get(field, "")).strip()
                    if existing_val != str(value).strip():
                        is_dup = False
                        break
                if is_dup:
                    return json.dumps({
                        "status": "duplicate_found",
                        "message": f"发现重复记录！字段 {list(fields.keys())} 完全匹配。",
                        "matched_fields": fields,
                        "action_required": "该记录已存在，无需重复录入。请发送告知邮件说明已收到过相同申请。",
                    }, ensure_ascii=False)

            return json.dumps({
                "status": "no_duplicate",
                "message": "未发现重复记录，可以正常录入。",
                "checked_fields": list(fields.keys()),
            }, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"去重检查失败: {e}"
            }, ensure_ascii=False)


    def _read_excel_fallback(self, full_path: Path, sheet_name: str) -> str:
        """不使用pandas的备用读取方案"""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(full_path, read_only=True, data_only=True)
            if sheet_name not in wb.sheetnames:
                sheet_name = wb.sheetnames[0] if wb.sheetnames else ""
            ws = wb[sheet_name]

            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return json.dumps({"status": "success", "total": 0, "records": []})

            headers = [str(h) if h is not None else "" for h in rows[0]]
            records = []
            for row in rows[1:]:
                record = {}
                for i, val in enumerate(row):
                    if i < len(headers):
                        record[headers[i]] = str(val) if val is not None else ""
                records.append(record)

            wb.close()
            return json.dumps({
                "status": "success",
                "total": len(records),
                "columns": headers,
                "records": records,
            }, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"读取失败: {e}"
            }, ensure_ascii=False)


    def _resolve_path(self, file_path: str) -> Path:
        """
        解析文件路径（支持相对/绝对路径），防止 data/ 目录重复嵌套。

        处理场景：
        - "活动报名表.xlsx"              -> data/活动报名表.xlsx
        - "data/活动报名表.xlsx"          -> data/活动报名表.xlsx
        - "data/data/活动报名表.xlsx"     -> data/活动报名表.xlsx
        """
        p = Path(file_path)
        if p.is_absolute():
            return p

        default = Path(self.default_dir)
        default_name = default.name

        parts = list(p.parts)
        while parts and parts[0] == default_name:
            parts = parts[1:]

        p = Path(*parts) if parts else Path(".")
        return (default / p).resolve()
