# 改善 TUI 中 backend 错误可见性

任务编号：`2026-04-12-backend-error-visibility`
所属项目：`reactagent-refactor`
项目目录：`work/projects/reactagent-refactor`
任务目录：`work/projects/reactagent-refactor/tasks/2026-04-12-backend-error-visibility`

## 目标

- 改善 TUI 中 backend 启动失败时的错误可见性
- 让用户在界面中直接看到关键 stderr 摘要与日志文件位置
- 补最小回归验证，覆盖 backend fatal 场景

## 范围

- 调整 `frontend/tui.ts` 的 backend stderr / exit / fatal 展示逻辑
- 补充自动化测试，覆盖 TUI 对 backend fatal 的可见性
- 更新 README 与项目交接文档

## 非目标

- 不重做 TUI 整体错误交互设计
- 不引入完整前端测试框架
- 不改变 backend 自身业务逻辑

## 起始信息

- 开始日期：`2026-04-12`
- 起始 commit：`06656bf`

## 相关项目文档

- `work/projects/reactagent-refactor/README.md`
- `work/projects/reactagent-refactor/STATUS.md`
- `work/projects/reactagent-refactor/TASK_BOARD.md`

## 相关文件

- `frontend/tui.ts`
- `tests/test_startup_smoke.py`
- `README.md`
- `work/projects/reactagent-refactor/STATUS.md`
- `work/projects/reactagent-refactor/TASK_BOARD.md`
- `work/projects/reactagent-refactor/tasks/2026-04-12-backend-error-visibility/PROGRESS.md`
- `work/projects/reactagent-refactor/tasks/2026-04-12-backend-error-visibility/RESULT.md`

## 计划步骤

1. 在 TUI 中缓存 backend 最近 stderr，并在 fatal / exit 时展示出来
2. 新增 PTY 冒烟测试，覆盖 fake backend fatal + stderr 场景
3. 更新 README、任务档案与项目状态，完成验证并提交

## 完成标准

- backend 出错时，TUI 不再只显示 `code 1`
- TUI 会给出日志文件位置
- 自动化测试能覆盖 backend fatal 的可见性场景
