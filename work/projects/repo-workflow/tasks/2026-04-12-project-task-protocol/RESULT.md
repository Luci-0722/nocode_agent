# 切换到 project/task 任务档案模型 结果

任务编号：`2026-04-12-project-task-protocol`
所属项目：`repo-workflow`
任务目录：`work/projects/repo-workflow/tasks/2026-04-12-project-task-protocol`

## 提交信息

- 起始 commit：`5fdff62`
- 计划提交信息：`docs: adopt project-task workflow for Ralph`
- 最终提交 hash：以所属项目 `STATUS.md` 的“最近阶段提交”为准；如未更新，则通过回查命令定位
- 回查命令：`git log --oneline -- work/projects/repo-workflow/tasks/2026-04-12-project-task-protocol`

## 验证

- `bash -n scripts/create_project_scaffold.sh`
- `bash -n scripts/create_task_scaffold.sh`
- `bash scripts/create_project_scaffold.sh --help`
- `bash scripts/create_task_scaffold.sh --help`
- `bash scripts/create_project_scaffold.sh repo-workflow "仓库工作流规范"`
- `bash scripts/create_task_scaffold.sh repo-workflow 2026-04-12-project-task-protocol "切换到 project/task 任务档案模型"`
- `rg -n "work/tasks|work/reactagent-refactor" work/projects AGENTS.md scripts -S`

## 结果说明

- 已把仓库任务档案收口到 `work/projects/<project-id>/tasks/<task-id>/`
- 已新增 Ralph 执行规范文档，明确“外层新进程循环、内层单轮执行”的默认方式
- 已新增项目脚手架，并把任务脚手架改为项目内任务生成
- 已把 `reactagent-refactor` 项目迁到新路径，旧 `work/tasks/` 目录已删除

## 下一步建议

- 基于 `work/projects/RALPH.md` 落一个最小外层循环脚本
- 为结构化轮次结果补机器可读落盘文件，例如 `LOOP_STATE.json`
- 后续新增长期任务时，先创建项目，再创建项目内任务
