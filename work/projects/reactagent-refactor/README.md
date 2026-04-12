# ReactAgent 重构项目

项目编号：`reactagent-refactor`
项目目录：`work/projects/reactagent-refactor`

这个目录是这条长期任务线的项目级真相源。

## 目标

把当前项目从“历史平铺脚本集合”逐步改造成“围绕最小 `reactagent` 的模块化独立仓库”，并保证迁移过程中：

- 入口持续可用
- 每次只做一小段可提交的工作
- 下一个 agent 不依赖聊天上下文也能继续

## 文档说明

- `MASTER_PLAN.md`
  - 总体目标、阶段划分、每阶段交付物与完成标准
- `STATUS.md`
  - 当前进度、最近完成项、接力点、风险、下一优先任务
- `TASK_BOARD.md`
  - 更细的可执行任务板，适合下一个 agent 直接领取
- `tasks/`
  - 当前项目下的独立工作项目录

## 使用方式

新 agent 接手时按这个顺序读：

1. 先读 `STATUS.md`
2. 再读 `TASK_BOARD.md`
3. 如需理解长期方向，再读 `MASTER_PLAN.md`
4. 开始具体开发前，再进入 `tasks/<task-id>/`

## 当前已完成的起步工作

当前这条重构线的结构目标已经完成：

- 真实运行时代码已全部收口到 `src/nocode_agent/`
- 根目录 shim、旧入口与兼容桥接已删除
- 已补 `pyproject.toml`
- 通用 CLI 与 console script 入口已移除，当前用户入口以 TUI 为主
- 已新增 `nocode` TUI 启动命令与安装脚本
- 前端源码态回退启动已适配 `PYTHONPATH=src`

如需回看阶段起点，可从以下提交开始：

- `239b03f` Bootstrap standalone package runtime

## 重要约束

- 不要恢复根目录 shim、`__path__` 桥接或“双轨目录”兼容方案
- 后续结构演进一律以 `src/nocode_agent/` 为唯一真实源码目录
- 不要把 `nocode` 启动命令重新演变回“多子命令 CLI”
- 每做完一个独立工作项，必须先更新 `tasks/<task-id>/`，再更新本目录文档并提交一次
- 如果阶段设计变化，先改文档再改代码
