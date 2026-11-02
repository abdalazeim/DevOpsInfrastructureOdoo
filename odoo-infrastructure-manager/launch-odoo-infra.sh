#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/venv"

cd "$ROOT"
exec "$VENV/bin/python" -m app.main "$@"
