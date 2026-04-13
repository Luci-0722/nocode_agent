---
name: long-task-execution
description: Use when the user wants the agent to execute or continue a long-running engineering task through a dedicated task workspace that survives across turns, checkpoints, or commits, such as large refactors, staged migrations, release hardening, or multi-step feature delivery. This skill creates or resumes the workspace, keeps plan/progress/result files current, and can run iterative continue/verify loops with scripts/ralph_loop.sh. Do not use for one-shot fixes, reviews, or short questions.
---

# Long Task Execution

Use this skill only when the work needs its own task workspace and will likely span multiple commits, checkpoints, or sessions.

## Core Model

Treat the task workspace as the source of truth for the long task.
Every long task should have one workspace directory that another agent can resume without guessing.

Prefer a repo-native task location when one already exists. Otherwise use `.ai/tasks/<task-id>/`.

## When To Use It

Use for:

- large refactors
- staged migrations
- release hardening
- long-running bug hunts with checkpoints
- feature delivery that will take multiple bounded steps

Do not use for:

- one-shot bugfixes
- single-file edits
- reviews
- short Q&A
- tasks that fit in one bounded work item

## Workspace Selection

1. If the user points to a workspace or task directory, use it.
2. If one existing unfinished workspace clearly matches, resume it.
3. If multiple workspaces could match, ask the user before changing code.
4. If none exists, create a new workspace.

Never split one long task across multiple active workspaces unless the user explicitly wants separate tracks.

## Required Workspace Files

The minimal workspace is:

- `README.md`: goal, scope, non-goals, completion criteria
- `PLAN.md`: current phase, next bounded steps, open questions
- `PROGRESS.md`: dated log of completed work, verification, blockers
- `RESULT.md`: final outcome, commits or artifacts, remaining work or next-step advice

Before coding, make sure these files exist and reflect the current task.
Use the bundled initializer when needed:

```bash
bash .skills/long-task-execution/scripts/init_workspace.sh \
  --task-dir .ai/tasks/<task-id> \
  --task-id <task-id> \
  --goal "<task goal>"
```

## Standard Workflow

1. Select or create the workspace.
2. Read `README.md`, `PLAN.md`, and `PROGRESS.md`.
3. Update the workspace before changing code:
   - define the current bounded step in `PLAN.md`
   - record current context or blockers in `PROGRESS.md`
4. Execute one bounded work item.
5. Verify the result.
6. Update `PROGRESS.md` and `RESULT.md` with what changed, how it was verified, and what remains.
7. Commit once per independent work item when a commit is appropriate for the repo.

## Execution Mode

Use one of these modes:

- Manual bounded step:
  - Use when the current turn can complete one clear work item.
- Ralph loop:
  - Use when the user wants autonomous multi-round execution or the task clearly benefits from repeated continue/verify cycles.
  - The loop assumes the workspace already exists and contains the required files.
  - Use:

```bash
bash .skills/long-task-execution/scripts/ralph_loop.sh \
  --task-dir <task-dir> \
  --project-id <project-id> \
  --task-id <task-id> \
  --max-iterations <n> \
  -- <agent-command...>
```

Use `--create-task-dir` only when you intentionally want the loop to create a brand-new workspace directory. Prefer initializing the workspace first.

## Structured Status Output

When the work is running inside the Ralph loop, end each round with:

```text
STATUS: CONTINUE|DONE|BLOCKED|DECISION_NEEDED|BUDGET_EXCEEDED|UNSAFE_TO_CONTINUE
PROJECT_ID: <project-id-or-track>
TASK_ID: <task-id>
COMMIT_DONE: yes|no
NEXT_ACTION: <next bounded step or none>
BLOCKER: none|<reason>
VERIFY: <verification summary>
```

Field rules:

- Always emit all fields above.
- `NEXT_ACTION` is required for `CONTINUE`.
- `BLOCKER` must be `none` for `DONE`.
- If the agent cannot safely continue, use `BLOCKED`, `DECISION_NEEDED`, or `UNSAFE_TO_CONTINUE` instead of pretending the task succeeded.

## Guardrails

- Do not start a long-task loop without a task workspace.
- Do not silently choose between multiple plausible workspaces or project tracks.
- Do not continue coding after the plan or progress files have fallen behind reality.
- Do not mark a round `DONE` without recording verification and updating `RESULT.md`.
