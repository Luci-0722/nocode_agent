# 新增 nocode TUI 启动命令

任务编号：`2026-04-12-tui-launcher-command`
所属项目：`reactagent-refactor`
项目目录：`work/projects/reactagent-refactor`
任务目录：`work/projects/reactagent-refactor/tasks/2026-04-12-tui-launcher-command`

## 目标

- 增加一个名为 `nocode` 的终端启动命令
- 让该命令直接拉起当前唯一保留的 TUI 入口
- 保持“只保留 TUI、不恢复旧通用 CLI”的重构方向

## 范围

- 新增仓库内 TUI 启动脚本
- 新增安装到 `PATH` 的辅助脚本
- 更新仓库根 README 与项目级交接文档
- 补充本轮任务档案、验证记录与提交信息

## 非目标

- 不恢复 Python 通用 CLI
- 不恢复 `pyproject.toml` 的 console script
- 不处理依赖安装、发布流程或完整打包

## 起始信息

- 开始日期：`2026-04-12`
- 起始 commit：`f04148f`

## 相关项目文档

- `work/projects/reactagent-refactor/README.md`
- `work/projects/reactagent-refactor/STATUS.md`
- `work/projects/reactagent-refactor/TASK_BOARD.md`

## 相关文件

- `nocode`
- `scripts/install_nocode_launcher.sh`
- `src/nocode_agent/compression/auto_compact.py`
- `README.md`
- `work/projects/reactagent-refactor/README.md`
- `work/projects/reactagent-refactor/STATUS.md`
- `work/projects/reactagent-refactor/TASK_BOARD.md`
- `work/projects/reactagent-refactor/tasks/2026-04-12-tui-launcher-command/PROGRESS.md`
- `work/projects/reactagent-refactor/tasks/2026-04-12-tui-launcher-command/RESULT.md`

## 计划步骤

1. 新增仓库内 `nocode` 启动脚本，并确保 symlink 调用时仍能定位项目目录
2. 新增安装脚本，把 `nocode` 命令链接到已在 `PATH` 中的 `~/.local/bin`
3. 更新 README、项目级状态与任务档案，完成验证并提交

## 完成标准

- 仓库内存在可执行的 `nocode` 启动脚本
- 用户环境可以直接输入 `nocode` 启动 TUI
- 文档与交接档案已同步到当前结构
