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


from nocode_agent.tool import filesystem, kit, search  # noqa: E402


class ToolKitSecurityTest(unittest.TestCase):
    def setUp(self) -> None:
        kit._get_deny_paths.cache_clear()

    def tearDown(self) -> None:
        kit._get_deny_paths.cache_clear()

    def test_resolve_path_rejects_custom_deny_path_within_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            secret_dir = workspace / "secrets"
            secret_dir.mkdir()

            with (
                patch("nocode_agent.tool.kit._workspace_root", return_value=workspace),
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
                patch("nocode_agent.tool.kit._workspace_root", return_value=home_dir),
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
                patch("nocode_agent.tool.kit._workspace_root", return_value=workspace),
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
                patch("nocode_agent.tool.kit._workspace_root", return_value=workspace),
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


if __name__ == "__main__":
    unittest.main()
