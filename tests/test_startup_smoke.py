from __future__ import annotations

import json
import os
import pty
import select
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = REPO_ROOT / "nocode"


def _python_bin() -> str:
    """优先复用仓库虚拟环境，避免系统解释器缺少依赖。"""
    if sys.platform == "win32":
        venv_python = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = REPO_ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


class LauncherSmokeTest(unittest.TestCase):
    def test_launcher_uses_real_project_root_when_invoked_via_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            fake_bin = temp_root / "fake-bin"
            fake_bin.mkdir()
            output_path = temp_root / "node-output.txt"
            fake_node = fake_bin / "node"
            fake_node.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    {
                      printf 'cwd=%s\n' "$PWD"
                      printf 'project=%s\n' "${NOCODE_PROJECT_DIR:-}"
                      printf 'arg1=%s\n' "${1:-}"
                      printf 'arg2=%s\n' "${2:-}"
                    } > "${FAKE_NODE_OUTPUT:?}"
                    """
                ),
                encoding="utf-8",
            )
            fake_node.chmod(fake_node.stat().st_mode | stat.S_IXUSR)

            launcher_link = temp_root / "nocode"
            launcher_link.symlink_to(LAUNCHER_PATH)

            working_dir = temp_root / "workspace"
            working_dir.mkdir()
            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
            env["FAKE_NODE_OUTPUT"] = str(output_path)
            env.pop("NOCODE_PROJECT_DIR", None)

            completed = subprocess.run(
                [str(launcher_link), "--resume"],
                cwd=working_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            payload = dict(
                line.split("=", 1)
                for line in output_path.read_text(encoding="utf-8").splitlines()
            )
            self.assertEqual(Path(payload["cwd"]).resolve(), working_dir.resolve())
            self.assertEqual(Path(payload["project"]).resolve(), REPO_ROOT.resolve())
            self.assertEqual(Path(payload["arg1"]).resolve(), (REPO_ROOT / "frontend" / "tui.ts").resolve())
            self.assertEqual(payload["arg2"], "--resume")

    def test_launcher_overrides_stale_project_root_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            fake_bin = temp_root / "fake-bin"
            fake_bin.mkdir()
            output_path = temp_root / "node-output.txt"
            fake_node = fake_bin / "node"
            fake_node.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    printf '%s\n' "${NOCODE_PROJECT_DIR:-}" > "${FAKE_NODE_OUTPUT:?}"
                    """
                ),
                encoding="utf-8",
            )
            fake_node.chmod(fake_node.stat().st_mode | stat.S_IXUSR)

            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
            env["FAKE_NODE_OUTPUT"] = str(output_path)
            env["NOCODE_PROJECT_DIR"] = "/Users/lucheng/Projects/NoCode"

            completed = subprocess.run(
                [str(LAUNCHER_PATH)],
                cwd=temp_root,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            resolved_project_dir = Path(output_path.read_text(encoding="utf-8").strip()).resolve()
            self.assertEqual(resolved_project_dir, REPO_ROOT.resolve())


@unittest.skipIf(sys.platform == "win32", "当前冒烟测试依赖 POSIX 只读目录权限")
class BackendStartupSmokeTest(unittest.TestCase):
    def test_backend_can_start_from_readonly_cwd_with_relative_state_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            project_root = temp_root / "project-root"
            project_root.mkdir()
            config_path = project_root / "config.yaml"
            config_path.write_text(
                textwrap.dedent(
                    """\
                    model: qwen2.5-coder:14b
                    base_url: "http://127.0.0.1:11434/v1"
                    max_tokens: 256
                    temperature: 0.1
                    subagent_model: qwen2.5-coder:14b
                    checkpoint_db_path: ".state/langgraph-checkpoints.sqlite"
                    acp_sessions_path: ".state/acp-sessions.json"
                    auto_compact:
                      enabled: true
                    session_memory:
                      enabled: true
                      storage_path: ".state/session-memory"
                    """
                ),
                encoding="utf-8",
            )

            readonly_cwd = temp_root / "readonly-cwd"
            readonly_cwd.mkdir()
            readonly_cwd.chmod(0o555)

            env = os.environ.copy()
            env["NOCODE_PROJECT_DIR"] = str(project_root)
            env["NOCODE_AGENT_CONFIG"] = str(config_path)
            python_path_entries = [str(REPO_ROOT / "src")]
            if env.get("PYTHONPATH"):
                python_path_entries.append(env["PYTHONPATH"])
            env["PYTHONPATH"] = os.pathsep.join(python_path_entries)

            process = subprocess.Popen(
                [_python_bin(), "-m", "nocode_agent.app.backend_stdio"],
                cwd=readonly_cwd,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            events: list[dict[str, object]] = []
            stderr_output = ""
            try:
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    ready, _, _ = select.select([process.stdout], [], [], 0.5)
                    if ready:
                        line = process.stdout.readline()
                        if not line:
                            break
                        if line.strip().startswith("{"):
                            event = json.loads(line)
                            events.append(event)
                            if event.get("type") == "hello":
                                break
                    if process.poll() is not None:
                        break
            finally:
                if process.stdin is not None:
                    process.stdin.close()
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                readonly_cwd.chmod(0o755)
                if process.stderr is not None:
                    stderr_output = process.stderr.read()
                    process.stderr.close()
                if process.stdout is not None:
                    process.stdout.close()

            if process.returncode not in (0, -15):
                self.fail(f"stdout events={events}\n\nstderr:\n{stderr_output}")

            hello_event = next((event for event in events if event.get("type") == "hello"), None)
            self.assertIsNotNone(hello_event, msg=stderr_output)
            self.assertEqual(Path(str(hello_event["cwd"])).resolve(), readonly_cwd.resolve())
            self.assertTrue((project_root / ".state" / "langgraph-checkpoints.sqlite").exists())
            self.assertFalse((readonly_cwd / ".state").exists())


@unittest.skipIf(sys.platform == "win32", "当前冒烟测试依赖 POSIX PTY")
class TuiBackendErrorVisibilityTest(unittest.TestCase):
    def test_tui_shows_backend_stderr_excerpt_and_log_path_on_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            fake_backend = temp_root / "fake-python"
            fake_backend.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    printf 'mock stderr line 1\\nmock stderr line 2\\n' >&2
                    printf '{"type":"fatal","message":"mock fatal"}\\n'
                    sleep 0.2
                    exit 1
                    """
                ),
                encoding="utf-8",
            )
            fake_backend.chmod(fake_backend.stat().st_mode | stat.S_IXUSR)

            log_path = temp_root / "mock-backend.log"
            env = os.environ.copy()
            env["PYTHON_BIN"] = str(fake_backend)
            # 让这条用例绕过仓库内 .venv，稳定命中 fake backend 分支。
            env["NOCODE_PROJECT_DIR"] = str(temp_root)
            env["NOCODE_LOG_FILE"] = str(log_path)
            env["TERM"] = env.get("TERM", "xterm-256color")

            master_fd, slave_fd = pty.openpty()
            process = subprocess.Popen(
                ["node", "frontend/tui.ts"],
                cwd=REPO_ROOT,
                env=env,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
            )
            os.close(slave_fd)

            output = bytearray()
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    ready, _, _ = select.select([master_fd], [], [], 0.5)
                    if ready:
                        chunk = os.read(master_fd, 8192)
                        if not chunk:
                            break
                        output.extend(chunk)
                        decoded = output.decode("utf-8", errors="ignore")
                        if (
                            "fatal: mock fatal" in decoded
                            and "最近 stderr:" in decoded
                            and "mock stderr line 2" in decoded
                            and f"日志文件: {log_path}" in decoded
                        ):
                            break
                    if process.poll() is not None:
                        break
            finally:
                if process.poll() is None:
                    os.write(master_fd, b"\x03")
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                os.close(master_fd)

            decoded = output.decode("utf-8", errors="ignore")
            self.assertIn("fatal: mock fatal", decoded)
            self.assertIn("最近 stderr:", decoded)
            self.assertIn("mock stderr line 2", decoded)
            self.assertIn(f"日志文件: {log_path}", decoded)

    def test_tui_prefers_repo_venv_over_stale_python_bin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            fake_python = temp_root / "fake-python"
            marker_path = temp_root / "fake-python-used.txt"
            fake_python.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    printf 'used\\n' > {marker_path!s}
                    printf 'stale python bin should not be used\\n' >&2
                    exit 1
                    """
                ),
                encoding="utf-8",
            )
            fake_python.chmod(fake_python.stat().st_mode | stat.S_IXUSR)

            env = os.environ.copy()
            env["PYTHON_BIN"] = str(fake_python)
            env["TERM"] = env.get("TERM", "xterm-256color")

            master_fd, slave_fd = pty.openpty()
            process = subprocess.Popen(
                ["node", "frontend/tui.ts"],
                cwd=REPO_ROOT,
                env=env,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
            )
            os.close(slave_fd)

            output = bytearray()
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    ready, _, _ = select.select([master_fd], [], [], 0.5)
                    if ready:
                        chunk = os.read(master_fd, 8192)
                        if not chunk:
                            break
                        output.extend(chunk)
                        decoded = output.decode("utf-8", errors="ignore")
                        if "model: glm-5" in decoded and "backend exited with code 1" not in decoded:
                            break
                    if process.poll() is not None:
                        break
            finally:
                if process.poll() is None:
                    os.write(master_fd, b"\x03")
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                os.close(master_fd)

            decoded = output.decode("utf-8", errors="ignore")
            self.assertIn("model: glm-5", decoded)
            self.assertFalse(marker_path.exists(), msg=decoded)


if __name__ == "__main__":
    unittest.main()
