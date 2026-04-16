from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from nocode_agent.runtime.paths import (  # noqa: E402
    default_acp_sessions_path,
    default_checkpoint_db_path,
    default_session_memory_path,
    project_config_path,
    runtime_root,
)
from nocode_agent.config import load_config  # noqa: E402


class RuntimePathsTest(unittest.TestCase):
    def test_default_state_paths_do_not_fallback_to_project_state_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            project_root = temp_root / "project"
            legacy_state_dir = project_root / ".state"
            user_home = temp_root / "home"

            legacy_state_dir.mkdir(parents=True)
            (legacy_state_dir / "langgraph-checkpoints.sqlite").write_text("", encoding="utf-8")
            (legacy_state_dir / "acp-sessions.json").write_text("{}", encoding="utf-8")
            (legacy_state_dir / "session-memory").mkdir()

            with patch.dict(os.environ, {"HOME": str(user_home)}, clear=False):
                with patch("pathlib.Path.cwd", return_value=project_root):
                    expected_root = user_home / ".nocode" / "projects"
                    self.assertEqual(runtime_root(), project_root.resolve())

                    checkpoint = default_checkpoint_db_path()
                    acp_sessions = default_acp_sessions_path()
                    session_memory = default_session_memory_path()

            self.assertIn(expected_root, checkpoint.parents)
            self.assertIn(expected_root, acp_sessions.parents)
            self.assertIn(expected_root, session_memory.parents)
            self.assertNotEqual(checkpoint.parent, legacy_state_dir)
            self.assertNotEqual(acp_sessions.parent, legacy_state_dir)
            self.assertNotEqual(session_memory.parent, legacy_state_dir)

    def test_runtime_root_resolves_ancestor_with_project_dot_nocode_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            user_home = temp_root / "home"
            project_root = temp_root / "project"
            nested_cwd = project_root / "src" / "pkg"
            config_file = project_root / ".nocode" / "config.yaml"

            user_home.mkdir()
            nested_cwd.mkdir(parents=True)
            config_file.parent.mkdir(parents=True)
            config_file.write_text("default_model: project\n", encoding="utf-8")

            with patch.dict(os.environ, {"HOME": str(user_home)}, clear=False):
                with patch("pathlib.Path.cwd", return_value=nested_cwd):
                    self.assertEqual(runtime_root(), project_root.resolve())
                    self.assertEqual(project_config_path(), config_file.resolve())

    def test_runtime_root_does_not_treat_home_global_config_as_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            user_home = temp_root / "home"
            cwd = user_home / "workspace" / "nested"
            global_config = user_home / ".nocode" / "config.yaml"

            cwd.mkdir(parents=True)
            global_config.parent.mkdir(parents=True)
            global_config.write_text("default_model: global\n", encoding="utf-8")

            with patch.dict(os.environ, {"HOME": str(user_home)}, clear=False):
                with patch("pathlib.Path.cwd", return_value=cwd):
                    self.assertEqual(runtime_root(), cwd.resolve())
                    self.assertEqual(load_config().get("default_model"), "global")

    def test_load_config_prefers_project_dot_nocode_config_over_legacy_root_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            user_home = temp_root / "home"
            project_root = temp_root / "project"
            cwd = project_root / "app"
            legacy_root_config = project_root / "config.yaml"
            project_config = project_root / ".nocode" / "config.yaml"

            user_home.mkdir()
            cwd.mkdir(parents=True)
            legacy_root_config.write_text("default_model: legacy\n", encoding="utf-8")
            project_config.parent.mkdir(parents=True)
            project_config.write_text("default_model: project\n", encoding="utf-8")

            with patch.dict(os.environ, {"HOME": str(user_home)}, clear=False):
                with patch("pathlib.Path.cwd", return_value=cwd):
                    self.assertEqual(load_config().get("default_model"), "project")

    def test_load_config_ignores_legacy_root_config_and_falls_back_to_global(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            user_home = temp_root / "home"
            project_root = temp_root / "project"
            cwd = project_root / "app"
            legacy_root_config = project_root / "config.yaml"
            global_config = user_home / ".nocode" / "config.yaml"

            user_home.mkdir()
            cwd.mkdir(parents=True)
            legacy_root_config.write_text("default_model: legacy\n", encoding="utf-8")
            global_config.parent.mkdir(parents=True)
            global_config.write_text("default_model: global\n", encoding="utf-8")

            with patch.dict(os.environ, {"HOME": str(user_home)}, clear=False):
                with patch("pathlib.Path.cwd", return_value=cwd):
                    self.assertEqual(load_config().get("default_model"), "global")


if __name__ == "__main__":
    unittest.main()
