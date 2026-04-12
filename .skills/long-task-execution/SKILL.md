---
name: long-task-execution
description: Use when the user asks to continue or execute a multi-stage, long-running engineering task that spans multiple commits, sessions, or checkpoints, such as refactors, staged migrations, release hardening, or other long tasks. This skill is self-contained and reusable across repos and agents: it handles project or task-line selection, mandatory user confirmation when ownership is ambiguous, task workspace or dossier continuation, bundled Ralph loop execution via its own scripts/ralph_loop.sh, structured STATUS output, and per-stage documentation plus commit updates. Do not use for one-shot bugfixes, small edits, casual Q&A, or short tasks that fit in a single bounded work item.
---

# Long Task Execution

Use this skill only for long-running work that should be treated as a project or task line, not for normal single-turn edits.

## Read Order

1. Read any repo-level instructions such as `AGENTS.md`, `CLAUDE.md`, or local handoff docs if they exist.
2. Read any project, track, or task-board docs that define the current long task.
3. Read the current task dossier or working directory if one already exists.

## Project Selection

Use this priority order when a repo has multiple long-task lines:

1. If the user explicitly names a project, use it.
2. If the request maps uniquely to one existing project, use it.
3. If the request does not map uniquely, ask the user to confirm the project before creating a task or changing code.

Never silently guess ownership when multiple tracks are plausible.

## Task Dossier Workflow

- If the repo already has a task dossier or project-tracking workflow, follow it.
- Otherwise create or reuse a dedicated task workspace directory for the long task.
- If the current repo uses the `work/projects/<project-id>/tasks/<task-id>/` layout, continue an existing unfinished task when it matches the current work.
- In repos without a built-in workflow, create a lightweight task workspace such as `.ai/tasks/<task-id>/` and keep progress notes there.
- For repos that use the current repository's workflow, create a new task with:

```bash
bash scripts/create_task_scaffold.sh <project-id> <task-id> "<task-title>"
```

- Fill in the task notes before coding.
- After each independent work item, update the task notes and any project-level status source the repo expects.
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
