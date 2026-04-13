#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash .skills/long-task-execution/scripts/ralph_loop.sh --task-dir <path> [options] -- <agent-command...>

Examples:
  bash .skills/long-task-execution/scripts/ralph_loop.sh \
    --task-dir .ai/tasks/2026-04-12-refactor \
    --project-id refactor \
    --task-id 2026-04-12-refactor \
    --max-iterations 5 \
    -- codex exec "Continue the long task and end with STATUS lines."

Options:
  --task-dir <path>            Required. Task workspace directory.
  --create-task-dir            Create task-dir when it does not already exist.
  --project-id <id>            Optional. Project or task-line identifier.
  --task-id <id>               Optional. Defaults to the task-dir basename.
  --max-iterations <n>         Maximum loop iterations. Default: 5.
  --sleep-seconds <n>          Seconds to sleep between rounds. Default: 0.
  --state-file <path>          State file path. Default: <task-dir>/LOOP_STATE.json
  --log-dir <path>             Log directory. Default: <task-dir>/logs/ralph-loop
  -h, --help                   Show this help text.

Exit codes:
  0  DONE
  2  Argument error, parse error, or invalid command result
  3  BLOCKED
  4  DECISION_NEEDED
  5  BUDGET_EXCEEDED
  6  UNSAFE_TO_CONTINUE
EOF
}

log() {
  printf '[ralph-loop] %s\n' "$*"
}

fail() {
  log "$*" >&2
  exit 2
}

json_escape() {
  local value="${1:-}"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\r'/\\r}"
  value="${value//$'\t'/\\t}"
  printf '%s' "$value"
}

extract_field() {
  local field="$1"
  local file="$2"

  awk -v field="$field" '
    index($0, field ": ") == 1 {
      value = substr($0, length(field) + 3)
    }
    END {
      print value
    }
  ' "$file"
}

require_workspace_files() {
  local workspace_dir="$1"
  local missing=()
  local required=(
    "README.md"
    "PLAN.md"
    "PROGRESS.md"
    "RESULT.md"
  )

  for file in "${required[@]}"; do
    if [[ ! -f "$workspace_dir/$file" ]]; then
      missing+=("$file")
    fi
  done

  if (( ${#missing[@]} > 0 )); then
    fail "workspace is missing required files: ${missing[*]}. Initialize it with bash .skills/long-task-execution/scripts/init_workspace.sh --task-dir $workspace_dir"
  fi
}

write_state() {
  local state_path="$1"
  local updated_at="$2"
  local iteration="$3"
  local status="$4"
  local project_id="$5"
  local task_id="$6"
  local task_dir="$7"
  local commit_done="$8"
  local next_action="$9"
  local blocker="${10}"
  local verify="${11}"
  local log_file="${12}"
  local command_exit_code="${13}"
  local agent_command="${14}"

  mkdir -p "$(dirname "$state_path")"

  cat > "$state_path" <<EOF
{
  "updated_at": "$(json_escape "$updated_at")",
  "iteration": $iteration,
  "status": "$(json_escape "$status")",
  "project_id": "$(json_escape "$project_id")",
  "task_id": "$(json_escape "$task_id")",
  "task_dir": "$(json_escape "$task_dir")",
  "commit_done": "$(json_escape "$commit_done")",
  "next_action": "$(json_escape "$next_action")",
  "blocker": "$(json_escape "$blocker")",
  "verify": "$(json_escape "$verify")",
  "log_file": "$(json_escape "$log_file")",
  "command_exit_code": $command_exit_code,
  "agent_command": "$(json_escape "$agent_command")"
}
EOF
}

status_exit_code() {
  case "$1" in
    DONE)
      echo 0
      ;;
    BLOCKED)
      echo 3
      ;;
    DECISION_NEEDED)
      echo 4
      ;;
    BUDGET_EXCEEDED)
      echo 5
      ;;
    UNSAFE_TO_CONTINUE)
      echo 6
      ;;
    *)
      echo 2
      ;;
  esac
}

validate_status_block() {
  local status="$1"
  local project_id="$2"
  local task_id="$3"
  local commit_done="$4"
  local next_action="$5"
  local blocker="$6"
  local verify="$7"
  local errors=()

  [[ -n "$project_id" ]] || errors+=("PROJECT_ID")
  [[ -n "$task_id" ]] || errors+=("TASK_ID")

  if [[ "$commit_done" != "yes" && "$commit_done" != "no" ]]; then
    errors+=("COMMIT_DONE must be yes or no")
  fi

  [[ -n "$next_action" ]] || errors+=("NEXT_ACTION")
  [[ -n "$blocker" ]] || errors+=("BLOCKER")
  [[ -n "$verify" ]] || errors+=("VERIFY")

  case "$status" in
    CONTINUE)
      if [[ "$next_action" == "none" ]]; then
        errors+=("NEXT_ACTION must not be none for CONTINUE")
      fi
      ;;
    DONE)
      if [[ "$blocker" != "none" ]]; then
        errors+=("BLOCKER must be none for DONE")
      fi
      ;;
    BLOCKED|DECISION_NEEDED|UNSAFE_TO_CONTINUE)
      if [[ "$blocker" == "none" ]]; then
        errors+=("BLOCKER must explain why execution stopped")
      fi
      ;;
  esac

  if (( ${#errors[@]} > 0 )); then
    printf '%s' "${errors[*]}"
    return 1
  fi

  return 0
}

task_dir=""
create_task_dir=0
project_id=""
task_id=""
max_iterations=5
sleep_seconds=0
state_file=""
log_dir=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task-dir)
      task_dir="${2:-}"
      shift 2
      ;;
    --create-task-dir)
      create_task_dir=1
      shift
      ;;
    --project-id)
      project_id="${2:-}"
      shift 2
      ;;
    --task-id)
      task_id="${2:-}"
      shift 2
      ;;
    --max-iterations)
      max_iterations="${2:-}"
      shift 2
      ;;
    --sleep-seconds)
      sleep_seconds="${2:-}"
      shift 2
      ;;
    --state-file)
      state_file="${2:-}"
      shift 2
      ;;
    --log-dir)
      log_dir="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
done

if [[ -z "$task_dir" ]]; then
  fail "Missing --task-dir"
fi

if [[ $# -eq 0 ]]; then
  fail "Missing agent command. Use -- <agent-command...>"
fi

if ! [[ "$max_iterations" =~ ^[0-9]+$ ]] || [[ "$max_iterations" -lt 1 ]]; then
  fail "--max-iterations must be an integer greater than 0"
fi

if ! [[ "$sleep_seconds" =~ ^[0-9]+$ ]]; then
  fail "--sleep-seconds must be a non-negative integer"
fi

if [[ -d "$task_dir" ]]; then
  :
elif [[ "$create_task_dir" -eq 1 ]]; then
  mkdir -p "$task_dir"
else
  fail "task-dir does not exist: $task_dir"
fi

task_dir="$(cd "$task_dir" && pwd)"

if [[ -z "$task_id" ]]; then
  task_id="$(basename "$task_dir")"
fi

if [[ -z "$project_id" ]]; then
  project_id="$task_id"
fi

if [[ -z "$state_file" ]]; then
  state_file="$task_dir/LOOP_STATE.json"
fi

if [[ -z "$log_dir" ]]; then
  log_dir="$task_dir/logs/ralph-loop"
fi

mkdir -p "$log_dir"
require_workspace_files "$task_dir"

agent_cmd=("$@")
agent_command_string="${agent_cmd[*]}"

iteration=1

while (( iteration <= max_iterations )); do
  timestamp="$(date '+%Y-%m-%dT%H:%M:%S%z')"
  log_file="$log_dir/$(date '+%Y%m%d-%H%M%S')-iter$(printf '%02d' "$iteration").log"

  log "Starting iteration $iteration / $max_iterations"
  log "Task directory: $task_dir"
  log "Log file: $log_file"

  set +e
  env \
    RALPH_PROJECT_ID="$project_id" \
    RALPH_TASK_ID="$task_id" \
    RALPH_TASK_DIR="$task_dir" \
    RALPH_ITERATION="$iteration" \
    RALPH_MAX_ITERATIONS="$max_iterations" \
    RALPH_STATE_FILE="$state_file" \
    RALPH_LOG_FILE="$log_file" \
    "${agent_cmd[@]}" 2>&1 | tee "$log_file"
  command_exit_code=${PIPESTATUS[0]}
  set -e

  status="$(extract_field STATUS "$log_file")"
  output_project_id="$(extract_field PROJECT_ID "$log_file")"
  output_task_id="$(extract_field TASK_ID "$log_file")"
  commit_done="$(extract_field COMMIT_DONE "$log_file")"
  next_action="$(extract_field NEXT_ACTION "$log_file")"
  blocker="$(extract_field BLOCKER "$log_file")"
  verify="$(extract_field VERIFY "$log_file")"

  effective_project_id="${project_id}"
  effective_task_id="${task_id}"

  if [[ -n "$output_project_id" ]]; then
    effective_project_id="$output_project_id"
  fi

  if [[ -n "$output_task_id" ]]; then
    effective_task_id="$output_task_id"
  fi

  if [[ -z "$status" ]]; then
    write_state \
      "$state_file" \
      "$timestamp" \
      "$iteration" \
      "PARSE_ERROR" \
      "$effective_project_id" \
      "$effective_task_id" \
      "$task_dir" \
      "${commit_done:-unknown}" \
      "${next_action:-missing}" \
      "missing STATUS line" \
      "${verify:-missing}" \
      "$log_file" \
      "$command_exit_code" \
      "$agent_command_string"
    fail "Iteration $iteration did not emit a STATUS line. Check $log_file"
  fi

  case "$status" in
    CONTINUE|DONE|BLOCKED|DECISION_NEEDED|BUDGET_EXCEEDED|UNSAFE_TO_CONTINUE)
      ;;
    *)
      write_state \
        "$state_file" \
        "$timestamp" \
        "$iteration" \
        "PARSE_ERROR" \
        "$effective_project_id" \
        "$effective_task_id" \
        "$task_dir" \
        "${commit_done:-unknown}" \
        "${next_action:-invalid}" \
        "unknown status: $status" \
        "${verify:-missing}" \
        "$log_file" \
        "$command_exit_code" \
        "$agent_command_string"
      fail "Iteration $iteration returned an unknown status: $status"
      ;;
  esac

  validation_error=""
  if ! validation_error="$(validate_status_block \
    "$status" \
    "$effective_project_id" \
    "$effective_task_id" \
    "${commit_done:-}" \
    "${next_action:-}" \
    "${blocker:-}" \
    "${verify:-}")"; then
    write_state \
      "$state_file" \
      "$timestamp" \
      "$iteration" \
      "PARSE_ERROR" \
      "$effective_project_id" \
      "$effective_task_id" \
      "$task_dir" \
      "${commit_done:-unknown}" \
      "${next_action:-invalid}" \
      "$validation_error" \
      "${verify:-missing}" \
      "$log_file" \
      "$command_exit_code" \
      "$agent_command_string"
    fail "Iteration $iteration returned an invalid structured status: $validation_error"
  fi

  if [[ "$command_exit_code" -ne 0 ]]; then
    case "$status" in
      BLOCKED|DECISION_NEEDED|BUDGET_EXCEEDED|UNSAFE_TO_CONTINUE)
        ;;
      *)
        write_state \
          "$state_file" \
          "$timestamp" \
          "$iteration" \
          "COMMAND_ERROR" \
          "$effective_project_id" \
          "$effective_task_id" \
          "$task_dir" \
          "${commit_done:-unknown}" \
          "${next_action:-none}" \
          "agent command exited with code $command_exit_code" \
          "${verify:-none}" \
          "$log_file" \
          "$command_exit_code" \
          "$agent_command_string"
        fail "Iteration $iteration exited with code $command_exit_code and status $status cannot continue"
        ;;
    esac
  fi

  effective_status="$status"
  effective_blocker="${blocker:-none}"

  if [[ "$status" == "CONTINUE" && "$iteration" -eq "$max_iterations" ]]; then
    effective_status="BUDGET_EXCEEDED"
    effective_blocker="reached max iteration limit: $max_iterations"
  fi

  write_state \
    "$state_file" \
    "$timestamp" \
    "$iteration" \
    "$effective_status" \
    "$effective_project_id" \
    "$effective_task_id" \
    "$task_dir" \
    "${commit_done:-unknown}" \
    "${next_action:-none}" \
    "$effective_blocker" \
    "${verify:-none}" \
    "$log_file" \
    "$command_exit_code" \
    "$agent_command_string"

  if [[ "$command_exit_code" -ne 0 ]]; then
    log "Iteration $iteration command exit code: $command_exit_code"
  fi

  if [[ "$effective_status" != "CONTINUE" ]]; then
    log "Loop finished with final status: $effective_status"
    exit "$(status_exit_code "$effective_status")"
  fi

  if [[ "$sleep_seconds" -gt 0 ]]; then
    log "Sleeping $sleep_seconds seconds before the next iteration"
    sleep "$sleep_seconds"
  fi

  iteration=$((iteration + 1))
done

fail "Loop exited unexpectedly without reaching a terminal status"
