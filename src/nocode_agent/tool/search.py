"""搜索工具。"""

from __future__ import annotations

import asyncio
import fnmatch
import os
import platform
import re
import shutil
from pathlib import Path

from langchain.tools import tool
from pydantic import BaseModel, Field

from nocode_agent.runtime.paths import repo_root


class GrepInput(BaseModel):
    pattern: str = Field(description="正则或普通文本模式。")
    path: str = Field(default=".", description="搜索起点目录。")
    file_glob: str = Field(default="*", description="文件筛选 glob，例如 `*.py`。")
    output_mode: str = Field(
        default="content",
        description=(
            "输出模式："
            "content（默认，显示匹配行及行号）、"
            "files_with_matches（仅显示包含匹配的文件路径）、"
            "count（显示每个文件的匹配计数）。"
        ),
    )
    context_lines: int = Field(
        default=0, ge=0, le=10,
        description="上下文行数（前后各N行），仅 content 模式有效。",
    )
    max_matches: int = Field(default=200, ge=1, le=2000, description="最多返回多少条结果。")


_rg_path: str | None = None


def _normalize_rg_platform_key() -> str:
    """Build the bundled rg platform suffix used under ``bin/``."""
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        arch = "x86_64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"
    else:
        arch = machine

    system = platform.system().lower()
    if system.startswith(("msys", "mingw", "cygwin")):
        system = "windows"

    return f"{system}-{arch}"


def _find_rg_binary() -> str | None:
    """查找可用的 rg 二进制。优先级：项目内置 > 系统 PATH。"""
    platform_key = _normalize_rg_platform_key()

    project_root = repo_root()
    bundled_names = [f"rg-{platform_key}"]
    if platform.system().lower() == "windows":
        bundled_names.insert(0, f"rg-{platform_key}.exe")

    for name in bundled_names:
        bundled = project_root / "bin" / name
        if bundled.exists() and os.access(str(bundled), os.X_OK):
            return str(bundled)

    system_rg = shutil.which("rg")
    if system_rg:
        return system_rg

    return None


def _get_rg_path() -> str | None:
    global _rg_path
    if _rg_path is None:
        _rg_path = _find_rg_binary()
    return _rg_path


def _grep_with_rg(
    pattern: str,
    base: Path,
    file_glob: str,
    output_mode: str,
    context_lines: int,
    max_matches: int,
) -> str | None:
    """用 ripgrep 执行搜索。返回结果字符串，或 None 表示 rg 不可用/出错。"""
    from nocode_agent.tool.kit import _get_deny_paths, _trim_output, _workspace_root

    rg = _get_rg_path()
    if not rg:
        return None

    cmd = [rg, "--no-config", "--no-ignore-vcs"]
    anchor = _workspace_root()
    try:
        search_root = base.relative_to(anchor)
        rg_cwd = anchor
        cwd = "." if str(search_root) == "." else str(search_root)
    except ValueError:
        rg_cwd = base.parent if base.is_file() else base
        cwd = str(base)

    if output_mode == "files_with_matches":
        cmd += ["--files-with-matches", "--max-count", str(max_matches)]
    elif output_mode == "count":
        cmd += ["--count", "--max-count", str(max_matches)]
    else:
        cmd += ["--line-number", "--max-count", str(max_matches)]
        if context_lines > 0:
            cmd += [f"--context={context_lines}"]

    if file_glob and file_glob != "*":
        cmd += ["--glob", file_glob]

    for deny_path in _get_deny_paths():
        try:
            rel = deny_path.relative_to(rg_cwd)
        except ValueError:
            continue
        rel_pattern = rel.as_posix()
        if not rel_pattern:
            continue
        cmd += ["--glob", f"!{rel_pattern}"]
        if deny_path.is_dir():
            cmd += ["--glob", f"!{rel_pattern}/**"]

    cmd.append(pattern)
    cmd.append(cwd)

    try:
        proc = asyncio.run(_run_rg(cmd, rg_cwd))
    except Exception:
        return None

    if not proc:
        return None

    stdout, stderr, returncode = proc
    if returncode == 1:
        return "未找到匹配内容。"
    if returncode >= 2:
        return None

    text = stdout.decode("utf-8", errors="replace").strip()
    if not text:
        return "未找到匹配内容。"

    return _trim_output(text)


async def _run_rg(cmd: list[str], cwd: Path) -> tuple[bytes, bytes, int] | None:
    """异步运行 rg 命令。"""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        return stdout, stderr, proc.returncode or 0
    except Exception:
        return None


def _grep_with_python(
    pattern: str,
    base: Path,
    file_glob: str,
    output_mode: str,
    context_lines: int,
    max_matches: int,
) -> str:
    """纯 Python 的 grep 实现。"""
    from nocode_agent.runtime.workspace import render_workspace_path
    from nocode_agent.tool.kit import _is_path_accessible, _trim_output

    try:
        regex = re.compile(pattern)
    except re.error as error:
        return f"错误：无效正则: {error}"

    results: list[str] = []
    files = [base] if base.is_file() else sorted(base.rglob("*"))

    for file in files:
        if not file.is_file():
            continue
        if not _is_path_accessible(file):
            continue
        if not fnmatch.fnmatch(file.name, file_glob):
            continue
        try:
            lines = file.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, Exception):
            continue

        rel_path = render_workspace_path(file)

        if output_mode == "files_with_matches":
            for line in lines:
                if regex.search(line):
                    results.append(rel_path)
                    break
            if len(results) >= max_matches:
                break
            continue

        if output_mode == "count":
            count = sum(1 for line in lines if regex.search(line))
            if count > 0:
                results.append(f"{rel_path}:{count}")
            if len(results) >= max_matches:
                break
            continue

        for line_no, line in enumerate(lines, start=1):
            if regex.search(line):
                if context_lines > 0:
                    start = max(0, line_no - 1 - context_lines)
                    end = min(len(lines), line_no + context_lines)
                    snippet_lines = []
                    for index in range(start, end):
                        prefix = ">" if index == line_no - 1 else " "
                        snippet_lines.append(f"{prefix}{index + 1}:{lines[index]}")
                    results.append(f"{rel_path}-{line_no - context_lines}-{line_no + context_lines}:")
                    results.extend(f"  {item}" for item in snippet_lines)
                else:
                    results.append(f"{rel_path}:{line_no}: {line}")
                if len(results) >= max_matches:
                    return _trim_output("\n".join(results) + f"\n\n[结果已截断，最多 {max_matches} 条]")

    if not results:
        return "未找到匹配内容。"
    return _trim_output("\n".join(results))


@tool("grep", args_schema=GrepInput)
def grep_search(
    pattern: str,
    path: str = ".",
    file_glob: str = "*",
    output_mode: str = "content",
    context_lines: int = 0,
    max_matches: int = 200,
) -> str:
    """在工作区内搜索文本。优先使用 rg，不可用时回退到 Python 实现。"""
    from nocode_agent.tool.kit import _resolve_path

    try:
        base = _resolve_path(path)
    except Exception as error:
        return f"错误：路径无效: {error}"

    if output_mode not in ("content", "files_with_matches", "count"):
        return "错误：output_mode 必须是 content、files_with_matches 或 count。"

    result = _grep_with_rg(pattern, base, file_glob, output_mode, context_lines, max_matches)
    if result is not None:
        return result
    return _grep_with_python(pattern, base, file_glob, output_mode, context_lines, max_matches)


__all__ = [
    "GrepInput",
    "grep_search",
]
