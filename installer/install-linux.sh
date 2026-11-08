#!/usr/bin/env bash
# FOSSEverything: Desktop shortcut and launcher installer for Linux
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_PATH="${SCRIPT_DIR}/FOSSEverything"

if [ ! -f "${BIN_PATH}" ]; then
    echo "[ERROR] FOSSEverything executable not found in ${SCRIPT_DIR}"
    exit 1
fi

chmod +x "${BIN_PATH}"

echo "Installing FOSSEverything desktop launcher..."
"${BIN_PATH}" --install-desktop

echo "Installation complete! FOSSEverything is now available in your application launcher."
