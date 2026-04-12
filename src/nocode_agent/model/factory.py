"""模型客户端构建与上下文窗口解析。"""

from __future__ import annotations

import ipaddress
import logging
from typing import Any

import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from nocode_agent.config import normalize_model_base_url, resolve_model_provider

logger = logging.getLogger(__name__)

# 已知模型的上下文窗口大小。
# 匹配规则：模型名包含 key 即命中（小写比较）。
_CONTEXT_WINDOWS: dict[str, int] = {
    # ── 智谱 GLM 系列 ─────────────────────────────
    "glm-4-long": 1_000_000,
    "glm-4v": 8_000,
    "glm-4v-plus": 8_000,
    "glm-4": 128_000,
    # ── Anthropic Claude 系列 ──────────────────────
    "claude-opus-4": 200_000,
    "claude-sonnet-4": 200_000,
    "claude-3-7-sonnet": 200_000,
    "claude-3-5-sonnet": 200_000,
    "claude-3-5-haiku": 200_000,
    "claude-3-opus": 200_000,
    "claude-3-sonnet": 200_000,
    "claude-3-haiku": 200_000,
    # ── OpenAI 系列 ───────────────────────────────
    "gpt-4.5": 128_000,
    "gpt-4o": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4-32k": 32_768,
    "gpt-4": 8_192,
    "gpt-3.5": 16_385,
    "o3-mini": 200_000,
    "o3": 200_000,
    "o4-mini": 200_000,
    "o1-mini": 128_000,
    "o1-preview": 128_000,
    "o1": 200_000,
}


def resolve_context_window(model: str) -> int:
    """根据模型名称解析上下文窗口大小。"""
    model_lower = model.lower()
    for key in sorted(_CONTEXT_WINDOWS, key=len, reverse=True):
        if key in model_lower:
            return _CONTEXT_WINDOWS[key]
    return 128_000


def build_model(
    api_key: str,
    model: str,
    base_url: str,
    temperature: float,
    max_tokens: int,
    proxy: str = "",
    no_proxy: list[str] | None = None,
    request_timeout: float = 90.0,
) -> BaseChatModel:
    """按 provider 构建聊天模型客户端。"""
    normalized_base_url = normalize_model_base_url(base_url)
    provider = resolve_model_provider({"base_url": normalized_base_url})
    if provider == "anthropic":
        kwargs: dict[str, Any] = {
            "model": model,
            "api_key": api_key,
            "base_url": normalized_base_url,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "max_retries": 6,
            "timeout": request_timeout,
        }
        if proxy:
            kwargs["anthropic_proxy"] = proxy
        if proxy and no_proxy:
            # Anthropic 客户端暂不支持像 OpenAI 客户端那样显式挂载 no_proxy 规则。
            logger.warning(
                "Anthropic client ignores explicit no_proxy mounts; proxy=%s, no_proxy=%s",
                proxy,
                ",".join(no_proxy),
            )
        return ChatAnthropic(**kwargs)

    kwargs = {
        "model": model,
        "api_key": api_key,
        "base_url": normalized_base_url,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "max_retries": 6,
        "timeout": request_timeout,
    }
    if proxy:
        mounts = build_no_proxy_mounts(no_proxy)
        # 用显式 httpx client 支持 no_proxy，而不是仅传 openai_proxy。
        kwargs["http_client"] = httpx.Client(
            proxy=proxy,
            mounts=mounts,
            timeout=request_timeout,
        )
        kwargs["http_async_client"] = httpx.AsyncClient(
            proxy=proxy,
            mounts=mounts,
            timeout=request_timeout,
        )
    return ChatOpenAI(**kwargs)


def build_no_proxy_mounts(no_proxy: list[str] | None) -> dict[str, None] | None:
    """把 no_proxy 配置转成 httpx mounts 规则。"""
    mounts: dict[str, None] = {}
    for raw_item in no_proxy or []:
        item = str(raw_item).strip()
        if not item:
            continue
        if item == "*":
            # `all://` 直连表示完全禁用代理，优先级最高。
            return {"all://": None}
        if "://" in item:
            mounts[item] = None
            continue
        if item.startswith("[") and item.endswith("]"):
            mounts[f"all://{item}"] = None
            continue
        if "/" in item:
            try:
                ipaddress.ip_network(item, strict=False)
            except ValueError:
                mounts[f"all://*{item}"] = None
            else:
                mounts[f"all://{item}"] = None
            continue
        try:
            ipaddress.ip_address(item)
        except ValueError:
            pass
        else:
            if ":" in item:
                mounts[f"all://[{item}]"] = None
            else:
                mounts[f"all://{item}"] = None
            continue
        if item.lower() == "localhost":
            mounts[f"all://{item}"] = None
            continue
        mounts[f"all://*{item}"] = None
    return mounts or None
