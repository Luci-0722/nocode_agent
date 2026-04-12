"""项目路径解析。"""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """返回源码检出目录的根路径。"""
    root = _find_repo_root(package_dir())
    if root is not None:
        return root

    package_parent = package_dir().parent
    if package_parent.name == "src":
        return package_parent.parent
    return package_parent


def package_dir() -> Path:
    """返回真实包目录，例如 ``repo/src/nocode_agent``。"""
    return Path(__file__).resolve().parent.parent


def _looks_like_repo_root(path: Path) -> bool:
    """判断给定路径是否像当前源码仓库根目录。"""
    return (
        ((path / "src" / "nocode_agent").is_dir() or (path / "nocode_agent").is_dir())
        and (path / "work" / "projects" / "README.md").exists()
        and (path / "config.yaml").exists()
    )


def _find_repo_root(start: Path) -> Path | None:
    """从给定目录向上搜索仓库根。"""
    resolved = start.resolve()
    for candidate in [resolved, *resolved.parents]:
        if _looks_like_repo_root(candidate):
            return candidate
    return None


def runtime_root() -> Path:
    """返回当前运行实例应绑定的项目根目录。

    优先级：
    1. `NOCODE_PROJECT_DIR`
    2. 当前工作目录向上搜索到的仓库根 / `config.yaml`
    3. 当前工作目录
    """
    configured = os.environ.get("NOCODE_PROJECT_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()

    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "config.yaml").exists():
            return candidate

    root = _find_repo_root(cwd)
    if root is not None:
        return root

    return cwd


def state_dir() -> Path:
    """返回默认状态目录。

    优先使用环境变量 ``NOCODE_STATE_DIR``，否则回落到当前运行项目根目录
    下的 ``.state``。这样源码仓库与已安装脚本都能得到合理默认值。
    """
    configured = os.environ.get("NOCODE_STATE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return runtime_root() / ".state"


def resolve_runtime_path(path_value: str | os.PathLike[str]) -> Path:
    """把运行时路径解析为绝对路径。

    约定：
    - 绝对路径保持不变
    - 相对路径统一锚定到当前运行项目根，而不是当前 shell 的 cwd
    """
    raw_value = str(path_value).strip()
    if not raw_value:
        return runtime_root()

    candidate = Path(raw_value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (runtime_root() / candidate).resolve()


def legacy_state_dir() -> Path:
    """返回历史状态目录。"""
    return package_dir() / ".state"


def _prefer_existing_path(new_path: Path, legacy_path: Path) -> Path:
    """优先使用新路径；若仅存在历史文件，则回落到历史路径。"""
    if new_path.exists() or not legacy_path.exists():
        return new_path
    return legacy_path


def default_log_path() -> Path:
    """返回日志文件默认路径。"""
    return state_dir() / "nocode.log"


def default_checkpoint_db_path() -> Path:
    """返回 checkpoint 数据库默认路径。"""
    return _prefer_existing_path(
        state_dir() / "langgraph-checkpoints.sqlite",
        legacy_state_dir() / "langgraph-checkpoints.sqlite",
    )


def default_acp_sessions_path() -> Path:
    """返回 ACP 会话索引默认路径。"""
    return _prefer_existing_path(
        state_dir() / "acp-sessions.json",
        legacy_state_dir() / "acp-sessions.json",
    )


def default_session_memory_path() -> Path:
    """返回 Session Memory 默认存储目录。"""
    return _prefer_existing_path(
        state_dir() / "session-memory",
        legacy_state_dir() / "session-memory",
    )
