#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
python3 "$REPO_ROOT/sg194/bs_fix_reaudit_v1/experiment/debug_sg194_bs_fix_experiment_v1.py"
