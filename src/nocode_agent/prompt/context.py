"""Prompt context helper。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import platform

MAX_INSTRUCTION_FILE_CHARS = 4000
MAX_TOTAL_INSTRUCTION_CHARS = 12000


@dataclass(slots=True)
class ContextFile:
    path: Path
    content: str


def _collapse_blank_lines(content: str) -> str:
    """压缩连续空行，减少 prompt 噪声。"""
    lines: list[str] = []
    previous_blank = False
    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        is_blank = not line.strip()
        if is_blank and previous_blank:
            continue
        lines.append(line)
        previous_blank = is_blank
    return "\n".join(lines).strip()


def _truncate(content: str, limit: int) -> str:
    """按字符预算截断单个指令文件。"""
    normalized = content.strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "\n\n[truncated]"


def _dedupe_files(files: list[ContextFile]) -> list[ContextFile]:
    """按规范化内容去重，避免重复注入同一份指令。"""
    seen: set[str] = set()
    deduped: list[ContextFile] = []
    for file in files:
        normalized = _collapse_blank_lines(file.content)
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(file)
    return deduped


def discover_instruction_files(cwd: Path) -> list[ContextFile]:
    """从当前目录向上发现指令文件。"""
    directories = [cwd, *cwd.parents]
    directories.reverse()

    files: list[ContextFile] = []
    for directory in directories:
        for candidate in (
            directory / "Agent.md",
            directory / "AGENTS.md",
            directory / "claude.md",
            directory / "CLAUDE.md",
            directory / ".claude" / "CLAUDE.md",
            directory / ".claude" / "instructions.md",
        ):
            if not candidate.exists():
                continue
            content = candidate.read_text(encoding="utf-8").strip()
            if content:
                files.append(ContextFile(path=candidate, content=content))

    return _dedupe_files(files)


def render_instruction_files(files: list[ContextFile]) -> str:
    """把发现到的指令文件渲染成 prompt 段落。"""
    sections = ["# Claude instructions"]
    remaining = MAX_TOTAL_INSTRUCTION_CHARS
    for file in files:
        if remaining <= 0:
            sections.append("_Additional instruction content omitted after reaching the prompt budget._")
            break
        rendered = _truncate(
            _collapse_blank_lines(file.content),
            min(MAX_INSTRUCTION_FILE_CHARS, remaining),
        )
        remaining -= len(rendered)
        sections.append(f"## {file.path.name}")
        sections.append(rendered)
    return "\n\n".join(sections)


def build_environment_section(
    cwd: Path | None = None,
    *,
    include_date: bool = True,
) -> str:
    """构建环境上下文段，供主代理与子代理复用。"""
    resolved_cwd = (cwd or Path.cwd()).resolve()
    items = [
        "# 环境上下文",
        f" - 工作目录: {resolved_cwd}",
    ]
    if include_date:
        items.append(f" - 日期: {date.today().isoformat()}")
    items.append(f" - 平台: {platform.system()} {platform.release()}")
    return "\n".join(items)
