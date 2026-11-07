#!/usr/bin/env bash
# FOSSEverything — one-command dev install and launch (macOS / Linux).
# Installs uv if missing (uv then provisions the right Python itself), syncs
# dependencies, and runs the app. No pre-existing Python install required.
set -e

echo "============================================================"
echo "   FOSSEverything dev setup"
echo "============================================================"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found -- installing it now..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "uv installation did not put 'uv' on PATH. Open a new terminal and re-run this script."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Installing/updating dependencies with uv..."
uv sync

echo "Launching FOSSEverything..."
uv run python main.py "$@"
