"""
pytest 会话级配置
=================
每次测试会话结束后自动清理运行时缓存（保留模板文件本身）。
"""

import os
import shutil
import pytest


@pytest.fixture(scope="session", autouse=True)
def auto_clean_cache(request):
    """
    整个测试会话结束后自动清理运行时生成的缓存文件，
    避免 data/ 目录堆积日志、任务状态和附件等测试产物。

    行为：
    - logs/ tasks/ attachments/ → 清空目录
    - *.xlsx → 仅清除数据行，保留模板结构和表头
    """

    def _clear_excel_data(filepath: str) -> None:
        """保留 Excel 模板的前 N 行（标题+表头），清除后面的数据行"""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(filepath)
            for ws in wb.worksheets:
                # 找到第一个空行（表头后的第一个空行即数据边界）
                max_row = ws.max_row or 0
                has_data = False
                for row in range(ws.max_row or 1, 0, -1):
                    if any(ws.cell(row=row, column=c).value for c in range(1, (ws.max_column or 1) + 1)):
                        has_data = True
                        break
                if has_data:
                    # 找到表头行（最后一个非空行的上一行就是表头）
                    # 实际上：保留第1行标题 + 可能第2行说明 + 表头行
                    # 从表头行+1开始清到末尾
                    header_row = 1
                    # 检查是否有标题行+说明行模式
                    for r in range(1, min(max_row + 1, 5)):
                        row_vals = [ws.cell(row=r, column=c).value for c in range(1, min((ws.max_column or 1) + 1, 3))]
                        # 如果某行包含"表头"特征词或列名关键词，这就是表头行
                        text = "".join(str(v) for v in row_vals if v)
                        if any(kw in text for kw in ("姓名*", "立项通过日期", "荣誉时数值*", "活动名称")):
                            header_row = r
                            break
                    # 清除表头之后的所有行
                    for row in range(header_row + 1, max_row + 1):
                        for col in range(1, (ws.max_column or 1) + 1):
                            ws.cell(row=row, column=col).value = None
            wb.save(filepath)
        except Exception as e:
            print(f"  [clean_cache] 清理 Excel 数据失败 {filepath}: {e}")

    def cleanup():
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(project_root, "data")

        # 清理运行时目录（日志、任务状态、附件缓存等）
        runtime_dirs = [
            os.path.join(data_dir, "logs"),
            os.path.join(data_dir, "tasks"),
            os.path.join(data_dir, "attachments"),
        ]

        for dir_path in runtime_dirs:
            if os.path.isdir(dir_path):
                for fname in os.listdir(dir_path):
                    fpath = os.path.join(dir_path, fname)
                    try:
                        if os.path.isfile(fpath) or os.path.islink(fpath):
                            os.unlink(fpath)
                        elif os.path.isdir(fpath):
                            shutil.rmtree(fpath)
                    except Exception as e:
                        print(f"  [clean_cache] 清理失败 {fpath}: {e}")

        # 清理 Excel 模板中的数据行（保留模板文件本身）
        import glob as _glob
        for fpath in _glob.glob(os.path.join(data_dir, "*.xlsx")):
            _clear_excel_data(fpath)

    request.addfinalizer(cleanup)
