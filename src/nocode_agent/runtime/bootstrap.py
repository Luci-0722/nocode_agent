"""公共运行时启动逻辑。

把配置读取、日志初始化、API Key 解析、MainAgent 参数装配集中到这里，
供 TUI backend 与 ACP server 共享，减少重复逻辑。
"""

from __future__ import annotations

from typing import Any

from nocode_agent.agent import MainAgent, create_mainagent
from nocode_agent.config import (
    load_config,
    resolve_api_key,
    resolve_no_proxy,
    resolve_proxy,
    resolve_request_timeout,
)
from nocode_agent.log import setup_logging

_DEFAULT_MODEL = "glm-4-flash"
_DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
_DEFAULT_MAX_TOKENS = 4096
_DEFAULT_TEMPERATURE = 0.7
_DEFAULT_SUBAGENT_TEMPERATURE = 0.1
_API_KEY_ERROR = (
    "missing API key: set NOCODE_API_KEY/DASHSCOPE_API_KEY/BAILIAN_API_KEY/"
    "ANTHROPIC_API_KEY/OPENAI_API_KEY/OLLAMA_API_KEY/ZHIPU_API_KEY, or configure api_key"
)


def load_runtime_config(
    config_path: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """读取运行时配置，并应用显式覆盖项。"""
    config = load_config(config_path)
    if not overrides:
        return config

    merged = dict(config)
    for key, value in overrides.items():
        if value is None:
            continue
        merged[key] = value
    return merged


def configure_runtime_logging(config: dict[str, Any] | None = None) -> None:
    """根据配置初始化日志。"""
    payload = config or {}
    level = str(payload.get("log_level", "") or None) if payload.get("log_level") else None
    setup_logging(level=level)


def require_api_key(config: dict[str, Any]) -> str:
    """解析并校验 API Key。"""
    api_key = resolve_api_key(config)
    if not api_key:
        raise RuntimeError(_API_KEY_ERROR)
    return api_key


def build_mainagent_kwargs(
    config: dict[str, Any],
    *,
    api_key: str | None = None,
    thread_id: str | None = None,
    mcp_servers: list[Any] | None = None,
) -> dict[str, Any]:
    """把运行时配置转换成 ``create_mainagent`` 参数。"""
    resolved_api_key = api_key or require_api_key(config)
    return {
        "api_key": resolved_api_key,
        "model": config.get("model", _DEFAULT_MODEL),
        "base_url": config.get("base_url", _DEFAULT_BASE_URL),
        "max_tokens": config.get("max_tokens", _DEFAULT_MAX_TOKENS),
        "temperature": config.get("temperature", _DEFAULT_TEMPERATURE),
        "compression": config.get("compression"),
        "auto_compact": config.get("auto_compact"),
        "session_memory": config.get("session_memory"),
        "permissions": config.get("permissions"),
        "subagent_model": config.get("subagent_model"),
        "subagent_temperature": config.get("subagent_temperature", _DEFAULT_SUBAGENT_TEMPERATURE),
        "thread_id": thread_id,
        "persistence_config": config,
        "mcp_servers": mcp_servers,
        "proxy": resolve_proxy(config),
        "no_proxy": resolve_no_proxy(config),
        "request_timeout": resolve_request_timeout(config),
    }


async def create_agent_from_config(
    config: dict[str, Any],
    *,
    thread_id: str | None = None,
    mcp_servers: list[Any] | None = None,
) -> MainAgent:
    """基于配置创建 MainAgent。"""
    return await create_mainagent(
        **build_mainagent_kwargs(
            config,
            thread_id=thread_id,
            mcp_servers=mcp_servers,
        )
    )
