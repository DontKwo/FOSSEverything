#!/usr/bin/env bash
# FOSSEverything: configurable launcher installer for Linux.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_PREFIX="${HOME}/.local/opt/FOSSEverything"
PREFIX="${DEFAULT_PREFIX}"
IN_PLACE=0
LINK_CLI=1
THEME=""
UI_SCALE=""
UNINSTALL=0
ASSUME_YES=0
ARGS_GIVEN=$#

usage() {
    cat <<'EOF'
Usage: ./install.sh [options]

  --prefix DIR        Copy the app to DIR (default: ~/.local/opt/FOSSEverything)
  --in-place          Do not copy; register the launcher for the current folder
  --no-cli-link       Skip the ~/.local/bin/fosseverything command
  --theme ID          First-run theme: ut_austin_dark, dark, light, solarized,
                      monokai, cyberpunk, ut_austin
  --ui-scale N        First-run interface scale, 0.5 to 2.5 (for example 1.25)
  --uninstall         Remove the launcher, menu entry, and installed copy
  -y, --yes           Never prompt; use defaults and the options above
  -h, --help          Show this help
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --prefix) PREFIX="${2:?--prefix needs a directory}"; shift 2 ;;
        --in-place) IN_PLACE=1; shift ;;
        --no-cli-link) LINK_CLI=0; shift ;;
        --theme) THEME="${2:?--theme needs an id}"; shift 2 ;;
        --ui-scale) UI_SCALE="${2:?--ui-scale needs a number}"; shift 2 ;;
        --uninstall) UNINSTALL=1; shift ;;
        -y|--yes) ASSUME_YES=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "[ERROR] Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

ask() {
    # ask "question" "default" -> echoes answer
    local reply
    read -r -p "$1 [$2]: " reply
    echo "${reply:-$2}"
}

if [ "${UNINSTALL}" -eq 1 ]; then
    for candidate in "${PREFIX}" "${SCRIPT_DIR}"; do
        if [ -x "${candidate}/FOSSEverything" ]; then
            "${candidate}/FOSSEverything" --uninstall-desktop || true
            break
        fi
    done
    rm -f "${HOME}/.local/bin/fosseverything"
    if [ -d "${PREFIX}" ] && [ "${PREFIX}" != "${SCRIPT_DIR}" ]; then
        rm -rf "${PREFIX}"
    fi
    echo "FOSSEverything removed. Preferences remain in ~/.fosseverything (delete it manually to reset)."
    exit 0
fi

if [ "${ARGS_GIVEN}" -eq 0 ] && [ "${ASSUME_YES}" -eq 0 ] && [ -t 0 ]; then
    echo "FOSSEverything setup (press Enter to accept each default)"
    if [ "$(ask 'Copy the app to a permanent folder? (y/n)' 'y')" = "y" ]; then
        PREFIX="$(ask 'Install folder' "${DEFAULT_PREFIX}")"
    else
        IN_PLACE=1
    fi
    if [ "$(ask 'Add a fosseverything command to ~/.local/bin? (y/n)' 'y')" != "y" ]; then
        LINK_CLI=0
    fi
    THEME="$(ask 'Theme (ut_austin_dark, dark, light, solarized, monokai, cyberpunk, ut_austin)' 'ut_austin_dark')"
    UI_SCALE="$(ask 'Interface scale (0.5 to 2.5)' '1.0')"
fi

if [ ! -f "${SCRIPT_DIR}/FOSSEverything" ]; then
    echo "[ERROR] FOSSEverything executable not found in ${SCRIPT_DIR}" >&2
    exit 1
fi

if [ "${IN_PLACE}" -eq 1 ]; then
    TARGET="${SCRIPT_DIR}"
else
    TARGET="${PREFIX}"
    if [ "${TARGET}" != "${SCRIPT_DIR}" ]; then
        echo "Copying files to ${TARGET}..."
        mkdir -p "${TARGET}"
        cp -a "${SCRIPT_DIR}/." "${TARGET}/"
    fi
fi

BIN_PATH="${TARGET}/FOSSEverything"
chmod +x "${BIN_PATH}"

echo "Installing FOSSEverything desktop launcher..."
"${BIN_PATH}" --install-desktop

if [ "${LINK_CLI}" -eq 1 ]; then
    mkdir -p "${HOME}/.local/bin"
    ln -sf "${BIN_PATH}" "${HOME}/.local/bin/fosseverything"
fi

CONFIGURE_ARGS=()
[ -n "${THEME}" ] && CONFIGURE_ARGS+=("--theme=${THEME}")
[ -n "${UI_SCALE}" ] && CONFIGURE_ARGS+=("--ui-scale=${UI_SCALE}")
if [ ${#CONFIGURE_ARGS[@]} -gt 0 ]; then
    "${BIN_PATH}" --configure "${CONFIGURE_ARGS[@]}" || echo "[WARN] Could not apply preferences; change them in Settings."
fi

echo "Installation complete! FOSSEverything is now available in your application launcher."
