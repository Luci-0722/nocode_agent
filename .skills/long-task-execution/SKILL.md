---
name: long-task-execution
description: Use when the user asks to continue or execute a multi-stage, long-running engineering task that spans multiple commits, sessions, or checkpoints, such as refactors, staged migrations, release hardening, or other long tasks. This skill handles project selection, mandatory user confirmation when project mapping is ambiguous, task dossier creation or continuation under work/projects/, Ralph loop usage via scripts/ralph_loop.sh, structured STATUS output, and per-stage documentation plus commit updates. Do not use for one-shot bugfixes, small edits, casual Q&A, or short tasks that fit in a single bounded work item.
---

# Long Task Execution

Use this skill only for long-running work that should be treated as a project task line, not for normal single-turn edits.

## Read Order

1. Read `AGENTS.md`.
2. Read `work/projects/README.md`.
3. Read `work/projects/RALPH.md`.
4. Read candidate project `README.md`, `STATUS.md`, and `TASK_BOARD.md`.
5. Read the current task dossier if one already exists.

## Project Selection

Use this priority order:

1. If the user explicitly names a project, use it.
2. If the request maps uniquely to one existing project, use it.
3. If the request does not map uniquely, ask the user to confirm the project before creating a task or changing code.

Never default ambiguous work to `reactagent-refactor`.

Current repo project roles:

- `reactagent-refactor`: product code refactors, engineering hardening, runtime and packaging work for `nocode_agent`
- `repo-workflow`: repository workflow, task dossier protocol, Ralph rules, skills, and related scripts

## Task Dossier Workflow

- Before coding, continue an existing unfinished task under `work/projects/<project-id>/tasks/` when it matches the current work.
- Otherwise create a new task with:

```bash
bash scripts/create_task_scaffold.sh <project-id> <task-id> "<task-title>"
```

- Fill in the task `README.md` before coding.
- After each independent work item, update:
  - task `PROGRESS.md`
  - task `RESULT.md`
  - project `STATUS.md`
  - project `TASK_BOARD.md`
- Commit once per independent work item.

## Execution Mode

Use one of these modes:

- Manual bounded step:
  - Use when the current turn can complete one clear work item.
- Ralph loop:
  - Use when the user wants autonomous multi-round execution or the task clearly benefits from repeated continue/verify cycles.
  - Start from an existing task dossier.
  - Use:

```bash
bash scripts/ralph_loop.sh \
  --project <project-id> \
  --task <task-id> \
  --max-iterations <n> \
  -- <agent-command...>
```

## Structured Status Output

When the work is running inside the Ralph loop, end each round with:

```text
STATUS: CONTINUE
PROJECT_ID: <project-id>
TASK_ID: <task-id>
COMMIT_DONE: yes|no
NEXT_ACTION: <next step>
BLOCKER: none|<reason>
VERIFY: <verification summary>
```

Allowed final statuses:

- `DONE`
- `BLOCKED`
- `DECISION_NEEDED`
- `BUDGET_EXCEEDED`
- `UNSAFE_TO_CONTINUE`

## Do Not Use This Skill

Do not use this skill for:

- single-file edits
- one-shot bugfixes
- short questions or reviews
- tasks that do not need a task dossier or stage checkpoints
