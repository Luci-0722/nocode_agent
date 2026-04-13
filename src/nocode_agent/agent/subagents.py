"""子代理定义、发现与注册。"""

from __future__ import annotations

import base64
import logging
import platform
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable

import yaml

logger = logging.getLogger(__name__)

_BUILTIN_RUNTIME_NAME_BY_TYPE: dict[str, str] = {
    "general-purpose": "subagent_general_purpose",
    "Explore": "subagent_explore",
    "Plan": "subagent_plan",
    "verification": "subagent_verification",
}
_BUILTIN_TYPE_BY_RUNTIME_NAME: dict[str, str] = {
    runtime_name: agent_type
    for agent_type, runtime_name in _BUILTIN_RUNTIME_NAME_BY_TYPE.items()
}
_CUSTOM_RUNTIME_PREFIX = "subagent_b64_"


@dataclass(slots=True)
class AgentDefinition:
    """子代理定义。"""

    agent_type: str
    when_to_use: str
    when_not_to_use: str | None = None
    allowed_tools: list[str] | None = None
    disallowed_tools: list[str] = field(default_factory=list)
    model: str | None = None
    get_system_prompt: Callable[[], str] = field(default=lambda: "")
    source: str = "custom"
    definition_path: Path | None = None

    @property
    def is_readonly(self) -> bool:
        """该代理是否为只读（禁止 write/edit）。"""
        allowed = set(self.allowed_tools or [])
        if allowed and "*" not in allowed:
            return "write" not in allowed and "edit" not in allowed
        return "write" in self.disallowed_tools or "edit" in self.disallowed_tools


class AgentRegistry:
    """Central registry for discovered agent definitions."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}

    def register(self, entry: AgentDefinition) -> None:
        self._agents[entry.agent_type] = entry

    def register_many(self, entries: list[AgentDefinition]) -> None:
        for entry in entries:
            self.register(entry)

    def get(self, name: str) -> AgentDefinition | None:
        return self._agents.get(name)

    def all_agents(self) -> list[AgentDefinition]:
        return list(self._agents.values())

_AGENT_REGISTRY: AgentRegistry | None = None


def _build_environment_section(cwd: Path | None = None, *, include_date: bool = False) -> str:
    resolved_cwd = (cwd or Path.cwd()).resolve()
    items = [
        "# 环境上下文",
        f" - 工作目录: {resolved_cwd}",
    ]
    if include_date:
        items.append(f" - 日期: {date.today().isoformat()}")
    items.append(f" - 平台: {platform.system()} {platform.release()}")
    return "\n".join(items)


def _build_subagent_shared_notes(cwd: Path | None = None) -> str:
    return "\n".join(
        [
            "Notes:",
            " - 子代理不继承 AGENTS.md、CLAUDE.md 或其他指令文件内容；如有需要，应直接读取相关文件。",
            " - 代理线程在两次 bash 调用之间会重置 cwd，因此请始终使用绝对路径。",
            " - 在最终回复里，只分享与任务相关的文件路径（必须使用绝对路径，不要用相对路径）。"
            "只有当精确文本本身会影响结论时才贴代码片段，不要复述你只是读过的代码。",
            " - 为了与用户清晰沟通，禁止使用 emoji。",
            " - 不要在工具调用前加冒号。像“让我读一下文件：”这种写法应改成“让我读一下文件。”。",
            "",
            _build_environment_section(cwd, include_date=False),
        ]
    )


def _compose_subagent_prompt(base_prompt: str, cwd: Path | None = None) -> str:
    return base_prompt + "\n\n" + _build_subagent_shared_notes(cwd)


def _parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    text = raw.strip()
    if not text.startswith("---"):
        return {}, text

    rest = text[3:]
    close = rest.find("\n---")
    if close == -1:
        return {}, text

    frontmatter_text = rest[:close].strip()
    body = rest[close + 4:].strip()

    try:
        frontmatter = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError:
        frontmatter = {}

    if not isinstance(frontmatter, dict):
        frontmatter = {}
    return frontmatter, body


def _normalize_tool_names(raw_value: Any) -> list[str] | None:
    if raw_value is None:
        return None

    values: list[str] = []
    if isinstance(raw_value, str):
        values = [item.strip() for item in raw_value.split(",")]
    elif isinstance(raw_value, (list, tuple, set)):
        for item in raw_value:
            if isinstance(item, str):
                values.extend(part.strip() for part in item.split(","))
            elif item is not None:
                values.append(str(item).strip())
    else:
        values = [str(raw_value).strip()]

    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _scan_markdown_dir(base_dir: Path) -> list[Path]:
    if not base_dir.exists():
        return []
    try:
        return sorted(path for path in base_dir.rglob("*.md") if path.is_file())
    except OSError:
        return []


def _scan_project_agent_files(cwd: Path) -> list[Path]:
    directories: list[Path] = []
    for parent in [cwd.resolve(), *cwd.resolve().parents]:
        agents_dir = parent / ".nocode" / "agents"
        if agents_dir.exists():
            directories.append(agents_dir)

    files: list[Path] = []
    for directory in reversed(directories):
        files.extend(_scan_markdown_dir(directory))
    return files


def _scan_user_agent_files() -> list[Path]:
    return _scan_markdown_dir(Path.home() / ".nocode" / "agents")


def _build_custom_agent_definition(agent_md: Path, source: str) -> AgentDefinition | None:
    try:
        content = agent_md.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Failed to read agent definition %s: %s", agent_md, exc)
        return None

    frontmatter, markdown = _parse_frontmatter(content)
    agent_type = str(frontmatter.get("name") or agent_md.stem).strip()
    when_to_use = str(frontmatter.get("description") or "").strip()
    if not agent_type or not when_to_use:
        logger.warning(
            "Skipping agent definition %s: missing name/description frontmatter",
            agent_md,
        )
        return None

    prompt_body = markdown.strip()
    if not prompt_body:
        logger.warning("Skipping agent definition %s: empty prompt body", agent_md)
        return None

    allowed_tools = _normalize_tool_names(
        frontmatter.get("tools")
        or frontmatter.get("allowed_tools")
        or frontmatter.get("allowed-tools")
    )
    disallowed_tools = _normalize_tool_names(
        frontmatter.get("disallowedTools")
        or frontmatter.get("disallowed_tools")
        or frontmatter.get("disallowed-tools")
    ) or []
    model = str(frontmatter.get("model") or "").strip() or None
    when_not_to_use = str(
        frontmatter.get("when_not_to_use")
        or frontmatter.get("when-not-to-use")
        or ""
    ).strip() or None

    return AgentDefinition(
        agent_type=agent_type,
        when_to_use=when_to_use,
        when_not_to_use=when_not_to_use,
        allowed_tools=allowed_tools,
        disallowed_tools=disallowed_tools,
        model=model,
        get_system_prompt=lambda body=prompt_body: _compose_subagent_prompt(body),
        source=source,
        definition_path=agent_md,
    )


def discover_custom_agents(cwd: Path | str) -> list[AgentDefinition]:
    """发现项目级和用户级自定义子代理。"""
    resolved_cwd = Path(cwd).resolve()
    discovered: list[AgentDefinition] = []

    for path in _scan_user_agent_files():
        definition = _build_custom_agent_definition(path, source="user")
        if definition is not None:
            discovered.append(definition)

    for path in _scan_project_agent_files(resolved_cwd):
        definition = _build_custom_agent_definition(path, source="project")
        if definition is not None:
            discovered.append(definition)

    return discovered


def init_agent_registry(cwd: Path | str) -> AgentRegistry:
    """发现项目级与用户级子代理，并填充全局 registry。"""
    global _AGENT_REGISTRY
    registry = AgentRegistry()
    registry.register_many(discover_custom_agents(cwd))
    _AGENT_REGISTRY = registry
    logger.info("Agent registry initialized: %d agents discovered", len(registry.all_agents()))
    return registry


def get_agent_registry() -> AgentRegistry:
    global _AGENT_REGISTRY
    if _AGENT_REGISTRY is None:
        _AGENT_REGISTRY = init_agent_registry(Path.cwd())
    return _AGENT_REGISTRY


def get_all_agent_definitions() -> list[AgentDefinition]:
    return get_agent_registry().all_agents()


def get_agent_definition(agent_type: str) -> AgentDefinition | None:
    """按类型名查找子代理定义。"""
    return get_agent_registry().get(agent_type)


def describe_agent_tools(agent_definition: AgentDefinition) -> str:
    """将 agent 的工具约束转成人类可读描述。"""
    allowed_tools = agent_definition.allowed_tools or []
    disallowed_tools = agent_definition.disallowed_tools

    if allowed_tools:
        if "*" in allowed_tools:
            if disallowed_tools:
                return f"全部工具，除 {', '.join(disallowed_tools)}"
            return "全部工具"

        effective = [tool for tool in allowed_tools if tool not in disallowed_tools]
        return ", ".join(effective) if effective else "无"

    if disallowed_tools:
        return f"全部工具，除 {', '.join(disallowed_tools)}"
    return "全部工具"


def resolve_agent_tools(
    agent_definition: AgentDefinition,
    *,
    all_tools: list[Any],
    readonly_tools: list[Any],
) -> list[Any]:
    """根据 agent 定义过滤可用工具。"""
    allowed_tools = agent_definition.allowed_tools or []
    disallowed = set(agent_definition.disallowed_tools)
    if allowed_tools:
        allowed = None if "*" in allowed_tools else set(allowed_tools)
        base_tools = all_tools
    else:
        allowed = None
        base_tools = readonly_tools if agent_definition.is_readonly else all_tools

    return [
        tool_obj
        for tool_obj in base_tools
        if (allowed is None or tool_obj.name in allowed)
        and tool_obj.name not in disallowed
    ]


def build_readonly_tool_names() -> list[str]:
    """返回只读子代理可用的工具名列表（排除 write/edit/delegate_code）。"""
    return [
        "read",
        "glob",
        "list_dir",
        "grep",
        "bash",
        "web_search",
        "web_fetch",
        "todo_write",
        "todo_read",
    ]


def encode_runtime_subagent_name(agent_type: str) -> str:
    """把子代理类型编码为稳定的运行时节点名。"""
    builtin = _BUILTIN_RUNTIME_NAME_BY_TYPE.get(agent_type)
    if builtin:
        return builtin

    encoded = base64.urlsafe_b64encode(agent_type.encode("utf-8")).decode("ascii").rstrip("=")
    return f"{_CUSTOM_RUNTIME_PREFIX}{encoded}"


def decode_runtime_subagent_type(agent_name: str) -> str:
    """把运行时节点名还原为子代理类型。"""
    if not agent_name:
        return "subagent"

    builtin = _BUILTIN_TYPE_BY_RUNTIME_NAME.get(agent_name)
    if builtin:
        return builtin

    if not agent_name.startswith(_CUSTOM_RUNTIME_PREFIX):
        return agent_name

    encoded = agent_name[len(_CUSTOM_RUNTIME_PREFIX):]
    padding = "=" * (-len(encoded) % 4)
    try:
        return base64.urlsafe_b64decode(encoded + padding).decode("utf-8")
    except Exception:
        logger.warning("Failed to decode runtime subagent name: %s", agent_name)
        return agent_name


__all__ = [
    "AgentDefinition",
    "AgentRegistry",
    "build_readonly_tool_names",
    "decode_runtime_subagent_type",
    "describe_agent_tools",
    "discover_custom_agents",
    "encode_runtime_subagent_name",
    "get_agent_definition",
    "get_agent_registry",
    "get_all_agent_definitions",
    "init_agent_registry",
    "resolve_agent_tools",
]
