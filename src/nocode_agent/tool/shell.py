"""Shell 工具。"""

from __future__ import annotations

import asyncio

from langchain.tools import tool
from pydantic import BaseModel, Field


class BashInput(BaseModel):
    command: str = Field(description="要执行的 shell 命令。")
    timeout: int = Field(default=30, ge=1, le=300, description="超时时间，单位秒。")


@tool("bash", args_schema=BashInput)
async def bash(command: str, timeout: int = 30) -> str:
    """在当前工作区执行 shell 命令并返回输出。"""
    from nocode_agent.tool.kit import _trim_output, _workspace_root, logger

    logger.info("bash: %s (timeout=%ds)", command[:200], timeout)
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=str(_workspace_root()),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return f"错误：命令执行超时（{timeout} 秒）。"
    except Exception as error:
        return f"错误：命令执行失败: {error}"

    parts: list[str] = []
    if stdout:
        parts.append(stdout.decode("utf-8", errors="replace"))
    if stderr:
        parts.append(f"[stderr]\n{stderr.decode('utf-8', errors='replace')}")
    if not parts:
        parts.append("(无输出)")
    parts.append(f"[退出码: {proc.returncode}]")
    return _trim_output("\n".join(parts))


__all__ = [
    "BashInput",
    "bash",
]
