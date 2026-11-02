#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/venv"

echo "[*] Installing system packages..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git

echo "[*] Creating virtual environment..."
python3 -m venv "$VENV"

echo "[*] Installing Python dependencies..."
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r "$ROOT/odoo-infrastructure-manager/requirements.txt" 2>/dev/null || true
cd "$ROOT"
"$VENV/bin/pip" install -e .

echo "[+] Bootstrap complete. Run: $ROOT/launch-odoo-infra.sh"
