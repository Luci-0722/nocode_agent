# 新增长任务执行 skill 进度

任务编号：`2026-04-12-long-task-skill`
所属项目：`repo-workflow`
任务目录：`work/projects/repo-workflow/tasks/2026-04-12-long-task-skill`

## 当前状态

- 状态：`已完成`
- 最近更新时间：`2026-04-12`

## 已完成

- 已创建任务档案
- 已确定 skill 放在仓库内 `.skills/`
- 已新增 `.skills/long-task-execution/SKILL.md`
- 已新增 `.skills/long-task-execution/agents/openai.yaml`
- 已在仓库协议中声明：只在多阶段长任务时优先使用该 skill
- 已同步更新 `repo-workflow` 的项目状态和任务板
- 已把 Ralph 循环脚本收口到 skill 自带 `scripts/ralph_loop.sh`
- 已把根目录 `scripts/ralph_loop.sh` 改为兼容 wrapper
- 已验证 skill 脚本可在任意 `--task-dir` 下运行，不依赖当前仓库目录结构

## 进行中

- 无

## 待做

- 无

## 决策记录

- skill 只用于多阶段长任务，不用于普通短任务
- skill 负责把项目确认、任务档案、Ralph 循环和结构化状态输出绑在一起
- `allow_implicit_invocation` 保持开启，但通过窄描述限制触发范围
- skill 脚本必须放在 skill 目录里，保证它是自包含、可迁移的
- skill 脚本参数改为 `--task-dir`，避免硬编码依赖当前仓库的 `work/projects/` 结构

## 风险与阻塞

- 如果 skill 描述写得不够窄，仍可能在不该触发的任务上误触发
