"""动态提示词中间件，每次模型调用前实时读取指令文件和 skills。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import SystemMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command
from typing_extensions import override

from nocode_agent.skills.discover import SkillDiscover
from nocode_agent.skills.listing import SkillListBuilder
from nocode_agent.skills.registry import get_skill_registry

from .main import build_agent_listing_section, get_static_prompt

logger = logging.getLogger(__name__)


class DynamicPromptMiddleware(AgentMiddleware):
    """每次模型调用前动态构建 system prompt。

    功能：
    - 实时读取 AGENTS.md 等指令文件
    - 实时扫描 skills 目录
    - 可选 mtime 缓存减少 I/O
    """

    def __init__(
        self,
        cwd: Path,
        *,
        use_cache: bool = True,
    ) -> None:
        self._cwd = cwd.resolve()
        self._use_cache = use_cache
        # mtime 缓存: path_str -> (mtime, content)
        self._file_cache: dict[str, tuple[float, str]] = {}
        # skills 缓存: (dir_str, mtime) -> entries
        self._skills_cache_key: tuple[str, float] | None = None
        self._skills_cache_entries: list[Any] | None = None

    @override
    async def awrap_model_call(self, request: Any, handler: Any) -> Any:
        """每次模型调用前动态构建并注入 system prompt。"""
        prompt = self._build_prompt()
        new_system = SystemMessage(content=prompt)
        return await handler(request.override(system_message=new_system))

    def _build_prompt(self) -> str:
        """构建完整的 system prompt。"""
        static = get_static_prompt()
        dynamic = self._build_dynamic_prompt()
        return static + "\n\n" + dynamic

    def _build_dynamic_prompt(self) -> str:
        """构建动态部分：环境、指令文件、subagents、skills。"""
        from .context import build_environment_section, discover_instruction_files, render_instruction_files

        sections = [build_environment_section(self._cwd)]

        # 实时读取指令文件
        if self._use_cache:
            files = self._discover_instruction_files_cached()
        else:
            files = discover_instruction_files(self._cwd)

        if files:
            sections.append(render_instruction_files(files))

        agent_listing = build_agent_listing_section()
        if agent_listing:
            sections.append(agent_listing)

        # 实时扫描 skills
        skills_section = self._build_skills_section()
        if skills_section:
            sections.append(skills_section)

        return "\n\n".join(sections)

    def _discover_instruction_files_cached(self) -> list[Any]:
        """带 mtime 缓存的指令文件发现。"""
        from .context import ContextFile

        directories = [self._cwd, *self._cwd.parents]
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
                content = self._read_file_cached(candidate)
                if content:
                    files.append(ContextFile(path=candidate, content=content))

        return files

    def _read_file_cached(self, path: Path) -> str:
        """带 mtime 缓存的文件读取。"""
        path_str = str(path)
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return ""

        cached = self._file_cache.get(path_str)
        if cached and cached[0] == mtime:
            return cached[1]

        try:
            content = path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""

        self._file_cache[path_str] = (mtime, content)
        return content

    def _build_skills_section(self) -> str:
        """构建 skills 列表部分。"""
        registry = get_skill_registry()

        if self._use_cache:
            entries = self._discover_skills_cached()
            # 更新 registry
            registry._skills.clear()
            registry._sent_skill_names.clear()
            for entry in entries:
                registry._skills[entry.name] = entry
        else:
            discover = SkillDiscover(self._cwd)
            entries = discover.discover_all()
            registry._skills.clear()
            registry._sent_skill_names.clear()
            for entry in entries:
                registry._skills[entry.name] = entry

        # 获取所有可用的 skills（标记为已发送）
        tool_skills = registry.get_tool_skills()
        for s in tool_skills:
            registry._sent_skill_names.add(s.name)

        if not tool_skills:
            return ""

        return SkillListBuilder().build_listing(tool_skills) or ""

    def _discover_skills_cached(self) -> list[Any]:
        """带缓存键的 skills 发现。"""
        # 计算所有 skills 目录的聚合 mtime
        discover = SkillDiscover(self._cwd)
        all_dirs: list[Path] = []

        # 收集所有扫描的目录
        for parent in [self._cwd, *self._cwd.parents]:
            skills_dir = parent / ".nocode" / "skills"
            if skills_dir.exists():
                all_dirs.append(skills_dir)

        user_dir = Path.home() / ".nocode" / "skills"
        if user_dir.exists():
            all_dirs.append(user_dir)

        builtin_dir = Path(__file__).resolve().parent.parent / "bundled_skills"
        if builtin_dir.exists():
            all_dirs.append(builtin_dir)

        # 计算聚合 mtime
        cache_key: tuple[str, float] = ("", 0.0)
        for d in all_dirs:
            try:
                mtime = d.stat().st_mtime
                cache_key = (cache_key[0] + str(d), cache_key[1] + mtime)
            except OSError:
                pass

        # 检查缓存
        if self._skills_cache_key == cache_key and self._skills_cache_entries is not None:
            return self._skills_cache_entries

        # 重新扫描
        entries = discover.discover_all()
        self._skills_cache_key = cache_key
        self._skills_cache_entries = entries
        return entries


__all__ = ["DynamicPromptMiddleware"]
