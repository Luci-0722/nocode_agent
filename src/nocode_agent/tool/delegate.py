"""子代理委派工具。"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from langchain.tools import tool
from langchain_core.messages import AIMessage, BaseMessage
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


def make_agent_tool(
    subagents: dict[str, Any],
    agent_definitions: list[Any] | None = None,
    name: str = "delegate_code",
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

    @tool(name, args_schema=AgentInput)
    async def delegate_code(
        subagent_type: str = "general-purpose",
        task: str = "",
        context: str = "",
        thread_id: str = "",
    ) -> str:
        """把任务委派给子代理执行。支持多种子代理类型，默认为通用编码代理。"""
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

        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"configurable": {"thread_id": resolved_thread_id}},
        )
        messages = result.get("messages", [])
        summary = _extract_last_ai_text(messages)
        return _sanitize_text(_strip_ansi(summary))

    return delegate_code


__all__ = [
    "make_agent_tool",
]
