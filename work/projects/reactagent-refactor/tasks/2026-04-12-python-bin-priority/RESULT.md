# 修复 stale PYTHON_BIN 污染 backend 启动 结果

任务编号：`2026-04-12-python-bin-priority`
所属项目：`reactagent-refactor`
任务目录：`work/projects/reactagent-refactor/tasks/2026-04-12-python-bin-priority`

## 提交信息

- 起始 commit：`2be916a`
- 计划提交信息：`fix: prefer local venv over stale python bin`
- 最终提交 hash：以所属项目 `STATUS.md` 的“最近阶段提交”为准；如未更新，则通过回查命令定位
- 回查命令：`git log --oneline -- work/projects/reactagent-refactor/tasks/2026-04-12-python-bin-priority`

## 验证

- `.venv/bin/python -m unittest discover -s tests -v`
- `node --check frontend/tui.ts`
- `python3 -m compileall -q src/nocode_agent tests`
- 真实回归：`env PYTHON_BIN=/Users/lucheng/Projects/NoCode/.venv/bin/python nocode`

## 结果说明

- 已将 `frontend/tui.ts` 的 Python 选择逻辑调整为本仓库 `.venv` 优先
- 现在即使外部残留错误 `PYTHON_BIN`，`nocode` 仍会优先使用当前仓库解释器
- 已新增 PTY 冒烟测试，覆盖 stale `PYTHON_BIN` 污染场景

## 下一步建议

- 可以继续排查并收口 `NOCODE_AGENT_CONFIG` / `NOCODE_STATE_DIR` 的跨项目污染风险
- 可以在 TUI 错误信息里额外显示实际采用的 Python 路径，进一步降低排障成本
