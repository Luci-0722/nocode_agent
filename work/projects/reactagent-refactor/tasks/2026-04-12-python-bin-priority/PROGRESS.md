# 修复 stale PYTHON_BIN 污染 backend 启动 进度

任务编号：`2026-04-12-python-bin-priority`
所属项目：`reactagent-refactor`
任务目录：`work/projects/reactagent-refactor/tasks/2026-04-12-python-bin-priority`

## 当前状态

- 状态：`已完成`
- 最近更新时间：`2026-04-12`

## 已完成

- 已创建任务档案
- 已定位到 `frontend/tui.ts` 先读 `PYTHON_BIN`，再读本地 `.venv`
- 已将优先级改为当前仓库 `.venv` 优先
- 已新增 stale `PYTHON_BIN` 的 PTY 冒烟测试
- 已完成真实命令回归：`env PYTHON_BIN=/Users/lucheng/Projects/NoCode/.venv/bin/python nocode`

## 进行中

- 无

## 待做

- 无

## 决策记录

- 对源码态 TUI 而言，当前仓库 `.venv` 比外部残留 `PYTHON_BIN` 更可信
- `PYTHON_BIN` 保留为回退能力，仅在本地 `.venv` 不存在时使用
- 用 PTY 驱动真实 TUI 比纯函数测试更能覆盖这类环境污染问题

## 风险与阻塞

- 当前工作树仍有用户自己的 `AGENTS.md` 与 workflow 文档改动，提交时必须排除
