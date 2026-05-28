"""
日志配置模块
===========
统一的日志配置，支持控制台和文件输出。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logger(
    name: str = "agent",
    level: int = logging.INFO,
    log_file: str | None = None,
    format_string: str | None = None,
) -> logging.Logger:
    """
    配置并返回一个日志记录器。

    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径（可选）
        format_string: 自定义格式字符串
    """
    fmt = format_string or (
        "[%(asctime)s] %(levelname)-8s | %(name)s | %(message)s"
    )
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出（可选）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 全局缺省日志配置
default_logger = setup_logger()
