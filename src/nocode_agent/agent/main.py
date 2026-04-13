"""主代理运行时与装配入口。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain_mcp_adapters.client import MultiServerMCPClient

from nocode_agent.model import build_model, resolve_context_window
from nocode_agent.persistence import CheckpointerManager, resolve_checkpoint_path
from nocode_agent.prompt import DynamicPromptMiddleware
from nocode_agent.runtime.interaction import InteractiveSessionBroker
from nocode_agent.skills.registry import init_skill_registry
from nocode_agent.skills.tool import invoke_skill
from nocode_agent.tool import build_core_tools, build_readonly_tools, make_agent_tool
from .builder import build_mainagent_setup
from .factory import create_subagent_map, create_supervisor_agent
from .runtime import MainAgentRuntime
from .subagents import get_all_agent_definitions, init_agent_registry

logger = logging.getLogger(__name__)


class MainAgent:
    """主代理负责协调工具和子代理。"""

    def __init__(
        self,
        agent,
        checkpointer: CheckpointerManager,
        interactive_broker: InteractiveSessionBroker,
        thread_id: str | None = None,
        model_name: str = "",
        subagent_model_name: str = "",
        context_window: int = 128_000,
        reasoning_effort: str = "",
    ):
        self._agent = agent
        self._checkpointer = checkpointer
        self._interactive_broker = interactive_broker
        self._thread_id = thread_id or self._new_thread_id()
        self._model_name = model_name
        self._subagent_model_name = subagent_model_name
        self._context_window = context_window
        self._reasoning_effort = reasoning_effort
        self._runtime = MainAgentRuntime(
            agent=self._agent,
            checkpointer=self._checkpointer,
            interactive_broker=self._interactive_broker,
            thread_id=self._thread_id,
        )

    @staticmethod
    def _new_thread_id() -> str:
        return f"mainagent-{uuid4().hex}"

    @property
    def thread_id(self) -> str:
        return self._thread_id

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def subagent_model_name(self) -> str:
        return self._subagent_model_name

    @property
    def context_window(self) -> int:
        return self._context_window

    @property
    def reasoning_effort(self) -> str:
        return self._reasoning_effort

    async def clear(self):
        await self._checkpointer.delete_thread(self._thread_id)

    async def enqueue_user_input(self, text: str) -> None:
        await self._interactive_broker.enqueue_user_input(text)

    async def submit_question_answer(self, answer: str) -> None:
        await self._interactive_broker.submit_question_answer(answer)

    async def submit_tool_permission_decision(
        self,
        request_id: str,
        decisions: list[dict[str, Any]],
    ) -> None:
        await self._interactive_broker.submit_tool_permission_decision(
            request_id,
            decisions,
        )

    async def chat(self, user_input: str):
        """异步生成器，yield (event_type, *data)。包含自动重试。"""
        async for event in self._runtime.chat(user_input):
            yield event


def _mcp_env_to_dict(items: list[Any] | None) -> dict[str, str]:
    env: dict[str, str] = {}
    for item in items or []:
        if isinstance(item, dict):
            name = str(item.get("name", "")).strip()
            value = str(item.get("value", ""))
        else:
            name = str(getattr(item, "name", "")).strip()
            value = str(getattr(item, "value", ""))
        if name:
            env[name] = value
    return env


def _normalize_mcp_server(server: Any) -> tuple[str, dict[str, Any]] | None:
    if isinstance(server, dict):
        payload = server
    elif hasattr(server, "model_dump"):
        payload = server.model_dump(by_alias=False)
    else:
        payload = {
            "name": getattr(server, "name", ""),
            "command": getattr(server, "command", ""),
            "args": getattr(server, "args", []),
            "env": getattr(server, "env", []),
            "url": getattr(server, "url", ""),
            "type": getattr(server, "type", ""),
        }

    name = str(payload.get("name", "")).strip()
    if not name:
        return None

    command = str(payload.get("command", "")).strip()
    if command:
        return (
            name,
            {
                "transport": "stdio",
                "command": command,
                "args": [str(item) for item in payload.get("args", []) or []],
                "env": _mcp_env_to_dict(payload.get("env")),
            },
        )

    url = str(payload.get("url", "")).strip()
    transport_type = str(payload.get("type", "")).strip().lower()
    if not url or transport_type not in {"http", "sse"}:
        return None

    return (
        name,
        {
            "transport": "streamable_http" if transport_type == "http" else "sse",
            "url": url,
        },
    )


async def _load_mcp_tools(mcp_servers: list[Any] | None) -> list[Any]:
    if not mcp_servers:
        return []

    connections: dict[str, dict[str, Any]] = {}
    for server in mcp_servers:
        normalized = _normalize_mcp_server(server)
        if normalized is None:
            continue
        name, connection = normalized
        connections[name] = connection

    if not connections:
        return []

    client = MultiServerMCPClient(connections, tool_name_prefix=True)
    return await client.get_tools()


async def create_mainagent(
    api_key: str,
    model: str = "glm-4-flash",
    base_url: str = "https://open.bigmodel.cn/api/paas/v4",
    max_tokens: int = 4096,
    temperature: float = 0.7,
    compression: dict | None = None,
    auto_compact: dict | None = None,
    session_memory: dict | None = None,
    permissions: dict | None = None,
    subagent_model: str | None = None,
    subagent_temperature: float = 0.1,
    thread_id: str | None = None,
    persistence_config: dict | None = None,
    mcp_servers: list[Any] | None = None,
    proxy: str = "",
    no_proxy: list[str] | None = None,
    request_timeout: float = 90.0,
) -> MainAgent:
    """创建主代理和代码子代理。"""
    logger.info(
        "Creating MainAgent: model=%s, base_url=%s, max_tokens=%d, temperature=%.2f, proxy=%s, no_proxy=%s, timeout=%.1fs",
        model, base_url, max_tokens, temperature, proxy or "(none)", ",".join(no_proxy or []) or "(none)", request_timeout,
    )
    context_window = resolve_context_window(model)
    checkpointer = CheckpointerManager(resolve_checkpoint_path(persistence_config))
    await checkpointer.ensure_setup()
    saver = checkpointer.get()
    setup_artifacts = build_mainagent_setup(
        api_key=api_key,
        model=model,
        base_url=base_url,
        compression=compression,
        auto_compact=auto_compact,
        session_memory=session_memory,
        permissions=permissions,
        thread_id=thread_id,
        context_window=context_window,
        proxy=proxy,
        no_proxy=no_proxy,
        request_timeout=request_timeout,
    )
    resolved_thread_id = setup_artifacts.resolved_thread_id
    interactive_broker = setup_artifacts.interactive_broker
    middleware = setup_artifacts.middleware
    main_middleware = setup_artifacts.main_middleware

    main_llm = build_model(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        proxy=proxy,
        no_proxy=no_proxy,
        request_timeout=request_timeout,
    )
    subagent_llm = build_model(
        api_key=api_key,
        model=subagent_model or model,
        base_url=base_url,
        temperature=subagent_temperature,
        max_tokens=max_tokens,
        proxy=proxy,
        no_proxy=no_proxy,
        request_timeout=request_timeout,
    )

    core_tools = build_core_tools(interactive_broker.ask_user_question)
    readonly_tools = build_readonly_tools(interactive_broker.ask_user_question)

    # Skill system — DynamicPromptMiddleware 会在每次调用时刷新
    # 这里只做一次初始扫描，确保 invoke_skill 工具可用
    init_skill_registry(Path.cwd())
    init_agent_registry(Path.cwd())
    skill_tools = [invoke_skill]
    mcp_tools = await _load_mcp_tools(mcp_servers)
    logger.info("Loaded %d MCP tools, %d core tools, %d skill tools", len(mcp_tools), len(core_tools), len(skill_tools))

    subagent_models: dict[str, Any] = {str(subagent_model or model): subagent_llm}

    def _resolve_subagent_model(agent_definition) -> Any:
        model_name = str(agent_definition.model or subagent_model or model).strip() or str(model)
        cached = subagent_models.get(model_name)
        if cached is None:
            cached = build_model(
                api_key=api_key,
                model=model_name,
                base_url=base_url,
                temperature=subagent_temperature,
                max_tokens=max_tokens,
                proxy=proxy,
                no_proxy=no_proxy,
                request_timeout=request_timeout,
            )
            subagent_models[model_name] = cached
        return cached

    # ── 创建多类型子代理 ────────────────────────────────────
    subagents_map = create_subagent_map(
        model=subagent_llm,
        core_tools=core_tools,
        readonly_tools=readonly_tools,
        checkpointer=saver,
        middleware=middleware,
        resolve_model=_resolve_subagent_model,
    )

    tools = [
        *core_tools,
        *skill_tools,
        *mcp_tools,
        make_agent_tool(subagents_map, agent_definitions=get_all_agent_definitions()),
    ]

    # DynamicPromptMiddleware 放在最前面，确保每次调用前刷新 system prompt
    dynamic_prompt_middleware = DynamicPromptMiddleware(Path.cwd())
    final_main_middleware = [dynamic_prompt_middleware, *main_middleware]

    agent = create_supervisor_agent(
        model=main_llm,
        tools=tools,
        checkpointer=saver,
        middleware=final_main_middleware,
        system_prompt=None,  # 由 DynamicPromptMiddleware 动态注入
    )

    reasoning_config = persistence_config.get("reasoning") if isinstance(persistence_config, dict) else {}
    reasoning_effort = str(
        (
            (persistence_config or {}).get("reasoning_effort")
            or (reasoning_config.get("effort") if isinstance(reasoning_config, dict) else "")
            or ""
        )
    ).strip()

    logger.info("MainAgent created: thread_id=%s, context_window=%d", resolved_thread_id, context_window)

    return MainAgent(
        agent=agent,
        checkpointer=checkpointer,
        interactive_broker=interactive_broker,
        thread_id=resolved_thread_id,
        model_name=model,
        subagent_model_name=subagent_model or model,
        context_window=context_window,
        reasoning_effort=reasoning_effort,
    )
