# 新增项目选择确认规则

任务编号：`2026-04-12-project-selection-confirmation`
所属项目：`repo-workflow`
项目目录：`work/projects/repo-workflow`
任务目录：`work/projects/repo-workflow/tasks/2026-04-12-project-selection-confirmation`

## 目标

- 明确 agent 在开始开发前如何选择项目归属
- 避免把未明确归属的新任务默认挂到 `reactagent-refactor`
- 要求无法唯一映射时先和用户确认项目

## 范围

- 更新根 `AGENTS.md`
- 更新 `work/projects/README.md`
- 更新 `repo-workflow` 项目状态和任务板
- 为本轮任务补齐档案

## 非目标

- 不改变现有项目目录结构
- 不修改业务代码
- 不恢复已删除的旧任务入口

## 起始信息

- 开始日期：`2026-04-12`
- 起始 commit：`6d1786d`

## 相关项目文档

- `work/projects/repo-workflow/README.md`
- `work/projects/repo-workflow/STATUS.md`
- `work/projects/repo-workflow/TASK_BOARD.md`

## 相关文件

- `AGENTS.md`
- `work/projects/README.md`
- `work/projects/repo-workflow/STATUS.md`
- `work/projects/repo-workflow/TASK_BOARD.md`
- `work/projects/repo-workflow/tasks/2026-04-12-project-selection-confirmation/PROGRESS.md`
- `work/projects/repo-workflow/tasks/2026-04-12-project-selection-confirmation/RESULT.md`

## 计划步骤

1. 明确项目选择的判定顺序
2. 把确认规则写入仓库协议和项目目录说明
3. 更新项目状态并完成任务归档

## 完成标准

- 协议明确要求：无法唯一映射项目时先确认用户
- 文档明确区分 `reactagent-refactor` 与 `repo-workflow` 的职责
- 本轮任务档案和项目状态已同步更新
