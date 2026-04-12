# 改善 TUI 中 backend 错误可见性 结果

任务编号：`2026-04-12-backend-error-visibility`
所属项目：`reactagent-refactor`
任务目录：`work/projects/reactagent-refactor/tasks/2026-04-12-backend-error-visibility`

## 提交信息

- 起始 commit：`06656bf`
- 计划提交信息：`fix: surface backend startup errors in tui`
- 最终提交 hash：以所属项目 `STATUS.md` 的“最近阶段提交”为准；如未更新，则通过回查命令定位
- 回查命令：`git log --oneline -- work/projects/reactagent-refactor/tasks/2026-04-12-backend-error-visibility`

## 验证

- `node --check frontend/tui.ts`
- `.venv/bin/python -m unittest discover -s tests -v`
- `python3 -m compileall -q src/nocode_agent tests`
- `git diff --check`

## 结果说明

- 已让 TUI 缓存 backend 最近一段 `stderr`
- 已在 `fatal` 与非零退出时显示 `stderr` 摘要，而不是只显示 `backend exited with code 1`
- 已在错误提示里附带日志文件路径，默认指向项目根 `.state/nocode.log`
- 已抑制“先 `fatal` 再重复 `code 1`”的双重报错提示
- 已新增 PTY 冒烟测试，覆盖 fake backend fatal + stderr + 日志路径显示场景

## 下一步建议

- 可以继续补 ACP server 的会话错误可见性测试，覆盖 `acp_sessions_path` 写入失败或损坏场景
- 如果还想继续提升排障体验，可以在 TUI 状态栏或帮助页固定显示日志文件位置
