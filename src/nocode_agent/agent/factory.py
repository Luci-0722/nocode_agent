"""主代理与子代理的 create_agent 装配。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain.agents import create_agent

from nocode_agent.prompt import build_main_system_prompt
from .subagents import (
    AgentDefinition,
    encode_runtime_subagent_name,
    get_all_agent_definitions,
    resolve_agent_tools,
)


def create_subagent_map(
    *,
    model: Any,
    core_tools: list[Any],
    readonly_tools: list[Any],
    checkpointer: Any,
    middleware: list[Any],
    resolve_model: Callable[[AgentDefinition], Any] | None = None,
) -> dict[str, Any]:
    """根据已注册定义批量创建子代理实例。"""
    subagents: dict[str, Any] = {}
    for agent_definition in get_all_agent_definitions():
        tools = resolve_agent_tools(
            agent_definition,
            all_tools=core_tools,
            readonly_tools=readonly_tools,
        )
        subagents[agent_definition.agent_type] = create_agent(
            model=resolve_model(agent_definition) if resolve_model is not None else model,
            tools=tools,
            system_prompt=agent_definition.get_system_prompt(),
            checkpointer=checkpointer,
            middleware=middleware,
            name=encode_runtime_subagent_name(agent_definition.agent_type),
        )
    return subagents


def create_supervisor_agent(
    *,
    model: Any,
    tools: list[Any],
    checkpointer: Any,
    middleware: list[Any],
    system_prompt: str | None = None,
) -> Any:
    """创建主 supervisor agent。

    Args:
        system_prompt: 如果为 None，由 DynamicPromptMiddleware 动态注入；
                       如果为空字符串，完全不设置 system prompt；
                       否则使用传入的静态 prompt。
    """
    if system_prompt is None:
        # 由 middleware 动态注入，这里传空字符串
        prompt = ""
    else:
        prompt = system_prompt or build_main_system_prompt()

    return create_agent(
        model=model,
        tools=tools,
        system_prompt=prompt,
        checkpointer=checkpointer,
        middleware=middleware,
        name="mainagent_supervisor",
    )
