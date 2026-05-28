"""
系统配置文件
============
管理所有可配置项，支持环境变量覆盖。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# 自动加载 .env 文件（如果存在）
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    with open(_env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            if key and not os.environ.get(key):  # 不覆盖已有环境变量
                os.environ[key] = value


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "tongyi")
    )
    api_key: str = field(
        default_factory=lambda: os.getenv("DASHSCOPE_API_KEY", "")
    )
    model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", "qwen-plus")
    )
    base_url: str = field(
        default_factory=lambda: os.getenv(
            "LLM_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    )
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: int = 60
    max_retries: int = 3


@dataclass
class EmailConfig:
    """邮件服务器配置"""
    imap_server: str = field(
        default_factory=lambda: os.getenv("IMAP_SERVER", "")
    )
    imap_port: int = int(os.getenv("IMAP_PORT", "993"))
    smtp_server: str = field(
        default_factory=lambda: os.getenv("SMTP_SERVER", "")
    )
    smtp_port: int = int(os.getenv("SMTP_PORT", "465"))
    account: str = field(
        default_factory=lambda: os.getenv("EMAIL_ACCOUNT", "")
    )
    password: str = field(
        default_factory=lambda: os.getenv("EMAIL_PASSWORD", "")
    )


@dataclass
class EngineConfig:
    """引擎配置"""
    max_steps: int = int(os.getenv("AGENT_MAX_STEPS", "30"))
    deadlock_threshold: int = 3
    storage_dir: str = field(
        default_factory=lambda: os.getenv(
            "AGENT_STORAGE_DIR",
            os.path.join(os.getcwd(), "data", "tasks"),
        )
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("AGENT_LOG_LEVEL", "INFO")
    )
    log_file: Optional[str] = field(
        default_factory=lambda: os.getenv("AGENT_LOG_FILE", "")
        or None
    )


@dataclass
class AppConfig:
    """应用总配置"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    engine: EngineConfig = field(default_factory=EngineConfig)
    data_dir: str = field(
        default_factory=lambda: os.getenv(
            "AGENT_DATA_DIR",
            os.path.join(os.getcwd(), "data"),
        )
    )

    @classmethod
    def from_file(cls, path: str) -> AppConfig:
        """从JSON配置文件加载"""
        if not os.path.exists(path):
            return cls()

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        llm_cfg = LLMConfig(**data.get("llm", {}))
        email_cfg = EmailConfig(**data.get("email", {}))
        engine_cfg = EngineConfig(**data.get("engine", {}))

        return cls(
            llm=llm_cfg,
            email=email_cfg,
            engine=engine_cfg,
            data_dir=data.get("data_dir", os.path.join(os.getcwd(), "data")),
        )

    def validate(self) -> list[str]:
        """校验配置完整性，返回缺失项列表"""
        warnings = []
        if not self.llm.api_key:
            warnings.append("LLM API密钥未配置 (DASHSCOPE_API_KEY)")
        if not self.email.imap_server:
            warnings.append("IMAP服务器未配置 (IMAP_SERVER)")
        if not self.email.smtp_server:
            warnings.append("SMTP服务器未配置 (SMTP_SERVER)")
        if not self.email.account:
            warnings.append("邮箱账号未配置 (EMAIL_ACCOUNT)")
        return warnings
