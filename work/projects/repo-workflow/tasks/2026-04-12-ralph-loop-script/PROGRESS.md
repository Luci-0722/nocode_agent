# 新增 Ralph 外层循环脚本 进度

任务编号：`2026-04-12-ralph-loop-script`
所属项目：`repo-workflow`
任务目录：`work/projects/repo-workflow/tasks/2026-04-12-ralph-loop-script`

## 当前状态

- 状态：`已完成`
- 最近更新时间：`2026-04-12`

## 已完成

- 已创建任务档案
- 已明确脚本默认落盘到 `LOOP_STATE.json` 和 `logs/ralph-loop/`
- 已实现 `scripts/ralph_loop.sh`
- 已补充 Ralph 规范中的状态文件、日志目录和脚本调用方式
- 已完成 `CONTINUE -> DONE` 和超轮次转 `BUDGET_EXCEEDED` 的脚本自检

## 进行中

- 无

## 待做

- 无

## 决策记录

- 先做最小串行 while 循环，不引入并发和队列
- 结构化结果继续沿用 `STATUS / PROJECT_ID / TASK_ID / COMMIT_DONE / NEXT_ACTION / BLOCKER / VERIFY`
- 默认状态文件固定为任务目录下的 `LOOP_STATE.json`
- 默认日志目录固定为任务目录下的 `logs/ralph-loop/`

## 风险与阻塞

- 如果 agent 没有输出标准化 `STATUS:` 行，脚本只能按解析失败退出
- 当前脚本只做最小解析，还没有对字段完整性做更严格校验
