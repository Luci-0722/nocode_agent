# 新增 Ralph 外层循环脚本

任务编号：`2026-04-12-ralph-loop-script`
所属项目：`repo-workflow`
项目目录：`work/projects/repo-workflow`
任务目录：`work/projects/repo-workflow/tasks/2026-04-12-ralph-loop-script`

## 目标

- 新增仓库内最小可用的 Ralph 外层循环脚本
- 让脚本可以按轮次执行 agent 命令并解析结构化状态
- 把轮次状态和日志稳定落回当前任务目录

## 范围

- 新增 `scripts/ralph_loop.sh`
- 更新 `work/projects/RALPH.md`
- 更新 `repo-workflow` 项目状态和任务板
- 为本轮任务补齐档案

## 非目标

- 不实现更复杂的队列、并发或调度器
- 不自动生成 agent 提示词
- 不修改业务代码

## 起始信息

- 开始日期：`2026-04-12`
- 起始 commit：`f04148f`

## 相关项目文档

- `work/projects/repo-workflow/README.md`
- `work/projects/repo-workflow/STATUS.md`
- `work/projects/repo-workflow/TASK_BOARD.md`

## 相关文件

- `scripts/ralph_loop.sh`
- `work/projects/RALPH.md`
- `work/projects/repo-workflow/STATUS.md`
- `work/projects/repo-workflow/TASK_BOARD.md`
- `work/projects/repo-workflow/tasks/2026-04-12-ralph-loop-script/PROGRESS.md`
- `work/projects/repo-workflow/tasks/2026-04-12-ralph-loop-script/RESULT.md`

## 计划步骤

1. 设计脚本输入输出和默认落盘路径
2. 实现循环执行、状态解析、结果落盘
3. 更新 Ralph 规范和项目文档并验证

## 完成标准

- 可以通过 `scripts/ralph_loop.sh` 执行任意 agent 命令
- 脚本能解析 `STATUS:` 结构化结果并据此继续或停止
- 脚本会把当前轮次结果写入 `LOOP_STATE.json`
- 相关文档已同步更新
