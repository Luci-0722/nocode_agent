---
name: long-task-execution
description: Use when the user asks to continue or execute a multi-stage, long-running engineering task that spans multiple commits, sessions, or checkpoints, such as refactors, staged migrations, release hardening, or other long tasks. This skill is self-contained and reusable across repos and agents: it handles project or task-line selection, mandatory user confirmation when ownership is ambiguous, task workspace or dossier continuation, bundled Ralph loop execution via its own scripts/ralph_loop.sh, structured STATUS output, and per-stage documentation plus commit updates. Do not use for one-shot bugfixes, small edits, casual Q&A, or short tasks that fit in a single bounded work item.
---

# Long Task Execution

Use this skill only for long-running work that should be treated as a project or task line, not for normal single-turn edits.

This skill is self-contained. It does not require repo-specific instruction files, workflow docs, or scaffold scripts in order to work.

## Read Order

1. Read the user request and identify whether the task is truly multi-stage and long-running.
2. Read any existing task dossier or task workspace if one already exists.
3. Read repo-level docs only as supplemental context when they exist; they are optional, not required by this skill.

## Project Selection

Use this priority order when a repo has multiple long-task lines:

1. If the user explicitly names a project, use it.
2. If the request maps uniquely to one existing project, use it.
3. If the request does not map uniquely, ask the user to confirm the project before creating a task or changing code.

Never silently guess ownership when multiple tracks are plausible.

## Task Dossier Workflow

- Continue an existing unfinished task workspace when it matches the current work.
- Otherwise create a dedicated task workspace directory for the long task.
- If the repo already has its own workflow, reuse it.
- If the repo does not have one, create a lightweight task workspace such as `.ai/tasks/<task-id>/`.
- The minimal self-contained dossier format is:
  - `README.md`: goal, scope, non-goals, completion criteria
  - `PROGRESS.md`: current state, completed work, in-progress work, blockers
  - `RESULT.md`: verification, commit info, outcome, next-step advice
- Fill in the task notes before coding.
- After each independent work item, update the task notes and any optional repo-level status source the repo expects.
- Commit once per independent work item.

## Execution Mode

Use one of these modes:

- Manual bounded step:
  - Use when the current turn can complete one clear work item.
- Ralph loop:
  - Use when the user wants autonomous multi-round execution or the task clearly benefits from repeated continue/verify cycles.
  - Start from an existing task dossier or task workspace directory.
  - Use:

```bash
bash .skills/long-task-execution/scripts/ralph_loop.sh \
  --task-dir <task-dir> \
  --project-id <project-id> \
  --task-id <task-id> \
  --max-iterations <n> \
  -- <agent-command...>
```

The bundled script is self-contained and does not require the current repo's `work/projects/` structure.

## Structured Status Output

When the work is running inside the Ralph loop, end each round with:

```text
STATUS: CONTINUE
PROJECT_ID: <project-id-or-track>
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
