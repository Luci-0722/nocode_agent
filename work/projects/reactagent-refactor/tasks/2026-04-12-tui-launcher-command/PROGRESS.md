# 新增 nocode TUI 启动命令 进度

任务编号：`2026-04-12-tui-launcher-command`
所属项目：`reactagent-refactor`
任务目录：`work/projects/reactagent-refactor/tasks/2026-04-12-tui-launcher-command`

## 当前状态

- 状态：`已完成`
- 最近更新时间：`2026-04-12`

## 已完成

- 已创建任务档案
- 已确认当前 TUI 唯一入口为 `frontend/tui.ts`
- 已确认用户 `PATH` 包含 `~/.local/bin`
- 已新增仓库根 `nocode` 启动脚本
- 已新增 `scripts/install_nocode_launcher.sh`
- 已修复 `auto_compact.py` 缺失导入导致的 backend 启动 fatal
- 已把 `nocode` 安装到 `~/.local/bin/nocode`
- 已完成本地语法检查、编译检查与真实启动验证

## 进行中

- 无

## 待做

- 无

## 决策记录

- 不恢复旧 CLI 或 console script，只增加一个直接指向 TUI 的 shell launcher
- 启动脚本保留当前 shell 的工作目录，只通过 `NOCODE_PROJECT_DIR` 绑定仓库根
- 真实安装位置使用 `~/.local/bin/nocode`，因为该目录已在用户 `PATH` 中
- 为了让 `nocode` 真正可用，本轮顺手修复了后端启动路径上的现存 fatal bug

## 风险与阻塞

- 当前工作树存在与本任务无关的未提交变更，提交时必须按文件精确暂存
