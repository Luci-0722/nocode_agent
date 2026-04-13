#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash .skills/long-task-execution/scripts/init_workspace.sh --task-dir <path> [options]

Examples:
  bash .skills/long-task-execution/scripts/init_workspace.sh \
    --task-dir .ai/tasks/2026-04-12-refactor \
    --task-id 2026-04-12-refactor \
    --goal "Break the refactor into resumable checkpoints"

Options:
  --task-dir <path>      Required. Workspace directory to create or refresh.
  --task-id <id>         Optional. Defaults to the task-dir basename.
  --goal <text>          Optional. Task goal written into README.md.
  --scope <text>         Optional. Scope note written into README.md.
  --force                Rewrite the workspace files even if they already exist.
  -h, --help             Show this help text.
EOF
}

log() {
  printf '[init-workspace] %s\n' "$*"
}

fail() {
  log "$*" >&2
  exit 2
}

write_file_if_needed() {
  local path="$1"
  local content="$2"
  local force="$3"

  if [[ -f "$path" && "$force" -ne 1 ]]; then
    log "Keeping existing $(basename "$path")"
    return
  fi

  printf '%s' "$content" > "$path"
  log "Wrote $(basename "$path")"
}

task_dir=""
task_id=""
goal=""
scope=""
force=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task-dir)
      task_dir="${2:-}"
      shift 2
      ;;
    --task-id)
      task_id="${2:-}"
      shift 2
      ;;
    --goal)
      goal="${2:-}"
      shift 2
      ;;
    --scope)
      scope="${2:-}"
      shift 2
      ;;
    --force)
      force=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
done

if [[ -z "$task_dir" ]]; then
  fail "Missing --task-dir"
fi

mkdir -p "$task_dir"
task_dir="$(cd "$task_dir" && pwd)"

if [[ -z "$task_id" ]]; then
  task_id="$(basename "$task_dir")"
fi

if [[ -z "$goal" ]]; then
  goal="Describe the long-running task goal here."
fi

if [[ -z "$scope" ]]; then
  scope="List what is in scope for this task."
fi

readme_content=$(cat <<EOF
# $task_id

## Goal

$goal

## Scope

$scope

## Non-goals

- List what this task should not change.

## Completion Criteria

- Define the concrete signals that mean this task is done.
EOF
)

plan_content=$(cat <<'EOF'
# Plan

## Current Phase

- Describe the current phase of the task.

## Next Bounded Steps

- Add the next concrete step.

## Open Questions

- Capture unresolved questions or decisions.
EOF
)

progress_content=$(cat <<'EOF'
# Progress

## Current Status

- Not started yet.

## Latest Verification

- Not run yet.

## Work Log

- Create dated entries as work progresses.
EOF
)

result_content=$(cat <<'EOF'
# Result

## Outcome

- Summarize the current outcome or final result.

## Verification Summary

- Record the most relevant verification.

## Commits And Artifacts

- Link commits, PRs, or output artifacts here.

## Remaining Work

- Note follow-up work or write `none`.
EOF
)

write_file_if_needed "$task_dir/README.md" "$readme_content" "$force"
write_file_if_needed "$task_dir/PLAN.md" "$plan_content" "$force"
write_file_if_needed "$task_dir/PROGRESS.md" "$progress_content" "$force"
write_file_if_needed "$task_dir/RESULT.md" "$result_content" "$force"

log "Workspace ready at $task_dir"
