# 补最小启动冒烟测试 结果

任务编号：`2026-04-12-smoke-test-baseline`
所属项目：`reactagent-refactor`
任务目录：`work/projects/reactagent-refactor/tasks/2026-04-12-smoke-test-baseline`

## 提交信息

- 起始 commit：`10cea98`
- 计划提交信息：`test: add startup smoke coverage`
- 最终提交 hash：以所属项目 `STATUS.md` 的“最近阶段提交”为准；如未更新，则通过回查命令定位
- 回查命令：`git log --oneline -- work/projects/reactagent-refactor/tasks/2026-04-12-smoke-test-baseline`

## 验证

- `.venv/bin/python -m unittest discover -s tests -v`
- `python3 -m compileall -q src/nocode_agent tests`
- `git diff --check`

## 结果说明

- 已新增 `tests/test_startup_smoke.py`
- 已覆盖 `nocode` symlink 启动器对 `NOCODE_PROJECT_DIR` 与参数透传的行为
- 已覆盖 `backend_stdio` 在“仓库外只读 cwd + 相对状态路径配置”下的初始化成功场景
- 已修复相对路径按当前 shell cwd 解析的问题；现在 checkpoint、ACP sessions、session memory 都会锚定到项目根
- 已顺手修复 `runtime.paths` 中过时的仓库根识别规则，使其适配 `work/projects/` 新结构

## 下一步建议

- 可以把这两条冒烟测试接到后续 CI 或发布前脚本中，避免启动链再次回归
- 可以继续补 ACP server 的最小会话存取测试，覆盖 `acp_sessions_path` 新的路径锚定逻辑
