"""NoCode Agent 正式包入口。"""

from __future__ import annotations

from .runtime.paths import package_dir, repo_root

__version__ = "0.3.0"

_PACKAGE_DIR = package_dir()
_REPO_ROOT = repo_root()

__all__ = [
    "__version__",
    "_PACKAGE_DIR",
    "_REPO_ROOT",
]
