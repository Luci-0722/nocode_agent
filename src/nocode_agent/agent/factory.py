"""主代理与子代理的 create_agent 装配。"""

from __future__ import annotations

from typing import Any

from langchain.agents import create_agent

from nocode_agent.prompt import build_main_system_prompt
from .subagents import get_builtin_agents

_SUBAGENT_NAME_BY_TYPE: dict[str, str] = {
    "general-purpose": "subagent_general_purpose",
    "Explore": "subagent_explore",
    "Plan": "subagent_plan",
    "verification": "subagent_verification",
}


def _resolve_subagent_runtime_name(agent_type: str) -> str:
    """把子代理类型转换成运行时节点名。"""
    return _SUBAGENT_NAME_BY_TYPE.get(
        agent_type,
        f"subagent_{agent_type.replace('-', '_').lower()}",
    )


def create_subagent_map(
    *,
    model: Any,
    core_tools: list[Any],
    readonly_tools: list[Any],
    checkpointer: Any,
    middleware: list[Any],
) -> dict[str, Any]:
    """根据内置定义批量创建子代理实例。"""
    subagents: dict[str, Any] = {}
    for agent_definition in get_builtin_agents():
        tools = readonly_tools if agent_definition.is_readonly else core_tools
        subagents[agent_definition.agent_type] = create_agent(
            model=model,
            tools=tools,
            system_prompt=agent_definition.get_system_prompt(),
            checkpointer=checkpointer,
            middleware=middleware,
            name=_resolve_subagent_runtime_name(agent_definition.agent_type),
        )
    return subagents


def create_supervisor_agent(
    *,
    model: Any,
    tools: list[Any],
    checkpointer: Any,
    middleware: list[Any],
) -> Any:
    """创建主 supervisor agent。"""
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=build_main_system_prompt(),
        checkpointer=checkpointer,
        middleware=middleware,
        name="mainagent_supervisor",
    )
