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
    runtime_root,
)


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


if __name__ == "__main__":
    unittest.main()
