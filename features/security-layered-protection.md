# 三层安全防护

## 功能概述

为 nocode_agent 实现纵深防御架构，通过三层安全检查保护用户敏感数据：

1. **deny 规则** — 应用层路径黑名单
2. **符号链接检查** — 防止 symlink 逃逸
3. **系统沙箱** — 操作系统级隔离

## 设计动机

参考 Claude Code 的安全设计（见 `claude-code-analysis/analysis/02-security-analysis.md`），单一边界检查存在以下局限：

- 代码可能有 bug
- 配置可能被篡改
- 符号链接可绕过路径检查
- 应用层检查被绕过后无兜底保护

多层防御可以互为补充，即使一层失效，其他层仍然有效。

## 实现细节

### 第1层：deny 规则

**位置**：`src/nocode_agent/tool/kit.py`

**函数**：
- `_get_deny_paths()` — 从配置读取禁止访问的路径列表
- `_check_deny_rules(path)` — 检查路径是否命中 deny 规则

**默认禁止目录**（硬编码，无需配置）：
```python
_DEFAULT_DENY_PATHS = [
    "~/.ssh",
    "~/.gnupg",
    "~/.aws",
    "~/.netrc",
    "~/.config/gh",
    "~/.docker",
]
```

**配置扩展**（`config.yaml`）：
```yaml
security:
  deny_paths:
    - ~/private-keys
    - /etc/shadow
```

**检查逻辑**：
```python
def _check_deny_rules(path: Path) -> bool:
    for deny_path in _get_deny_paths():
        if path == deny_path or deny_path in path.parents:
            return True
    return False
```

---

### 第2层：符号链接边界检查

**位置**：`src/nocode_agent/tool/kit.py`

**函数**：
- `_get_all_path_representations(path)` — 获取路径的所有表示形式
- `_check_symlink_boundary(path, root)` — 检查符号链接是否逃逸

**攻击场景**：
```bash
# 工作区内创建符号链接指向敏感目录
ln -s ~/.ssh/id_rsa ./secret_link

# 如果只检查原始路径，可能绕过 deny 规则
read("secret_link")  # → ~/.ssh/id_rsa
```

**防护逻辑**：
```python
def _get_all_path_representations(path: Path) -> list[Path]:
    representations = [path.resolve()]

    if path.exists():
        # 检查路径本身是否是符号链接
        if path.is_symlink():
            real_target = path.resolve()
            representations.append(real_target)

        # 检查每个父目录是否是符号链接
        for parent in path.parents:
            if parent.is_symlink():
                representations.append(parent.resolve())

    return representations
```

每个表示形式都必须通过 deny 检查和工作区边界检查。

---

### 第3层：系统沙箱

**位置**：`src/nocode_agent/runtime/sandbox.py`

**平台支持**：
- macOS：`sandbox-exec`（Seatbelt）
- Linux：`bwrap`（bubblewrap）

**配置示例**：
```yaml
security:
  sandbox:
    enabled: true
    allow_read:
      - /usr
      - /lib
    allow_write:
      - .  # 工作区
      - ~/.cache/pip
    allow_network:
      - api.anthropic.com
      - pypi.org
```

**macOS Seatbelt 规则示例**：
```
(version 1)
(deny default)
(allow process-exec)
(allow file-read* (subpath "/Users/xxx/workspace"))
(allow file-write* (subpath "/Users/xxx/workspace"))
(allow network-outbound (remote ip "api.anthropic.com"))
```

**Linux bwrap 命令示例**：
```bash
bwrap \
  --ro-bind /usr /usr \
  --ro-bind /lib /lib \
  --bind /workspace /workspace \
  --dev /dev \
  --proc /proc \
  --unshare-all \
  sh -c 'echo hello'
```

---

## 调用链路

```
用户调用 read/write/edit/bash
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  _resolve_path() / SandboxManager.wrap_command()             │
│                                                              │
│  第1层：deny 规则                                             │
│  - 检查路径是否在敏感目录黑名单                                  │
│  - 快速拒绝，返回 ValueError                                   │
└─────────────────────────────────────────────────────────────┘
    │ 通过
    ▼
┌─────────────────────────────────────────────────────────────┐
│  第2层：工作区边界                                             │
│  - 检查路径是否在 cwd 范围内                                    │
│  - 防止 ../ 逃逸                                              │
└─────────────────────────────────────────────────────────────┘
    │ 通过
    ▼
┌─────────────────────────────────────────────────────────────┐
│  第3层：符号链接检查                                           │
│  - 检查路径的所有表示形式                                       │
│  - 每个表示都必须通过 deny + 工作区检查                          │
└─────────────────────────────────────────────────────────────┘
    │ 通过（文件操作）
    ▼
┌─────────────────────────────────────────────────────────────┐
│  第3层（bash）：系统沙箱                                        │
│  - macOS: sandbox-exec                                       │
│  - Linux: bwrap                                              │
│  - 文件系统白名单 + 网络白名单                                   │
└─────────────────────────────────────────────────────────────┘
    │ 通过
    ▼
  命令/操作真正执行
```

---

## 文件改动

| 文件 | 改动 |
|------|------|
| `src/nocode_agent/tool/kit.py` | 新增 `_get_deny_paths()`, `_check_deny_rules()`, `_get_all_path_representations()`, `_check_symlink_boundary()`；修改 `_resolve_path()` |
| `src/nocode_agent/runtime/sandbox.py` | 新增沙箱管理器 |
| `src/nocode_agent/tool/shell.py` | 集成沙箱包装 |
| `config.example.yaml` | 新增 `security` 配置示例 |

---

## 测试验证

```python
# deny 规则测试
_resolve_path('~/.ssh/id_rsa')  # ValueError: 被禁止访问（敏感目录）
_resolve_path('~/.gnupg/pubring.kbx')  # ValueError: 被禁止访问

# 工作区边界测试
_resolve_path('/etc/passwd')  # ValueError: 超出当前工作区

# 符号链接逃逸测试（在工作区内创建 symlink）
ln -s ~/.ssh/id_rsa ./secret_link
_resolve_path('secret_link')  # ValueError: 通过符号链接指向敏感目录

# 正常路径测试
_resolve_path('config.example.yaml')  # 正常返回路径
```

---

## 与 Claude Code 对比

| 维度 | nocode_agent | Claude Code |
|------|--------------|-------------|
| deny 规则 | ✅ 硬编码默认值 + 配置扩展 | ✅ `permissions.deny` 配置 |
| 符号链接检查 | ✅ 多表示形式检查 | ✅ `getPathsForPermissionCheck()` |
| 系统沙箱 | ✅ macOS/Linux | ✅ macOS Seatbelt / Linux bwrap |
| 网络白名单 | ✅ 沙箱层支持 | ✅ 从 WebFetch 权限反推 |
| 路径语义 | 单一 cwd | 多工作区 + add-dir |

---

## 后续改进方向

1. **deny 规则热更新** — 监听配置文件变化，无需重启
2. **网络域名精确控制** — Linux bwrap 不支持域名白名单，需配合代理
3. **多工作区支持** — 类似 Claude Code 的 `add-dir` 功能
4. **Windows 沙箱** — 当前不支持，可考虑 Windows Sandbox 或 AppLocker

---

## 参考资料

- Claude Code 源码分析：`claude-code-analysis/analysis/02-security-analysis.md`
- Claude Code Sandbox 实现：`claude-code-analysis/analysis/04e-sandbox-implementation.md`
- macOS Seatbelt 文档：https://developer.apple.com/library/archive/documentation/Security/Conceptual/AppSandboxDesignGuide/
- Linux bubblewrap：https://github.com/containers/bubblewrap