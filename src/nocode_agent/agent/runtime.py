"""MainAgent 的运行时流包装。"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langgraph.types import Command

from nocode_agent.persistence import CheckpointerManager
from nocode_agent.runtime.hitl import extract_hitl_request
from nocode_agent.runtime.interaction import InteractiveSessionBroker

logger = logging.getLogger(__name__)

_STREAM_MODES = ["messages", "updates", "custom"]
_MAX_RETRIES = 5
_BASE_RETRY_DELAY = 2.0


def _is_retryable_error(exc: Exception) -> bool:
    """判断是否为可重试的 API 错误（429、5xx、网络超时等）。"""
    exc_str = str(exc).lower()
    # HTTP 429 rate limit
    if "429" in exc_str or "rate" in exc_str or "速率" in exc_str:
        return True
    # HTTP 5xx server errors
    if any(code in exc_str for code in ("500", "502", "503", "504")):
        return True
    # Connection / timeout errors
    if isinstance(exc, (ConnectionError, TimeoutError, asyncio.TimeoutError)):
        return True
    for klass in (
        "ConnectionError",
        "TimeoutError",
        "APIConnectionError",
        "APITimeoutError",
        "RateLimitError",
        "InternalServerError",
        "ServiceUnavailableError",
    ):
        if klass in type(exc).__name__:
            return True
    return False


def _render_tool_output(content: Any) -> str:
    """把工具输出压缩成稳定的前端展示文本。"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content[:4000] + ("..." if len(content) > 4000 else "")
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
                    continue
                parts.append(json.dumps(item, ensure_ascii=False))
                continue
            parts.append(str(item))
        rendered = "\n".join(part for part in parts if part).strip()
        return rendered[:4000] + ("..." if len(rendered) > 4000 else "")
    rendered = str(content)
    return rendered[:4000] + ("..." if len(rendered) > 4000 else "")


def _normalize_subagent_type(agent_name: str) -> str:
    """把运行时节点名映射回前端已知的子代理类型。"""
    mapping = {
        "subagent_general_purpose": "general-purpose",
        "subagent_explore": "Explore",
        "subagent_plan": "Plan",
        "subagent_verification": "verification",
    }
    return mapping.get(agent_name, agent_name or "subagent")


def _subagent_key_from_namespace(namespace: tuple[str, ...]) -> tuple[str, ...]:
    if not namespace:
        return ()
    return (namespace[0],)


def _parent_tool_call_id_from_namespace(namespace: tuple[str, ...]) -> str:
    if not namespace:
        return ""
    head = namespace[0]
    if ":" not in head:
        return ""
    node_name, task_id = head.split(":", 1)
    if node_name != "tools":
        return ""
    return task_id


def _extract_interrupt_request(
    update_data: Any,
) -> tuple[str, dict[str, Any] | None]:
    """从 langgraph updates 里提取 HITL interrupt 请求。"""
    if not isinstance(update_data, dict) or "__interrupt__" not in update_data:
        return "", None

    interrupts = update_data.get("__interrupt__") or ()
    for interrupt in interrupts:
        request_id = str(getattr(interrupt, "id", "") or "")
        request = extract_hitl_request(getattr(interrupt, "value", None))
        if request:
            return request_id, request
    return "", None


@dataclass
class _SubgraphTracker:
    """跟踪子代理运行时事件与摘要文本。"""

    meta_by_key: dict[tuple[str, ...], dict[str, str]] = field(default_factory=dict)
    text_by_key: dict[tuple[str, ...], list[str]] = field(default_factory=dict)

    def register_subagent_chunk(
        self,
        namespace: tuple[str, ...],
        agent_name: str,
        token: Any,
    ) -> list[tuple[Any, ...]]:
        """记录子代理的首个 token，并在必要时产出 start 事件。"""
        events: list[tuple[Any, ...]] = []
        subagent_key = _subagent_key_from_namespace(namespace)
        parent_tool_call_id = _parent_tool_call_id_from_namespace(namespace)
        if (
            subagent_key
            and parent_tool_call_id
            and subagent_key not in self.meta_by_key
        ):
            subagent_type = _normalize_subagent_type(agent_name)
            self.meta_by_key[subagent_key] = {
                "parent_tool_call_id": parent_tool_call_id,
                "subagent_id": " / ".join(subagent_key),
                "subagent_type": subagent_type,
            }
            events.append(
                (
                    "subagent_start",
                    {
                        "type": "subagent_start",
                        "parent_tool_call_id": parent_tool_call_id,
                        "subagent_id": " / ".join(subagent_key),
                        "subagent_type": subagent_type,
                        "thread_id": " / ".join(subagent_key),
                    },
                )
            )

        if isinstance(token, AIMessageChunk) and token.text and subagent_key in self.meta_by_key:
            self.text_by_key.setdefault(subagent_key, []).append(token.text)
        return events

    def build_model_events(
        self,
        namespace: tuple[str, ...],
        message: AIMessage,
    ) -> list[tuple[Any, ...]]:
        """把模型阶段消息转成 tool_start 相关事件。"""
        events: list[tuple[Any, ...]] = []
        subagent_key = _subagent_key_from_namespace(namespace)
        if subagent_key and subagent_key in self.meta_by_key:
            subgraph_meta = self.meta_by_key.get(subagent_key, {})
            parent_tool_call_id = subgraph_meta.get("parent_tool_call_id", "")
            for tool_call in message.tool_calls:
                events.append(
                    (
                        "subagent_tool_start",
                        {
                            "type": "subagent_tool_start",
                            "parent_tool_call_id": parent_tool_call_id,
                            "subagent_id": subgraph_meta.get("subagent_id", " / ".join(subagent_key)),
                            "subagent_type": subgraph_meta.get("subagent_type", "subagent"),
                            "name": tool_call["name"],
                            "args": tool_call.get("args", {}),
                            "tool_call_id": tool_call.get("id", ""),
                        },
                    )
                )
            return events

        for tool_call in message.tool_calls:
            events.append(
                (
                    "tool_start",
                    tool_call["name"],
                    tool_call.get("args", {}),
                    tool_call.get("id", ""),
                )
            )
        return events

    def build_tool_events(
        self,
        namespace: tuple[str, ...],
        message: ToolMessage,
    ) -> list[tuple[Any, ...]]:
        """把工具阶段消息转成 tool_end / subagent_finish 事件。"""
        events: list[tuple[Any, ...]] = []
        subagent_key = _subagent_key_from_namespace(namespace)
        if subagent_key and subagent_key in self.meta_by_key:
            subgraph_meta = self.meta_by_key.get(subagent_key, {})
            parent_tool_call_id = subgraph_meta.get("parent_tool_call_id", "")
            events.append(
                (
                    "subagent_tool_end",
                    {
                        "type": "subagent_tool_end",
                        "parent_tool_call_id": parent_tool_call_id,
                        "subagent_id": subgraph_meta.get("subagent_id", " / ".join(subagent_key)),
                        "subagent_type": subgraph_meta.get("subagent_type", "subagent"),
                        "name": message.name or "tool",
                        "output": _render_tool_output(message.content),
                        "tool_call_id": getattr(message, "tool_call_id", ""),
                    },
                )
            )
            return events

        tool_call_id = getattr(message, "tool_call_id", "")
        if (message.name or "") == "delegate_code":
            finished_keys = [
                key
                for key, meta in self.meta_by_key.items()
                if meta.get("parent_tool_call_id") == str(tool_call_id or "")
            ]
            for finished_key in finished_keys:
                subgraph_meta = self.meta_by_key.get(finished_key, {})
                summary = "".join(self.text_by_key.get(finished_key, [])).strip()
                events.append(
                    (
                        "subagent_finish",
                        {
                            "type": "subagent_finish",
                            "parent_tool_call_id": str(tool_call_id or ""),
                            "subagent_id": subgraph_meta.get("subagent_id", " / ".join(finished_key)),
                            "subagent_type": subgraph_meta.get("subagent_type", "subagent"),
                            "summary": _render_tool_output(summary),
                        },
                    )
                )
                self.meta_by_key.pop(finished_key, None)
                self.text_by_key.pop(finished_key, None)

        events.append(
            (
                "tool_end",
                message.name or "tool",
                _render_tool_output(message.content),
                tool_call_id,
            )
        )
        return events

    def build_permission_request_event(
        self,
        request_id: str,
        request: dict[str, Any],
        namespace: tuple[str, ...],
    ) -> dict[str, Any]:
        """把 HITL interrupt 转成前端事件格式。"""
        payload: dict[str, Any] = {
            "type": "permission_request",
            "request_id": request_id,
            "actions": request.get("actions", []),
        }
        subagent_key = _subagent_key_from_namespace(namespace)
        if subagent_key and subagent_key in self.meta_by_key:
            meta = self.meta_by_key[subagent_key]
            payload["parent_tool_call_id"] = meta.get("parent_tool_call_id", "")
            payload["subagent_id"] = meta.get("subagent_id", " / ".join(subagent_key))
            payload["subagent_type"] = meta.get("subagent_type", "subagent")
        return payload


class MainAgentRuntime:
    """封装 MainAgent 会话流、事件转译和权限恢复。"""

    def __init__(
        self,
        agent: Any,
        checkpointer: CheckpointerManager,
        interactive_broker: InteractiveSessionBroker,
        thread_id: str,
    ) -> None:
        self._agent = agent
        self._checkpointer = checkpointer
        self._interactive_broker = interactive_broker
        self._thread_id = thread_id

    def _start_stream(
        self,
        current_input: Any,
        config: dict[str, Any],
    ) -> tuple[Any, asyncio.Task[Any]]:
        """启动一轮 langgraph astream，并预取下一个 chunk。"""
        stream_iter = self._agent.astream(
            current_input,
            config=config,
            stream_mode=_STREAM_MODES,
            subgraphs=True,
            version="v2",
        ).__aiter__()
        return stream_iter, asyncio.create_task(stream_iter.__anext__())

    async def _cancel_pending_task(
        self,
        next_chunk_task: asyncio.Task[Any] | None,
    ) -> None:
        """清理尚未消费的预取任务，避免协程泄漏。"""
        if next_chunk_task is None or next_chunk_task.done():
            return
        next_chunk_task.cancel()
        await asyncio.gather(next_chunk_task, return_exceptions=True)

    def _build_initial_input(self, user_input: str) -> dict[str, Any]:
        """构造用户首轮输入。"""
        return {"messages": [{"role": "user", "content": user_input}]}

    def _iter_update_events(
        self,
        namespace: tuple[str, ...],
        update_data: Any,
        tracker: _SubgraphTracker,
    ):
        """遍历 updates chunk，并转成前端消费的事件。"""
        if not isinstance(update_data, dict):
            return

        for step, data in update_data.items():
            if step == "__interrupt__":
                continue
            if not isinstance(data, dict):
                continue
            new_messages = data.get("messages", [])
            if not isinstance(new_messages, list):
                continue

            if step == "model":
                for message in new_messages:
                    if isinstance(message, AIMessage):
                        for event in tracker.build_model_events(namespace, message):
                            yield event
                continue

            if step == "tools":
                for message in new_messages:
                    if isinstance(message, ToolMessage):
                        for event in tracker.build_tool_events(namespace, message):
                            yield event

    async def chat(self, user_input: str):
        """异步生成器，yield (event_type, *data)。包含自动重试。"""
        logger.info("Chat started: thread=%s, chars=%d", self._thread_id[:20], len(user_input))
        await self._checkpointer.ensure_setup()
        config = {"configurable": {"thread_id": self._thread_id}}
        tracker = _SubgraphTracker()

        for attempt in range(_MAX_RETRIES + 1):
            saw_first_token = False
            current_input: Any = self._build_initial_input(user_input)
            stream_iter = None
            next_chunk_task: asyncio.Task[Any] | None = None
            try:
                stream_iter, next_chunk_task = self._start_stream(current_input, config)

                # 处理模型流，custom 事件通过 stream_mode="custom" 直接进入同一流。
                while next_chunk_task:
                    try:
                        chunk = await next_chunk_task
                    except StopAsyncIteration:
                        next_chunk_task = None
                        break

                    next_chunk_task = asyncio.create_task(stream_iter.__anext__())
                    namespace = tuple(chunk.get("ns", ()))
                    chunk_type = chunk.get("type")

                    if chunk_type == "messages":
                        token, metadata = chunk["data"]
                        agent_name = str(metadata.get("lc_agent_name") or "")
                        if namespace and agent_name and agent_name != "mainagent_supervisor":
                            for event in tracker.register_subagent_chunk(namespace, agent_name, token):
                                yield event
                            continue

                        if metadata.get("langgraph_node") != "model":
                            continue
                        if isinstance(token, AIMessageChunk) and token.text:
                            if not saw_first_token:
                                saw_first_token = True
                                logger.info(
                                    "Chat first token: thread=%s, attempt=%d",
                                    self._thread_id[:20],
                                    attempt + 1,
                                )
                            yield ("text", token.text)
                        continue

                    if chunk_type == "custom":
                        custom_data = chunk["data"]
                        if isinstance(custom_data, dict):
                            yield ("runtime_event", custom_data)
                        continue

                    if chunk_type != "updates":
                        continue

                    update_data = chunk.get("data", {})
                    request_id, interrupt_request = _extract_interrupt_request(update_data)

                    for event in self._iter_update_events(namespace, update_data, tracker):
                        yield event

                    if interrupt_request is not None:
                        await self._cancel_pending_task(next_chunk_task)
                        next_chunk_task = None

                        permission_event = tracker.build_permission_request_event(
                            request_id=request_id,
                            request=interrupt_request,
                            namespace=namespace,
                        )
                        yield ("runtime_event", permission_event)
                        decision_payload = await self._interactive_broker.wait_for_tool_permission(
                            request_id
                        )
                        current_input = Command(resume=decision_payload)
                        stream_iter, next_chunk_task = self._start_stream(current_input, config)
                        continue

                logger.info(
                    "Chat finished: thread=%s, attempt=%d, first_token=%s",
                    self._thread_id[:20],
                    attempt + 1,
                    "yes" if saw_first_token else "no",
                )
                return
            except Exception as exc:
                is_retryable = _is_retryable_error(exc)
                if not is_retryable or attempt >= _MAX_RETRIES:
                    logger.error(
                        "Chat failed: thread=%s, attempt=%d, retryable=%s, error=%s",
                        self._thread_id[:20],
                        attempt + 1,
                        is_retryable,
                        exc,
                    )
                    raise

                delay = _BASE_RETRY_DELAY * (2 ** attempt)
                logger.warning(
                    "请求失败 (attempt %d/%d): %s，%.1f 秒后重试...",
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                    delay,
                )
                yield ("retry", str(exc), attempt + 1, _MAX_RETRIES, delay)
                await asyncio.sleep(delay)
            finally:
                await self._cancel_pending_task(next_chunk_task)
