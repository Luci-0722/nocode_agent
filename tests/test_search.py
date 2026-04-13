from __future__ import annotations

import sys
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
    raise unittest.SkipTest(f"search tests require repo dependencies: {exc}")


from nocode_agent.tool import search  # noqa: E402


class SearchToolTest(unittest.TestCase):
    def tearDown(self) -> None:
        search._rg_path = None

    def test_find_rg_binary_supports_windows_bundled_exe(self) -> None:
        temp_root = Path(r"D:\repo")
        bundled = temp_root / "bin" / "rg-windows-x86_64.exe"

        def fake_exists(self: Path) -> bool:
            return self == bundled

        def fake_access(path: str, mode: int) -> bool:
            return path == str(bundled)

        with (
            patch("nocode_agent.tool.search.repo_root", return_value=temp_root),
            patch("nocode_agent.tool.search.platform.system", return_value="Windows"),
            patch("nocode_agent.tool.search.platform.machine", return_value="AMD64"),
            patch("nocode_agent.tool.search.shutil.which", return_value=None),
            patch("pathlib.Path.exists", autospec=True, side_effect=fake_exists),
            patch("nocode_agent.tool.search.os.access", side_effect=fake_access),
        ):
            self.assertEqual(search._find_rg_binary(), str(bundled))

    def test_find_rg_binary_falls_back_to_system_rg_on_windows(self) -> None:
        system_rg = r"C:\Tools\rg.exe"
        with (
            patch("nocode_agent.tool.search.repo_root", return_value=REPO_ROOT),
            patch("nocode_agent.tool.search.platform.system", return_value="Windows"),
            patch("nocode_agent.tool.search.platform.machine", return_value="AMD64"),
            patch("nocode_agent.tool.search.shutil.which", return_value=system_rg),
        ):
            self.assertEqual(search._find_rg_binary(), system_rg)

    def test_grep_with_rg_uses_workspace_relative_search_root(self) -> None:
        workspace = Path(r"D:\workspace")
        target = workspace / "src" / "app.py"
        captured: dict[str, object] = {}

        async def fake_run_rg(cmd: list[str], cwd: Path) -> tuple[bytes, bytes, int]:
            captured["cmd"] = cmd
            captured["cwd"] = cwd
            return (b"src\\app.py:12:print('hi')", b"", 0)

        with (
            patch("nocode_agent.tool.search._get_rg_path", return_value="rg"),
            patch("nocode_agent.tool.search._run_rg", side_effect=fake_run_rg),
            patch("nocode_agent.tool.kit._workspace_root", return_value=workspace),
        ):
            result = search._grep_with_rg("print", target, "*.py", "content", 0, 20)

        self.assertEqual(result, r"src\app.py:12:print('hi')")
        self.assertEqual(captured["cwd"], workspace)
        self.assertEqual(
            captured["cmd"],
            [
                "rg",
                "--no-config",
                "--no-ignore-vcs",
                "--line-number",
                "--max-count",
                "20",
                "--glob",
                "*.py",
                "print",
                r"src\app.py",
            ],
        )


if __name__ == "__main__":
    unittest.main()
