# 仓库协作约定

从这一轮开始，本仓库采用“可中途接力”的工作方式。后续 agent 不应依赖聊天上下文，而应先读取仓库内的交接文档，再继续开发。

## 仓库级必读入口

开始任何开发前，先阅读以下目录中的文档：

- `work/projects/README.md`
- `work/projects/RALPH.md`

当用户要求继续多阶段、长周期、需要分阶段提交的任务时，优先使用仓库 skill：`.skills/long-task-execution/`。
普通短任务、单次修复、问答不要启用这个 skill。

## 仓库级工作规则

1. 每个独立工作项都必须归属到一个项目目录：`work/projects/<project-id>/`。
   - 如果项目不存在，先使用 `scripts/create_project_scaffold.sh <project-id> "<project-title>"` 创建
   - `project-id` 使用稳定英文短名，例如 `reactagent-refactor`、`repo-workflow`
   - 如果用户请求无法唯一映射到现有项目，必须先和用户确认项目归属，再开始建立任务目录或编码
   - 不得因为仓库里已有 `reactagent-refactor`，就把未明确归属的新任务默认挂到它下面
2. 每个独立工作项开始前，先在 `work/projects/<project-id>/tasks/<task-id>/` 下建立任务目录。
   - 优先使用 `scripts/create_task_scaffold.sh <project-id> <task-id> "<task-title>"` 从模板生成
   - `task-id` 建议使用 `YYYY-MM-DD-任务短名` 或 `T4-runtime-wrapper` 这种稳定命名
   - 如果已经存在对应的未完成任务目录，优先续做，不要重复新建
3. 项目目录至少包含以下文件：
   - `README.md`：项目目标、范围、关键约束、阅读顺序
   - `STATUS.md`：当前阶段、最近完成、接力点、风险、最近阶段提交
   - `TASK_BOARD.md`：可领取任务、优先级、完成情况
4. 任务目录至少包含以下文件：
   - `README.md`：目标、范围、起始 commit、相关文件、完成标准
   - `PROGRESS.md`：步骤拆分、进行中状态、决策、风险、阻塞
   - `RESULT.md`：验证结果、提交信息、下一步建议
5. 开始编码前，必须先补齐本轮任务目录的基础信息：
   - 当前任务目标
   - 起始 commit
   - 计划步骤
   - 所属项目
   - 相关文件 / 非目标
6. 每完成一个独立工作项：
   - 先更新当前任务目录中的 `PROGRESS.md` / `RESULT.md`
   - 再更新所属项目的 `STATUS.md` / `TASK_BOARD.md`
   - 然后提交一次 commit
7. 如果你改变了目录规划、阶段划分、兼容策略，或任务档案流程，必须把变化写进对应交接文档，不能只体现在代码里。
8. 不要删除新结构下的任务档案；后续阶段只增量更新。

## 任务档案说明

目录分为两层：

- `work/projects/<project-id>/`：项目级真相源
- `work/projects/<project-id>/tasks/<task-id>/`：单任务级细节

目的是让 agent 在上下文压缩、会话切换、甚至完全重新启动后，仍能仅靠仓库内事实继续开发。

约定如下：

- 一个项目目录只对应一条长期任务线，不要在同一目录里混入多个长期主题
- 一个任务目录只对应一个独立工作项，不要在同一目录里混入多个主题
- 项目级文档维护“长期规划 / 当前接力点 / 下一优先任务”
- 任务级文档维护“本轮步骤 / 局部决策 / 验证结果 / 提交信息”
- 项目选择优先级是：用户明确指定 > 仓库文档唯一映射 > 先确认用户
- 任务进行中，优先把临时决策、风险、检查结果写进 `PROGRESS.md`
- 任务完成后，把最终结论写进 `RESULT.md`
- 长期循环执行时，额外遵循 `work/projects/RALPH.md`

关于提交信息：

- 任务目录必须记录起始 commit、计划提交信息、验证结果、相关历史提交
- 同一个提交无法在自身内容中稳定写入自己的 commit hash
- 如果当前工作属于某个已有项目，最终提交 hash 统一以该项目 `STATUS.md` 的“最近阶段提交”为准
- 如果当前工作所在项目未显式记录阶段提交，则至少在 `RESULT.md` 中写明回查命令
- 如需从任务目录反查实际结果提交，使用 `git log --oneline -- work/projects/<project-id>/tasks/<task-id>`
