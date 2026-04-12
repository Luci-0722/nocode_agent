# nocode_agent

单独的 NoCode agent 包。

## 仓库边界

当前目录现在作为独立项目使用，建议始终在 `nocode_agent/` 目录内执行 `git` 命令。

- 当前项目目录：`/Users/lucheng/Projects/NoCode/nocode_agent`
- 父级历史仓库：`/Users/lucheng/Projects/NoCode`

这次拆分采用“独立初始化新 git”的方式：

- 当前 `nocode_agent/` 会拥有自己的 `.git/`
- 父仓库不会被自动改造成 submodule
- 旧父仓库历史不会自动迁入当前子仓库

如果后续还要保留旧历史，再单独做一次 `subtree` / `filter-repo` 型历史切分即可。

## 当前结构

- 运行时主包：`src/nocode_agent/`
- 终端前端：`frontend/tui.ts`
- 默认配置：`config.yaml`
- 默认状态目录：`.state/`

当前代码已经完成包内收口：

- 根目录历史 shim 与旧入口已删除
- 真实 Python 包已切到 `src/nocode_agent/`
- 包根散落模块已继续收口到：
  - `src/nocode_agent/app/`
  - `src/nocode_agent/runtime/`
- `skills/`、`compression/`、`bundled_skills/` 已迁入包内
- 正式 Python 入口统一为 `nocode_agent.*`
- 已补正式 `pyproject.toml`

## 主要子模块

- `src/nocode_agent/app/`
- `src/nocode_agent/agent/`
- `src/nocode_agent/prompt/`
- `src/nocode_agent/tool/`
- `src/nocode_agent/skills/`
- `src/nocode_agent/compression/`
- `src/nocode_agent/runtime/`
- `src/nocode_agent/config/`
- `src/nocode_agent/log/`
- `src/nocode_agent/persistence/`

## 安装

在仓库根目录执行：

```bash
pip install -e .
```

本地私有配置不进版本库：

- 提交中保留 `config.example.yaml`
- 你自己的 `config.yaml` 会被忽略

如果你希望在终端里直接输入 `nocode` 启动 TUI，再执行：

```bash
bash scripts/install_nocode_launcher.sh
```

如果你刚接手这个目录，先确认当前 git 根已经是本目录：

```bash
git rev-parse --show-toplevel
```

期望输出：

```text
/Users/lucheng/Projects/NoCode/nocode_agent
```

## TUI 启动

优先使用全局启动命令：

```bash
nocode
```

恢复历史会话：

```bash
nocode --resume
```

如果你还没有安装启动命令，也可以在仓库根目录直接执行：

```bash
node frontend/tui.ts
```

或：

```bash
node frontend/tui.ts --resume
```

TUI 会自动拉起 Python backend。

如果 backend 启动失败，TUI 现在会直接显示最近的 `stderr` 摘要和日志文件位置。

## 最小验证

执行最小启动冒烟测试：

```bash
python3 -m unittest discover -s tests -v
```

## 调试入口

如果你只想单独调试后端模块，可以显式注入 `src` 后运行：

```bash
PYTHONPATH=src python3 -m nocode_agent.app.backend_stdio
```

## 默认路径

- 默认配置文件：当前项目根目录下的 `config.yaml`
- 默认状态目录：当前项目根目录下的 `.state/`
- 默认日志文件：当前项目根目录下的 `.state/nocode.log`
- 可通过环境变量覆盖：
  - `NOCODE_PROJECT_DIR`
  - `NOCODE_STATE_DIR`
  - `NOCODE_AGENT_CONFIG`

## 非目标

- 不包含多会话编排
- 不包含会话注册表 MCP
- 不包含 Web UI
