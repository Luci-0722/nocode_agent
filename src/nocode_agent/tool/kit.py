"""高层工具装配与共享 helper。"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from functools import lru_cache
from pathlib import Path
from typing import Any

from .delegate import make_agent_tool
from .filesystem import (
    EditInput,
    GlobInput,
    ListDirInput,
    ReadInput,
    WriteInput,
    edit_file,
    glob_search,
    list_dir,
    read_file,
    write_file,
)
from .interactive import (
    AskUserQuestionInput,
    TodoInput,
    make_ask_user_question_tool,
    todo_read,
    todo_write,
)
from .registry import (
    build_core_tool_list,
    build_readonly_tool_list,
    dump_tools_manifest_json,
    is_concurrency_safe,
    is_read_only,
)
from .search import GrepInput, grep_search
from .shell import BashInput, bash
from .web import (
    WebFetchInput,
    WebSearchInput,
    http_get as _web_http_get,
    strip_html as _web_strip_html,
    web_fetch,
    web_search,
)

logger = logging.getLogger(__name__)

_MAX_OUTPUT = 12_000
_DEFAULT_DENY_PATHS: tuple[str, ...] = (
    "~/.ssh",
    "~/.gnupg",
    "~/.aws",
    "~/.netrc",
    "~/.config/gh",
    "~/.docker",
)

# 匹配所有 ANSI 转义序列（包括真彩色、256色、粗体等）
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[mK]")


def _strip_ansi(text: str) -> str:
    """剥离所有 ANSI 转义序列。"""
    return _ANSI_ESCAPE_RE.sub("", text)


def _sanitize_text(text: str) -> str:
    """Replace lone surrogates (U+D800–U+DFFF) with U+FFFD.

    Prevents ``UnicodeEncodeError: surrogates not allowed`` when
    encoding strings to UTF-8 (e.g. in the OpenAI/Anthropic client).
    The fast path (no surrogates) is nearly free because ``str.encode``
    is implemented in C.
    """
    try:
        text.encode("utf-8")
        return text
    except UnicodeEncodeError:
        return text.encode("utf-8", errors="replace").decode("utf-8")


def _workspace_root() -> Path:
    return Path.cwd().resolve()


def _normalize_string_list(raw_value: Any) -> list[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, str):
        value = raw_value.strip()
        return [value] if value else []
    if isinstance(raw_value, (list, tuple, set)):
        normalized: list[str] = []
        for item in raw_value:
            value = str(item or "").strip()
            if value:
                normalized.append(value)
        return normalized
    value = str(raw_value).strip()
    return [value] if value else []


@lru_cache(maxsize=1)
def _get_deny_paths() -> tuple[Path, ...]:
    from nocode_agent.config import load_config

    config = load_config()
    security = config.get("security", {}) if isinstance(config, dict) else {}
    raw_deny_paths = []
    if isinstance(security, dict):
        raw_deny_paths = _normalize_string_list(security.get("deny_paths"))

    deny_paths: list[Path] = []
    seen: set[Path] = set()
    for raw_path in [*_DEFAULT_DENY_PATHS, *raw_deny_paths]:
        try:
            resolved = Path(raw_path).expanduser().resolve(strict=False)
        except Exception:
            logger.warning("忽略无法解析的 deny_paths 配置: %r", raw_path)
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        deny_paths.append(resolved)
    return tuple(deny_paths)


def _check_deny_rules(path: Path) -> Path | None:
    for deny_path in _get_deny_paths():
        if path == deny_path or deny_path in path.parents:
            return deny_path
    return None


def _is_path_within_workspace(path: Path) -> bool:
    root = _workspace_root().resolve(strict=False)
    resolved = path.resolve(strict=False)
    return resolved == root or root in resolved.parents


def _is_path_denied(path: Path) -> bool:
    return _check_deny_rules(path.resolve(strict=False)) is not None


def _is_path_accessible(path: Path) -> bool:
    resolved = path.resolve(strict=False)
    return _is_path_within_workspace(resolved) and _check_deny_rules(resolved) is None


def _resolve_path(file_path: str) -> Path:
    root = _workspace_root().resolve(strict=False)
    path = Path(file_path).expanduser()
    if not path.is_absolute():
        path = root / path
    path = path.resolve(strict=False)
    denied_by = _check_deny_rules(path)
    if denied_by is not None:
        raise ValueError(f"路径 {path} 命中禁止访问规则 {denied_by}")
    if path != root and root not in path.parents:
        raise ValueError(f"路径 {path} 超出当前工作区 {root}")
    return path


def _trim_output(text: str) -> str:
    text = _strip_ansi(text)
    if len(text) <= _MAX_OUTPUT:
        return text
    return text[:_MAX_OUTPUT] + f"\n... (已截断，共 {len(text)} 字符)"


def _http_get(url: str) -> str:
    return _web_http_get(url)


def _strip_html(text: str) -> str:
    return _web_strip_html(text)


def build_core_tools(
    wait_for_answer: Callable[[list[dict[str, Any]]], Awaitable[str]],
) -> list:
    """返回全部核心工具（含 ask_user_question）。"""
    ask_user_question = make_ask_user_question_tool(wait_for_answer)
    return build_core_tool_list(
        {
            "read": read_file,
            "write": write_file,
            "edit": edit_file,
            "glob": glob_search,
            "list_dir": list_dir,
            "grep": grep_search,
            "bash": bash,
            "web_search": web_search,
            "web_fetch": web_fetch,
            "ask_user_question": ask_user_question,
            "todo_write": todo_write,
            "todo_read": todo_read,
        }
    )


def build_readonly_tools(
    wait_for_answer: Callable[[list[dict[str, Any]]], Awaitable[str]],
) -> list:
    """返回只读工具集，供只读子代理使用。"""
    all_tools = build_core_tools(wait_for_answer)
    return build_readonly_tool_list(all_tools)


def dump_tools_manifest() -> str:
    from nocode_agent.agent.subagents import get_all_agent_definitions

    return dump_tools_manifest_json(
        [agent_definition.agent_type for agent_definition in get_all_agent_definitions()]
    )


__all__ = [
    "AskUserQuestionInput",
    "BashInput",
    "EditInput",
    "GlobInput",
    "GrepInput",
    "ListDirInput",
    "ReadInput",
    "TodoInput",
    "WriteInput",
    "WebFetchInput",
    "WebSearchInput",
    "_http_get",
    "_check_deny_rules",
    "_get_deny_paths",
    "_is_path_accessible",
    "_is_path_denied",
    "_is_path_within_workspace",
    "_resolve_path",
    "_strip_ansi",
    "_strip_html",
    "_trim_output",
    "_workspace_root",
    "bash",
    "build_core_tools",
    "build_readonly_tools",
    "dump_tools_manifest",
    "edit_file",
    "glob_search",
    "grep_search",
    "is_concurrency_safe",
    "is_read_only",
    "list_dir",
    "logger",
    "make_agent_tool",
    "read_file",
    "todo_read",
    "todo_write",
    "web_fetch",
    "web_search",
    "write_file",
]
