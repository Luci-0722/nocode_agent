# Ralph 执行规范

这个文档约束“外层循环 + 内层 agent 单轮执行”的工作方式。

目标不是让同一个 agent 一直跑到上下文失真，而是让每一轮都能：

- 从仓库内真相源重新启动
- 完成一个最小可验证步骤
- 把状态落回项目文档和任务文档
- 再由外层循环决定是否继续

## 基本原则

1. 外层循环使用“每轮启动一个新 agent”的方式。
2. 内层单轮执行负责：读取状态、改动、验证、写文档、提交。
3. 状态保存在仓库文件和 git 历史里，不保存在聊天上下文里。
4. 提交是检查点，不是默认停止点。

## 每轮必读顺序

1. `AGENTS.md`
2. `work/projects/README.md`
3. `work/projects/RALPH.md`
4. 目标项目的 `README.md`
5. 目标项目的 `STATUS.md`
6. 目标项目的 `TASK_BOARD.md`
7. 当前任务目录的 `README.md`
8. 当前任务目录的 `PROGRESS.md`
9. 当前任务目录的 `RESULT.md`
10. 当前 `git status`、必要的 diff、必要的测试输出

## 默认继续原则

- 如果还能从 `TASK_BOARD.md` 或当前任务计划里选出下一个可直接执行的最小步骤，就必须继续。
- 测试通过不是停止信号，只表示当前子步骤可落档。
- 提交完成不是停止信号，只表示当前子步骤已形成检查点。
- 只有命中允许停止状态时，循环才可以结束。

## 允许停止状态

只允许以下状态结束一轮外层循环：

- `DONE`
  - 当前任务完成标准全部满足
- `BLOCKED`
  - 缺信息、缺权限、缺外部依赖，且无法自行绕过
- `DECISION_NEEDED`
  - 存在高影响分叉，需要人工拍板
- `BUDGET_EXCEEDED`
  - 达到预设轮次、时间或成本上限
- `UNSAFE_TO_CONTINUE`
  - 继续执行可能造成大范围错误修改

除此之外，一律视为 `CONTINUE`。

## 单轮标准动作

每一轮必须完成以下动作：

1. 读取项目级和任务级真相源
2. 选择一个最小、可验证的下一步
3. 实施代码或文档改动
4. 运行必要验证
5. 更新当前任务的 `PROGRESS.md` / `RESULT.md`
6. 更新所属项目的 `STATUS.md` / `TASK_BOARD.md`
7. 提交一次 commit
8. 输出本轮状态，交给外层循环判断是否继续

## 结构化轮次结果

每轮结束时，agent 应输出固定格式结果，供外层脚本解析：

```text
STATUS: CONTINUE
PROJECT_ID: reactagent-refactor
TASK_ID: 2026-04-12-tool-web-split
COMMIT_DONE: yes
NEXT_ACTION: 继续拆分剩余 web 调用路径
BLOCKER: none
VERIFY: pytest -q
```

默认落盘约定：

- 状态文件：`work/projects/<project-id>/tasks/<task-id>/LOOP_STATE.json`
- 日志目录：`work/projects/<project-id>/tasks/<task-id>/logs/ralph-loop/`

仓库内最小外层循环脚本：

```bash
bash scripts/ralph_loop.sh \
  --project <project-id> \
  --task <task-id> \
  --max-iterations 5 \
  -- <agent-command...>
```

脚本会向 agent 命令注入以下环境变量：

- `RALPH_PROJECT_ID`
- `RALPH_TASK_ID`
- `RALPH_ITERATION`
- `RALPH_MAX_ITERATIONS`
- `RALPH_STATE_FILE`
- `RALPH_LOG_FILE`

## 项目与任务的职责边界

- 项目目录回答“这条长期任务线要去哪、做到哪、接下来做什么”
- 任务目录回答“这一轮具体做了什么、怎么验证、有哪些局部决策”

## 适用场景

优先用于：

- 长期重构
- 多阶段工程化收尾
- 需要多轮接力推进的任务

不强制用于：

- 纯问答
- 一次性几分钟内即可完成的小修复
- 必须维持同一交互会话状态的任务
