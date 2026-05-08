"""子代理委派工具。"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any
from uuid import uuid4

from langchain.tools import tool
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import InjectedToolCallId
from pydantic import BaseModel, Field

from .registry import build_subagent_type_description


def _stringify_message_content(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(item) for item in content)
    return str(content)


def _extract_last_ai_text(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            text = _stringify_message_content(message.content).strip()
            if text:
                return text
    return "子代理已完成任务，但没有返回文本结果。"


def _coerce_stream_chunk(chunk: Any) -> tuple[str, Any]:
    """兼容 LangGraph 不同 stream 形态，返回 mode 和 payload。"""
    if isinstance(chunk, tuple):
        if len(chunk) == 3:
            return str(chunk[1]), chunk[2]
        if len(chunk) == 2:
            return str(chunk[0]), chunk[1]
    if isinstance(chunk, dict):
        return str(chunk.get("type") or ""), chunk.get("data", chunk)
    return "", chunk


def _emit_subagent_event(writer: Any, payload: dict[str, Any]) -> None:
    if writer is None:
        return
    writer(payload)


def make_agent_tool(
    subagents: dict[str, Any],
    agent_definitions: list[Any] | None = None,
    name: str = "delegate_code",
    stream_idle_timeout: float = 120.0,
) -> Any:
    """创建多类型子代理委派工具。"""
    subagent_type_description = build_subagent_type_description(agent_definitions)

    class AgentInput(BaseModel):
        subagent_type: str = Field(
            default="general-purpose",
            description=subagent_type_description,
        )
        task: str = Field(description="要委派给子代理的具体任务。")
        context: str = Field(default="", description="补充上下文，可选。")
        thread_id: str = Field(
            default="",
            description="可选的子代理会话名；传入相同值会复用同一个子代理线程。",
        )
        tool_call_id: Annotated[str, InjectedToolCallId]

    @tool(name, args_schema=AgentInput)
    async def delegate_code(
        subagent_type: str = "general-purpose",
        task: str = "",
        context: str = "",
        thread_id: str = "",
        tool_call_id: Annotated[str, InjectedToolCallId] = "",
    ) -> str:
        """把任务委派给子代理执行。支持多种子代理类型，默认为通用编码代理。"""
        from langgraph.config import get_stream_writer
        from nocode_agent.tool.kit import _sanitize_text, _strip_ansi, logger

        normalized_type = subagent_type.strip() or "general-purpose"
        agent = subagents.get(normalized_type)
        if agent is None:
            available = ", ".join(subagents.keys()) or "(none)"
            return f"错误：未知子代理类型 {normalized_type}。可选值：{available}"

        prompt = task.strip()
        if not prompt:
            return "错误：task 不能为空。"
        if context.strip():
            prompt = f"任务：{task.strip()}\n\n补充上下文：\n{context.strip()}"

        resolved_thread_id = (
            f"subagent-named-{thread_id.strip()}"
            if thread_id.strip()
            else f"subagent-{uuid4().hex}"
        )

        logger.info("delegate_code: type=%s, thread=%s", normalized_type, resolved_thread_id)

        writer = get_stream_writer()
        subagent_id = resolved_thread_id
        base_event = {
            "parent_tool_call_id": tool_call_id,
            "subagent_id": subagent_id,
            "subagent_type": normalized_type,
        }
        _emit_subagent_event(
            writer,
            {
                "type": "subagent_start",
                **base_event,
                "thread_id": resolved_thread_id,
            },
        )

        messages: list[BaseMessage] = []
        stream_iter = agent.astream(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"configurable": {"thread_id": resolved_thread_id}},
            stream_mode=["updates"],
            version="v2",
        ).__aiter__()
        next_task: asyncio.Task[Any] | None = asyncio.ensure_future(stream_iter.__anext__())
        try:
            while next_task:
                try:
                    chunk = await asyncio.wait_for(next_task, timeout=stream_idle_timeout)
                except StopAsyncIteration:
                    next_task = None
                    break
                except asyncio.TimeoutError:
                    logger.warning(
                        "Subagent stream idle timeout (%.1fs): type=%s, thread=%s",
                        stream_idle_timeout,
                        normalized_type,
                        resolved_thread_id,
                    )
                    raise
                next_task = asyncio.ensure_future(stream_iter.__anext__())

                chunk_type, chunk_data = _coerce_stream_chunk(chunk)
                if chunk_type != "updates" or not isinstance(chunk_data, dict):
                    continue

                for step, data in chunk_data.items():
                    if not isinstance(data, dict):
                        continue
                    step_messages = data.get("messages", [])
                    if not isinstance(step_messages, list):
                        continue

                    for message in step_messages:
                        if isinstance(message, BaseMessage):
                            messages.append(message)

                        if step == "model" and isinstance(message, AIMessage):
                            for sub_tool_call in message.tool_calls:
                                _emit_subagent_event(
                                    writer,
                                    {
                                        "type": "subagent_tool_start",
                                        **base_event,
                                        "name": sub_tool_call["name"],
                                        "args": sub_tool_call.get("args", {}),
                                        "tool_call_id": sub_tool_call.get("id", ""),
                                    },
                                )
                            continue

                        if step == "tools" and isinstance(message, ToolMessage):
                            _emit_subagent_event(
                                writer,
                                {
                                    "type": "subagent_tool_end",
                                    **base_event,
                                    "name": message.name or "tool",
                                    "output": _sanitize_text(_strip_ansi(_stringify_message_content(message.content))),
                                    "tool_call_id": getattr(message, "tool_call_id", ""),
                                },
                            )
        finally:
            if next_task and not next_task.done():
                next_task.cancel()
            try:
                await stream_iter.aclose()
            except Exception:
                pass

        summary = _extract_last_ai_text(messages)
        cleaned_summary = _sanitize_text(_strip_ansi(summary))
        _emit_subagent_event(
            writer,
            {
                "type": "subagent_finish",
                **base_event,
                "summary": cleaned_summary,
            },
        )
        return cleaned_summary

    return delegate_code


__all__ = [
    "make_agent_tool",
]
