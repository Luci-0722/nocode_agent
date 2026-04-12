# 修复 launcher 继承错误项目根 结果

任务编号：`2026-04-12-launcher-project-root-override`
所属项目：`reactagent-refactor`
任务目录：`work/projects/reactagent-refactor/tasks/2026-04-12-launcher-project-root-override`

## 提交信息

- 起始 commit：`6d1786d`
- 计划提交信息：`fix: pin launcher project root`
- 最终提交 hash：以所属项目 `STATUS.md` 的“最近阶段提交”为准；如未更新，则通过回查命令定位
- 回查命令：`git log --oneline -- work/projects/reactagent-refactor/tasks/2026-04-12-launcher-project-root-override`

## 验证

- `.venv/bin/python -m unittest discover -s tests -v`
- `node --check frontend/tui.ts`
- 真实回归：`env NOCODE_PROJECT_DIR=/Users/lucheng/Projects/NoCode nocode`

## 结果说明

- 已将 `nocode` 中的 `NOCODE_PROJECT_DIR` 改为无条件覆盖当前仓库根
- 已消除 shell 中旧项目根环境变量污染 launcher 的问题
- 已新增自动化测试，覆盖 stale `NOCODE_PROJECT_DIR` 场景

## 下一步建议

- 可以继续检查是否需要对 `NOCODE_AGENT_CONFIG` 这类环境变量增加类似的防污染保护
- 可以补一个 `which/realpath` 诊断命令到 README，方便用户快速确认当前命中的 launcher
