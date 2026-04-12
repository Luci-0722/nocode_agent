# 切换到 project/task 任务档案模型 进度

任务编号：`2026-04-12-project-task-protocol`
所属项目：`repo-workflow`
任务目录：`work/projects/repo-workflow/tasks/2026-04-12-project-task-protocol`

## 当前状态

- 状态：`已完成`
- 最近更新时间：`2026-04-12`

## 已完成

- 已把根 `AGENTS.md` 切换到 `work/projects/...` 模型
- 已新增 `work/projects/README.md` 与 `work/projects/RALPH.md`
- 已新增项目模板、任务模板、项目脚手架
- 已把 `scripts/create_task_scaffold.sh` 改为项目内任务脚手架
- 已修正脚手架根路径判定，避免误用上级 git 根目录
- 已把 `reactagent-refactor` 迁到 `work/projects/reactagent-refactor/`
- 已建立 `repo-workflow` 项目和当前任务档案

## 进行中

- 无

## 待做

- 无

## 决策记录

- 目录模型固定为 `project -> tasks -> task`
- 所有独立工作项必须归属项目，不再保留仓库级平铺任务目录
- Ralph 规范独立成 `work/projects/RALPH.md`，避免根 `AGENTS.md` 过重
- 项目脚手架用脚本所在目录推导仓库根，避免 monorepo 顶层误判

## 风险与阻塞

- 旧 `work/tasks/` 删除后，历史单任务细节只剩 git 历史可回看
- 目前没有外层循环脚本，Ralph 规范还无法强制执行
