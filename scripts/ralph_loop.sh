#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
用法：
  bash scripts/ralph_loop.sh --project <project-id> --task <task-id> [选项] -- <agent-command...>

示例：
  bash scripts/ralph_loop.sh \
    --project repo-workflow \
    --task 2026-04-12-ralph-loop-script \
    --max-iterations 5 \
    -- codex exec "继续当前任务，按 RALPH.md 输出结构化状态"

选项：
  --project <project-id>       必填，项目编号
  --task <task-id>             必填，任务编号
  --max-iterations <n>         最大轮次，默认 5
  --sleep-seconds <n>          每轮之间休眠秒数，默认 0
  --state-file <path>          状态文件路径，默认 <task-dir>/LOOP_STATE.json
  --log-dir <path>             日志目录，默认 <task-dir>/logs/ralph-loop
  -h, --help                   显示帮助

退出码：
  0  DONE
  2  参数错误或未解析到结构化状态
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

write_state() {
  local state_path="$1"
  local updated_at="$2"
  local iteration="$3"
  local status="$4"
  local project_id="$5"
  local task_id="$6"
  local commit_done="$7"
  local next_action="$8"
  local blocker="$9"
  local verify="${10}"
  local log_file="${11}"
  local command_exit_code="${12}"
  local agent_command="${13}"

  mkdir -p "$(dirname "$state_path")"

  cat > "$state_path" <<EOF
{
  "updated_at": "$(json_escape "$updated_at")",
  "iteration": $iteration,
  "status": "$(json_escape "$status")",
  "project_id": "$(json_escape "$project_id")",
  "task_id": "$(json_escape "$task_id")",
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

project_id=""
task_id=""
max_iterations=5
sleep_seconds=0
state_file=""
log_dir=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)
      project_id="${2:-}"
      shift 2
      ;;
    --task)
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
      fail "未知参数: $1"
      ;;
  esac
done

if [[ -z "$project_id" ]]; then
  fail "缺少 --project"
fi

if [[ -z "$task_id" ]]; then
  fail "缺少 --task"
fi

if [[ $# -eq 0 ]]; then
  fail "缺少 agent 命令，请使用 -- <agent-command...>"
fi

if ! [[ "$max_iterations" =~ ^[0-9]+$ ]] || [[ "$max_iterations" -lt 1 ]]; then
  fail "--max-iterations 必须是大于 0 的整数"
fi

if ! [[ "$sleep_seconds" =~ ^[0-9]+$ ]]; then
  fail "--sleep-seconds 必须是非负整数"
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
task_dir="$repo_root/work/projects/$project_id/tasks/$task_id"
task_readme="$task_dir/README.md"
task_progress="$task_dir/PROGRESS.md"
task_result="$task_dir/RESULT.md"

for required_file in "$task_readme" "$task_progress" "$task_result"; do
  if [[ ! -f "$required_file" ]]; then
    fail "缺少任务文档: $required_file"
  fi
done

if [[ -z "$state_file" ]]; then
  state_file="$task_dir/LOOP_STATE.json"
fi

if [[ -z "$log_dir" ]]; then
  log_dir="$task_dir/logs/ralph-loop"
fi

mkdir -p "$log_dir"

agent_cmd=("$@")
agent_command_string="${agent_cmd[*]}"

iteration=1

while (( iteration <= max_iterations )); do
  timestamp="$(date '+%Y-%m-%dT%H:%M:%S%z')"
  log_file="$log_dir/$(date '+%Y%m%d-%H%M%S')-iter$(printf '%02d' "$iteration").log"

  log "开始第 $iteration / $max_iterations 轮"
  log "日志文件: ${log_file#$repo_root/}"

  set +e
  env \
    RALPH_PROJECT_ID="$project_id" \
    RALPH_TASK_ID="$task_id" \
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

  if [[ -z "$status" ]]; then
    write_state \
      "$state_file" \
      "$timestamp" \
      "$iteration" \
      "PARSE_ERROR" \
      "$project_id" \
      "$task_id" \
      "${commit_done:-unknown}" \
      "${next_action:-missing}" \
      "未解析到 STATUS: 行" \
      "${verify:-missing}" \
      "${log_file#$repo_root/}" \
      "$command_exit_code" \
      "$agent_command_string"
    fail "第 $iteration 轮未解析到 STATUS: 行，请检查 ${log_file#$repo_root/}"
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
        "$project_id" \
        "$task_id" \
        "${commit_done:-unknown}" \
        "${next_action:-invalid}" \
        "未知状态: $status" \
        "${verify:-missing}" \
        "${log_file#$repo_root/}" \
        "$command_exit_code" \
        "$agent_command_string"
      fail "第 $iteration 轮返回了未知状态: $status"
      ;;
  esac

  if [[ -n "$output_project_id" && "$output_project_id" != "$project_id" ]]; then
    log "警告：输出中的 PROJECT_ID 为 $output_project_id，命令参数为 $project_id"
  fi

  if [[ -n "$output_task_id" && "$output_task_id" != "$task_id" ]]; then
    log "警告：输出中的 TASK_ID 为 $output_task_id，命令参数为 $task_id"
  fi

  effective_status="$status"
  effective_blocker="${blocker:-none}"

  if [[ "$status" == "CONTINUE" && "$iteration" -eq "$max_iterations" ]]; then
    effective_status="BUDGET_EXCEEDED"
    effective_blocker="达到最大轮次限制: $max_iterations"
  fi

  write_state \
    "$state_file" \
    "$timestamp" \
    "$iteration" \
    "$effective_status" \
    "$project_id" \
    "$task_id" \
    "${commit_done:-unknown}" \
    "${next_action:-none}" \
    "$effective_blocker" \
    "${verify:-none}" \
    "${log_file#$repo_root/}" \
    "$command_exit_code" \
    "$agent_command_string"

  if [[ "$command_exit_code" -ne 0 ]]; then
    log "第 $iteration 轮命令退出码: $command_exit_code"
  fi

  if [[ "$effective_status" != "CONTINUE" ]]; then
    log "循环结束，最终状态: $effective_status"
    exit "$(status_exit_code "$effective_status")"
  fi

  if [[ "$sleep_seconds" -gt 0 ]]; then
    log "休眠 $sleep_seconds 秒后继续"
    sleep "$sleep_seconds"
  fi

  iteration=$((iteration + 1))
done

fail "循环异常退出，未命中预期结束条件"
