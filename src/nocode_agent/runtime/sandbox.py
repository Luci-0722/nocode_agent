"""系统沙箱适配器。

为 bash 命令执行提供系统级隔离：
- macOS: sandbox-exec (Seatbelt)
- Linux: bwrap (bubblewrap) 或 unshare

即使应用层检查被绕过，沙箱仍然能在系统层拦截。
"""

from __future__ import annotations

import logging
import platform
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 沙箱配置缓存
_SANDBOX_CONFIG: dict[str, Any] | None = None
_SANDBOX_ENABLED: bool = False


class SandboxManager:
    """沙箱管理器，根据平台选择合适的隔离方案。"""

    @classmethod
    def init_from_config(cls, config: dict[str, Any]) -> None:
        """从配置初始化沙箱。

        Args:
            config: 完整配置字典，读取 config.get("security", {}).get("sandbox", {})
        """
        sandbox_config = config.get("security", {}).get("sandbox", {})
        enabled = sandbox_config.get("enabled", False)

        if enabled:
            # 检查平台支持
            system = platform.system()
            if system == "Darwin":
                # macOS 有内置 sandbox-exec
                logger.info("沙箱已启用 (macOS sandbox-exec)")
                cls._enabled = True
                cls._config = sandbox_config
            elif system == "Linux":
                # Linux 需要 bwrap
                if cls._check_bwrap_available():
                    logger.info("沙箱已启用 (Linux bwrap)")
                    cls._enabled = True
                    cls._config = sandbox_config
                else:
                    logger.warning(
                        "沙箱配置已启用，但 bwrap 不可用。"
                        "请安装 bubblewrap: apt install bubblewrap 或 dnf install bubblewrap"
                    )
                    cls._enabled = False
            else:
                logger.warning("沙箱不支持当前平台: %s", system)
                cls._enabled = False
        else:
            cls._enabled = False
            cls._config = {}

    @classmethod
    def is_enabled(cls) -> bool:
        """返回沙箱是否启用。"""
        return cls._enabled

    @classmethod
    def get_config(cls) -> dict[str, Any]:
        """返回当前沙箱配置。"""
        return cls._config if cls._config else {}

    @classmethod
    def wrap_command(cls, command: str, cwd: Path) -> str:
        """将命令包装在沙箱中执行。

        Args:
            command: 原始 shell 命令
            cwd: 当前工作目录

        Returns:
            包装后的命令字符串，如果沙箱未启用则返回原命令
        """
        if not cls._enabled:
            return command

        system = platform.system()
        if system == "Darwin":
            return cls._wrap_macos(command, cwd)
        elif system == "Linux":
            return cls._wrap_linux(command, cwd)
        else:
            return command

    @classmethod
    def _check_bwrap_available(cls) -> bool:
        """检查 bwrap 是否可用。"""
        import subprocess
        try:
            subprocess.run(
                ["bwrap", "--version"],
                capture_output=True,
                timeout=5,
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return False

    @classmethod
    def _wrap_macos(cls, command: str, cwd: Path) -> str:
        """macOS Seatbelt 沙箱包装。

        sandbox-exec 使用规则文件控制权限。
        """
        rules = cls._build_macos_rules(cwd)
        rule_file = cls._write_temp_rules(rules)

        # 使用 sandbox-exec 执行命令
        # 注意：需要转义命令中的特殊字符
        escaped_command = command.replace("'", "'\"'\"'")
        return f"sandbox-exec -f '{rule_file}' sh -c '{escaped_command}'"

    @classmethod
    def _build_macos_rules(cls, cwd: Path) -> str:
        """构建 macOS Seatbelt 规则。

        规则语法：
        (version 1)
        (deny default)           # 默认拒绝所有
        (allow process-exec)     # 允许执行进程
        (allow file-read* ...)   # 允许读取
        (allow file-write* ...)  # 允许写入
        (allow network-outbound ...) # 允许网络
        """
        config = cls._config

        lines = [
            "(version 1)",
            "(deny default)",  # 默认拒绝所有操作
            "(allow process-exec)",  # 允许执行进程
            "(allow process-fork)",  # 允许 fork 子进程
            "(allow signal)",  # 允许信号处理
            "(allow sysctl-read)",  # 允许读取系统信息
            # 允许读取和写入工作区
            f'(allow file-read* (subpath "{cwd}"))',
            f'(allow file-write* (subpath "{cwd}"))',
        ]

        # 系统目录（只读）
        system_dirs = ["/usr", "/lib", "/bin", "/sbin", "/System", "/Library"]
        for dir_path in system_dirs:
            if Path(dir_path).exists():
                lines.append(f'(allow file-read* (subpath "{dir_path}"))')

        # 临时目录
        tmp_dir = Path("/tmp").resolve()
        lines.append(f'(allow file-read* (subpath "{tmp_dir}"))')
        lines.append(f'(allow file-write* (subpath "{tmp_dir}"))')

        # 用户缓存目录（用于 pip 等）
        cache_dir = Path.home() / ".cache"
        if cache_dir.exists():
            lines.append(f'(allow file-read* (subpath "{cache_dir}"))')
            lines.append(f'(allow file-write* (subpath "{cache_dir}"))')

        # 配置的白名单
        for path_pattern in config.get("allow_read", []):
            try:
                p = Path(path_pattern).expanduser().resolve()
                if p.exists():
                    lines.append(f'(allow file-read* (subpath "{p}"))')
            except Exception as e:
                logger.warning("无法解析 allow_read 路径 %s: %s", path_pattern, e)

        for path_pattern in config.get("allow_write", []):
            try:
                p = Path(path_pattern).expanduser().resolve()
                # 如果是 "."，跳过（已添加 cwd）
                if path_pattern == ".":
                    continue
                if p.exists():
                    lines.append(f'(allow file-write* (subpath "{p}"))')
            except Exception as e:
                logger.warning("无法解析 allow_write 路径 %s: %s", path_pattern, e)

        # 网络白名单
        network_allowed = config.get("allow_network", [])
        if network_allowed:
            # 允许 DNS 解析
            lines.append('(allow network-outbound (remote dns))')
            for domain in network_allowed:
                # macOS sandbox 支持域名白名单
                lines.append(f'(allow network-outbound (remote ip "{domain}"))')
        else:
            # 没有配置网络白名单时，默认禁止网络
            lines.append("(deny network-outbound)")

        return "\n".join(lines)

    @classmethod
    def _write_temp_rules(cls, rules: str) -> str:
        """写入临时规则文件。

        macOS sandbox-exec 需要从文件读取规则。
        文件在命令执行后可以删除（但这里简化处理，不删除）。
        """
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".sb",
            delete=False,
            prefix="nocode_sandbox_",
        ) as f:
            f.write(rules)
            return f.name

    @classmethod
    def _wrap_linux(cls, command: str, cwd: Path) -> str:
        """Linux bwrap 沙箱包装。

        bwrap 参数：
        --ro-bind SRC DEST  只读挂载
        --bind SRC DEST     可读写挂载
        --dev /dev          挂载设备
        --proc /proc        挂载 proc
        --unshare-all       隔离所有命名空间
        """
        config = cls._config

        args = [
            "bwrap",
            # 系统目录（只读）
            "--ro-bind", "/usr", "/usr",
            "--ro-bind", "/lib", "/lib",
            "--ro-bind-try", "/lib64", "/lib64",  # 某些系统没有 lib64
            "--ro-bind", "/bin", "/bin",
            "--ro-bind-try", "/sbin", "/sbin",
            # 工作区（可读写）
            "--bind", str(cwd), str(cwd),
            # 设备和 proc
            "--dev", "/dev",
            "--proc", "/proc",
            # 临时目录
            "--bind", "/tmp", "/tmp",
        ]

        # 用户缓存目录
        cache_dir = Path.home() / ".cache"
        if cache_dir.exists():
            args.extend(["--bind", str(cache_dir), str(cache_dir)])

        # 配置的白名单
        for path_pattern in config.get("allow_read", []):
            try:
                p = Path(path_pattern).expanduser().resolve()
                if p.exists():
                    args.extend(["--ro-bind", str(p), str(p)])
            except Exception as e:
                logger.warning("无法解析 allow_read 路径 %s: %s", path_pattern, e)

        for path_pattern in config.get("allow_write", []):
            try:
                p = Path(path_pattern).expanduser().resolve()
                if path_pattern == ".":
                    continue
                if p.exists():
                    args.extend(["--bind", str(p), str(p)])
            except Exception as e:
                logger.warning("无法解析 allow_write 路径 %s: %s", path_pattern, e)

        # 网络隔离
        network_allowed = config.get("allow_network", [])
        if network_allowed:
            # 如果允许网络，不隔离网络命名空间
            args.extend([
                "--unshare-user",
                "--unshare-pid",
                "--unshare-ipc",
                "--unshare-cgroup",
            ])
            # 注意：bwrap 本身不支持域名白名单，需要配合其他工具
            # 这里简化处理：允许网络就共享网络命名空间
        else:
            # 禁止网络：隔离所有命名空间
            args.append("--unshare-all")

        # 执行命令
        args.extend(["sh", "-c", command])

        return " ".join(args)


def init_sandbox() -> None:
    """初始化沙箱（从配置加载）。"""
    from nocode_agent.config import load_config

    config = load_config()
    SandboxManager.init_from_config(config)


__all__ = [
    "SandboxManager",
    "init_sandbox",
]