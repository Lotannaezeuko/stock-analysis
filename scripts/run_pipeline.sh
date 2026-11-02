#!/bin/bash
# Wrapper for cron. cron runs jobs with a minimal environment from $HOME, so
# move to the repo and use the project's virtualenv explicitly.
# Usage: scripts/run_pipeline.sh [SYMBOL ...]
set -euo pipefail

cd "$(dirname "$0")/.."
exec .venv/bin/python -m pipeline.run "$@"
