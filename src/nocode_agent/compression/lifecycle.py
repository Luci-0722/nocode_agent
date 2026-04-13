"""压缩生命周期中间件。"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain_core.messages import AIMessage, RemoveMessage, ToolMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.runtime import Runtime
from langgraph.types import Command
from typing_extensions import override

from nocode_agent.compression.auto_compact import AutoCompactor
from nocode_agent.compression.session_memory import SessionMemoryExtractor

logger = logging.getLogger(__name__)


def get_context_tokens_from_metadata(messages: list[Any]) -> int:
    """从最后一条 AIMessage.usage_metadata 获取当前上下文 token 数。"""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            meta = getattr(msg, "usage_metadata", None)
            if meta and isinstance(meta, dict):
                input_tokens = meta.get("input_tokens", 0)
                logger.debug(
                    "Token usage from metadata: input_tokens=%d, full_meta=%s",
                    input_tokens,
                    meta,
                )
                return input_tokens
    logger.debug("No usage_metadata found in messages, returning 0")
    return 0


class CompressionLifecycleMiddleware(AgentMiddleware):
    """统一管理压缩相关生命周期。"""

    def __init__(
        self,
        auto_compactor: AutoCompactor | None = None,
        sm_extractor: SessionMemoryExtractor | None = None,
        context_window: int = 128_000,
    ) -> None:
        self._auto_compactor = auto_compactor
        self._sm_extractor = sm_extractor
        self._context_window = context_window

    @override
    async def abefore_model(
        self,
        state: AgentState[Any],
        runtime: Runtime[Any],
    ) -> dict[str, Any] | None:
        if not self._auto_compactor:
            return None

        messages = state["messages"]
        if not self._auto_compactor.should_trigger(messages):
            return None

        runtime.stream_writer({"type": "auto_compact_start"})

        logger.info("Auto-compact triggered in middleware, generating summary...")
        result = await self._auto_compactor.compact(messages)
        if result is None:
            runtime.stream_writer({"type": "auto_compact_failed"})
            logger.warning("Auto-compact failed in middleware, will retry next turn")
            return None

        logger.info(
            "Auto-compact completed in middleware: %d → %d tokens (%d files restored)",
            result.pre_tokens,
            result.post_tokens,
            result.files_restored,
        )

        from nocode_agent.runtime.file_state import get_file_state_cache

        get_file_state_cache().clear()
        runtime.stream_writer(
            {
                "type": "auto_compact_done",
                "strategy": result.strategy,
                "pre_tokens": result.pre_tokens,
                "post_tokens": result.post_tokens,
                "files_restored": result.files_restored,
            }
        )
        return {
            "messages": [
                RemoveMessage(id=REMOVE_ALL_MESSAGES),
                *result.messages,
            ]
        }

    @override
    async def aafter_model(
        self,
        state: AgentState[Any],
        runtime: Runtime[Any],
    ) -> dict[str, Any] | None:
        messages = state["messages"]

        if self._sm_extractor:
            await self._sm_extractor.maybe_extract(messages)

        input_tokens = get_context_tokens_from_metadata(messages)
        tokens_left = max(0, self._context_window - input_tokens)
        tokens_left_percent = max(0, min(100, round(tokens_left * 100 / self._context_window)))

        logger.debug(
            "Token usage report: input_tokens=%d, context_window=%d, tokens_left=%d, tokens_left_percent=%d",
            input_tokens,
            self._context_window,
            tokens_left,
            tokens_left_percent,
        )

        runtime.stream_writer(
            {
                "type": "token_usage",
                "input_tokens": input_tokens,
                "context_window": self._context_window,
                "tokens_left": tokens_left,
                "tokens_left_percent": tokens_left_percent,
            }
        )

        return None

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        if self._sm_extractor:
            self._sm_extractor.notify_tool_call()

        result = await handler(request)

        if (
            self._auto_compactor
            and isinstance(result, ToolMessage)
            and request.tool_call.get("name") == "read"
        ):
            self._auto_compactor.file_tracker.record_from_tool_message(result)

        return result


__all__ = [
    "CompressionLifecycleMiddleware",
    "get_context_tokens_from_metadata",
]
