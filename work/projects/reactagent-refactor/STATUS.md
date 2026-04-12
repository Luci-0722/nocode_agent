# 当前状态

更新时间：2026-04-12

## 最近完成

已完成整条 ReactAgent 重构线的结构收口：

- 真实运行时代码已全部迁入 `src/nocode_agent/`
- 根目录 shim、旧入口与过渡桥接已删除
- 已新增 `pyproject.toml`
- 已修正仓库态 / 安装态默认路径解析
- 前端源码态回退启动已显式注入 `PYTHONPATH=src`
- 包根散落模块已收口到 `app/` 与 `runtime/`
- `tool/` 与 `prompt/` 已成为正式聚合入口，包根 `tools.py` / `prompts.py` 已删除
- 通用 CLI 与 console script 入口已移除，当前用户入口统一为 TUI
- 已新增 `nocode` 启动命令，可直接拉起 TUI
- 已修复后端启动时 `SessionMemoryCompactor` 缺失导入导致的 fatal
- 已把相对状态路径锚定到项目根，避免 `nocode` 在仓库外 cwd 启动时 backend 直接退出
- 已新增最小启动冒烟测试基线
- 已让 TUI 在 backend 启动失败时直接显示 stderr 摘要与日志文件位置
- 已修复 launcher 继承错误 `NOCODE_PROJECT_DIR` 导致项目根错乱的问题
- 已修复 stale `PYTHON_BIN` 优先级过高导致 backend 误用旧解释器的问题
- 已把 `nocode_agent/` 初始化为独立 git 仓库，后续可在子项目内单独提交
- 已把 `config.yaml` 改为本地私有配置，不再作为独立仓库首提内容

最近阶段提交：

- `239b03f` Bootstrap standalone package runtime
- `587b813` refactor: package compression lifecycle
- `5a50e76` refactor: finalize package cutover
- `ed224d8` build: add package entrypoints
- `d69ce35` refactor: adopt src layout
- `ecf213e` refactor: flatten package root modules
- `5fdff62` refactor: remove generic cli surface
- `10cea98` feat: add nocode tui launcher
- `06656bf` test: add startup smoke coverage
- `6d1786d` fix: surface backend startup errors in tui
- `b31a25a` fix: pin launcher project root
- `36637f4` fix: prefer local venv over stale python bin
- 当前工作项：初始化 `nocode_agent` 独立 git 仓库（独立仓库首提请在子仓库内执行 `git log --oneline -1`）

## 当前基线

当前仓库已经不再处于“根目录平铺 + 兼容桥”的过渡态，而是正式 `src` 布局：

- 真实运行时代码位于 `src/nocode_agent/`
- 主要目录：
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
- 包级真实入口：
  - `src/nocode_agent/app/backend_stdio.py`
  - `src/nocode_agent/app/acp_server.py`
  - `src/nocode_agent/runtime/paths.py`
  - `src/nocode_agent/runtime/file_state.py`
- 当前用户入口：
  - `nocode`
  - `nocode --resume`
  - 未安装启动命令时，可回退到 `node frontend/tui.ts`
- 根目录仅保留仓库级文档、配置文件与前端代码
- 仓库已包含正式 `pyproject.toml`
- 当前目录已拥有独立 `.git/`，后续默认在 `nocode_agent/` 内执行 git 操作

## 当前接力点

这条重构线的既定结构目标已经完成，当前没有必须继续推进的兼容迁移任务。

如果后续还要继续演进，建议把它视为新阶段，而不是继续沿用旧的兼容迁移计划。优先级建议：

1. 补真实依赖环境下的端到端验证
2. 建立发布流程
3. 增补最小自动化测试

## 下一优先任务

无强制下一任务。

如果用户继续要求工程化收尾，建议下一轮只做一个明确工作项：

- 真实依赖下的集成验证
- 发布流程与版本管理
- ACP / 会话存取测试基线

## 已知风险

- 当前环境依赖仍不完整，至少 `yaml`、`httpx`、`aiosqlite`、`acp`、LangChain 相关依赖未保证齐全
- 虽然已有 `pyproject.toml` 和 `src` 布局，但依赖版本仍未在真实环境中完整回归
- 若未来需要从仓库外稳定安装使用，仍需补安装验证与发布路径
- 当前仅有启动冒烟测试，尚未覆盖真实 prompt、工具调用与 ACP 会话流转
- 当前 TUI 已能显示启动失败摘要，但尚未覆盖更细粒度的运行中异常分级提示
- 若用户长期在 shell 中导出 `NOCODE_AGENT_CONFIG` 或 `NOCODE_STATE_DIR`，仍可能造成跨项目污染
- 若用户长期导出错误的 `NOCODE_AGENT_CONFIG`，仍可能让 TUI 读取到别的项目配置
- 父仓库 `/Users/lucheng/Projects/NoCode` 仍会继续看到 `nocode_agent/` 的文件改动；若要彻底物理解耦，还需要后续单独迁出目录

## 交接规则

下一个 agent 开始前：

1. 先读本文件
2. 再读 `TASK_BOARD.md`
3. 如果是新目标，先在 `tasks/` 下新建独立任务目录
4. 不要恢复根目录 shim、`__path__` 桥接或非 `src` 双轨布局
