# 任务板

## 使用方式

- 一次只领取一个“可单独提交”的任务
- 做完后先更新 `tasks/<task-id>/`，再更新状态并提交
- 当前旧重构线已完成，新的工程化工作请单独立项

## 已完成

### T0 独立运行引导层

状态：已完成

结果：

- 建立 `src/nocode_agent/runtime/paths.py`
- 建立 `src/nocode_agent/runtime/bootstrap.py`
- 默认状态路径统一为仓库根 `.state/`

### T1 包内化低风险模块

状态：已完成

结果：

- 已迁移 `config`、`log`、`persistence`

### T2 拆 agent 运行时

状态：已完成

结果：

- 已迁移 `model`、`agent/runtime`、`agent/factory`、`agent/builder`、`agent/subagents`

### T3 拆 prompt / tool / middleware / 接入层

状态：已完成

结果：

- 已迁移 `prompt/*`
- 已迁移 `tool/*`
- 已迁移 `interactive.py`
- 已迁移 `hitl.py`
- 已迁移 `backend_stdio.py`
- 已迁移 `acp_server.py`
- 已迁移 `compression/lifecycle.py`

### T4 最终收口兼容层

状态：已完成

结果：

- 已迁移 `skills/` 到 `src/nocode_agent/skills/`
- 已迁移 `bundled_skills/` 到 `src/nocode_agent/bundled_skills/`
- 已迁移剩余 `compression/*.py` 到 `src/nocode_agent/compression/`
- 已建立包内正式聚合入口，并在后续阶段继续收口到子目录
- 已删除根目录 shim、旧入口与桥接逻辑

### T5 补正式打包配置与分发入口

状态：已完成

结果：

- 已新增 `pyproject.toml`
- 已修正安装态默认配置与状态目录解析
- 已补源码态同步启动入口

### T6 切换到 src 布局

状态：已完成

结果：

- 已将真实包目录迁移到 `src/nocode_agent/`
- 已将 `pyproject.toml` 切到 `src` 布局打包
- 已修正仓库根路径解析与 bundled `rg` 查找逻辑
- 已让 `frontend/tui.ts` 在源码态 Python 回退启动时注入 `PYTHONPATH=src`

### T7 压缩包根散落模块

状态：已完成

结果：

- 已将入口模块收口到 `src/nocode_agent/app/`
- 已将路径 / 交互 / HITL / 文件状态模块收口到 `src/nocode_agent/runtime/`
- 已删除包根 `tools.py` / `prompts.py` façade
- `tool/` 与 `prompt/` 直接成为正式聚合入口

### T8 移除通用 CLI 入口

状态：已完成

结果：

- 已删除 `src/nocode_agent/app/cli.py`
- 已删除 `src/nocode_agent/__main__.py`
- 已移除 `pyproject.toml` 中的 console script 入口
- 当前用户入口统一为 `node frontend/tui.ts`

### T9 补 `nocode` TUI 启动命令

状态：已完成

结果：

- 已新增仓库根 `nocode` 启动脚本
- 已新增 `scripts/install_nocode_launcher.sh`
- 已支持把 `nocode` 安装到 `~/.local/bin`
- 当前用户入口统一为 `nocode`
- 已修复 `auto_compact.py` 缺失导入导致的 backend 启动 fatal

### T10 补最小启动冒烟测试

状态：已完成

结果：

- 已新增 `tests/test_startup_smoke.py`
- 已覆盖 `nocode` symlink 启动器的项目根与参数透传行为
- 已覆盖 backend 在仓库外只读 cwd 启动时的初始化成功场景
- 已修复相对状态路径按 shell cwd 解析导致的 backend 启动回归

### T11 改善 TUI 中 backend 错误可见性

状态：已完成

结果：

- 已在 TUI 中缓存 backend 最近一段 `stderr`
- 已在 `fatal` 与非零退出时显示 `stderr` 摘要与日志文件位置
- 已抑制 `fatal` 后重复出现的 `backend exited with code 1`
- 已新增 PTY 冒烟测试，覆盖 fake backend fatal 场景

### T12 修复 launcher 继承错误项目根

状态：已完成

结果：

- 已让 `nocode` 无条件绑定到当前仓库根，不再继承外部残留的 `NOCODE_PROJECT_DIR`
- 已新增 stale `NOCODE_PROJECT_DIR` 的自动化回归测试
- 已验证错误项目根环境变量不会再导致 `ModuleNotFoundError: nocode_agent`

### T13 修复 stale `PYTHON_BIN` 污染 backend 启动

状态：已完成

结果：

- 已让 `frontend/tui.ts` 优先使用当前仓库 `.venv`
- 已把 `PYTHON_BIN` 降级为本地 `.venv` 不存在时的回退选项
- 已新增 stale `PYTHON_BIN` 的 PTY 冒烟测试
- 已验证错误外部解释器路径不会再导致 backend 启动失败

### T14 初始化独立 git 仓库

状态：已完成

结果：

- 已在 `nocode_agent/` 目录内初始化独立 `.git/`
- 已新增独立仓库最小忽略规则，排除 `.venv/`、`.state/`、`.idea/`、`config.yaml`、`*.egg-info/`
- 已确认后续默认在 `nocode_agent/` 目录内执行 git 操作
- 已把 `config.yaml` 调整为本地私有配置，只保留 `config.example.yaml` 入库

## 待办

当前无既定待办。

如果用户继续要求工程化收尾，建议新增任务而不是在本板上追加兼容迁移项：

- 真实依赖环境下的集成测试
- 发布流程与版本管理
- 最小自动化测试基线
- 父仓库与子仓库的彻底物理解耦
