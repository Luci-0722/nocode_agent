# 补最小启动冒烟测试 进度

任务编号：`2026-04-12-smoke-test-baseline`
所属项目：`reactagent-refactor`
任务目录：`work/projects/reactagent-refactor/tasks/2026-04-12-smoke-test-baseline`

## 当前状态

- 状态：`已完成`
- 最近更新时间：`2026-04-12`

## 已完成

- 已创建任务档案
- 已确认当前仓库没有现成测试基线
- 已定位到 `nocode` 保留外部 cwd 时，相对状态路径可能按 cwd 解析
- 已把运行时相对路径统一锚定到项目根
- 已新增 `tests/test_startup_smoke.py`
- 已通过自动化冒烟测试、编译检查与 diff 检查

## 进行中

- 无

## 待做

- 无

## 决策记录

- 测试框架保持最小化，直接使用标准库 `unittest`
- 相对状态路径统一锚定到项目根 `NOCODE_PROJECT_DIR`，不改变用户当前工作目录
- 通过子进程冒烟测试覆盖真实 shell launcher 与 backend 初始化，而不是只测纯函数
- backend 冒烟测试使用“只读 cwd”场景，直接卡住这次用户实际踩到的启动回归

## 风险与阻塞

- backend 启动依赖 LangChain 等运行时依赖，因此测试默认优先复用仓库 `.venv`
