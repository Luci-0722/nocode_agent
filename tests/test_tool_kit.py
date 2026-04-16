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

try:
    import pydantic  # noqa: F401
    import langchain  # noqa: F401
except ModuleNotFoundError as exc:  # pragma: no cover - 环境依赖守卫
    raise unittest.SkipTest(f"tool kit tests require repo dependencies: {exc}")


from nocode_agent.config import load_config  # noqa: E402
from nocode_agent.runtime import workspace  # noqa: E402
from nocode_agent.tool import filesystem, kit, search  # noqa: E402


class ToolKitSecurityTest(unittest.TestCase):
    def setUp(self) -> None:
        kit._get_deny_paths.cache_clear()
        workspace.invalidate_workspace_cache()

    def tearDown(self) -> None:
        kit._get_deny_paths.cache_clear()
        workspace.invalidate_workspace_cache()

    def test_resolve_path_rejects_custom_deny_path_within_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            secret_dir = workspace / "secrets"
            secret_dir.mkdir()

            with (
                patch("pathlib.Path.cwd", return_value=workspace),
                patch(
                    "nocode_agent.config.load_config",
                    return_value={"security": {"deny_paths": [str(secret_dir)]}},
                ),
            ):
                with self.assertRaisesRegex(ValueError, "命中禁止访问规则"):
                    kit._resolve_path("secrets/token.txt")

    def test_resolve_path_rejects_default_sensitive_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            home_dir = temp_root / "home"
            ssh_dir = home_dir / ".ssh"
            ssh_dir.mkdir(parents=True)
            (ssh_dir / "id_rsa").write_text("secret", encoding="utf-8")

            with (
                patch.dict(os.environ, {"HOME": str(home_dir)}, clear=False),
                patch("pathlib.Path.cwd", return_value=home_dir),
                patch("nocode_agent.config.load_config", return_value={}),
            ):
                with self.assertRaisesRegex(ValueError, r"\.ssh"):
                    kit._resolve_path(".ssh/id_rsa")

    def test_glob_search_skips_denied_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            secret_dir = workspace / "secrets"
            secret_dir.mkdir()
            (workspace / "visible.txt").write_text("visible", encoding="utf-8")
            (secret_dir / "hidden.txt").write_text("hidden", encoding="utf-8")

            with (
                patch("pathlib.Path.cwd", return_value=workspace),
                patch(
                    "nocode_agent.config.load_config",
                    return_value={"security": {"deny_paths": [str(secret_dir)]}},
                ),
            ):
                result = filesystem.glob_search.invoke({"pattern": "**/*.txt"})

        self.assertIn("visible.txt", result)
        self.assertNotIn("hidden.txt", result)

    def test_python_grep_skips_denied_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            secret_dir = workspace / "secrets"
            secret_dir.mkdir()
            (secret_dir / "hidden.txt").write_text("TOKEN=secret", encoding="utf-8")

            with (
                patch("pathlib.Path.cwd", return_value=workspace),
                patch(
                    "nocode_agent.config.load_config",
                    return_value={"security": {"deny_paths": [str(secret_dir)]}},
                ),
                patch("nocode_agent.tool.search._get_rg_path", return_value=None),
            ):
                result = search.grep_search.invoke(
                    {
                        "pattern": "TOKEN",
                        "path": ".",
                        "file_glob": "*.txt",
                        "output_mode": "content",
                        "context_lines": 0,
                        "max_matches": 20,
                    }
                )

        self.assertEqual(result, "未找到匹配内容。")

    def test_resolve_path_allows_project_config_additional_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            project_root = temp_root / "project"
            extra_dir = temp_root / "shared"
            config_file = project_root / ".nocode" / "config.yaml"
            target = extra_dir / "notes.txt"

            project_root.mkdir()
            extra_dir.mkdir()
            config_file.parent.mkdir(parents=True)
            config_file.write_text(
                f"workspace:\n  additional_directories:\n    - {extra_dir}\n",
                encoding="utf-8",
            )

            with patch("pathlib.Path.cwd", return_value=project_root):
                resolved = kit._resolve_path(str(target))

            self.assertEqual(resolved, target.resolve())

    def test_persist_additional_workspace_roots_creates_project_config_without_hiding_global_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            user_home = temp_root / "home"
            project_root = temp_root / "project"
            extra_dir = temp_root / "shared"
            global_config = user_home / ".nocode" / "config.yaml"
            project_config = project_root / ".nocode" / "config.yaml"

            user_home.mkdir()
            project_root.mkdir()
            extra_dir.mkdir()
            global_config.parent.mkdir(parents=True)
            global_config.write_text(
                "default_model: global\nmodels:\n  global:\n    model: test-model\n",
                encoding="utf-8",
            )

            with (
                patch.dict(os.environ, {"HOME": str(user_home)}, clear=False),
                patch("pathlib.Path.cwd", return_value=project_root),
            ):
                persisted = workspace.persist_additional_workspace_roots([extra_dir])

                self.assertEqual(persisted, (extra_dir.resolve(),))
                self.assertEqual(kit._resolve_path(str(extra_dir / "data.txt")), (extra_dir / "data.txt").resolve())
                self.assertTrue(project_config.exists())
                self.assertEqual(load_config().get("default_model"), "global")

            payload = project_config.read_text(encoding="utf-8")
            self.assertIn("workspace:", payload)
            self.assertIn(str(extra_dir.resolve()), payload)


if __name__ == "__main__":
    unittest.main()
