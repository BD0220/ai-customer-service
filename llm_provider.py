"""
LLM Provider 抽象层
将大模型调用抽象为统一接口，支持 DeepSeek / OpenAI 等多 Provider 无缝切换。
通过环境变量 LLM_PROVIDER 选择，新增 Provider 只需继承 LLMProvider 并实现 chat_completion。
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """LLM Provider 抽象基类，所有 Provider 必须实现 chat_completion 方法。"""

    @abstractmethod
    def chat_completion(self, messages: list, tools: list = None, **kwargs) -> dict:
        """
        调用大模型聊天补全接口。

        Args:
            messages: 消息列表（OpenAI 格式）
            tools: Function Calling 工具定义列表
            **kwargs: 其他参数（temperature、max_tokens 等）

        Returns:
            统一格式的响应字典：
            {
                "content": str,           # 文本回复（无 tool_calls 时）
                "tool_calls": [           # 工具调用列表（有则返回）
                    {
                        "id": str,
                        "name": str,
                        "arguments": dict,
                    }
                ]
            }
        """
        pass


class DeepSeekProvider(LLMProvider):
    """DeepSeek API Provider（兼容 OpenAI SDK）。"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        if not self.api_key:
            raise ValueError("缺少 DEEPSEEK_API_KEY 环境变量")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        logger.info(f"DeepSeekProvider 初始化完成，模型：{self.model}")

    def chat_completion(self, messages: list, tools: list = None, **kwargs) -> dict:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice=kwargs.get("tool_choice", "auto"),
            temperature=kwargs.get("temperature", 0.5),
            max_tokens=kwargs.get("max_tokens", 1000),
        )
        msg = response.choices[0].message
        return self._normalize_response(msg)

    @staticmethod
    def _normalize_response(msg) -> dict:
        """将 OpenAI SDK 响应统一为标准格式。"""
        result = {"content": (msg.content or "").strip(), "tool_calls": []}
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}
                result["tool_calls"].append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": arguments,
                })
        return result


class OpenAIProvider(LLMProvider):
    """OpenAI API Provider。"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if not self.api_key:
            raise ValueError("缺少 OPENAI_API_KEY 环境变量")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        logger.info(f"OpenAIProvider 初始化完成，模型：{self.model}")

    def chat_completion(self, messages: list, tools: list = None, **kwargs) -> dict:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice=kwargs.get("tool_choice", "auto"),
            temperature=kwargs.get("temperature", 0.5),
            max_tokens=kwargs.get("max_tokens", 1000),
        )
        msg = response.choices[0].message
        return DeepSeekProvider._normalize_response(msg)


# Provider 注册表，新增 Provider 在此注册即可
PROVIDER_REGISTRY = {
    "deepseek": DeepSeekProvider,
    "openai": OpenAIProvider,
}


def get_llm_provider(provider_name: str = None) -> LLMProvider:
    """
    工厂函数：根据配置返回 LLM Provider 实例。

    Args:
        provider_name: Provider 名称，不传则从 LLM_PROVIDER 环境变量读取（默认 deepseek）

    Returns:
        LLMProvider 实例
    """
    name = (provider_name or os.getenv("LLM_PROVIDER", "deepseek")).lower()
    provider_cls = PROVIDER_REGISTRY.get(name)
    if not provider_cls:
        raise ValueError(
            f"未知的 LLM Provider：{name}，"
            f"当前支持：{', '.join(PROVIDER_REGISTRY.keys())}"
        )
    return provider_cls()
