# 修复 stale PYTHON_BIN 污染 backend 启动

任务编号：`2026-04-12-python-bin-priority`
所属项目：`reactagent-refactor`
项目目录：`work/projects/reactagent-refactor`
任务目录：`work/projects/reactagent-refactor/tasks/2026-04-12-python-bin-priority`

## 目标

- 修复 stale `PYTHON_BIN` 污染 backend 启动的问题
- 保证 TUI 默认优先使用当前仓库自己的 `.venv`
- 补自动化回归，覆盖错误解释器路径污染场景

## 范围

- 修改 `frontend/tui.ts` 的 Python 选择优先级
- 补充 PTY 冒烟测试
- 更新项目级状态与任务档案

## 非目标

- 不处理全局 Python 版本管理策略
- 不修改 backend 业务逻辑
- 不重做多仓库环境变量体系

## 起始信息

- 开始日期：`2026-04-12`
- 起始 commit：`2be916a`

## 相关项目文档

- `work/projects/reactagent-refactor/README.md`
- `work/projects/reactagent-refactor/STATUS.md`
- `work/projects/reactagent-refactor/TASK_BOARD.md`

## 相关文件

- `frontend/tui.ts`
- `tests/test_startup_smoke.py`
- `work/projects/reactagent-refactor/STATUS.md`
- `work/projects/reactagent-refactor/TASK_BOARD.md`
- `work/projects/reactagent-refactor/tasks/2026-04-12-python-bin-priority/PROGRESS.md`
- `work/projects/reactagent-refactor/tasks/2026-04-12-python-bin-priority/RESULT.md`

## 计划步骤

1. 把 TUI 的 Python 选择顺序改为“本仓库 `.venv` 优先，`PYTHON_BIN` 回退”
2. 新增 stale `PYTHON_BIN` 的 PTY 冒烟测试
3. 跑通回归、更新项目状态与任务档案并提交

## 完成标准

- 错误外部 `PYTHON_BIN` 不再导致 `nocode` 启动失败
- 自动化测试覆盖该场景
- 项目档案与状态已同步
