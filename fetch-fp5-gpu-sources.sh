#!/bin/sh
set -eu

DEST=${1:-/tmp/fp5-gpu-sources}
mkdir -p "$DEST"

clone_pinned() {
	name=$1
	url=$2
	commit=$3
	path="$DEST/$name"

	if [ -e "$path" ]; then
		printf 'Refusing to overwrite existing path: %s\n' "$path" >&2
		exit 1
	fi
	git clone --filter=blob:none "$url" "$path"
	git -C "$path" -c advice.detachedHead=false checkout --detach "$commit"
}

clone_pinned Adreno740 \
	https://github.com/UniXNU/Adreno740.git \
	6fa7bae2a5b3b523e790eb3e0348af4d98969e4d
clone_pinned AdrenoPM4 \
	https://github.com/UniXNU/AdrenoPM4.git \
	282606b528b2595bc4274ea7490b62b323f35a5f
clone_pinned AdrenoFirmware \
	https://github.com/UniXNU/AdrenoFirmware.git \
	20ad3d7aca14bd46aecab6335c780f5413fa054b
clone_pinned ArmSmmu4K \
	https://github.com/UniXNU/ArmSmmu4K.git \
	83969cd874503e65997ff7639f7dcf3d0a92cd17
clone_pinned Sm8550Platform \
	https://github.com/UniXNU/UniXNU-sm8550-common.git \
	a9f45dc60c035084b95463781538380f4c3606c9

KGSL="$DEST/kgsl"
if [ -e "$KGSL" ]; then
	printf 'Refusing to overwrite existing path: %s\n' "$KGSL" >&2
	exit 1
fi
git clone --depth 1 --single-branch --branch gfx-kernel.le.0.0 \
	https://github.com/qualcomm-linux/kgsl.git "$KGSL"

printf '\nSources cloned under %s\n' "$DEST"
