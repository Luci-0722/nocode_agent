"""基于 LangChain HumanInTheLoopMiddleware 的工具审批支持。"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.agents.middleware.human_in_the_loop import InterruptOnConfig

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
    if not isinstance(raw_interrupt_on, dict) or not raw_interrupt_on:
        raw_interrupt_on = _default_interrupt_map()

    interrupt_on: dict[str, bool | InterruptOnConfig] = {}
    for tool_name, raw_tool_config in raw_interrupt_on.items():
        normalized = _normalize_interrupt_config(str(tool_name), raw_tool_config)
        if normalized is not False:
            interrupt_on[str(tool_name)] = normalized

    if not interrupt_on:
        return None

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
