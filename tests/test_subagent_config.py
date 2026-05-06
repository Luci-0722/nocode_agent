from __future__ import annotations

import os
import sys
import tempfile
import asyncio
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    import yaml  # noqa: F401
    import langchain  # noqa: F401
    import langgraph  # noqa: F401
except ModuleNotFoundError as exc:  # pragma: no cover - 环境依赖守卫
    raise unittest.SkipTest(f"subagent config tests require repo dependencies: {exc}")


from nocode_agent.agent.subagents import (  # noqa: E402
    AgentDefinition,
    decode_runtime_subagent_type,
    encode_runtime_subagent_name,
    init_agent_registry,
    resolve_agent_tools,
)
from langchain_core.messages import AIMessage, ToolMessage  # noqa: E402
from nocode_agent.tool.delegate import make_agent_tool  # noqa: E402
from nocode_agent.tool.registry import build_subagent_type_description  # noqa: E402


class SubagentConfigTest(unittest.TestCase):
    def test_registry_discovers_custom_agents_and_project_overrides_user(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            project_root = temp_root / "project"
            subdir = project_root / "app"
            user_home = temp_root / "home"
            project_agents = project_root / ".nocode" / "agents"
            user_agents = user_home / ".nocode" / "agents"

            subdir.mkdir(parents=True)
            project_agents.mkdir(parents=True)
            user_agents.mkdir(parents=True)

            (user_agents / "reviewer.md").write_text(
                """---
name: reviewer
description: User reviewer
tools: [read, grep]
model: user-model
---
You are the user reviewer.
""",
                encoding="utf-8",
            )
            (project_agents / "reviewer.md").write_text(
                """---
name: reviewer
description: Project reviewer
tools: [read, grep, bash]
disallowedTools: [bash]
model: project-model
---
You are the project reviewer.
""",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"HOME": str(user_home)}, clear=False):
                registry = init_agent_registry(subdir)

            agent = registry.get("reviewer")
            self.assertIsNotNone(agent)
            assert agent is not None
            self.assertEqual(agent.when_to_use, "Project reviewer")
            self.assertEqual(agent.allowed_tools, ["read", "grep", "bash"])
            self.assertEqual(agent.disallowed_tools, ["bash"])
            self.assertEqual(agent.model, "project-model")
            self.assertIn("You are the project reviewer.", agent.get_system_prompt())
            self.assertIn("Notes:", agent.get_system_prompt())

            builtin = registry.get("general-purpose")
            self.assertIsNotNone(builtin)
            assert builtin is not None
            self.assertEqual(builtin.source, "builtin")
            self.assertEqual(builtin.definition_path, REPO_ROOT / "src" / "nocode_agent" / "bundled_agents" / "general-purpose.md")

    def test_project_agent_can_override_builtin_agent_definition(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            project_root = temp_root / "project"
            subdir = project_root / "app"
            project_agents = project_root / ".nocode" / "agents"

            subdir.mkdir(parents=True)
            project_agents.mkdir(parents=True)

            (project_agents / "general-purpose.md").write_text(
                """---
name: general-purpose
description: Project-specific general purpose agent
tools: [read, write]
---
You are the project general-purpose agent.
""",
                encoding="utf-8",
            )

            registry = init_agent_registry(subdir)

            agent = registry.get("general-purpose")
            self.assertIsNotNone(agent)
            assert agent is not None
            self.assertEqual(agent.when_to_use, "Project-specific general purpose agent")
            self.assertEqual(agent.source, "project")
            self.assertEqual(agent.allowed_tools, ["read", "write"])
            self.assertEqual(agent.definition_path, (project_agents / "general-purpose.md").resolve())
            self.assertIn("You are the project general-purpose agent.", agent.get_system_prompt())

    def test_registry_requires_description_frontmatter_for_when_to_use(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            project_root = temp_root / "project"
            subdir = project_root / "app"
            project_agents = project_root / ".nocode" / "agents"

            subdir.mkdir(parents=True)
            project_agents.mkdir(parents=True)

            (project_agents / "reviewer.md").write_text(
                """---
name: reviewer
when_to_use: Review code
---
You are the project reviewer.
""",
                encoding="utf-8",
            )

            registry = init_agent_registry(subdir)

            self.assertIsNone(registry.get("reviewer"))

    def test_resolve_agent_tools_honors_allow_and_deny_lists(self) -> None:
        all_tools = [
            SimpleNamespace(name="read"),
            SimpleNamespace(name="write"),
            SimpleNamespace(name="grep"),
            SimpleNamespace(name="bash"),
        ]
        readonly_tools = [
            SimpleNamespace(name="read"),
            SimpleNamespace(name="grep"),
            SimpleNamespace(name="bash"),
        ]

        reviewer = AgentDefinition(
            agent_type="reviewer",
            when_to_use="Review code",
            allowed_tools=["read", "write", "grep"],
            disallowed_tools=["write"],
        )
        selected = resolve_agent_tools(
            reviewer,
            all_tools=all_tools,
            readonly_tools=readonly_tools,
        )
        self.assertEqual([tool.name for tool in selected], ["read", "grep"])

        explore = AgentDefinition(
            agent_type="Explore",
            when_to_use="Explore code",
            disallowed_tools=["write", "edit", "delegate_code"],
        )
        readonly_selected = resolve_agent_tools(
            explore,
            all_tools=all_tools,
            readonly_tools=readonly_tools,
        )
        self.assertEqual([tool.name for tool in readonly_selected], ["read", "grep", "bash"])

    def test_runtime_name_round_trip_for_custom_agent(self) -> None:
        runtime_name = encode_runtime_subagent_name("code reviewer v2")
        self.assertNotEqual(runtime_name, "code reviewer v2")
        self.assertEqual(decode_runtime_subagent_type(runtime_name), "code reviewer v2")

    def test_subagent_description_includes_custom_agent(self) -> None:
        description = build_subagent_type_description([
            AgentDefinition(
                agent_type="reviewer",
                when_to_use="Review database migrations",
                allowed_tools=["read", "grep"],
            )
        ])
        self.assertIn("reviewer", description)
        self.assertIn("Review database migrations", description)
        self.assertIn("read, grep", description)

    def test_delegate_code_returns_full_subagent_summary(self) -> None:
        long_summary = "\x1b[31m" + ("x" * 13_000) + "\x1b[0m"

        class FakeAgent:
            async def astream(self, payload, config=None, stream_mode=None, version=None):  # noqa: ANN001
                yield (
                    "updates",
                    {"model": {"messages": [AIMessage(content=long_summary)]}},
                )

        delegate_code = make_agent_tool({"Explore": FakeAgent()})
        events: list[dict] = []
        with patch("langgraph.config.get_stream_writer", return_value=events.append):
            result = asyncio.run(
                delegate_code.ainvoke(
                    {
                        "type": "tool_call",
                        "name": "delegate_code",
                        "args": {
                            "subagent_type": "Explore",
                            "task": "return a long summary",
                        },
                        "id": "parent-tool",
                    }
                )
            )

        self.assertEqual(result.content, "x" * 13_000)
        self.assertNotIn("已截断", result.content)
        self.assertNotIn("\x1b[31m", result.content)
        self.assertEqual(events[0]["type"], "subagent_start")
        self.assertEqual(events[-1]["type"], "subagent_finish")

    def test_delegate_code_streams_subagent_tool_events(self) -> None:
        class FakeAgent:
            async def astream(self, payload, config=None, stream_mode=None, version=None):  # noqa: ANN001
                yield (
                    "updates",
                    {
                        "model": {
                            "messages": [
                                AIMessage(
                                    content="",
                                    tool_calls=[
                                        {
                                            "name": "read",
                                            "args": {"path": "src/nocode_agent/tool/delegate.py"},
                                            "id": "sub-tool",
                                        }
                                    ],
                                )
                            ]
                        }
                    },
                )
                yield (
                    "updates",
                    {
                        "tools": {
                            "messages": [
                                ToolMessage(
                                    content="\x1b[32mfile content\x1b[0m",
                                    name="read",
                                    tool_call_id="sub-tool",
                                )
                            ]
                        }
                    },
                )
                yield (
                    "updates",
                    {"model": {"messages": [AIMessage(content="done")]}},
                )

        delegate_code = make_agent_tool({"Explore": FakeAgent()})
        events: list[dict] = []
        with patch("langgraph.config.get_stream_writer", return_value=events.append):
            result = asyncio.run(
                delegate_code.ainvoke(
                    {
                        "type": "tool_call",
                        "name": "delegate_code",
                        "args": {
                            "subagent_type": "Explore",
                            "task": "inspect the delegate tool",
                            "thread_id": "named-thread",
                        },
                        "id": "parent-tool",
                    }
                )
            )

        self.assertEqual(result.content, "done")
        self.assertEqual(
            [event["type"] for event in events],
            ["subagent_start", "subagent_tool_start", "subagent_tool_end", "subagent_finish"],
        )
        for event in events:
            self.assertEqual(event["parent_tool_call_id"], "parent-tool")
            self.assertEqual(event["subagent_id"], "subagent-named-named-thread")
            self.assertEqual(event["subagent_type"], "Explore")
        self.assertEqual(events[1]["name"], "read")
        self.assertEqual(events[1]["args"], {"path": "src/nocode_agent/tool/delegate.py"})
        self.assertEqual(events[2]["tool_call_id"], "sub-tool")
        self.assertEqual(events[2]["output"], "file content")


if __name__ == "__main__":
    unittest.main()
