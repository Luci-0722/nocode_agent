"""文件系统工具。"""

from __future__ import annotations

from langchain.tools import tool
from pydantic import BaseModel, Field

_FILE_UNCHANGED_STUB = (
    "文件自上次读取后未变更。之前的读取内容仍然有效，无需重复读取。"
)


class ReadInput(BaseModel):
    file_path: str = Field(description="工作区内的文件路径，支持相对路径。")
    offset: int = Field(default=1, ge=1, description="起始行号，从 1 开始。")
    limit: int = Field(default=2000, ge=1, le=4000, description="最多读取多少行。")


@tool("read", args_schema=ReadInput)
def read_file(file_path: str, offset: int = 1, limit: int = 2000) -> str:
    """读取文件内容并返回带行号的文本。"""
    from nocode_agent.runtime.file_state import get_file_state_cache
    from nocode_agent.tool.kit import _resolve_path, _trim_output

    try:
        path = _resolve_path(file_path)
    except ValueError as error:
        return f"错误：{error}"

    cache = get_file_state_cache()
    state = cache.get(path)
    if state is not None and state.is_mtime_valid(path):
        try:
            total_lines = len(path.read_text(encoding="utf-8").splitlines())
            start = offset - 1
            end = min(total_lines, start + limit)
            is_full_read = (start == 0 and end >= total_lines)
            if is_full_read:
                return _FILE_UNCHANGED_STUB
        except Exception:
            pass

    try:
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
    except FileNotFoundError:
        return f"错误：文件不存在: {file_path}"
    except Exception as error:
        return f"错误：读取文件失败: {error}"

    start = offset - 1
    end = min(len(lines), start + limit)
    if start >= len(lines):
        return f"错误：起始行号 {offset} 超出总行数 {len(lines)}。"

    rendered = [f"{index:>6}\t{line}" for index, line in enumerate(lines[start:end], start=offset)]
    suffix = ""
    if start > 0 or end < len(lines):
        suffix = f"\n\n[显示第 {offset}-{end} 行，共 {len(lines)} 行]"

    cache.set(path, content)
    return _trim_output("\n".join(rendered) + suffix)


class WriteInput(BaseModel):
    file_path: str = Field(description="工作区内的文件路径，支持相对路径。")
    content: str = Field(description="完整文件内容。")


@tool("write", args_schema=WriteInput)
def write_file(file_path: str, content: str) -> str:
    """覆盖写入文件。如果是已有文件，必须先使用 read 工具读取过才能写入。"""
    from nocode_agent.runtime.file_state import get_file_state_cache
    from nocode_agent.tool.kit import _resolve_path, logger

    logger.info("write: %s (%d chars)", file_path, len(content))
    try:
        path = _resolve_path(file_path)
    except ValueError as error:
        return f"错误：{error}"

    cache = get_file_state_cache()
    if path.exists() and not cache.has_valid_read(path):
        return (
            "错误：必须先使用 read 工具读取此文件，然后才能写入。"
            "（此检查防止在不了解文件内容的情况下意外覆盖。）"
        )

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        cache.set(path, content)
        return f"已写入 {path}"
    except Exception as error:
        return f"错误：写入失败: {error}"


class EditInput(BaseModel):
    file_path: str = Field(description="工作区内的文件路径。")
    old_text: str = Field(description="要替换的原始文本。")
    new_text: str = Field(description="替换后的文本。")
    replace_all: bool = Field(default=False, description="是否替换全部匹配。")


@tool("edit", args_schema=EditInput)
def edit_file(file_path: str, old_text: str, new_text: str, replace_all: bool = False) -> str:
    """基于精确文本匹配编辑文件。必须先使用 read 工具读取此文件。"""
    from nocode_agent.runtime.file_state import get_file_state_cache
    from nocode_agent.tool.kit import _resolve_path, logger

    logger.info("edit: %s (replace_all=%s)", file_path, replace_all)
    try:
        path = _resolve_path(file_path)
    except ValueError as error:
        return f"错误：{error}"

    cache = get_file_state_cache()
    if not cache.has_valid_read(path):
        if cache.get(path) is None:
            return (
                "错误：必须先使用 read 工具读取此文件，然后才能编辑。"
                "（此检查防止在不了解文件内容的情况下意外修改。）"
            )
        return (
            "错误：文件自上次读取后已被修改（mtime 不匹配），请重新使用 read 读取最新内容。"
        )

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as error:
        return f"错误：读取文件失败: {error}"

    occurrences = content.count(old_text)
    if occurrences == 0:
        return "错误：未找到要替换的文本。"
    if occurrences > 1 and not replace_all:
        return f"错误：命中 {occurrences} 处；如需全部替换，请设置 replace_all=true。"

    updated = content.replace(old_text, new_text) if replace_all else content.replace(old_text, new_text, 1)
    path.write_text(updated, encoding="utf-8")
    cache.set(path, updated)
    return f"已更新 {path}，替换 {occurrences if replace_all else 1} 处。"


class GlobInput(BaseModel):
    pattern: str = Field(description="glob 模式，例如 `nocode_agent/**/*.py`。")


@tool("glob", args_schema=GlobInput)
def glob_search(pattern: str) -> str:
    """在工作区内执行 glob 搜索，返回按修改时间降序排列的路径。目录以 `/` 结尾。"""
    from nocode_agent.tool.kit import _trim_output, _workspace_root

    root = _workspace_root()
    try:
        paths = list(root.glob(pattern))
    except Exception:
        paths = []
    paths.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    matches = []
    for path in paths:
        rel = str(path.relative_to(root))
        if path.is_dir():
            rel += "/"
        matches.append(rel)
    if not matches:
        return "未找到匹配。"
    return _trim_output("\n".join(matches))


class ListDirInput(BaseModel):
    path: str = Field(default=".", description="要列出的目录，默认当前工作区。")
    recursive: bool = Field(default=False, description="是否递归列出子目录。")
    max_entries: int = Field(default=200, ge=1, le=5000, description="最多返回多少条。")


@tool("list_dir", args_schema=ListDirInput)
def list_dir(path: str = ".", recursive: bool = False, max_entries: int = 200) -> str:
    """列出目录内容。"""
    from nocode_agent.tool.kit import _resolve_path, _trim_output, _workspace_root

    try:
        root = _resolve_path(path)
        iterator = root.rglob("*") if recursive else root.iterdir()
        entries: list[str] = []
        workspace = _workspace_root()
        for index, item in enumerate(sorted(iterator), start=1):
            rel = item.relative_to(workspace)
            suffix = "/" if item.is_dir() else ""
            entries.append(f"{rel}{suffix}")
            if index >= max_entries:
                entries.append(f"\n[结果已截断，最多 {max_entries} 条]")
                break
        if not entries:
            return "目录为空。"
        return _trim_output("\n".join(entries))
    except Exception as error:
        return f"错误：列目录失败: {error}"


__all__ = [
    "EditInput",
    "GlobInput",
    "ListDirInput",
    "ReadInput",
    "WriteInput",
    "edit_file",
    "glob_search",
    "list_dir",
    "read_file",
    "write_file",
]
