# 仓库工作流规范

项目编号：`repo-workflow`
项目目录：`work/projects/repo-workflow`

## 目标

- 统一仓库内长期任务线与独立工作项的目录模型
- 固化适配 Ralph 循环执行的项目级 / 任务级真相源
- 为后续 agent 提供可直接复用的模板与脚手架

## 范围

- 更新根 `AGENTS.md`
- 建立 `work/projects/` 根目录说明与 Ralph 执行规范
- 新增项目模板、任务模板、项目脚手架、任务脚手架
- 把 `reactagent-refactor` 收口到 `work/projects/reactagent-refactor/`
- 用本轮任务创建真实项目与真实任务档案

## 非目标

- 不改动业务代码与运行时逻辑
- 不补 Ralph 外层 while 脚本
- 不保留旧 `work/tasks/` 的兼容入口

## 起始信息

- 开始日期：`2026-04-12`
- 起始 commit：`5fdff62`

## 关键文档

- 仓库级入口以 `work/projects/README.md` 和 `work/projects/RALPH.md` 为准
- `work/projects/repo-workflow/STATUS.md`
- `work/projects/repo-workflow/TASK_BOARD.md`

## 阅读顺序

1. 先读 `work/projects/README.md`
2. 再读 `work/projects/RALPH.md`
3. 再读 `STATUS.md`
4. 最后读 `TASK_BOARD.md`

## 当前接力规则

- 所有独立工作项都必须挂在某个 `work/projects/<project-id>/tasks/<task-id>/` 下
- 提交是检查点，不是默认停止点
- 如果后续继续演进仓库协作协议，优先在本项目下新增任务，而不是直接改历史任务档案
