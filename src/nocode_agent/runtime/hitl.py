"""基于 LangChain HumanInTheLoopMiddleware 的工具审批支持。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.agents.middleware.human_in_the_loop import (
    ActionRequest,
    HITLRequest,
    InterruptOnConfig,
    ReviewConfig,
    interrupt,
)
from langchain_core.messages import AIMessage, ToolMessage

from nocode_agent.runtime.paths import project_config_path
from nocode_agent.runtime.workspace import (
    get_unauthorized_workspace_roots,
    persist_additional_workspace_roots,
)

logger = logging.getLogger(__name__)

_SUPPORTED_DECISIONS = {"approve", "reject"}


def _truncate(value: str, limit: int = 300) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "..."


def _format_json(value: Any) -> str:
    try:
        rendered = json.dumps(value, ensure_ascii=False, indent=2)
    except TypeError:
        rendered = str(value)
    return _truncate(rendered, limit=1200)


def _default_description(tool_call: dict[str, Any], *_args: Any) -> str:
    """生成默认审批说明，避免把复杂 dict 直接拼成单行字符串。"""
    tool_name = str(tool_call.get("name", "") or "tool")
    args = tool_call.get("args", {})
    parts = [
        "以下工具调用需要用户审批：",
        "",
        f"工具: {tool_name}",
        "参数:",
        _format_json(args if isinstance(args, dict) else {}),
    ]
    return "\n".join(parts)


class NoCodeHumanInTheLoopMiddleware(HumanInTheLoopMiddleware):
    """扩展官方 HITL middleware，在 action request 中附带 tool_call_id。"""

    def _create_action_and_config(self, tool_call, config, state, runtime):  # type: ignore[override]
        action_request, review_config = super()._create_action_and_config(
            tool_call, config, state, runtime
        )
        action_request["tool_call_id"] = str(tool_call.get("id", "") or "")
        return action_request, review_config

    def _build_workspace_action(self, tool_call: dict[str, Any]) -> tuple[ActionRequest, ReviewConfig, InterruptOnConfig, tuple[str, ...]] | None:
        tool_name = str(tool_call.get("name", "") or "tool")
        tool_args = tool_call.get("args", {}) if isinstance(tool_call.get("args"), dict) else {}
        requested_roots = tuple(str(path) for path in get_unauthorized_workspace_roots(tool_name, tool_args))
        if not requested_roots:
            return None

        config = InterruptOnConfig(
            allowed_decisions=["approve", "reject"],
            description=self._workspace_description(tool_name, tool_args, requested_roots),
        )
        action_request = ActionRequest(
            name=tool_name,
            args=self._workspace_action_args(tool_name, tool_args, requested_roots),
            description=config["description"],
        )
        action_request["tool_call_id"] = str(tool_call.get("id", "") or "")
        review_config = ReviewConfig(
            action_name=tool_name,
            allowed_decisions=config["allowed_decisions"],
        )
        return action_request, review_config, config, requested_roots

    def _workspace_action_args(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        requested_roots: tuple[str, ...],
    ) -> dict[str, Any]:
        preview: dict[str, Any] = {"additional_directories": list(requested_roots)}
        if tool_name == "bash":
            preview["command"] = str(tool_args.get("command", "") or "").strip()
            return preview
        for key in ("file_path", "path", "pattern"):
            value = str(tool_args.get(key, "") or "").strip()
            if value:
                preview[key] = value
                break
        return preview

    def _workspace_description(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        requested_roots: tuple[str, ...],
    ) -> str:
        config_file = project_config_path()
        args_preview = _format_json(self._workspace_action_args(tool_name, tool_args, requested_roots))
        lines = [
            "以下工具调用需要为当前项目授权额外目录：",
            "",
            f"工具: {tool_name}",
            "将要授权的目录:",
            *[f"- {root}" for root in requested_roots],
            "",
            f"批准后会写入: {config_file}",
            "配置字段: workspace.additional_directories",
            "",
            "参数预览:",
            args_preview,
        ]
        return "\n".join(lines)

    def after_model(self, state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:  # type: ignore[override]
        messages = state["messages"]
        if not messages:
            return None

        last_ai_msg = next((msg for msg in reversed(messages) if isinstance(msg, AIMessage)), None)
        if not last_ai_msg or not last_ai_msg.tool_calls:
            return None

        action_requests: list[ActionRequest] = []
        review_configs: list[ReviewConfig] = []
        interrupt_indices: list[int] = []
        configs_by_index: dict[int, InterruptOnConfig] = {}
        workspace_roots_by_index: dict[int, tuple[str, ...]] = {}

        for idx, tool_call in enumerate(last_ai_msg.tool_calls):
            workspace_action = self._build_workspace_action(tool_call)
            if workspace_action is not None:
                action_request, review_config, config, requested_roots = workspace_action
                action_requests.append(action_request)
                review_configs.append(review_config)
                interrupt_indices.append(idx)
                configs_by_index[idx] = config
                workspace_roots_by_index[idx] = requested_roots
                continue

            if (config := self.interrupt_on.get(tool_call["name"])) is None:
                continue
            action_request, review_config = self._create_action_and_config(
                tool_call, config, state, runtime
            )
            action_requests.append(action_request)
            review_configs.append(review_config)
            interrupt_indices.append(idx)
            configs_by_index[idx] = config

        if not action_requests:
            return None

        decisions = interrupt(
            HITLRequest(action_requests=action_requests, review_configs=review_configs)
        )["decisions"]
        if (decisions_len := len(decisions)) != (interrupt_count := len(interrupt_indices)):
            msg = (
                f"Number of human decisions ({decisions_len}) does not match "
                f"number of hanging tool calls ({interrupt_count})."
            )
            raise ValueError(msg)

        revised_tool_calls: list[dict[str, Any]] = []
        artificial_tool_messages: list[ToolMessage] = []
        decision_idx = 0

        for idx, tool_call in enumerate(last_ai_msg.tool_calls):
            if idx not in interrupt_indices:
                revised_tool_calls.append(tool_call)
                continue

            config = configs_by_index[idx]
            decision = decisions[decision_idx]
            decision_idx += 1
            revised_tool_call, tool_message = self._process_decision(decision, tool_call, config)

            requested_roots = workspace_roots_by_index.get(idx)
            if requested_roots and revised_tool_call is not None and tool_message is None:
                try:
                    persisted = persist_additional_workspace_roots(Path(root) for root in requested_roots)
                except Exception as error:
                    logger.error("Persist additional workspace roots failed: %s", error, exc_info=True)
                    revised_tool_call = None
                    tool_message = ToolMessage(
                        content=f"授权额外目录失败: {error}",
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"],
                        status="error",
                    )
                else:
                    if persisted:
                        logger.info("Persisted additional workspace roots: %s", ", ".join(str(item) for item in persisted))

            if revised_tool_call is not None:
                revised_tool_calls.append(revised_tool_call)
            if tool_message is not None:
                artificial_tool_messages.append(tool_message)

        last_ai_msg.tool_calls = revised_tool_calls
        return {"messages": [last_ai_msg, *artificial_tool_messages]}


def _normalize_interrupt_config(
    tool_name: str,
    raw_config: Any,
) -> bool | InterruptOnConfig:
    """把 YAML 配置归一化成官方 middleware 可接受的格式。"""
    if isinstance(raw_config, bool):
        if raw_config is False:
            return False
        return InterruptOnConfig(
            allowed_decisions=["approve", "reject"],
            description=_default_description,
        )

    if not isinstance(raw_config, dict):
        logger.warning(
            "Ignoring invalid permissions.interrupt_on[%s]=%r",
            tool_name,
            raw_config,
        )
        return False

    raw_decisions = raw_config.get("allowed_decisions") or ["approve", "reject"]
    normalized_decisions = [
        str(item).strip().lower()
        for item in raw_decisions
        if str(item).strip().lower() in _SUPPORTED_DECISIONS
    ]
    if not normalized_decisions:
        logger.warning(
            "Tool %s has no supported approval decisions after normalization; auto-approving it.",
            tool_name,
        )
        return False

    description = raw_config.get("description")
    config: InterruptOnConfig = InterruptOnConfig(
        allowed_decisions=normalized_decisions,
    )
    if isinstance(description, str) and description.strip():
        config["description"] = description.strip()
    elif callable(description):
        config["description"] = description
    else:
        config["description"] = _default_description

    args_schema = raw_config.get("args_schema")
    if isinstance(args_schema, dict):
        config["args_schema"] = args_schema
    return config


def _default_interrupt_map() -> dict[str, bool | InterruptOnConfig]:
    """默认对高风险工具开启审批。"""
    risky_tools = (
        "write",
        "edit",
        "bash",
        "web_fetch",
        "web_search",
        "delegate_code",
    )
    return {
        tool_name: InterruptOnConfig(
            allowed_decisions=["approve", "reject"],
            description=_default_description,
        )
        for tool_name in risky_tools
    }


def build_human_in_the_loop_middleware(
    permissions_config: dict[str, Any] | None,
) -> HumanInTheLoopMiddleware | None:
    """根据配置创建官方 HITL middleware。"""
    config = permissions_config or {}
    enabled = bool(config.get("enabled", True))
    if not enabled:
        return None

    raw_interrupt_on = config.get("interrupt_on")
    if raw_interrupt_on is None:
        raw_interrupt_on = _default_interrupt_map()
    elif not isinstance(raw_interrupt_on, dict):
        raw_interrupt_on = _default_interrupt_map()

    interrupt_on: dict[str, bool | InterruptOnConfig] = {}
    for tool_name, raw_tool_config in raw_interrupt_on.items():
        normalized = _normalize_interrupt_config(str(tool_name), raw_tool_config)
        if normalized is not False:
            interrupt_on[str(tool_name)] = normalized

    description_prefix = str(
        config.get("description_prefix") or "Tool execution requires approval"
    ).strip()
    return NoCodeHumanInTheLoopMiddleware(
        interrupt_on=interrupt_on,
        description_prefix=description_prefix,
    )


def extract_hitl_request(interrupt_value: Any) -> dict[str, Any] | None:
    """从 LangGraph interrupt payload 中提取前端需要的审批请求。"""
    if not isinstance(interrupt_value, dict):
        return None

    action_requests = interrupt_value.get("action_requests")
    review_configs = interrupt_value.get("review_configs")
    if not isinstance(action_requests, list) or not isinstance(review_configs, list):
        return None

    actions: list[dict[str, Any]] = []
    for index, action in enumerate(action_requests):
        if not isinstance(action, dict):
            continue
        review = review_configs[index] if index < len(review_configs) else {}
        if not isinstance(review, dict):
            review = {}
        allowed_decisions = [
            str(item).strip().lower()
            for item in review.get("allowed_decisions", [])
            if str(item).strip().lower() in _SUPPORTED_DECISIONS
        ]
        actions.append(
            {
                "name": str(action.get("name", "") or "tool"),
                "args": action.get("args", {}) if isinstance(action.get("args"), dict) else {},
                "description": str(action.get("description", "") or "").strip(),
                "allowed_decisions": allowed_decisions or ["approve", "reject"],
                "tool_call_id": str(action.get("tool_call_id", "") or ""),
            }
        )

    if not actions:
        return None
    return {"actions": actions}


__all__ = [
    "NoCodeHumanInTheLoopMiddleware",
    "build_human_in_the_loop_middleware",
    "extract_hitl_request",
]
