#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
WORK=${FP5_UEFI_WORKSPACE:-"$ROOT/out/fp5-uefi-env"}
UEFI="$WORK/Mu-Silicium"
VENV="$WORK/venv"

usage() {
  cat <<'EOF'
Usage: scripts/fp5-uefi-env.sh <check|fetch|install-python>

  check           Report host tools and Mu-Silicium source readiness.
  fetch           Clone the upstream Mu-Silicium repository and all submodules.
  install-python  Install Mu-Silicium's pip requirements in a private venv.

Set FP5_UEFI_WORKSPACE to place generated files outside the repository.
This does not build firmware, flash partitions, or guess the FP5 FD address.
EOF
}

check() {
  local missing=0
  for tool in git python3 make clang nasm lld gcc aarch64-linux-gnu-gcc; do
    if command -v "$tool" >/dev/null 2>&1; then
      printf 'OK      %-8s %s\n' "$tool" "$(command -v "$tool")"
    else
      printf 'MISSING %-8s\n' "$tool"
      missing=1
    fi
  done
  python3 - <<'PY' || missing=1
import sys
print(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
if sys.version_info < (3, 11):
    raise SystemExit("Mu-Silicium requires Python 3.11 or newer")
PY
  if [[ -f /usr/include/uuid/uuid.h ]]; then
    printf 'OK      uuid development headers\n'
  else
    printf 'MISSING uuid development headers\n'
    missing=1
  fi
  if [[ -d "$UEFI/.git" ]]; then
    printf 'OK      Mu-Silicium %s\n' "$UEFI"
    git -C "$UEFI" submodule status --recursive || missing=1
    if [[ -f "$UEFI/Resources/Scripts/mkbootimg.py" ]]; then
      printf 'OK      boot image packer present\n'
    else
      printf 'MISSING Mu-Silicium boot image packer\n'
      missing=1
    fi
    if [[ -d "$VENV" ]]; then
      printf 'OK      private Python environment %s\n' "$VENV"
    else
      printf 'MISSING private Python environment (run install-python)\n'
      missing=1
    fi
  else
    printf 'MISSING Mu-Silicium source at %s (run fetch when network is available)\n' "$UEFI"
    missing=1
  fi
  return "$missing"
}

case "${1:-}" in
  check)
    check
    ;;
  fetch)
    mkdir -p "$WORK"
    if [[ -e "$UEFI" ]]; then
      echo "Refusing to overwrite existing path: $UEFI" >&2
      exit 2
    fi
    git clone --recurse-submodules https://github.com/Project-Silicium/Mu-Silicium.git "$UEFI"
    ;;
  install-python)
    [[ -f "$UEFI/pip-requirements.txt" ]] || {
      echo "Mu-Silicium source missing; run fetch first" >&2
      exit 2
    }
    python3 -m venv "$VENV"
    "$VENV/bin/python" -m pip install --upgrade pip
    "$VENV/bin/python" -m pip install -r "$UEFI/pip-requirements.txt"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
