from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    import pydantic  # noqa: F401
    import langchain  # noqa: F401
except ModuleNotFoundError as exc:  # pragma: no cover - 环境依赖守卫
    raise unittest.SkipTest(f"hitl workspace tests require repo dependencies: {exc}")


from langchain_core.messages import AIMessage  # noqa: E402

from nocode_agent.runtime.hitl import build_human_in_the_loop_middleware  # noqa: E402
from nocode_agent.runtime.workspace import invalidate_workspace_cache  # noqa: E402


class HitlWorkspacePermissionTest(unittest.TestCase):
    def setUp(self) -> None:
        invalidate_workspace_cache()

    def tearDown(self) -> None:
        invalidate_workspace_cache()

    def test_workspace_permission_approval_persists_directory_to_project_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            user_home = temp_root / "home"
            project_root = temp_root / "project"
            extra_dir = temp_root / "shared"
            target_file = extra_dir / "note.txt"
            captured: dict[str, object] = {}

            user_home.mkdir()
            project_root.mkdir()
            extra_dir.mkdir()

            middleware = build_human_in_the_loop_middleware(
                {"enabled": True, "interrupt_on": {}}
            )
            self.assertIsNotNone(middleware)

            message = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "read",
                        "args": {"file_path": str(target_file)},
                        "id": "tool-1",
                    }
                ],
            )

            def fake_interrupt(request):
                captured["request"] = request
                return {"decisions": [{"type": "approve"}]}

            with (
                patch.dict(os.environ, {"HOME": str(user_home)}, clear=False),
                patch("pathlib.Path.cwd", return_value=project_root),
                patch("nocode_agent.runtime.hitl.interrupt", side_effect=fake_interrupt),
            ):
                result = middleware.after_model({"messages": [message]}, runtime=object())

            self.assertIsNotNone(result)
            self.assertEqual(len(message.tool_calls), 1)

            request = captured["request"]
            action = request["action_requests"][0]
            self.assertEqual(action["name"], "read")
            self.assertEqual(
                action["args"]["additional_directories"],
                [str(extra_dir.resolve())],
            )
            self.assertEqual(action["args"]["file_path"], str(target_file))

            project_config = project_root / ".nocode" / "config.yaml"
            payload = yaml.safe_load(project_config.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["workspace"]["additional_directories"],
                [str(extra_dir.resolve())],
            )


if __name__ == "__main__":
    unittest.main()
