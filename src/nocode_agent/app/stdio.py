from __future__ import annotations

import sys


def configure_stdio_encoding() -> None:
    """Prefer UTF-8 for stdio so Windows consoles do not choke on streamed Unicode."""
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                # 某些嵌入环境可能不支持重配置；保持静默回退。
                pass


__all__ = ["configure_stdio_encoding"]
