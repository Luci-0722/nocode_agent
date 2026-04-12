# 把 nocode_agent 拆成独立 git 仓库

任务编号：`2026-04-12-standalone-git`
所属项目：`reactagent-refactor`
项目目录：`work/projects/reactagent-refactor`
任务目录：`work/projects/reactagent-refactor/tasks/2026-04-12-standalone-git`

## 目标

- 把 `nocode_agent/` 初始化为独立 git 仓库
- 让后续开发默认在当前子项目内提交，而不是继续混在父仓库里
- 补充独立仓库后的使用说明与任务档案

## 范围

- 初始化当前目录内的 `.git/`
- 为独立仓库补充最小忽略规则与说明文档
- 更新项目级状态文档，记录这次仓库边界变化

## 非目标

- 不把父仓库自动改造成 submodule
- 不清理或重写父仓库的历史提交
- 不迁移父仓库中 `nocode_agent/` 之外的目录

## 起始信息

- 开始日期：`2026-04-12`
- 起始 commit：`0838724`

## 相关项目文档

- `work/projects/reactagent-refactor/README.md`
- `work/projects/reactagent-refactor/STATUS.md`
- `work/projects/reactagent-refactor/TASK_BOARD.md`

## 相关文件

- `.gitignore`
- `README.md`
- `work/projects/reactagent-refactor/STATUS.md`
- `work/projects/reactagent-refactor/TASK_BOARD.md`
- `work/projects/reactagent-refactor/tasks/2026-04-12-standalone-git/README.md`
- `work/projects/reactagent-refactor/tasks/2026-04-12-standalone-git/PROGRESS.md`
- `work/projects/reactagent-refactor/tasks/2026-04-12-standalone-git/RESULT.md`

## 计划步骤

1. 补齐任务档案，记录独立 git 方案、范围与风险
2. 在 `nocode_agent/` 内初始化独立 git，并完成首个提交
3. 更新项目级文档和 README，说明新的仓库边界与使用方式

## 完成标准

- 在 `nocode_agent/` 目录内执行 `git rev-parse --show-toplevel` 返回当前目录
- 当前项目存在至少一个独立仓库提交
- 文档明确说明父仓库与子仓库的边界关系
