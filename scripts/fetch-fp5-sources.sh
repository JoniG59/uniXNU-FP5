#!/usr/bin/env bash
set -euo pipefail

# Prepare public source checkouts for the offline FP5 porting workspace.
# No package installation, device access, or flashing is performed.

FP5_SOURCE_ROOT=${FP5_SOURCE_ROOT:-/tmp/fp5-port}
MU_DIR="$FP5_SOURCE_ROOT/Mu-Silicium"
EDK2_DIR="$FP5_SOURCE_ROOT/Mu_Basecore"
MODE=${1:-all}

usage() {
    cat <<'EOF'
Usage: scripts/fetch-fp5-sources.sh [firmware|all]

  firmware  Mu-Silicium (recursive submodules) and the pinned Mu_Basecore
  all       firmware sources plus active UniXNU components and XNU build refs

Sources are placed under /tmp/fp5-port by default. Set FP5_SOURCE_ROOT to
choose another destination. Existing matching Git checkouts are reused;
other existing paths are left untouched and cause an error.
EOF
}

case "$MODE" in
    firmware|all) ;;
    -h|--help|help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
esac

mkdir -p "$FP5_SOURCE_ROOT"

clone_mu() {
    if [[ -e "$MU_DIR" ]]; then
        if [[ ! -d "$MU_DIR/.git" ]]; then
            echo "Refusing to overwrite non-Git path: $MU_DIR" >&2
            return 2
        fi
        echo "Using existing Mu-Silicium checkout: $MU_DIR"
        git -C "$MU_DIR" submodule update --init --recursive --depth 1
    else
        git clone --depth 1 --recurse-submodules --shallow-submodules \
            https://github.com/Project-Silicium/Mu-Silicium.git "$MU_DIR"
    fi
}

clone_pinned() {
    local name=$1 url=$2 revision=$3 destination="$FP5_SOURCE_ROOT/$1"
    if [[ -e "$destination" ]]; then
        if [[ ! -d "$destination/.git" ]]; then
            echo "Refusing to overwrite non-Git path: $destination" >&2
            return 2
        fi
        local existing
        existing=$(git -C "$destination" rev-parse HEAD)
        if [[ "$existing" != "$revision" ]]; then
            echo "Existing $name checkout is at $existing, expected $revision: $destination" >&2
            return 2
        fi
        echo "Using pinned $name checkout: $destination"
        return 0
    fi

    git clone --filter=blob:none --no-checkout "$url" "$destination"
    git -C "$destination" fetch --depth 1 origin "$revision"
    git -C "$destination" checkout --detach "$revision"
}

clone_mu

# Reuse Mu-Silicium's Basecore submodule when it matches this workspace's pin.
EDK2_PIN=cfb93724a06ff86ff5ba971413368a7809ee42a5
if git -C "$MU_DIR/Mu_Basecore" rev-parse HEAD >/dev/null 2>&1 &&
   [[ "$(git -C "$MU_DIR/Mu_Basecore" rev-parse HEAD)" == "$EDK2_PIN" ]]; then
    EDK2_DIR="$MU_DIR/Mu_Basecore"
    echo "Mu-Silicium Mu_Basecore matches the UniXNU pin; reusing it."
else
    clone_pinned Mu_Basecore https://github.com/microsoft/mu_basecore.git "$EDK2_PIN"
    # These EDK2 submodules are required by the pinned UniXNU feed.
    git -C "$EDK2_DIR" submodule update --init --depth 1 -- \
        MdePkg/Library/BaseFdtLib/libfdt \
        MdePkg/Library/MipiSysTLib/mipisyst \
        BaseTools/Source/C/BrotliCompress/brotli \
        MdeModulePkg/Library/BrotliCustomDecompressLib/brotli \
        SecurityPkg/DeviceSecurity/SpdmLib/libspdm
fi

case "$MODE" in
    firmware)
        echo "Firmware sources ready. Mu-Silicium: $MU_DIR; EDK2: $EDK2_DIR"
        ;;
    all)
        # Active FP5 board components and their exact revisions from components.toml.
        clone_pinned ArmCpu https://github.com/UniXNU/ArmCpu.git 93a5030c5d983d0ef90f0fca93879d6e36ad1ba8
        clone_pinned ArmDTPlatform https://github.com/UniXNU/ArmDTPlatform.git 417ff95d6a6e8607ddea9309ec45c3bfd4a67c60
        clone_pinned DarwinBoot https://github.com/UniXNU/DarwinBoot.git 3c75734014cdab0acd9541e88057b7606ee7ae08
        clone_pinned SoftwareAES https://github.com/UniXNU/SoftwareAES.git 4a45326da5c2cd6fe6813d79ee43db20805628af
        clone_pinned AppleKeyStoreState https://github.com/UniXNU/AppleKeyStoreState.git 8c70daf814aafdf4a3d35e40dde0322655fd0a83
        clone_pinned RamBlock https://github.com/UniXNU/RamBlock.git 4be2d7eb05ef5a98126c91e0302c149140c0e3e1
        clone_pinned GopFramebuffer https://github.com/UniXNU/GopFramebuffer.git e47c1b8de169cd2bd0b885c7d85e433010e3cdf2
        clone_pinned XnuPrelink https://github.com/UniXNU/XnuPrelink.git c645d76bb0ab8c506a76840ddf93a2276d419a0e

        # Kernel and build-time source references from feeds.toml.
        clone_pinned xnu https://github.com/apple-oss-distributions/xnu.git d8b80295118ef25ac3a784134bcf95cd8e88109f
        clone_pinned libplatform https://github.com/apple-oss-distributions/libplatform.git a00a4cc36da2110578bcf3b8eeeeb93dcc7f4e11
        clone_pinned libdispatch https://github.com/apple-oss-distributions/libdispatch.git 30fe6a7d945340ce69cef121132f049e810089a5
        clone_pinned AvailabilityVersions https://github.com/apple-oss-distributions/AvailabilityVersions.git 933f9360f1b70dfbda5548386a3d65e0358b4f7d
        clone_pinned libpthread https://github.com/apple-oss-distributions/libpthread.git c0e60fb5ecfc54cf379c261d3f9572cc22ded891
        clone_pinned corecrypto-2023 https://github.com/ONLYA/corecrypto-2023.git 11fba65b12d8830630e248dfa8344caf8b065f26
        clone_pinned IOStorageFamily https://github.com/apple-oss-distributions/IOStorageFamily.git e45fbe30a7879e0b16e26dddb78538f1b00e0bff

        echo "All listed source checkouts are ready under $FP5_SOURCE_ROOT"
        echo "Mu-Silicium: $MU_DIR"
        echo "EDK2/Mu_Basecore: $EDK2_DIR"
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
