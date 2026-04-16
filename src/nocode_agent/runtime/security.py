"""运行时安全相关 helper。"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DENY_PATHS: tuple[str, ...] = (
    "~/.ssh",
    "~/.gnupg",
    "~/.aws",
    "~/.netrc",
    "~/.config/gh",
    "~/.docker",
)


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
def get_deny_paths() -> tuple[Path, ...]:
    from nocode_agent.config import load_config

    config = load_config()
    security = config.get("security", {}) if isinstance(config, dict) else {}
    raw_deny_paths: list[str] = []
    if isinstance(security, dict):
        raw_deny_paths = _normalize_string_list(security.get("deny_paths"))

    deny_paths: list[Path] = []
    seen: set[Path] = set()
    for raw_path in [*DEFAULT_DENY_PATHS, *raw_deny_paths]:
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


def check_deny_rules(path: Path) -> Path | None:
    resolved = path.resolve(strict=False)
    for deny_path in get_deny_paths():
        if resolved == deny_path or deny_path in resolved.parents:
            return deny_path
    return None


def is_path_denied(path: Path) -> bool:
    return check_deny_rules(path) is not None


__all__ = [
    "DEFAULT_DENY_PATHS",
    "check_deny_rules",
    "get_deny_paths",
    "is_path_denied",
]
