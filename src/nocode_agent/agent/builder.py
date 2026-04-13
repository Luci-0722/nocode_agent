"""MainAgent 前置装配 helper。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from nocode_agent.compression import (
    AutoCompactor,
    CompressionLifecycleMiddleware,
    CompressionConfig,
    FileReadTracker,
    MicrocompactMiddleware,
    SessionMemoryExtractor,
    build_auto_compact_config,
    build_session_memory_config,
)
from nocode_agent.model import build_model
from nocode_agent.runtime.hitl import build_human_in_the_loop_middleware
from nocode_agent.runtime.interaction import (
    InteractiveSessionBroker,
    PendingUserInputMiddleware,
)


def _build_middleware(
    compression: dict | None,
    *,
    context_window: int,
    auto_compactor: AutoCompactor | None = None,
    sm_extractor: SessionMemoryExtractor | None = None,
) -> list[Any]:
    """构造主代理与子代理共用的压缩中间件链。"""
    middleware: list[Any] = []

    if compression:
        config = CompressionConfig.from_yaml(compression, context_window=context_window)
        middleware.append(MicrocompactMiddleware(config).as_langchain_middleware())

    # 始终添加 CompressionLifecycleMiddleware 以发送 token_usage 事件
    middleware.append(
        CompressionLifecycleMiddleware(
            auto_compactor=auto_compactor,
            sm_extractor=sm_extractor,
            context_window=context_window,
        )
    )

    return middleware


def _build_session_memory_extractor(
    *,
    api_key: str,
    model: str,
    base_url: str,
    session_memory: dict | None,
    proxy: str,
    no_proxy: list[str] | None,
    request_timeout: float,
    thread_id: str,
) -> SessionMemoryExtractor | None:
    """按配置构造 Session Memory 提取器。"""
    sm_config = build_session_memory_config(session_memory)
    if not sm_config:
        return None

    sm_llm = build_model(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=0.1,
        max_tokens=4096,
        proxy=proxy,
        no_proxy=no_proxy,
        request_timeout=request_timeout,
    )
    return SessionMemoryExtractor(
        config=sm_config,
        llm=sm_llm,
        thread_id=thread_id,
    )


def _build_auto_compactor(
    *,
    api_key: str,
    model: str,
    base_url: str,
    auto_compact: dict | None,
    context_window: int,
    proxy: str,
    no_proxy: list[str] | None,
    request_timeout: float,
    sm_extractor: SessionMemoryExtractor | None,
) -> AutoCompactor | None:
    """按配置构造 Auto-Compact 组件。"""
    ac_config = build_auto_compact_config(auto_compact, context_window=context_window)
    if not ac_config:
        return None

    summary_llm = build_model(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=0.1,
        max_tokens=ac_config.max_summary_tokens,
        proxy=proxy,
        no_proxy=no_proxy,
        request_timeout=request_timeout,
    )
    return AutoCompactor(
        config=ac_config,
        context_window=context_window,
        llm=summary_llm,
        file_tracker=FileReadTracker(),
        sm_extractor=sm_extractor,
    )


@dataclass
class MainAgentSetupArtifacts:
    """`create_mainagent()` 前置装配产物。"""

    resolved_thread_id: str
    interactive_broker: InteractiveSessionBroker
    middleware: list[Any]
    main_middleware: list[Any]


def build_mainagent_setup(
    *,
    api_key: str,
    model: str,
    base_url: str,
    compression: dict | None,
    auto_compact: dict | None,
    session_memory: dict | None,
    permissions: dict | None,
    thread_id: str | None,
    context_window: int,
    proxy: str,
    no_proxy: list[str] | None,
    request_timeout: float,
) -> MainAgentSetupArtifacts:
    """构造 MainAgent 的会话前置装配产物。"""
    resolved_thread_id = thread_id or f"mainagent-{uuid4().hex}"
    sm_extractor = _build_session_memory_extractor(
        api_key=api_key,
        model=model,
        base_url=base_url,
        session_memory=session_memory,
        proxy=proxy,
        no_proxy=no_proxy,
        request_timeout=request_timeout,
        thread_id=resolved_thread_id,
    )
    auto_compactor = _build_auto_compactor(
        api_key=api_key,
        model=model,
        base_url=base_url,
        auto_compact=auto_compact,
        context_window=context_window,
        proxy=proxy,
        no_proxy=no_proxy,
        request_timeout=request_timeout,
        sm_extractor=sm_extractor,
    )

    interactive_broker = InteractiveSessionBroker()
    middleware = _build_middleware(
        compression,
        context_window=context_window,
        auto_compactor=auto_compactor,
        sm_extractor=sm_extractor,
    )
    human_in_the_loop_middleware = build_human_in_the_loop_middleware(permissions)
    if human_in_the_loop_middleware is not None:
        middleware.append(human_in_the_loop_middleware)

    return MainAgentSetupArtifacts(
        resolved_thread_id=resolved_thread_id,
        interactive_broker=interactive_broker,
        middleware=middleware,
        main_middleware=[*middleware, PendingUserInputMiddleware(interactive_broker)],
    )
