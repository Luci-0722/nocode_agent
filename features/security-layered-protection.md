# 当前文件访问隔离与沙箱实现

这份说明以当前仓库主干代码为准，关注 nocode_agent 现在实际提供了哪些文件访问隔离、`bash` 沙箱是怎么做的，以及它能达到什么隔离水平。

先给结论：

- 当前真正生效的是“工具级工作区边界 + 已读校验 + 人工审批 + 可选 `bash` 系统沙箱”。
- 它不是“整个 agent 运行在统一 OS 沙箱里”。
- `read`/`write`/`edit`/`list_dir`/`grep` 的隔离主要在 Python 应用层。
- `security.deny_paths` 现在已经落到文件工具路径检查里，并内置了一组默认敏感目录。
- 真正的操作系统级沙箱只包裹内建 `bash` 工具，而且默认关闭。

## 1. 工作区边界是怎么做的

当前文件工具的边界是“backend 进程启动时的 `cwd` + denylist”。

- TUI 启动 backend 时，直接把后端工作目录设成当前终端目录：`frontend/hooks/useBackend.ts:562-569`
- 工具层通过 `_workspace_root()` 读取 `Path.cwd().resolve()` 作为工作区根：`src/nocode_agent/tool/kit.py:77-78`
- `_resolve_path()` 会先 `expanduser()`，相对路径拼到工作区下，再执行 `resolve()`，然后依次检查 denylist 和工作区边界：`src/nocode_agent/tool/kit.py`
- denylist 来自 `security.deny_paths`，并叠加默认敏感目录：`~/.ssh`、`~/.gnupg`、`~/.aws`、`~/.netrc`、`~/.config/gh`、`~/.docker`

这意味着：

- `../` 逃逸会被拦住
- 直接传绝对路径到工作区外会被拦住
- 即使目标在工作区内，只要命中 `deny_paths` 也会被拒绝
- 工作区内指向外部路径的 symlink，在 `resolve()` 后也会因为真实目标不在工作区内而被拒绝

当前依赖 `_resolve_path()` 的内建文件相关工具有：

- `read` / `write` / `edit` / `list_dir`：`src/nocode_agent/tool/filesystem.py`
- `grep`：先把起点路径过 `_resolve_path()`，再执行 `rg` 或 Python 搜索：`src/nocode_agent/tool/search.py:233-256`

`glob` 没有接收绝对路径参数，而是直接在工作区根上做 `root.glob(pattern)`；当前实现会在返回结果前过滤掉命中 denylist 的路径。`list_dir` 和 `grep` 也会跳过 denylist 下的条目：`src/nocode_agent/tool/filesystem.py`、`src/nocode_agent/tool/search.py`

这里要注意一个边界语义：

- 文件工具的隔离根是 `cwd`
- 运行时配置、日志、checkpoint 等路径解析更多使用 `runtime_root()` / `state_dir()`
- 这两套语义不是同一个“项目根”

也就是说，当前“文件读写隔离”是围绕终端当前目录做的，不是围绕 `config.yaml` 所在目录做的。

## 2. 文件修改前的“先读再改”校验

除了工作区边界，nocode_agent 还做了一层“操作安全校验”，防止模型在没读过文件的前提下直接覆盖。

实现位置：

- `src/nocode_agent/runtime/file_state.py`
- `src/nocode_agent/tool/filesystem.py`

实现方式：

- `read` 成功后，把文件的 `resolved absolute path + mtime + 内容 hash` 记进 `FileStateCache`：`src/nocode_agent/runtime/file_state.py:35-109`
- 读同一个文件且 `mtime` 没变化时，完整重读会直接返回“文件未变更”的 stub：`src/nocode_agent/tool/filesystem.py:30-40`
- `write` 对“已存在文件”要求先有有效读取记录，否则拒绝覆盖：`src/nocode_agent/tool/filesystem.py:82-87`
- `edit` 不但要求先读过，还要求当前 `mtime` 仍然匹配；如果文件被外部改过，必须重新 `read`：`src/nocode_agent/tool/filesystem.py:117-126`

这层机制的作用主要是：

- 防止盲写
- 防止基于陈旧上下文编辑
- 降低 agent 自己把文件改坏的概率

但它不是 OS 级安全边界，因为：

- 新文件仍然可以直接创建，不要求先 `read`
- 同一进程里只要能调用 `bash`，仍然可能绕过 `write` / `edit` 的显式约束
- 这层检查只保护内建文件工具，不自动约束外部 MCP 工具

## 3. 审批与只读子代理提供的是“策略隔离”

### 3.1 高风险工具默认走人工审批

默认配置里，以下工具会进入 Human-in-the-loop 审批：

- `write`
- `edit`
- `bash`
- `web_fetch`
- `web_search`
- `delegate_code`

配置示例见 `config.example.yaml:127-143`，实际 middleware 构建在 `src/nocode_agent/runtime/hitl.py:107-154`。

这层的价值是把高风险动作放到用户确认之后再执行，但它本质上仍然是“策略控制”，不是系统沙箱：

- 用户批准后，工具会以当前进程权限执行
- 如果审批被关闭，这一层就不存在

### 3.2 只读子代理会被裁掉 `write` / `edit`

主代理启动时会同时构建一份 `core_tools` 和一份 `readonly_tools`：`src/nocode_agent/agent/main.py:252-289`

`readonly_tools` 只是从核心工具里去掉 `write` 和 `edit`：`src/nocode_agent/tool/registry.py:46-83`

子代理定义再通过 `allowed_tools` / `disallowedTools` 做二次过滤：`src/nocode_agent/agent/subagents.py:44-50`、`src/nocode_agent/agent/subagents.py:297-318`

仓库内置的 `Explore` 代理就是这种模式：`.nocode/agents/explore.md:1-37`

这里有个很关键的现实边界：

- 当前“只读子代理”并不等于“完全无法改动系统”
- 因为 `readonly_tools` 仍然包含 `bash`：`src/nocode_agent/agent/subagents.py:321-333`
- 所以它更准确的定义是“没有直接文件编辑工具”，不是“没有副作用”

如果 `bash` 没有被审批拦住，或者审批被允许，子代理仍可能通过 shell 改文件。真正要把这条路压住，得叠加下一节的系统沙箱。

## 4. `bash` 沙箱是怎么实现的

### 4.1 生效范围

沙箱只作用于内建 `bash` 工具。

- `bash()` 首次调用时会 `init_sandbox()` 读取配置：`src/nocode_agent/tool/shell.py:24-27`
- 之后用 `SandboxManager.wrap_command(command, root)` 把原命令包上一层：`src/nocode_agent/tool/shell.py:29-40`
- 如果 `security.sandbox.enabled` 没开，返回原命令，不做任何沙箱处理：`src/nocode_agent/runtime/sandbox.py:35-63`、`src/nocode_agent/runtime/sandbox.py:76-95`

因此：

- `read` / `write` / `edit` 不是跑在系统沙箱里的
- MCP 工具也不会自动经过这个包装层
- skill 只是扩展 prompt / 工具使用方式，不会自动把所有执行都套进 `runtime/sandbox.py`

### 4.2 macOS 实现

macOS 走 `sandbox-exec`：

- 包装方式：`sandbox-exec -f <rule-file> sh -c '<command>'`：`src/nocode_agent/runtime/sandbox.py:112-123`
- 规则文件通过 `NamedTemporaryFile(delete=False)` 写到临时目录：`src/nocode_agent/runtime/sandbox.py:202-216`

当前生成的 Seatbelt 规则大致是：

- `(deny default)` 默认拒绝
- 允许 `process-exec` / `process-fork` / `signal` / `sysctl-read`
- 对当前工作区 `cwd` 开放 `file-read*` 和 `file-write*`
- 对 `/usr`、`/lib`、`/bin`、`/sbin`、`/System`、`/Library` 开放只读
- 对 `/tmp` 和 `~/.cache` 开放读写
- 再叠加配置里的 `allow_read` / `allow_write`
- 如果 `allow_network` 为空，则显式 `deny network-outbound`

对应代码在 `src/nocode_agent/runtime/sandbox.py:126-200`

现状上的几个注意点：

- 临时规则文件不会自动删除
- 网络放行是按代码里写出的 Seatbelt 规则拼出来的，但仓库当前没有回归测试覆盖这部分
- 它只约束 `bash` 子进程，不会反向限制 Python 进程本身已经拿到的其它能力

### 4.3 Linux 实现

Linux 走 `bubblewrap`：

- 系统目录用 `--ro-bind`
- 工作区 `cwd`、`/tmp`、`~/.cache` 用 `--bind`
- 再叠加 `allow_read` / `allow_write`
- 最后 `sh -c <command>` 执行原命令

核心代码在 `src/nocode_agent/runtime/sandbox.py:219-291`

网络行为分两档：

- `allow_network` 为空时，直接 `--unshare-all`
- `allow_network` 非空时，不做真正的域名白名单，而是保留网络命名空间，只隔离 `user/pid/ipc/cgroup`

这意味着 Linux 当前的 `allow_network` 更接近：

- 关闭时：尽量全隔离
- 打开时：网络基本放开

它不是一个真正可精确列出域名白名单的实现。代码里自己也写了这点：`bwrap` 本身不支持域名白名单，需要配合其他工具。

### 4.4 平台支持

- macOS：支持，依赖 `sandbox-exec`
- Linux：支持，但要求本机装有 `bwrap`
- Windows：当前不支持

## 5. 现在到底能达到什么隔离水平

如果按“默认配置”来讲，当前能提供的隔离水平大致是：

| 场景 | 当前水平 | 说明 |
| --- | --- | --- |
| `read` / `grep` / `list_dir` / `glob` 访问工作区外文件 | 中等 | 对常规 `../`、绝对路径和外跳 symlink 有效，因为最终都要落到 `_resolve_path()` 的真实路径检查上 |
| 访问工作区内但被 deny 的敏感路径 | 中等偏高 | `read` / `write` / `edit` 会直接拒绝，`glob` / `list_dir` / `grep` 会过滤这些路径 |
| 误覆盖已有文件 | 中等偏高 | `write` / `edit` 要求先读且 `mtime` 未变，能挡住大量误操作 |
| 未经确认执行高风险工具 | 中等 | 依赖 `permissions.enabled` 和审批配置，属于策略层，不是系统层 |
| `bash` 任意访问宿主机 | 低到中等 | 默认不开沙箱；一旦用户批准，命令就是宿主机当前用户权限 |
| 开启 macOS 沙箱后的 `bash` 文件系统隔离 | 中等偏高 | 对 `bash` 子进程是 OS 级限制，但范围只到 `bash`，不是整个 runtime |
| 开启 Linux 沙箱且禁网后的 `bash` 隔离 | 中等偏高 | `bwrap --unshare-all` 能提供更强的进程/文件系统隔离，但同样只覆盖 `bash` |
| 开启 Linux 沙箱且放开网络后的隔离 | 中等 | 文件系统仍隔离，但网络白名单会退化成“基本共享网络” |
| 对抗恶意 MCP 工具 / 恶意扩展 | 低 | 当前这套隔离主要针对内建核心工具，不自动包住外部工具实现 |

一句话概括：

- 对“防误操作”和“阻止明显越界读文件”，当前实现已经有用
- 对“把整个 agent 当成不可信代码来强隔离”，当前实现还不够

## 6. 明确存在的边界与缺口

### 已落地

- 工作区边界检查
- `security.deny_paths` 路径黑名单
- 已读校验与防陈旧编辑
- 高风险工具审批
- 可选 `bash` OS 沙箱

### 当前未落地或不完整

- “全运行时统一沙箱”
  当前只有 `bash` 被包装
- Linux 域名级网络白名单
  当前实现做不到
- Windows 沙箱
  当前没有实现
- 完整测试覆盖
  `deny_paths` 已补到 `tests/test_tool_kit.py` 与 `tests/test_search.py`，但 `runtime/sandbox.py` 仍缺少专门测试

### 安全语义上还要保守看待的点

- `_resolve_path()` 属于“检查后再打开”的应用层方案，不是基于 `openat` / fd 的抗竞争实现
- 只读子代理仍保留 `bash`
- 一旦人工批准 `bash`，在未启用系统沙箱时，它就是宿主机同权限执行

## 7. 实际上应该怎么理解这套设计

更准确的理解方式是：

1. 先用工作区边界，把大部分文件读写约束在当前目录内
2. 再用“先读再改”降低误改概率
3. 再用人工审批给高风险工具加一道人工闸门
4. 如果担心 shell 破坏面，再给 `bash` 单独叠加系统沙箱

所以当前 nocode_agent 的安全能力，更像：

- 一个对编码代理足够实用的“分层风险收敛”方案

而不是：

- 一个像容器、虚拟机、独立 UID 或完整沙箱运行时那样的“强隔离执行环境”

如果后续要继续提升隔离强度，优先级建议是：

1. 给 `runtime/sandbox.py` 补专门测试
2. 在只读子代理里默认去掉 `bash`，或至少把它和审批/沙箱强绑定
3. 把 Linux 网络控制从“开/关”升级为真正可组合的出口策略
4. 评估是否要把 deny 规则继续下沉到更多外部工具接入点
