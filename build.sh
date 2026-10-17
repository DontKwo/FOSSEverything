#!/usr/bin/env bash
# FOSSEverything — Standalone Executable / Bundle Builder for Linux and macOS
set -e

echo "============================================================"
echo "   Building FOSSEverything Standalone Executable / App Bundle..."
echo "============================================================"

# Check if uv is available, otherwise use python3
if command -v uv >/dev/null 2>&1; then
    uv run python scripts/build_executable.py "$@"
else
    python3 scripts/build_executable.py "$@"
fi
