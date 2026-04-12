"""日志模块。

把历史根目录 ``log.py`` 的实现迁入包内，供新的包路径直接引用；
根目录同名文件仅保留兼容转发能力。
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from nocode_agent.runtime.paths import default_log_path

_DEFAULT_FORMAT = "%(asctime)s %(levelname)-5s [%(name)s] %(message)s"
_DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_DEFAULT_LOG_PATH = default_log_path()
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 3


def _replace_handlers(logger: logging.Logger, handlers: list[logging.Handler]) -> None:
    """替换 logger 的 handlers，并关闭旧句柄避免重复写入。"""
    old_handlers = list(logger.handlers)
    logger.handlers.clear()
    for old_handler in old_handlers:
        try:
            old_handler.close()
        except Exception:
            # 日志回收不能影响主流程，这里保持静默兜底。
            pass

    for handler in handlers:
        logger.addHandler(handler)


def setup_logging(level: str | None = None, log_file: str | None = None) -> None:
    """初始化 nocode_agent 的日志系统。"""
    resolved_level = (
        level
        or os.environ.get("NOCODE_LOG_LEVEL")
        or "INFO"
    ).upper()
    numeric_level = getattr(logging, resolved_level, logging.INFO)

    formatter = logging.Formatter(_DEFAULT_FORMAT, datefmt=_DEFAULT_DATE_FORMAT)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)

    resolved_path = log_file or os.environ.get("NOCODE_LOG_FILE") or str(_DEFAULT_LOG_PATH)
    log_path = Path(resolved_path).expanduser()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    pkg_logger = logging.getLogger("nocode_agent")
    pkg_logger.setLevel(numeric_level)
    _replace_handlers(pkg_logger, [stderr_handler, file_handler])
    # 关闭向 root logger 的传播，避免控制台重复打印。
    pkg_logger.propagate = False


__all__ = [
    "setup_logging",
]
