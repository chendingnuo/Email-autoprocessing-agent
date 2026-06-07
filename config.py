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
            if key and not os.environ.get(key):
                os.environ[key] = value


# ── 邮件服务商预设 ─────────────────────────────────

PROVIDER_PRESETS: dict[str, dict] = {
    "gmail": {
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
    },
    "qq": {
        "imap_server": "imap.qq.com",
        "imap_port": 993,
        "smtp_server": "smtp.qq.com",
        "smtp_port": 465,
    },
}


@dataclass
class EmailAccountConfig:
    """单个邮箱账号的完整配置"""
    name: str = ""
    email: str = ""
    password: str = ""
    provider: str = "custom"
    imap_server: str = ""
    imap_port: int = 993
    smtp_server: str = ""
    smtp_port: int = 587

    def __post_init__(self):
        preset = PROVIDER_PRESETS.get(self.provider)
        if preset:
            if not self.imap_server:
                self.imap_server = preset["imap_server"]
                self.imap_port = preset["imap_port"]
            if not self.smtp_server:
                self.smtp_server = preset["smtp_server"]
                self.smtp_port = preset["smtp_port"]


def load_email_accounts(data_dir: str) -> dict[str, EmailAccountConfig]:
    """
    加载所有邮箱账号配置。
    返回值: {账号名: EmailAccountConfig}
    所有账号统一从 data/email_accounts.json 加载。
    兼容旧配置：如 JSON 文件不存在或为空，则从 .env 环境变量读取默认账号。
    """
    accounts: dict[str, EmailAccountConfig] = {}

    # 1. 主来源：email_accounts.json（含所有账号）
    accounts_file = os.path.join(data_dir, "email_accounts.json")
    if os.path.exists(accounts_file):
        try:
            with open(accounts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("accounts", []):
                acc = EmailAccountConfig(
                    name=item.get("name", "unknown"),
                    email=item.get("email", ""),
                    password=item.get("password", ""),
                    provider=item.get("provider", "custom"),
                    imap_server=item.get("imap_server", ""),
                    imap_port=item.get("imap_port", 993),
                    smtp_server=item.get("smtp_server", ""),
                    smtp_port=item.get("smtp_port", 587),
                )
                if acc.email and acc.name:
                    accounts[acc.name] = acc
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"加载 email_accounts.json 失败: {e}"
            )

    # 2. 兼容旧配置：JSON 不存在或无账号时从 .env 读取默认账号
    if not accounts:
        primary = EmailAccountConfig(
            name="default",
            email=os.getenv("EMAIL_ACCOUNT", ""),
            password=os.getenv("EMAIL_PASSWORD", ""),
            provider="custom",
            imap_server=os.getenv("IMAP_SERVER", ""),
            imap_port=int(os.getenv("IMAP_PORT", "993")),
            smtp_server=os.getenv("SMTP_SERVER", ""),
            smtp_port=int(os.getenv("SMTP_PORT", "465")),
        )
        if primary.email:
            accounts["default"] = primary

    return accounts


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
        default_factory=lambda: os.getenv(
            "AGENT_LOG_FILE",
            os.path.join(os.getcwd(), "data", "logs", "agent.log"),
        ) or None
    )


@dataclass
class AppConfig:
    """应用总配置"""
    llm: LLMConfig = field(default_factory=LLMConfig)
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
        engine_cfg = EngineConfig(**data.get("engine", {}))

        return cls(
            llm=llm_cfg,
            engine=engine_cfg,
            data_dir=data.get("data_dir", os.path.join(os.getcwd(), "data")),
        )

    def get_email_accounts(self) -> dict[str, EmailAccountConfig]:
        """便捷方法：获取所有邮箱账号"""
        return load_email_accounts(self.data_dir)

    def validate(self) -> list[str]:
        """校验配置完整性，返回缺失项列表"""
        warnings = []
        if not self.llm.api_key:
            warnings.append("LLM API密钥未配置 (DASHSCOPE_API_KEY)")
        return warnings
