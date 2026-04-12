#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

exec bash "$repo_root/.skills/long-task-execution/scripts/ralph_loop.sh" "$@"
