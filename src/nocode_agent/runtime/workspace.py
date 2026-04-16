"""工作区根解析与额外目录授权持久化。"""

from __future__ import annotations

import logging
import shlex
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import yaml

from nocode_agent.runtime.paths import project_config_path
from nocode_agent.runtime.security import check_deny_rules

logger = logging.getLogger(__name__)

_WORKSPACE_SECTION = "workspace"
_ADDITIONAL_DIRECTORIES_KEY = "additional_directories"
_GLOB_MAGIC = frozenset("*?[")
_SHELL_OPERATORS = {"&&", "||", "|", ";", "(", ")", "{", "}"}
_SHELL_PATH_OPTIONS = {"-C", "--directory"}
_SHELL_DIRECTORY_COMMANDS = {"cd", "pushd"}
_WORKSPACE_APPROVAL_TOOLS = frozenset({"read", "write", "edit", "list_dir", "grep", "glob", "bash"})


def _global_config_path() -> Path:
    return Path.home() / ".nocode" / "config.yaml"


def _read_yaml_mapping(config_file: Path) -> dict[str, Any]:
    try:
        with open(config_file, encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
    except FileNotFoundError:
        return {}
    except OSError as exc:
        logger.warning("Unable to read workspace config %s: %s", config_file, exc)
        return {}
    if loaded is None:
        return {}
    if isinstance(loaded, dict):
        return loaded
    logger.warning("Ignoring non-mapping workspace config %s", config_file)
    return {}


def _write_yaml_mapping(config_file: Path, payload: dict[str, Any]) -> None:
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, allow_unicode=True, sort_keys=False)


def _normalize_string_list(raw_value: Any) -> list[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, str):
        value = raw_value.strip()
        return [value] if value else []
    if isinstance(raw_value, (list, tuple, set)):
        values: list[str] = []
        for item in raw_value:
            value = str(item or "").strip()
            if value:
                values.append(value)
        return values
    value = str(raw_value).strip()
    return [value] if value else []


def _contains_glob_magic(part: str) -> bool:
    return any(char in part for char in _GLOB_MAGIC)


def _literal_glob_prefix(pattern: str) -> str:
    candidate = Path(pattern).expanduser()
    parts = candidate.parts
    literal_parts: list[str] = []
    for part in parts:
        if _contains_glob_magic(part):
            break
        literal_parts.append(part)

    if not literal_parts:
        return candidate.anchor or "."
    if candidate.anchor and literal_parts == [candidate.anchor]:
        return candidate.anchor
    return str(Path(*literal_parts))


def _resolve_directory_root(path: Path, *, prefer_directory: bool) -> Path:
    resolved = path.resolve(strict=False)
    if prefer_directory:
        if resolved.exists() and resolved.is_file():
            return resolved.parent
        return resolved
    if resolved.exists():
        return resolved if resolved.is_dir() else resolved.parent
    return resolved.parent


def _dedupe_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return tuple(deduped)


def current_workspace_root() -> Path:
    return Path.cwd().resolve(strict=False)


def resolve_user_path(path_value: str) -> Path:
    raw_value = str(path_value or "").strip()
    if not raw_value:
        return current_workspace_root()
    candidate = Path(raw_value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    return (current_workspace_root() / candidate).resolve(strict=False)


def _resolve_config_path(config_file: Path, path_value: str) -> Path:
    raw_value = str(path_value or "").strip()
    if not raw_value:
        return config_file.parent.parent.resolve(strict=False)
    candidate = Path(raw_value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    return (config_file.parent.parent / candidate).resolve(strict=False)


def resolve_glob_pattern(pattern: str) -> str:
    raw_pattern = str(pattern or "").strip()
    if not raw_pattern:
        return str(current_workspace_root())
    candidate = Path(raw_pattern).expanduser()
    if candidate.is_absolute():
        return str(candidate.resolve(strict=False))
    return str((current_workspace_root() / candidate).resolve(strict=False))


def _workspace_directories_from_config(config_file: Path) -> tuple[Path, ...]:
    config = _read_yaml_mapping(config_file)
    workspace = config.get(_WORKSPACE_SECTION)
    if not isinstance(workspace, dict):
        return ()

    directories: list[Path] = []
    for raw_path in _normalize_string_list(workspace.get(_ADDITIONAL_DIRECTORIES_KEY)):
        try:
            root = _resolve_directory_root(_resolve_config_path(config_file, raw_path), prefer_directory=True)
        except Exception:
            logger.warning("Ignoring invalid workspace.additional_directories entry: %r", raw_path)
            continue
        directories.append(root)
    return _dedupe_paths(directories)


@lru_cache(maxsize=1)
def get_additional_workspace_roots() -> tuple[Path, ...]:
    roots = [
        *_workspace_directories_from_config(_global_config_path()),
        *_workspace_directories_from_config(project_config_path()),
    ]
    return _dedupe_paths(roots)


def invalidate_workspace_cache() -> None:
    get_additional_workspace_roots.cache_clear()


def get_allowed_workspace_roots() -> tuple[Path, ...]:
    return _dedupe_paths((current_workspace_root(), *get_additional_workspace_roots()))


def render_workspace_path(path: Path) -> str:
    resolved = path.resolve(strict=False)
    root = current_workspace_root()
    if resolved == root:
        return "."
    try:
        return str(resolved.relative_to(root))
    except ValueError:
        return str(resolved)


def is_within_allowed_workspace(path: Path) -> bool:
    resolved = path.resolve(strict=False)
    for root in get_allowed_workspace_roots():
        if resolved == root or root in resolved.parents:
            return True
    return False


def persist_additional_workspace_roots(roots: Iterable[Path]) -> tuple[Path, ...]:
    normalized_roots = _dedupe_paths(
        _resolve_directory_root(path, prefer_directory=True)
        for path in roots
    )
    if not normalized_roots:
        return ()

    config_file = project_config_path()
    payload = _read_yaml_mapping(config_file)
    workspace = payload.get(_WORKSPACE_SECTION)
    if not isinstance(workspace, dict):
        workspace = {}

    existing_roots = list(_workspace_directories_from_config(config_file))
    seen = {path.resolve(strict=False) for path in existing_roots}
    added: list[Path] = []
    for root in normalized_roots:
        resolved = root.resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        existing_roots.append(resolved)
        added.append(resolved)

    if not added:
        return ()

    workspace[_ADDITIONAL_DIRECTORIES_KEY] = [str(path) for path in existing_roots]
    payload[_WORKSPACE_SECTION] = workspace
    _write_yaml_mapping(config_file, payload)
    invalidate_workspace_cache()
    return tuple(added)


def _resolve_workspace_request_roots(tool_name: str, args: dict[str, Any]) -> tuple[Path, ...]:
    requested: list[Path] = []
    if tool_name not in _WORKSPACE_APPROVAL_TOOLS:
        return ()

    if tool_name in {"read", "write", "edit"}:
        file_path = str(args.get("file_path", "") or "").strip()
        if file_path:
            requested.append(_resolve_directory_root(resolve_user_path(file_path), prefer_directory=False))
        return _dedupe_paths(requested)

    if tool_name in {"list_dir", "grep"}:
        raw_path = str(args.get("path", "") or ".").strip() or "."
        requested.append(_resolve_directory_root(resolve_user_path(raw_path), prefer_directory=True))
        return _dedupe_paths(requested)

    if tool_name == "glob":
        pattern = str(args.get("pattern", "") or "").strip()
        if pattern:
            prefix = _literal_glob_prefix(pattern)
            requested.append(_resolve_directory_root(resolve_user_path(prefix), prefer_directory=True))
        return _dedupe_paths(requested)

    if tool_name != "bash":
        return ()

    command = str(args.get("command", "") or "").strip()
    if not command:
        return ()
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return ()

    expect_directory_arg = False
    for token in tokens:
        if token in _SHELL_OPERATORS:
            expect_directory_arg = False
            continue
        if expect_directory_arg:
            resolved = _resolve_shell_token(token)
            if resolved is not None:
                requested.append(_resolve_directory_root(resolved, prefer_directory=True))
            expect_directory_arg = False
            continue
        if token in _SHELL_PATH_OPTIONS or token in _SHELL_DIRECTORY_COMMANDS:
            expect_directory_arg = True
            continue
        resolved = _resolve_shell_token(token)
        if resolved is None:
            continue
        requested.append(_resolve_directory_root(resolved, prefer_directory=_looks_like_directory_token(token)))
    return _dedupe_paths(requested)


def _looks_like_directory_token(token: str) -> bool:
    if token.endswith("/"):
        return True
    if any(char in token for char in "*?["):
        return True
    return token in {".", ".."}


def _resolve_shell_token(token: str) -> Path | None:
    stripped = str(token or "").strip()
    if not stripped or stripped.startswith("-") or stripped.startswith("$"):
        return None
    if stripped.startswith(("~", "/")) or stripped in {".", ".."} or stripped.startswith("./") or stripped.startswith("../"):
        prefix = _literal_glob_prefix(stripped) if any(char in stripped for char in "*?[") else stripped
        return resolve_user_path(prefix)
    return None


def get_unauthorized_workspace_roots(
    tool_name: str,
    args: dict[str, Any],
) -> tuple[Path, ...]:
    unauthorized: list[Path] = []
    for root in _resolve_workspace_request_roots(tool_name, args):
        if check_deny_rules(root) is not None:
            continue
        if is_within_allowed_workspace(root):
            continue
        unauthorized.append(root)
    return _dedupe_paths(unauthorized)


__all__ = [
    "current_workspace_root",
    "get_additional_workspace_roots",
    "get_allowed_workspace_roots",
    "get_unauthorized_workspace_roots",
    "invalidate_workspace_cache",
    "is_within_allowed_workspace",
    "persist_additional_workspace_roots",
    "render_workspace_path",
    "resolve_glob_pattern",
    "resolve_user_path",
]
