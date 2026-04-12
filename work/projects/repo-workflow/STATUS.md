# 仓库工作流规范 状态

项目编号：`repo-workflow`

更新时间：`2026-04-12`

## 当前阶段

- 已完成第一版 `project/task` 目录模型、Ralph 执行规范和最小外层循环脚本

## 最近完成

- 根 `AGENTS.md` 已切换到 `work/projects/...` 模型
- 已新增 `work/projects/README.md`
- 已新增 `work/projects/RALPH.md`
- 已新增项目模板、任务模板、项目脚手架、任务脚手架
- 已新增 `scripts/ralph_loop.sh`
- 已新增“项目归属需先确认”的协议规则
- 已新增仓库内 `long-task-execution` skill
- 已把 `reactagent-refactor` 迁到 `work/projects/reactagent-refactor/`
- 已建立 `repo-workflow` 项目与当前任务档案

## 当前接力点

- 长任务 skill 已可用，后续应继续收紧结构化输出模板和自检

## 下一优先任务

- 为 agent 提示词补标准化结构化输出模板，减少 `STATUS:` 解析歧义

## 已知风险

- 目前只有执行规范和脚手架，外层调度器还未实现
- `reactagent-refactor` 的历史任务档案未迁移，新结构下只保留项目级状态
- 虽然已有最小外层脚本，但当前还没有对 agent 输出格式做强约束和自动回放测试

## 最近阶段提交

- `f04148f` docs: adopt project-task workflow for Ralph
- `add5f95` feat: add Ralph loop supervisor script
- `2be916a` docs: require project confirmation before task creation
- 当前工作项：新增长任务执行 skill（见当前提交）
