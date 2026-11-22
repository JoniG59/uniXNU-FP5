#!/usr/bin/env bash
set -euo pipefail

# Install missing host build tools through APT and Mu Python requirements into
# a private venv. This script does not alter the system Python environment.

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
FP5_SOURCE_ROOT=${FP5_SOURCE_ROOT:-/tmp/fp5-port}
MU_DIR="$FP5_SOURCE_ROOT/Mu-Silicium"
VENV="$FP5_SOURCE_ROOT/venv"

if [[ ! -f "$MU_DIR/pip-requirements.txt" ]]; then
    echo "Mu-Silicium checkout not found at $MU_DIR" >&2
    echo "Download it with recursive submodules, then run this script again." >&2
    exit 2
fi

if ! command -v apt-get >/dev/null 2>&1; then
    echo "This installer supports Debian/Ubuntu systems with apt-get." >&2
    exit 2
fi

packages=()
command -v nasm >/dev/null 2>&1 || packages+=(nasm)
command -v lld >/dev/null 2>&1 || packages+=(lld)
command -v aarch64-linux-gnu-gcc >/dev/null 2>&1 || packages+=(gcc-aarch64-linux-gnu)
command -v llvm-objcopy >/dev/null 2>&1 || packages+=(llvm)
command -v llvm-nm >/dev/null 2>&1 || packages+=(llvm)
command -v mono >/dev/null 2>&1 || packages+=(mono-devel)
[[ -f /usr/include/uuid/uuid.h ]] || packages+=(uuid-dev)

if ((${#packages[@]})); then
    # Remove duplicate apt package names while preserving order.
    unique_packages=()
    for package in "${packages[@]}"; do
        found=false
        for existing in "${unique_packages[@]}"; do
            [[ "$existing" == "$package" ]] && found=true
        done
        [[ "$found" == true ]] || unique_packages+=("$package")
    done

    if [[ "$(id -u)" == 0 ]]; then
        apt_prefix=()
    elif command -v sudo >/dev/null 2>&1; then
        apt_prefix=(sudo)
    else
        echo "Need root or sudo to install: ${unique_packages[*]}" >&2
        exit 2
    fi

    "${apt_prefix[@]}" apt-get update
    "${apt_prefix[@]}" apt-get install -y --no-install-recommends "${unique_packages[@]}"
else
    echo "Required native build tools are already installed."
fi

python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Mu-Silicium requires Python 3.11 or newer")
print(f"Using Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
PY

if [[ ! -x "$VENV/bin/python" ]]; then
    python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install -r "$MU_DIR/pip-requirements.txt"

echo
echo "Host tools and Mu Python dependencies are ready."
echo "Private Python environment: $VENV"
echo "Recheck with: FP5_UEFI_WORKSPACE=$FP5_SOURCE_ROOT $ROOT/scripts/fp5-uefi-env.sh check"
echo "The FP5 board still needs a ported Mu DSC/FDF and a verified FD base/size before it can build."
