# 项目档案目录

这个目录用于保存“长期任务线 + 独立工作项”的完整上下文。

目标不是把所有信息都塞进一个大文档，而是把信息拆成两层：

- 项目级：长期目标、当前阶段、接力点、任务板
- 任务级：单轮工作项的步骤、局部决策、验证结果、提交信息

这样后续 agent 即使完全不依赖聊天上下文，也能只靠仓库内文档继续推进。

## 目录约定

每条长期任务线使用一个独立项目目录：

```text
work/projects/<project-id>/
  README.md
  STATUS.md
  TASK_BOARD.md
  tasks/
    README.md
    <task-id>/
      README.md
      PROGRESS.md
      RESULT.md
```

同时保留一个模板目录：

```text
work/projects/_template/
```

## 创建方式

先创建项目：

```bash
bash scripts/create_project_scaffold.sh reactagent-refactor "ReactAgent 重构"
```

再创建项目下的独立任务：

```bash
bash scripts/create_task_scaffold.sh reactagent-refactor 2026-04-12-tool-registry-split "拆分 tool registry"
```

## 文件职责

项目目录：

- `README.md`
  - 项目目标
  - 范围 / 非目标
  - 关键约束
  - 阅读顺序
- `STATUS.md`
  - 当前阶段
  - 最近完成
  - 当前接力点
  - 下一优先任务
  - 已知风险
  - 最近阶段提交
- `TASK_BOARD.md`
  - 可领取任务
  - 优先级
  - 完成情况

任务目录：

- `README.md`
  - 本轮工作目标
  - 所属项目
  - 起始 commit
  - 相关文件
  - 完成标准
- `PROGRESS.md`
  - 当前状态
  - 步骤拆分
  - 已完成 / 进行中 / 待做
  - 决策、风险、阻塞
- `RESULT.md`
  - 验证结果
  - 提交信息
  - 结果说明
  - 给下一位 agent 的建议

## 读取顺序

新 agent 接手时按这个顺序读：

1. 先读 `AGENTS.md`
2. 再读 `work/projects/README.md`
3. 再读 `work/projects/RALPH.md`
4. 然后进入目标项目的 `README.md`、`STATUS.md`、`TASK_BOARD.md`
5. 最后进入本轮任务目录的 `README.md`、`PROGRESS.md`、`RESULT.md`

如果用户请求的是多阶段、长周期、需要多次提交或多轮接力的任务，优先启用仓库 skill：`.skills/long-task-execution/`。

## 当前项目列表

- `reactagent-refactor` -> `work/projects/reactagent-refactor/README.md`
  - 用于 `nocode_agent` 的结构重构、工程化收尾和相关代码任务
- `repo-workflow` -> `work/projects/repo-workflow/README.md`
  - 用于仓库协作协议、任务档案、Ralph 规范与相关脚本

## 项目选择规则

- 如果用户明确说了项目名，直接进入对应项目
- 如果用户请求能被仓库文档唯一映射到某个项目，可以直接进入该项目
- 如果用户请求不能唯一映射到现有项目，必须先向用户确认项目归属
- 不得因为 `reactagent-refactor` 是主要开发项目，就把未明确归属的任务默认挂到它下面
- `repo-workflow` 只承接流程、规范、脚手架、Ralph 相关工作，不承接业务功能开发

## 关于提交 hash

任务目录需要记录：

- 起始 commit
- 计划提交信息
- 验证结果
- 相关历史提交

同一个提交无法在自身内容里稳定写入自己的 hash。

因此：

- 如果当前工作属于已有项目，最终提交 hash 统一以该项目 `STATUS.md` 的“最近阶段提交”为准
- 如果项目 `STATUS.md` 尚未更新，则至少在 `RESULT.md` 中写明回查命令

统一回查方式：

```bash
git log --oneline -- work/projects/<project-id>/tasks/<task-id>
```
