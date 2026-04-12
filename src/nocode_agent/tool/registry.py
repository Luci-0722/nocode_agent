"""工具注册表与分组 helper。"""

from __future__ import annotations

import json
from enum import Flag, auto
from typing import Any


class ToolSafety(Flag):
    READ_ONLY = auto()
    CONCURRENCY_SAFE = auto()
    DESTRUCTIVE = auto()


TOOL_SAFETY_MAP: dict[str, ToolSafety] = {
    "read": ToolSafety.READ_ONLY | ToolSafety.CONCURRENCY_SAFE,
    "glob": ToolSafety.READ_ONLY | ToolSafety.CONCURRENCY_SAFE,
    "list_dir": ToolSafety.READ_ONLY | ToolSafety.CONCURRENCY_SAFE,
    "grep": ToolSafety.READ_ONLY | ToolSafety.CONCURRENCY_SAFE,
    "web_search": ToolSafety.READ_ONLY | ToolSafety.CONCURRENCY_SAFE,
    "web_fetch": ToolSafety.READ_ONLY | ToolSafety.CONCURRENCY_SAFE,
    "todo_read": ToolSafety.READ_ONLY | ToolSafety.CONCURRENCY_SAFE,
    "ask_user_question": ToolSafety.CONCURRENCY_SAFE,
    "todo_write": ToolSafety.CONCURRENCY_SAFE,
    "write": ToolSafety.DESTRUCTIVE,
    "edit": ToolSafety.DESTRUCTIVE,
    "bash": ToolSafety(0),
}

CORE_TOOL_NAMES: tuple[str, ...] = (
    "read",
    "write",
    "edit",
    "glob",
    "list_dir",
    "grep",
    "bash",
    "web_search",
    "web_fetch",
    "ask_user_question",
    "todo_write",
    "todo_read",
)

READONLY_BLOCKED_TOOL_NAMES: frozenset[str] = frozenset({"write", "edit"})
SUBAGENT_TOOL_NAME = "delegate_code"
SUBAGENT_TOOL_TYPES: tuple[str, ...] = (
    "general-purpose",
    "Explore",
    "Plan",
    "verification",
)
SUBAGENT_TYPE_DESCRIPTION = (
    "子代理类型。可选值：\n"
    "- general-purpose（默认）：通用编码代理，拥有所有工具，可读写文件\n"
    "- Explore：快速搜索代理，只读，擅长文件搜索和代码分析。"
    "调用时在 prompt 中指定彻底程度：quick/medium/very thorough\n"
    "- Plan：架构规划代理，只读，擅长设计实施方案和识别关键文件\n"
    "- verification：对抗性验证代理，只读，尝试找出 bug 和遗漏"
)


def is_concurrency_safe(tool_name: str) -> bool:
    """判断工具是否可安全并发执行。"""
    safety = TOOL_SAFETY_MAP.get(tool_name)
    return safety is not None and ToolSafety.CONCURRENCY_SAFE in safety


def is_read_only(tool_name: str) -> bool:
    """判断工具是否只读。"""
    safety = TOOL_SAFETY_MAP.get(tool_name)
    return safety is not None and ToolSafety.READ_ONLY in safety


def build_core_tool_list(tool_map: dict[str, Any]) -> list[Any]:
    """按稳定顺序返回核心工具列表。"""
    return [tool_map[name] for name in CORE_TOOL_NAMES]


def build_readonly_tool_list(all_tools: list[Any]) -> list[Any]:
    """从全部核心工具中过滤出只读工具。"""
    return [tool_obj for tool_obj in all_tools if tool_obj.name not in READONLY_BLOCKED_TOOL_NAMES]


def build_tools_manifest() -> dict[str, Any]:
    """构造工具 manifest 数据。"""
    return {
        "core_tools": list(CORE_TOOL_NAMES),
        "subagent_tool": SUBAGENT_TOOL_NAME,
        "subagent_types": list(SUBAGENT_TOOL_TYPES),
    }


def dump_tools_manifest_json() -> str:
    """把工具 manifest 序列化为 JSON。"""
    return json.dumps(build_tools_manifest(), ensure_ascii=False, indent=2)
