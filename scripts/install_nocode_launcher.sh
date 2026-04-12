#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
用法：
  bash scripts/install_nocode_launcher.sh [--force]

说明：
  把仓库根目录下的 `nocode` 启动脚本安装到 `~/.local/bin/nocode`。
  安装完成后，可在终端直接输入 `nocode` 启动 TUI。
EOF
}

force_install="false"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "${1:-}" == "--force" ]]; then
  force_install="true"
elif [[ $# -gt 0 ]]; then
  usage >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_path="$repo_root/nocode"
target_dir="${NOCODE_BIN_DIR:-$HOME/.local/bin}"
target_path="$target_dir/nocode"

if [[ ! -f "$source_path" ]]; then
  echo "未找到启动脚本：$source_path" >&2
  exit 1
fi

mkdir -p "$target_dir"

if [[ -L "$target_path" ]]; then
  current_target="$(readlink "$target_path")"
  if [[ "$current_target" == "$source_path" ]]; then
    echo "已安装：$target_path -> $source_path"
    exit 0
  fi
fi

if [[ -e "$target_path" || -L "$target_path" ]]; then
  if [[ "$force_install" != "true" ]]; then
    echo "目标已存在：$target_path" >&2
    echo "如需替换，请重新执行：bash scripts/install_nocode_launcher.sh --force" >&2
    exit 1
  fi

  rm -f "$target_path"
fi

ln -s "$source_path" "$target_path"
echo "安装完成：$target_path -> $source_path"
