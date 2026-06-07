"""
LLM客户端抽象层
===============
封装对大语言模型API的调用，支持通义千问/OpenAI兼容接口。
"""

from __future__ import annotations

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """LLM调用的标准化返回"""
    content: str
    token_count: int = 0
    model: str = ""
    latency_ms: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)


class BaseLLMClient(ABC):
    """LLM客户端基类"""

    @abstractmethod
    def chat(self, messages: list[dict], system_prompt: str, **kwargs) -> LLMResponse:
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """估算token数量"""
        ...


class TongyiQianwenClient(BaseLLMClient):
    """
    通义千问 API 客户端（兼容 OpenAI 接口格式）
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qwen-plus",
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        timeout: int = 60,
        max_retries: int = 3,
    ):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "").strip()
        if not self.api_key:
            raise ValueError(
                "未配置API密钥。请设置环境变量 DASHSCOPE_API_KEY，"
                "或在配置文件中指定 api_key。"
            )
        # 检测是否误用了示例文件中的占位文字
        if any(ord(c) > 127 for c in self.api_key):
            raise ValueError(
                f"API密钥包含非ASCII字符，请检查 DASHSCOPE_API_KEY 是否正确设置。\n"
                f"当前值: {self.api_key[:30]}...\n"
                f"提示：请将 .env 文件中的 sk-你的阿里云API密钥 替换为从阿里云获取的真实密钥。"
            )
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """
        调用通义千问API进行对话。

        Args:
            messages: 历史消息列表
            system_prompt: 系统提示词
            temperature: 采样温度（默认0.1，偏向确定性输出）
            max_tokens: 最大输出token数

        Returns:
            LLMResponse: 标准化响应
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json; charset=utf-8",
        }

        full_messages = [{"role": "system", "content": system_prompt}]
        full_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        # 手动序列化 JSON，确保所有非 ASCII 字符被转义为 \uXXXX
        # 避免 requests 的 json 参数在某些版本/环境下触发 latin-1 编码错误
        try:
            body_bytes = json.dumps(payload, ensure_ascii=True).encode("ascii")
        except Exception as e:
            raise RuntimeError(f"JSON serialization failed: {e}")

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                start = time.time()
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    data=body_bytes,
                    timeout=self.timeout,
                )
                elapsed = (time.time() - start) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    choice = data["choices"][0]
                    content = choice["message"]["content"]
                    token_count = data.get("usage", {}).get("total_tokens", 0)

                    return LLMResponse(
                        content=content,
                        token_count=token_count,
                        model=self.model,
                        latency_ms=elapsed,
                        raw=data,
                    )
                elif resp.status_code == 429 and attempt < self.max_retries:
                    # 限流重试
                    wait = min(2 ** attempt, 30)
                    time.sleep(wait)
                    last_error = f"Rate limited (429), retry {attempt}/{self.max_retries}"
                    continue
                else:
                    last_error = (
                        f"API error {resp.status_code}: {resp.text[:500]}"
                    )
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    raise RuntimeError(last_error)

            except requests.exceptions.Timeout:
                last_error = f"Request timeout ({self.timeout}s), retry {attempt}/{self.max_retries}"
                if attempt < self.max_retries:
                    continue
                raise RuntimeError(last_error)
            except requests.exceptions.RequestException as e:
                last_error = f"Request failed: {e}"
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(last_error)

        raise RuntimeError(f"All retries exhausted: {last_error}")

    def count_tokens(self, text: str) -> int:
        """简单的token估算（中文约1.5字/token，英文约4字符/token）"""
        import re
        chinese_chars = len(re.findall(r'[一-鿿]', text))
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars / 4) + 4


class OpenAIClient(BaseLLMClient):
    """
    OpenAI 兼容接口客户端（备选方案）
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 60,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json; charset=utf-8",
        }
        full_messages = [{"role": "system", "content": system_prompt}]
        full_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        # 手动序列化 JSON，确保所有非 ASCII 字符被转义为 \uXXXX
        try:
            body_bytes = json.dumps(payload, ensure_ascii=True).encode("ascii")
        except Exception as e:
            raise RuntimeError(f"JSON serialization failed: {e}")

        for attempt in range(1, self.max_retries + 1):
            try:
                start = time.time()
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    data=body_bytes,
                    timeout=self.timeout,
                )
                elapsed = (time.time() - start) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    choice = data["choices"][0]
                    return LLMResponse(
                        content=choice["message"]["content"],
                        token_count=data.get("usage", {}).get("total_tokens", 0),
                        model=self.model,
                        latency_ms=elapsed,
                        raw=data,
                    )
                else:
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    raise RuntimeError(f"API error {resp.status_code}: {resp.text[:500]}")
            except requests.exceptions.Timeout:
                if attempt < self.max_retries:
                    continue
                raise

        raise RuntimeError("All retries exhausted")

    def count_tokens(self, text: str) -> int:
        import re
        chinese_chars = len(re.findall(r'[一-鿿]', text))
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars / 4) + 4
