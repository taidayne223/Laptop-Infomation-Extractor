#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if command -v python3 >/dev/null 2>&1; then
  python3 -m infomation_extractor "$@"
elif command -v python >/dev/null 2>&1; then
  python -m infomation_extractor "$@"
else
  echo "Python 3 was not found. Install Python 3.10+ or add it to PATH." >&2
  exit 1
fi
