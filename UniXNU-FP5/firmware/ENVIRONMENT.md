# FP5 UEFI build environment

The port uses Mu-Silicium and its recursive submodules, plus the FP5 factory
inputs under the ignored `out/fp5-uefi-inputs/`. Fetched sources and private
firmware inputs may be kept under the ignored `out/` tree or `/tmp`; they are
not board source files and must not be committed.

## Host requirements

The upstream Mu-Silicium build guide recommends Linux and requires Git, Python
3.11+, LLVM, GNU Make, NASM, LLD and the AArch64 GCC cross compiler. The
upstream Ubuntu setup additionally installs UUID development headers and its
Python package requirements. The current host check passes with Python 3.14,
Clang, GNU Make, NASM, LLD, AArch64 GCC, UUID headers and the private
`/tmp/fp5-port/venv` environment. `llvm-objcopy`, `llvm-nm` and Mono are also
available. `scripts/install-fp5-build-deps.sh` remains available to reproduce
host setup on Debian/Ubuntu.

The source checkout is currently under `/tmp/fp5-port/`. Check the host and
source tree with:

```sh
FP5_UEFI_WORKSPACE=/tmp/fp5-port scripts/fp5-uefi-env.sh check
```

Fetch Mu-Silicium and its submodules into the ignored output directory, then
install its Python requirements in a private virtual environment:

```sh
FP5_UEFI_WORKSPACE=/tmp/fp5-port scripts/fp5-uefi-env.sh fetch
FP5_UEFI_WORKSPACE=/tmp/fp5-port scripts/fp5-uefi-env.sh install-python
```

Mu-Silicium itself was cloned with its recursive submodules. Its reference
`build_uefi.py -d lisa -r DEBUG` compiled the BootShim but then failed to
download three SDE artifacts (OneCrypto, the Mu BaseTools release archive and
Mu NASM NuGet package) because package-host DNS resolution is unavailable. The
separate pinned Mu BaseTools checkout has its C tools built locally; this does
not replace the release artifacts expected by Mu's SDE build flow.

To isolate the EDK toolchain from those SDE downloads, Mu's nested BaseTools C
utilities were also built locally and the `lisa` reference DSC was built
directly with `CLANGPDB`, explicit `lisa` FD defines and `ENABLE_SECUREBOOT=0`.
It produced a 2-MiB reference FD. This confirms local EDK compilation and FV
generation, not an FP5 firmware build. The generated tree is under the ignored
Mu checkout in `/tmp`; no vendor source was modified.

## FP5 inputs already staged

`out/fp5-uefi-inputs/manifest.json` records the VT32 factory archive member,
size and SHA-256 for `xbl.elf`, `abl.elf`, `uefi_sec.mbn`, `imagefv.elf`,
`xbl_config.elf` and `devcfg.mbn`. These are VT32 reference binaries. Mu's
BaseTools C utilities have been built, and its FMMT parser decoded the ABL and
imagefv FV structure. The XBL FV header and address are known, but FMMT cannot
expand its compressed section without an external GUID-tool mapping. No
verified reusable FP5 DXE-driver set has been extracted. Keep VT32 facts
labeled as reference until compared with the user's VT31 device.

## Not build-ready yet

The Mu-Silicium checkout is now present at `/tmp/fp5-port/Mu-Silicium`, but its
device status and platform tree contain no FP5 package. `board.toml` therefore
has no real Mu device config, DSC or FD output path. The FD base and size must
come from a verified boot flow and usable-memory map before the build can be
configured. Do not substitute the ABL entry point or Android kernel load
offsets for the UEFI FD address. The staged VT32 ABL ELF has entry
`0x9fa00000`; this is not an FD address. The adjacent XBL ELF load map overlaps
the generic `lisa` FD candidate, but does not show whether XBL memory is
released before the RAM boot.

The upstream `build_uefi.py` flow expects a Mu device package containing
`DeviceBuild.py` and a matching `Resources/Configs/<codename>.toml`; it
coordinates the BootShim, EDK build, and image packaging. UniXNU's firmware
backend instead invokes EDK's `build -p <DSC>` directly and its own `bootimg`
step handles the temporary Android image. The two flows may share the FD
output, but this has not been exercised against an actual Mu checkout. To use
Mu through UniXNU, the FP5 platform DSC/FDF and UniXNU board's firmware fields
must first be completed and their generated FD verified to match the configured
base and size.

Source review found and fixed one concrete UniXNU/Mu integration mismatch:
Mu-Silicium's public `BootShim.S` writes `(FD_BASE, FD_SIZE)` into the ARM64
image header and copies exactly `FD_SIZE` bytes from `_Payload`. UniXNU's
packager had expected the second header value to include the shim length, which
would reject Mu's own shim. The packager now checks the upstream contract.

For Android image packaging, the U-Boot Qualcomm guide contains an FP5-specific
example using a v2 header, a separate DTB section, 4-KiB pages and
`kernel_offset=0x8000`, `dtb_offset=0x1f00000`. This is evidence that FP5 can use
the v2 format in that published workflow. Separately, the FP5 recovery device
tree publishes v3 packaging parameters: base `0`, 4096-byte pages, kernel
offset `0x8000`, tags offset `0x100`, and DTB offset `0x1f00000`. These are now
recorded in `board.toml`; v3 does not encode physical kernel or standalone DTB
load addresses in the boot header. Its instructions use `fastboot boot` for
the recovery image. The U-Boot v2 example omits the load-address base, so it
does **not** resolve a safe FP5 DTB destination. The stock FP5 boot image's v3
format places DTB in `vendor_boot`, whereas v2 carries DTB in `boot.img`.

UniXNU's image packer now supports both arrangements: it preserves the existing
appended-DTB path for other headers and emits/verifies the distinct DTB section
for header v2. It requires an explicit base for v2 images because the general
Android tool default is not a verified FP5 load address. The current FP5 board
uses v3 based on the stock image and public FP5 recovery build configuration.
See the
[AOSP boot-image v2 layout](https://source.android.com/docs/core/architecture/bootloader/boot-image-header#version-2)
and the [FP5-specific U-Boot example](https://docs.u-boot.org/en/stable/board/qualcomm/board.html).

The Fairphone community has publicly reported successful FP5 RAM boots of
TWRP using `fastboot boot`, including a test of `fastboot boot boot.img` that
reached TWRP 3.7.1. This confirms the general one-shot boot mechanism on some
FP5 setups. It does not establish that ABL accepts our UEFI image or that the
current image header/load contract is correct. No public FP5 Mu-Silicium or
UniXNU boot was found; see the [FP5 TWRP report](https://forum.fairphone.com/t/twrp-for-fairphone-5/99368?page=2).

The attempted `./unixnu build firmware --uefi ... -D UniXNU-FP5` currently
stops at the repository guard (`example = true`), before compilation. Removing
that guard would still not produce valid FP5 firmware: no FP5 DSC/FDF package
exists, Mu's SDE artifacts are not all available locally, and the FD base and
size have not been established from an FP5 boot-time memory map.

This environment targets the one-shot Android boot-image path. It does not
require creating or flashing a UEFI partition.

## References

- [Mu-Silicium build guide](https://github.com/Project-Silicium/Mu-Silicium/blob/main/Building.md)
- [Mu-Silicium upstream environment setup](https://github.com/Project-Silicium/Mu-Silicium/blob/main/setup_env.sh)
- [FP5 UEFI port notes](PORTING.md)
- [FP5 memory map and confidence labels](../../../docs/porting/fp5-memory-map.md)
