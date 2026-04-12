#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
用法：
  bash scripts/create_project_scaffold.sh <project-id> "<project-title>"

示例：
  bash scripts/create_project_scaffold.sh repo-workflow "仓库工作流规范"
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage >&2
  exit 1
fi

project_id="$1"
project_title="${2:-$project_id}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
projects_root="$repo_root/work/projects"
template_root="$projects_root/_template"
project_path="work/projects/$project_id"
target_dir="$projects_root/$project_id"
start_date="$(date +%F)"
start_commit="$(git -C "$repo_root" rev-parse --short HEAD)"

if [[ ! -d "$template_root" ]]; then
  echo "模板目录不存在: $template_root" >&2
  exit 1
fi

if [[ -e "$target_dir" ]]; then
  echo "项目目录已存在: $target_dir" >&2
  exit 1
fi

mkdir -p "$target_dir/tasks"

render_template() {
  local template_path="$1"
  local output_path="$2"

  PROJECT_ID_VALUE="$project_id" \
  PROJECT_TITLE_VALUE="$project_title" \
  START_DATE_VALUE="$start_date" \
  START_COMMIT_VALUE="$start_commit" \
  PROJECT_PATH_VALUE="$project_path" \
  perl -0pe '
    s/\{\{PROJECT_ID\}\}/$ENV{PROJECT_ID_VALUE}/g;
    s/\{\{PROJECT_TITLE\}\}/$ENV{PROJECT_TITLE_VALUE}/g;
    s/\{\{START_DATE\}\}/$ENV{START_DATE_VALUE}/g;
    s/\{\{START_COMMIT\}\}/$ENV{START_COMMIT_VALUE}/g;
    s/\{\{PROJECT_PATH\}\}/$ENV{PROJECT_PATH_VALUE}/g;
  ' "$template_path" > "$output_path"
}

for filename in README.md STATUS.md TASK_BOARD.md; do
  render_template "$template_root/$filename" "$target_dir/$filename"
done

render_template "$template_root/tasks/README.md" "$target_dir/tasks/README.md"

echo "已创建项目档案: $project_path"
