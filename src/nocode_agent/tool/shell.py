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
    from nocode_agent.runtime.sandbox import SandboxManager, init_sandbox

    logger.info("bash: %s (timeout=%ds)", command[:200], timeout)

    # 初始化沙箱（首次调用时从配置加载）
    if not hasattr(bash, "_sandbox_initialized"):
        init_sandbox()
        bash._sandbox_initialized = True

    root = _workspace_root()

    # 第三层：沙箱包装（如果启用）
    wrapped_command = SandboxManager.wrap_command(command, root)

    if wrapped_command != command:
        logger.debug("命令已包装在沙箱中执行")

    try:
        proc = await asyncio.create_subprocess_shell(
            wrapped_command,
            cwd=str(root),
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
