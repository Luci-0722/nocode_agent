"""Agent 包公共导出。"""

from __future__ import annotations

from typing import Any

__all__ = [
    "MainAgent",
    "create_mainagent",
]


def __getattr__(name: str) -> Any:
    if name not in {"MainAgent", "create_mainagent"}:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from .main import MainAgent, create_mainagent

    exports = {
        "MainAgent": MainAgent,
        "create_mainagent": create_mainagent,
    }
    return exports[name]
