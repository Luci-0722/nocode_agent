# 新增长任务执行 skill

任务编号：`2026-04-12-long-task-skill`
所属项目：`repo-workflow`
项目目录：`work/projects/repo-workflow`
任务目录：`work/projects/repo-workflow/tasks/2026-04-12-long-task-skill`

## 目标

- 把长任务执行协议收口成仓库内 skill
- 只在多阶段、长周期任务中使用这个 skill，而不是所有任务都默认启用
- 把项目确认、任务档案和 Ralph 循环规则放到同一个入口
- 让 skill 对任意项目或 agent 都可直接复用
- 让 skill 不依赖 `AGENTS.md`、仓库 workflow 文档或仓库专属脚手架

## 范围

- 新增 `.skills/long-task-execution/`
- 为 skill 补 `SKILL.md` 和 `agents/openai.yaml`
- 把循环脚本收口到 skill 自带 `scripts/ralph_loop.sh`
- 更新仓库协议，说明长任务时优先使用该 skill
- 更新 `repo-workflow` 项目状态和任务板

## 非目标

- 不修改业务代码
- 不把 skill 变成所有任务的默认工作流
- 不替代已有 `work/projects/RALPH.md` 和任务档案文档
- 不把 skill 锁死在当前仓库的 `work/projects/` 布局上
- 不要求其他仓库必须存在 `AGENTS.md` 或 `create_task_scaffold.sh`

## 起始信息

- 开始日期：`2026-04-12`
- 起始 commit：`2be916a`

## 相关项目文档

- `work/projects/repo-workflow/README.md`
- `work/projects/repo-workflow/STATUS.md`
- `work/projects/repo-workflow/TASK_BOARD.md`

## 相关文件

- `.skills/long-task-execution/SKILL.md`
- `.skills/long-task-execution/agents/openai.yaml`
- `.skills/long-task-execution/scripts/ralph_loop.sh`
- `scripts/ralph_loop.sh`
- `AGENTS.md`
- `work/projects/README.md`
- `work/projects/repo-workflow/STATUS.md`
- `work/projects/repo-workflow/TASK_BOARD.md`
- `work/projects/repo-workflow/tasks/2026-04-12-long-task-skill/PROGRESS.md`
- `work/projects/repo-workflow/tasks/2026-04-12-long-task-skill/RESULT.md`

## 计划步骤

1. 设计 skill 的触发边界和职责
2. 落 skill 元数据和执行说明
3. 更新仓库协议和项目状态

## 完成标准

- 多阶段长任务有明确的 skill 入口
- skill 明确限制只用于长任务，不用于普通短任务
- skill 中包含项目确认、任务档案和 Ralph 循环规则
- skill 自带脚本可以脱离当前仓库目录结构直接复用
- skill 说明不再把 `AGENTS.md` 或仓库脚手架当作前置依赖
- 相关协议和项目状态已同步更新
