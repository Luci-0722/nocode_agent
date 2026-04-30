from __future__ import annotations

import hashlib
import json
import os
import pty
import re
import select
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

LAUNCHER_PATH = REPO_ROOT / "nocode"
_FRONTEND_BUILT = False


def _python_bin() -> str:
    """优先复用仓库虚拟环境，避免系统解释器缺少依赖。"""
    if sys.platform == "win32":
        venv_python = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = REPO_ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _ensure_frontend_built() -> None:
    global _FRONTEND_BUILT
    if _FRONTEND_BUILT:
        return
    subprocess.run(
        ["npm", "--prefix", "frontend", "run", "build"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    _FRONTEND_BUILT = True


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", text)


class LauncherSmokeTest(unittest.TestCase):
    def test_launcher_resolves_real_script_path_when_invoked_via_symlink(self) -> None:
        _ensure_frontend_built()
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
            self.assertEqual(payload["project"], "")
            self.assertEqual(Path(payload["arg1"]).resolve(), (REPO_ROOT / "frontend" / "dist" / "index.js").resolve())
            self.assertEqual(payload["arg2"], "--resume")

    def test_launcher_does_not_set_project_root_env(self) -> None:
        _ensure_frontend_built()
        # 启动器不再设置 NOCODE_PROJECT_DIR，让 backend 根据 cwd 自动解析项目根。
        # 这样不同项目目录的会话会隔离到各自的 .state 目录。
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
            # 设置一个陈旧的环境变量，验证启动器不会传递它
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
            # 启动器不再设置 NOCODE_PROJECT_DIR，所以输出应该为空
            output = output_path.read_text(encoding="utf-8").strip()
            self.assertEqual(output, "")


class BackendStdioEncodingTest(unittest.TestCase):
    def test_backend_reconfigures_stdio_to_utf8(self) -> None:
        from nocode_agent.app import stdio

        calls: list[tuple[str, str, str]] = []

        class _FakeStream:
            def __init__(self, name: str) -> None:
                self.name = name

            def reconfigure(self, *, encoding: str, errors: str) -> None:
                calls.append((self.name, encoding, errors))

        with patch.multiple(
            stdio.sys,
            stdin=_FakeStream("stdin"),
            stdout=_FakeStream("stdout"),
            stderr=_FakeStream("stderr"),
        ):
            stdio.configure_stdio_encoding()

        self.assertEqual(
            calls,
            [
                ("stdin", "utf-8", "replace"),
                ("stdout", "utf-8", "replace"),
                ("stderr", "utf-8", "replace"),
            ],
        )


@unittest.skipIf(sys.platform == "win32", "当前冒烟测试依赖 POSIX 只读目录权限")
class BackendStartupSmokeTest(unittest.TestCase):
    def test_backend_can_start_from_readonly_cwd_with_home_state_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            project_root = temp_root / "project-root"
            project_root.mkdir()
            user_home = temp_root / "home"
            user_home.mkdir()
            config_path = project_root / ".nocode" / "config.yaml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                textwrap.dedent(
                    """\
                    default_model: qwen/qwen2.5-coder:14b
                    max_tokens: 256
                    temperature: 0.1
                    subagent_model: qwen2.5-coder:14b
                    providers:
                      qwen:
                        base_url: "http://127.0.0.1:11434/v1"
                    auto_compact:
                      enabled: true
                    session_memory:
                      enabled: true
                    """
                ),
                encoding="utf-8",
            )

            readonly_cwd = temp_root / "readonly-cwd"
            readonly_cwd.mkdir()
            readonly_cwd.chmod(0o555)

            env = os.environ.copy()
            env["HOME"] = str(user_home)
            env["NOCODE_PROJECT_DIR"] = str(project_root)
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
            project_id = hashlib.sha256(str(project_root.resolve()).encode()).hexdigest()[:8]
            state_dir = user_home / ".nocode" / "projects" / project_id
            self.assertTrue((state_dir / "langgraph-checkpoints.sqlite").exists())
            self.assertFalse((readonly_cwd / ".state").exists())
            self.assertFalse((project_root / ".state").exists())


@unittest.skipIf(sys.platform == "win32", "当前冒烟测试依赖 POSIX PTY")
class TuiBackendErrorVisibilityTest(unittest.TestCase):
    def test_tui_shows_backend_stderr_excerpt_and_log_path_on_fatal(self) -> None:
        _ensure_frontend_built()
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
            # 覆盖源码根，绕过仓库内 .venv，稳定命中 fake backend 分支。
            env["NOCODE_SOURCE_ROOT"] = str(temp_root)
            env["NOCODE_PROJECT_DIR"] = str(temp_root)
            env["NOCODE_LOG_FILE"] = str(log_path)
            env["TERM"] = env.get("TERM", "xterm-256color")

            master_fd, slave_fd = pty.openpty()
            process = subprocess.Popen(
                ["node", "frontend/dist/index.js"],
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
                        decoded = _strip_ansi(output.decode("utf-8", errors="ignore"))
                        if (
                            "fatal: mock fatal" in decoded
                            and "最近 stderr:" in decoded
                            and "mock stderr line 2" in decoded
                            and "日志文件:" in decoded
                            and str(log_path) in decoded
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

            decoded = _strip_ansi(output.decode("utf-8", errors="ignore"))
            self.assertIn("fatal: mock fatal", decoded)
            self.assertIn("最近 stderr:", decoded)
            self.assertIn("mock stderr line 2", decoded)
            self.assertIn("日志文件:", decoded)
            self.assertIn(str(log_path), decoded)

    def test_tui_prefers_repo_venv_over_stale_python_bin(self) -> None:
        _ensure_frontend_built()
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
            env["NOCODE_LOG_FILE"] = str(temp_root / "nocode.log")
            env["TERM"] = env.get("TERM", "xterm-256color")

            master_fd, slave_fd = pty.openpty()
            process = subprocess.Popen(
                ["node", "frontend/dist/index.js"],
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
                        decoded = _strip_ansi(output.decode("utf-8", errors="ignore"))
                        if "model: " in decoded and "glm-5" in decoded and "backend exited with code 1" not in decoded:
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

            decoded = _strip_ansi(output.decode("utf-8", errors="ignore"))
            self.assertIn("model: ", decoded)
            self.assertIn("glm-5", decoded)
            self.assertFalse(marker_path.exists(), msg=decoded)

    def test_tui_keeps_terminal_cwd_while_loading_backend_from_repo_source(self) -> None:
        _ensure_frontend_built()
        with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
            project_root = Path(temp_dir).resolve()
            config_path = project_root / ".nocode" / "config.yaml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                textwrap.dedent(
                    """\
                    default_model: qwen/glm-5
                    max_tokens: 256
                    temperature: 0.1
                    subagent_model: glm-5
                    providers:
                      qwen:
                        base_url: "http://127.0.0.1:11434/v1"
                    """
                ),
                encoding="utf-8",
            )

            fake_python = project_root / "fake-python"
            marker_path = project_root / "fake-python-used.txt"
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
            env["NOCODE_LOG_FILE"] = str(project_root / "nocode.log")
            env["NOCODE_STATE_DIR"] = str(project_root / ".state")
            env["TERM"] = env.get("TERM", "xterm-256color")

            master_fd, slave_fd = pty.openpty()
            process = subprocess.Popen(
                ["node", str(REPO_ROOT / "frontend" / "dist" / "index.js")],
                cwd=project_root,
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
                        decoded = _strip_ansi(output.decode("utf-8", errors="ignore"))
                        if (
                            "model: " in decoded
                            and "glm-5" in decoded
                            and f"cwd: {project_root}" in decoded
                            and "backend exited with code 1" not in decoded
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

            decoded = _strip_ansi(output.decode("utf-8", errors="ignore"))
            self.assertIn("model: ", decoded)
            self.assertIn("glm-5", decoded)
            self.assertIn(f"cwd: {project_root}", decoded)
            self.assertFalse(marker_path.exists(), msg=decoded)


if __name__ == "__main__":
    unittest.main()
