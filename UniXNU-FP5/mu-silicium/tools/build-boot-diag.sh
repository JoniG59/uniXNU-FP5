#!/usr/bin/env bash
# Baut die FP5-Diagnose-Images boot_a..boot_d (nur für "fastboot boot", nie flashen).
#   a = Mu ohne UniXNU, Header v3      b = wie a, Header v1
#   c = Mu mit UniXNU, Header v3       d = Mu ohne UniXNU, DXE-Heap 0xE3400000, Header v3
# Alle: TzDxeLA mit 1-Byte-Patch (patch-tzdxe.py), FB_DELAY=150000 (0,15 s pro Logzeile).
#
# Aufruf:  MU=/pfad/Mu-Silicium [VENV=/pfad/venv] [CLANG_BIN=/usr/lib/llvm-14/bin/] \
#          [DTB=<Mu>/Resources/DTBs/fp5.dtb] [OUT=<repo>/out/fp5-mu/boot] build-boot-diag.sh [a b c d]
# Voraussetzung: Mu-Patches 0001-0006 angewendet, Binaries-fp5 erzeugt, einmal
# "python3 build_uefi.py -d fp5 -r DEBUG" gelaufen (Stuart-Setup + Mu_Basecore-Patches).
set -euo pipefail

TOOLS=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(cd "$TOOLS/../../.." && pwd)
: "${MU:?MU=<Mu-Silicium-Checkout> setzen}"
MU=$(cd "$MU" && pwd)
DTB=${DTB:-$MU/Resources/DTBs/fp5.dtb}
OUT=${OUT:-$REPO/out/fp5-mu/boot}
VARIANTS=("${@:-a b c d}")
read -r -a VARIANTS <<< "${VARIANTS[*]}"

die() { echo "FEHLER: $*" >&2; exit 1; }
[[ -n "${VENV:-}" ]] && source "$VENV/bin/activate"
[[ -f "$MU/Platforms/Fairphone/fp5Pkg/DeviceBuild.py" ]] || die "fp5Pkg fehlt in $MU (Patches 0001-0006 mit git am --keep-cr anwenden)"
grep -q NO_TZDXE "$MU/Platforms/Fairphone/fp5Pkg/Include/APRIORI.inc" || die "Mu-Patch 0006 fehlt"
grep -q FB_DELAY "$MU/Platforms/Fairphone/fp5Pkg/fp5.dsc" || die "Mu-Patch 0005 fehlt"
[[ -d "$MU/Binaries-fp5/QcomPkg" ]] || die "$MU/Binaries-fp5 fehlt (siehe README: Proprietäre Treiber)"
[[ -d "$MU/Build" ]] || die "Mu-Setup fehlt: einmal 'python3 build_uefi.py -d fp5 -r DEBUG' im Mu-Ordner ausführen"
[[ -f "$DTB" ]] || die "DTB fehlt: $DTB (tools/extract-fp5-dtb.py)"
python3 -c 'import edk2toolext' 2>/dev/null || die "Mu-venv nicht aktiv (VENV=... setzen)"

python3 "$TOOLS/patch-tzdxe.py" "$MU/Binaries-fp5"
export FP5_EXTRA_PACKAGES_PATH=$REPO/package:$REPO/drivers/DarwinBoot
mkdir -p "$OUT/fd"

build_fd() {  # $1 = Name, Rest = zusätzliche BLD-Defines
    local name=$1; shift
    local defs=("BLD_*_FB_DELAY=150000")
    for d in "$@"; do defs+=("BLD_*_$d"); done
    echo "== FD $name: ${defs[*]}"
    ( cd "$MU" && rm -rf Build/fp5Pkg &&
      python3 Platforms/Fairphone/fp5Pkg/DeviceBuild.py TARGET=DEBUG ENABLE_SECUREBOOT=0 \
          FD_BASE=0x9fd00000 FD_SIZE=0x200000 FD_BLOCKS=0x200 DEVICE_MODEL=0 "${defs[@]}" )
    cp "$MU/Build/fp5Pkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd" "$OUT/fd/$name.fd"
}

declare -A DONE=()
for v in "${VARIANTS[@]}"; do
    case $v in
        a|b) fd=mu;     [[ -n "${DONE[$fd]:-}" ]] || build_fd mu ;;
        c)   fd=unixnu; build_fd unixnu UNIXNU=1 ;;
        d)   fd=dxeheap; build_fd dxeheap DXE_HEAP_HIGH=1 ;;
        *)   die "unbekannte Variante: $v (a b c d)" ;;
    esac
    DONE[$fd]=1
    extra=(); [[ $v == b ]] && extra=(--v1)
    python3 "$TOOLS/mkboot-diag.py" "$MU" "$OUT/fd/$fd.fd" "$DTB" "$OUT/boot_$v.img" "${extra[@]}"
done

( cd "$OUT" && sha256sum boot_?.img > SHA256SUMS && cat SHA256SUMS )
echo "Fertig. Nur testen mit: fastboot boot $OUT/boot_<x>.img  (nie flashen)"
