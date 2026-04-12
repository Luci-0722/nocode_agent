# 切换到 project/task 任务档案模型

任务编号：`2026-04-12-project-task-protocol`
所属项目：`repo-workflow`
项目目录：`work/projects/repo-workflow`
任务目录：`work/projects/repo-workflow/tasks/2026-04-12-project-task-protocol`

## 目标

- 把仓库任务档案从平铺 `work/tasks/` 收口为 `work/projects/<project-id>/tasks/<task-id>/`
- 为 Ralph 风格的多轮执行提供项目级和任务级双层真相源
- 提供后续可复用的模板和脚手架

## 范围

- 更新根 `AGENTS.md`
- 新增 `work/projects/README.md` 与 `work/projects/RALPH.md`
- 新增项目模板与任务模板
- 新增项目脚手架与更新任务脚手架
- 迁移 `reactagent-refactor` 项目目录
- 删除旧 `work/tasks/` 目录

## 非目标

- 不实现 Ralph 外层 while 脚本
- 不恢复旧任务目录兼容入口
- 不改动产品功能代码

## 起始信息

- 开始日期：`2026-04-12`
- 起始 commit：`5fdff62`

## 相关项目文档

- `work/projects/repo-workflow/README.md`
- `work/projects/repo-workflow/STATUS.md`
- `work/projects/repo-workflow/TASK_BOARD.md`

## 相关文件

- `AGENTS.md`
- `scripts/create_project_scaffold.sh`
- `scripts/create_task_scaffold.sh`
- `work/projects/README.md`
- `work/projects/RALPH.md`
- `work/projects/_template/`
- `work/projects/reactagent-refactor/`

## 计划步骤

1. 设计新的项目级 / 任务级目录协议
2. 落模板与脚手架并自检
3. 迁移现有项目入口并删除旧平铺任务目录

## 完成标准

- 根协议只引用 `work/projects/...`
- 新项目和新任务可通过脚手架创建
- `reactagent-refactor` 在新路径下可继续接力
- 仓库内不再保留旧 `work/tasks/` 结构
