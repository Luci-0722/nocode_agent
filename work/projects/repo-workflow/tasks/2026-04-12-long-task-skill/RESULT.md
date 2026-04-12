# 新增长任务执行 skill 结果

任务编号：`2026-04-12-long-task-skill`
所属项目：`repo-workflow`
任务目录：`work/projects/repo-workflow/tasks/2026-04-12-long-task-skill`

## 提交信息

- 起始 commit：`2be916a`
- 计划提交信息：`feat: add long-task execution skill`
- 最终提交 hash：以所属项目 `STATUS.md` 的“最近阶段提交”为准；如未更新，则通过回查命令定位
- 回查命令：`git log --oneline -- work/projects/repo-workflow/tasks/2026-04-12-long-task-skill`

## 验证

- `find .skills -maxdepth 3 -type f | sort`
- 人工检查 `.skills/long-task-execution/SKILL.md` 的 frontmatter 和触发范围
- 人工检查 `.skills/long-task-execution/agents/openai.yaml` 的元数据
- `rg -n "\\.skills/long-task-execution|long-task-execution" AGENTS.md work/projects work/projects/repo-workflow -S`

## 结果说明

- 已把长任务执行协议收口为仓库内 skill：`.skills/long-task-execution/`
- skill 明确只用于多阶段、长周期、需要任务档案和阶段检查点的任务
- skill 内部已经绑定项目确认规则、任务档案流程、Ralph 循环脚本和结构化状态输出模板
- 仓库协议现在会把长任务优先引导到这个 skill，而不是让所有任务都默认走长任务流程

## 下一步建议

- 后续再补一个更固定的长任务提示词模板，直接配合这个 skill 使用
- 如果你希望它更保守，可以把 `allow_implicit_invocation` 改成 `false`，只在显式调用时启用
