"""模型客户端构建与上下文窗口解析。"""

from __future__ import annotations

import ipaddress
import json
import logging
import threading
import time
import urllib.request
from typing import Any

import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from nocode_agent.config import normalize_model_base_url, resolve_model_provider
from nocode_agent.tool.kit import _sanitize_text

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

# ── models.dev 远程上下文窗口查询 ──────────────────────────────────
_MODELS_DEV_URL = "https://models.dev/api.json"
_CACHE_TTL = 86_400  # 24 hours

# 进程级缓存: {model_id_lower: (context_window, timestamp)}
_models_dev_cache: dict[str, tuple[int, float]] = {}
_cache_lock = threading.Lock()


def _load_models_dev() -> None:
    """Fetch and cache context window data from models.dev."""
    try:
        req = urllib.request.Request(
            _MODELS_DEV_URL, headers={"User-Agent": "nocode-agent"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        now = time.time()
        with _cache_lock:
            for provider_data in data.values():
                if not isinstance(provider_data, dict):
                    continue
                for mid, m in provider_data.get("models", {}).items():
                    ctx = (m.get("limit") or {}).get("context")
                    if ctx and isinstance(ctx, int):
                        _models_dev_cache[mid.lower()] = (ctx, now)
        logger.debug("Loaded models.dev context data, %d models cached", len(_models_dev_cache))
    except Exception:
        logger.debug("Failed to fetch models.dev data", exc_info=True)


def preload_models_dev() -> None:
    """Trigger background preload of models.dev data."""
    if _models_dev_cache:
        return
    threading.Thread(target=_load_models_dev, daemon=True).start()


def _lookup_models_dev(model: str) -> int | None:
    """Look up context window from models.dev cache."""
    model_lower = model.lower()
    with _cache_lock:
        if model_lower in _models_dev_cache:
            ctx, ts = _models_dev_cache[model_lower]
            if time.time() - ts < _CACHE_TTL:
                return ctx
    # Cache miss or expired — trigger background refresh
    threading.Thread(target=_load_models_dev, daemon=True).start()
    return None


def resolve_context_window(model: str) -> int:
    """根据模型名称解析上下文窗口大小。"""
    model_lower = model.lower()
    # 1. Try models.dev cache (exact match)
    dev_ctx = _lookup_models_dev(model_lower)
    if dev_ctx is not None:
        return dev_ctx
    # 2. Fallback to hardcoded table (substring match)
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
    ssl_verify: bool = True,
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
            "stream_usage": True,  # 流式模式下也返回 usage_metadata
        }
        if proxy or not ssl_verify:
            anthropic_httpx_kwargs: dict[str, Any] = {
                "timeout": request_timeout,
                "verify": ssl_verify,
            }
            if proxy:
                anthropic_httpx_kwargs["proxy"] = proxy
            kwargs["http_client"] = httpx.Client(**anthropic_httpx_kwargs)
            kwargs["http_async_client"] = httpx.AsyncClient(**anthropic_httpx_kwargs)
        if proxy and no_proxy:
            # Anthropic 客户端暂不支持像 OpenAI 客户端那样显式挂载 no_proxy 规则。
            logger.warning(
                "Anthropic client ignores explicit no_proxy mounts; proxy=%s, no_proxy=%s",
                proxy,
                ",".join(no_proxy),
            )
        return _make_sanitized_model(ChatAnthropic(**kwargs))

    kwargs = {
        "model": model,
        "api_key": api_key,
        "base_url": normalized_base_url,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "max_retries": 6,
        "timeout": request_timeout,
        "stream_usage": True,  # 流式模式下也返回 usage_metadata
    }
    if proxy:
        mounts = build_no_proxy_mounts(no_proxy)
        # 用显式 httpx client 支持 no_proxy，而不是仅传 openai_proxy。
        kwargs["http_client"] = httpx.Client(
            proxy=proxy,
            mounts=mounts,
            timeout=request_timeout,
            verify=ssl_verify,
        )
        kwargs["http_async_client"] = httpx.AsyncClient(
            proxy=proxy,
            mounts=mounts,
            timeout=request_timeout,
            verify=ssl_verify,
        )
    elif not ssl_verify:
        kwargs["http_client"] = httpx.Client(
            timeout=request_timeout,
            verify=False,
        )
        kwargs["http_async_client"] = httpx.AsyncClient(
            timeout=request_timeout,
            verify=False,
        )
    return _make_sanitized_model(ChatOpenAI(**kwargs))


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


# ── Surrogate sanitization wrapper ────────────────────────────────
# The TUI may split emoji surrogate pairs (e.g. when cursor moves
# through non-BMP chars), producing lone surrogates like \uDCA6.
# These end up in the LangGraph checkpoint and crash the OpenAI /
# Anthropic client when it tries to serialize the request to UTF-8.
# Patching the model ensures every API call gets clean messages
# without requiring a checkpoint migration.


def _sanitize_messages(messages: list) -> list:
    """Sanitize all string content in a list of LangChain messages."""
    result: list = []
    any_changed = False
    for msg in messages:
        content = getattr(msg, "content", None)
        if isinstance(content, str):
            new_content = _sanitize_text(content)
            if new_content != content:
                any_changed = True
                try:
                    msg = msg.model_copy(update={"content": new_content})
                except AttributeError:
                    msg = msg.copy(update={"content": new_content})
        elif isinstance(content, list):
            new_items: list = []
            items_changed = False
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    new_text = _sanitize_text(item["text"])
                    if new_text != item["text"]:
                        items_changed = True
                        any_changed = True
                        item = {**item, "text": new_text}
                new_items.append(item)
            if items_changed:
                try:
                    msg = msg.model_copy(update={"content": new_items})
                except AttributeError:
                    msg = msg.copy(update={"content": new_items})
        result.append(msg)
    if any_changed:
        logger.warning("Sanitized lone surrogates in %d message(s)", len(messages))
    return result


def _make_sanitized_model(model: BaseChatModel) -> BaseChatModel:
    """Patch a model to sanitize messages before API calls."""
    original_astream = model._astream

    async def _sanitized_astream(messages, stop=None, run_manager=None, **kwargs):
        messages = _sanitize_messages(messages)
        async for chunk in original_astream(messages, stop=stop, run_manager=run_manager, **kwargs):
            yield chunk

    model._astream = _sanitized_astream

    original_agenerate = getattr(model, "_agenerate", None)
    if original_agenerate is not None:
        async def _sanitized_agenerate(messages, stop=None, run_manager=None, **kwargs):
            messages = _sanitize_messages(messages)
            return await original_agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)

        model._agenerate = _sanitized_agenerate

    return model
