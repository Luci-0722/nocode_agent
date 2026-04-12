#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
用法：
  bash scripts/create_task_scaffold.sh <project-id> <task-id> "<task-title>"

示例：
  bash scripts/create_task_scaffold.sh reactagent-refactor 2026-04-12-acp-timeout "修复 ACP 超时处理"
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 2 || $# -gt 3 ]]; then
  usage >&2
  exit 1
fi

project_id="$1"
task_id="$2"
task_title="${3:-$task_id}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
projects_root="$repo_root/work/projects"
project_dir="$projects_root/$project_id"
tasks_root="$project_dir/tasks"
template_root="$projects_root/_template/tasks/_template"
project_path="work/projects/$project_id"
task_path="$project_path/tasks/$task_id"
target_dir="$tasks_root/$task_id"
start_date="$(date +%F)"
start_commit="$(git -C "$repo_root" rev-parse --short HEAD)"

if [[ ! -d "$project_dir" ]]; then
  echo "项目目录不存在: $project_dir" >&2
  exit 1
fi

if [[ ! -d "$template_root" ]]; then
  echo "模板目录不存在: $template_root" >&2
  exit 1
fi

if [[ -e "$target_dir" ]]; then
  echo "任务目录已存在: $target_dir" >&2
  exit 1
fi

mkdir -p "$target_dir"

render_template() {
  local template_path="$1"
  local output_path="$2"

  PROJECT_ID_VALUE="$project_id" \
  PROJECT_PATH_VALUE="$project_path" \
  TASK_ID_VALUE="$task_id" \
  TASK_TITLE_VALUE="$task_title" \
  START_DATE_VALUE="$start_date" \
  START_COMMIT_VALUE="$start_commit" \
  TASK_PATH_VALUE="$task_path" \
  perl -0pe '
    s/\{\{PROJECT_ID\}\}/$ENV{PROJECT_ID_VALUE}/g;
    s/\{\{PROJECT_PATH\}\}/$ENV{PROJECT_PATH_VALUE}/g;
    s/\{\{TASK_ID\}\}/$ENV{TASK_ID_VALUE}/g;
    s/\{\{TASK_TITLE\}\}/$ENV{TASK_TITLE_VALUE}/g;
    s/\{\{START_DATE\}\}/$ENV{START_DATE_VALUE}/g;
    s/\{\{START_COMMIT\}\}/$ENV{START_COMMIT_VALUE}/g;
    s/\{\{TASK_PATH\}\}/$ENV{TASK_PATH_VALUE}/g;
  ' "$template_path" > "$output_path"
}

for filename in README.md PROGRESS.md RESULT.md; do
  render_template "$template_root/$filename" "$target_dir/$filename"
done

echo "已创建任务档案: $task_path"
