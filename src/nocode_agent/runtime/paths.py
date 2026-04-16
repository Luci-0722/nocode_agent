"""项目路径解析。"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

PROJECT_CONFIG_DIRNAME = ".nocode"
PROJECT_CONFIG_FILENAME = "config.yaml"
PROJECT_CONFIG_PATH = Path(PROJECT_CONFIG_DIRNAME) / PROJECT_CONFIG_FILENAME


def _project_hash(project_path: Path) -> str:
    """计算项目路径的唯一标识符。"""
    # 使用路径的绝对值计算 hash，取前 8 位作为标识
    path_str = str(project_path.resolve())
    return hashlib.sha256(path_str.encode()).hexdigest()[:8]


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


def _project_config_path_for(project_root: Path) -> Path:
    return project_root / PROJECT_CONFIG_PATH


def project_config_path(project_root: Path | None = None) -> Path:
    """返回项目级配置文件路径 ``<project>/.nocode/config.yaml``。"""
    base = project_root.resolve() if project_root is not None else runtime_root()
    return _project_config_path_for(base)


def _find_runtime_project_root(cwd: Path) -> Path | None:
    """从当前目录向上查找项目根，只认项目级 `.nocode/config.yaml`。"""
    home = Path.home().resolve()
    for candidate in [cwd, *cwd.parents]:
        # ~/.nocode/config.yaml 是全局兜底配置，不应把 HOME 误判成项目根。
        if candidate == home and cwd != home:
            continue
        if _project_config_path_for(candidate).exists():
            return candidate
    return None


def runtime_root() -> Path:
    """返回当前运行实例应绑定的项目根目录。

    优先级：
    1. `NOCODE_PROJECT_DIR` 环境变量
    2. 从当前工作目录向上搜索到的包含 `.nocode/config.yaml` 的目录
    3. 当前工作目录
    """
    configured = os.environ.get("NOCODE_PROJECT_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()

    cwd = Path.cwd().resolve()
    detected = _find_runtime_project_root(cwd)
    if detected is not None:
        return detected

    return cwd


def global_state_root() -> Path:
    """返回全局状态根目录 ~/.nocode。"""
    return Path.home() / ".nocode"


def state_dir() -> Path:
    """返回当前项目的状态目录。

    统一存放在 ~/.nocode/projects/<project-hash>/ 下，按项目隔离。
    """
    configured = os.environ.get("NOCODE_STATE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()

    project = runtime_root()
    project_id = _project_hash(project)
    return global_state_root() / "projects" / project_id


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


def default_log_path() -> Path:
    """返回日志文件默认路径。"""
    return state_dir() / "nocode.log"


def default_checkpoint_db_path() -> Path:
    """返回 checkpoint 数据库默认路径。"""
    return state_dir() / "langgraph-checkpoints.sqlite"


def default_acp_sessions_path() -> Path:
    """返回 ACP 会话索引默认路径。"""
    return state_dir() / "acp-sessions.json"


def default_session_memory_path() -> Path:
    """返回 Session Memory 默认存储目录。"""
    return state_dir() / "session-memory"
