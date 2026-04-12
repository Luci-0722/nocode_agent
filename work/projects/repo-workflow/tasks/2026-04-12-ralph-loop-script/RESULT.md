# 新增 Ralph 外层循环脚本 结果

任务编号：`2026-04-12-ralph-loop-script`
所属项目：`repo-workflow`
任务目录：`work/projects/repo-workflow/tasks/2026-04-12-ralph-loop-script`

## 提交信息

- 起始 commit：`f04148f`
- 计划提交信息：`feat: add Ralph loop supervisor script`
- 最终提交 hash：以所属项目 `STATUS.md` 的“最近阶段提交”为准；如未更新，则通过回查命令定位
- 回查命令：`git log --oneline -- work/projects/repo-workflow/tasks/2026-04-12-ralph-loop-script`

## 验证

- `bash -n scripts/ralph_loop.sh`
- `bash scripts/ralph_loop.sh --help`
- 使用临时 fake agent 验证 `CONTINUE -> DONE`，并检查 `LOOP_STATE.json`
- 使用临时 fake agent 验证超轮次后转为 `BUDGET_EXCEEDED`，退出码为 `5`

## 结果说明

- 已新增 `scripts/ralph_loop.sh`，可按轮次执行任意 agent 命令
- 脚本会解析 `STATUS / PROJECT_ID / TASK_ID / COMMIT_DONE / NEXT_ACTION / BLOCKER / VERIFY`
- 默认会把当前轮次结果写入任务目录下的 `LOOP_STATE.json`
- 默认会把每轮原始输出写入任务目录下的 `logs/ralph-loop/`
- 脚本会注入 `RALPH_PROJECT_ID`、`RALPH_TASK_ID`、`RALPH_ITERATION` 等环境变量给 agent 命令

## 下一步建议

- 给 agent 提示词补固定结构化输出模板，降低解析失败概率
- 为 `scripts/ralph_loop.sh` 补一个仓库内可复用的自测脚本
- 如果后续要支持更长时间运行，再补断点续跑和单轮超时控制
