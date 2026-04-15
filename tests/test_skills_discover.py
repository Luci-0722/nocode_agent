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


from nocode_agent.skills.discover import SkillDiscover  # noqa: E402


class SkillDiscoverTest(unittest.TestCase):
    def test_discovers_project_and_user_level_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            project_root = temp_root / "project"
            project_workdir = project_root / "app"
            user_home = temp_root / "home"

            project_skill_dir = project_root / ".nocode" / "skills" / "project-skill"
            user_skill_dir = user_home / ".nocode" / "skills" / "user-skill"

            project_workdir.mkdir(parents=True)
            project_skill_dir.mkdir(parents=True)
            user_skill_dir.mkdir(parents=True)

            (project_skill_dir / "SKILL.md").write_text(
                """---
name: project-skill
description: Project level skill
---
Use the project skill.
""",
                encoding="utf-8",
            )
            (user_skill_dir / "SKILL.md").write_text(
                """---
name: user-skill
description: User level skill
---
Use the user skill.
""",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"HOME": str(user_home)}, clear=False):
                entries = SkillDiscover(project_workdir).discover_all()

            by_name = {entry.name: entry for entry in entries}
            self.assertIn("project-skill", by_name)
            self.assertIn("user-skill", by_name)
            self.assertEqual(by_name["project-skill"].source, "project")
            self.assertEqual(by_name["user-skill"].source, "user")


if __name__ == "__main__":
    unittest.main()
