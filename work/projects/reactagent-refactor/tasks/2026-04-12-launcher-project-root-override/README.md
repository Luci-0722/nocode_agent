# 修复 launcher 继承错误项目根

任务编号：`2026-04-12-launcher-project-root-override`
所属项目：`reactagent-refactor`
项目目录：`work/projects/reactagent-refactor`
任务目录：`work/projects/reactagent-refactor/tasks/2026-04-12-launcher-project-root-override`

## 目标

- 修复 `nocode` 启动器继承错误 `NOCODE_PROJECT_DIR` 的问题
- 保证 shell 中残留旧项目根时，当前仓库 launcher 仍绑定到自己
- 补自动化回归，覆盖错误环境变量污染场景

## 范围

- 修改仓库根 `nocode` 启动脚本
- 补充 launcher 相关自动化测试
- 更新项目级状态与任务档案

## 非目标

- 不处理用户显式自定义 `NOCODE_AGENT_CONFIG` 的语义
- 不重做多仓库 launcher 管理方案
- 不修改 backend 业务逻辑

## 起始信息

- 开始日期：`2026-04-12`
- 起始 commit：`6d1786d`

## 相关项目文档

- `work/projects/reactagent-refactor/README.md`
- `work/projects/reactagent-refactor/STATUS.md`
- `work/projects/reactagent-refactor/TASK_BOARD.md`

## 相关文件

- `nocode`
- `tests/test_startup_smoke.py`
- `work/projects/reactagent-refactor/STATUS.md`
- `work/projects/reactagent-refactor/TASK_BOARD.md`
- `work/projects/reactagent-refactor/tasks/2026-04-12-launcher-project-root-override/PROGRESS.md`
- `work/projects/reactagent-refactor/tasks/2026-04-12-launcher-project-root-override/RESULT.md`

## 计划步骤

1. 改 `nocode` 启动脚本，禁止继承外部残留的错误项目根
2. 新增自动化测试，覆盖 stale `NOCODE_PROJECT_DIR` 场景
3. 跑通回归、更新文档与任务档案并提交

## 完成标准

- `nocode` 启动时不再受错误外部 `NOCODE_PROJECT_DIR` 污染
- 自动化测试覆盖该场景
- 项目档案与状态已同步
