# 新增项目选择确认规则 结果

任务编号：`2026-04-12-project-selection-confirmation`
所属项目：`repo-workflow`
任务目录：`work/projects/repo-workflow/tasks/2026-04-12-project-selection-confirmation`

## 提交信息

- 起始 commit：`6d1786d`
- 计划提交信息：`docs: require project confirmation before task creation`
- 最终提交 hash：以所属项目 `STATUS.md` 的“最近阶段提交”为准；如未更新，则通过回查命令定位
- 回查命令：`git log --oneline -- work/projects/repo-workflow/tasks/2026-04-12-project-selection-confirmation`

## 验证

- 人工检查 `AGENTS.md` 是否明确要求无法唯一映射时先确认项目
- 人工检查 `work/projects/README.md` 是否明确区分 `reactagent-refactor` 和 `repo-workflow` 的职责
- 人工检查 `repo-workflow/STATUS.md` 与 `TASK_BOARD.md` 是否同步记录本轮规则调整

## 结果说明

- 已新增强约束：用户请求无法唯一映射到现有项目时，必须先确认项目归属
- 已明确禁止把未明确归属的任务默认挂到 `reactagent-refactor`
- 已把 `repo-workflow` 定义为流程、规范、脚本类项目，不承接业务功能开发

## 下一步建议

- 把这条项目确认规则再写进 agent 提示词模板，减少只看局部文档时的偏差
- 后续如果项目数量继续增加，可以在 `work/projects/README.md` 再补一张“请求类型 -> 推荐项目”的映射表
