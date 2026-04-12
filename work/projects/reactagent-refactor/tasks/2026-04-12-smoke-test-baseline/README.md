# 补最小启动冒烟测试

任务编号：`2026-04-12-smoke-test-baseline`
所属项目：`reactagent-refactor`
项目目录：`work/projects/reactagent-refactor`
任务目录：`work/projects/reactagent-refactor/tasks/2026-04-12-smoke-test-baseline`

## 目标

- 建立最小启动冒烟测试基线
- 覆盖 `nocode` 启动器与 `backend_stdio` 初始化链路
- 顺手修复测试过程中暴露出的运行时路径解析问题

## 范围

- 新增 `tests/` 目录与启动冒烟测试
- 修正相对状态路径对项目根的锚定逻辑
- 更新 README、项目状态与任务档案

## 非目标

- 不补完整业务测试矩阵
- 不引入 `pytest` 等额外测试框架
- 不处理发布流程或 CI 集成

## 起始信息

- 开始日期：`2026-04-12`
- 起始 commit：`10cea98`

## 相关项目文档

- `work/projects/reactagent-refactor/README.md`
- `work/projects/reactagent-refactor/STATUS.md`
- `work/projects/reactagent-refactor/TASK_BOARD.md`

## 相关文件

- `tests/test_startup_smoke.py`
- `src/nocode_agent/runtime/paths.py`
- `src/nocode_agent/persistence/__init__.py`
- `src/nocode_agent/app/acp_server.py`
- `src/nocode_agent/compression/config.py`
- `README.md`
- `work/projects/reactagent-refactor/STATUS.md`
- `work/projects/reactagent-refactor/TASK_BOARD.md`
- `work/projects/reactagent-refactor/tasks/2026-04-12-smoke-test-baseline/PROGRESS.md`
- `work/projects/reactagent-refactor/tasks/2026-04-12-smoke-test-baseline/RESULT.md`

## 计划步骤

1. 修正配置中的相对运行时路径解析，避免 `nocode` 在仓库外 cwd 启动时写错状态目录
2. 新增 `nocode` 启动器和 backend 初始化的最小冒烟测试
3. 跑通验证、同步文档与任务档案并提交

## 完成标准

- 仓库内存在可重复执行的启动冒烟测试
- `nocode` 在仓库外 cwd 启动时不再因相对状态路径而崩溃
- 文档与项目级交接状态已同步
