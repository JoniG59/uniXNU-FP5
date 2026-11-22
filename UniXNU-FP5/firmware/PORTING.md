# FP5 Mu-Silicium port

Status: **port scaffold; no FP5 firmware volume is built yet**.

The target boot path is RAM-only: package BootShim + the Mu-Silicium FD + the
FP5 DTB into a boot image and pass it with bootloader-mode `fastboot boot`.
There is no UEFI partition requirement and no firmware flashing step. The
factory boot image is header v3 with 4-KiB pages. Public Fairphone FP5
recovery build parameters also specify v3, base `0`, kernel offset `0x8000`,
tags offset `0x100`, and DTB offset parameter `0x1f00000`; these values are
recorded in `board.toml`. Header v3 does not store physical kernel or standalone
DTB load addresses. Community TWRP builds have been reported to work with
`fastboot boot`, but the existing `fastboot getvar` capture came from
fastbootd and does not establish compatibility of this custom image or the
bootloader version on the user's phone.

## Confirmed inputs

- Public Fairphone specifications identify the FP5 platform as QCM6490.
- The VT32 factory analysis identifies `vendor_boot_dtb_16` as `qcom,yupik-iot`
  with `msm-id = <0x1f1 0x10000>`. It provides the public-reference GICv3
  distributor and redistributor ranges, eight CPU affinity IDs, PSCI SMC, and
  the 19.2 MHz architectural timer. See `../memory.toml` and
  `../../docs/porting/fp5-memory-map.md`.
- The stock boot image is Android header v3, with 4-KiB pages. Fairphone's
  public FP5 recovery device tree supplies the additional v3 packaging values
  recorded in `board.toml`; they do not supply a UEFI FD execution address.
- The Abacus-3 upload contains the complete VT32 factory ZIP. The six
  boot-firmware inputs have been extracted to the ignored
  `out/fp5-uefi-inputs/` directory; `manifest.json` records their exact source
  member, size, and SHA-256. These are **VT32 references**, not proof of the
  user's VT31 firmware revision. They are kept out of source control.
- Basic ELF inspection confirms `xbl.elf` and `devcfg.mbn` are AArch64 files;
  `abl.elf`, `uefi_sec.mbn`, and `imagefv.elf` are ARM32 containers. This is
  metadata only: no DXE/UEFI driver extraction has been performed yet.
- The factory archive is the VT32 reference package; its staged inputs are
  outside the repository under `out/fp5-uefi-inputs/`.

## Firmware ELF address audit

The staged VT32 `xbl.elf` and `abl.elf` were parsed for ELF `PT_LOAD` ranges.
ABL's entry and sole load segment begin at `0x9fa00000` and end at
`0x9fa23000`. One XBL segment spans `0x9fc00000–0x9fe71000`. The latter
intersects the `0x9fd00000–0x9ff00000` FD interval used by Mu-Silicium's Xiaomi
`lisa` config. These ELF ranges describe image load segments; they do not tell
us which pages the bootloader releases before `fastboot boot`, so they neither
prove a conflict at UEFI handoff nor prove the candidate interval is free.
Consequently the `lisa` FD base remains unsuitable as an FP5 value without a
runtime memory map.

The Mu BaseTools C utilities built successfully. Using Mu's FMMT parser on
the extracted FV headers found an XBL FV of `0x271000` bytes at
`0x9fc00000`; an ABL FV of `0x23000` bytes at `0x9fa00000` containing a
compressed child FV with a `LinuxLoader` FFS; and an `imagefv.elf` FV of
`0xd000` bytes containing UI bitmap assets. FMMT could not expand the XBL
compressed section because its GUID tool is unavailable in this environment.
The small `imagefv` asset FV is not the FP5's full reusable DXE driver set.

Reproduce the report with:

```sh
python3 scripts/audit-fp5-firmware-elves.py
```

The JSON report is written to the ignored `out/fp5-uefi-inputs/` directory.

To extract only those inputs into the ignored build tree:

```sh
python3 scripts/extract-fp5-uefi-inputs.py /path/to/FP5-factory.zip
```

The extractor writes a SHA-256 manifest and never changes or flashes the
source archive. Feed these files to UEFIReader or another firmware-volume
inspection tool when available; retain extracted drivers and their provenance
outside source control.

## XBL UEFI firmware volume (update 2026-11-22)

The compressed XBL sections are not EDK2 LZMA: their GUIDed-section GUID is
`1d301fe9-be79-4353-91c2-d23bc959ae0c` and the payload is a plain gzip stream
(`1f 8b`). `scripts/extract-fp5-xbl-uefi.py` decodes it without FMMT and walks
the FV at `0x9fc00000` (ELF phdr 8, file offset `0x93000`, size `0x271000`):

- 127 FFS files: 1 SEC core, 1 DxeCore, 90 DXE drivers, 2 applications
  (`QcomChargerApp`, `Ebl`), 31 freeform/config files, 2 nested FVs.
- Present drivers include `UFSDxe`, `ClockDxe`, `PmicDxe`, `RpmhDxe`,
  `SmemDxe`, `DisplayDxe`, `UsbfnDwc3Dxe`, `ArmGicDxe`, `ArmTimerDxe`,
  `ButtonsDxe`, `TzDxeLA`, `ScmDxeLA`, `PILDxe`, `VerifiedBootDxe`.
- `Panel_rm692e5_boe_amoled_cmd.xml` describes a 1224x2700, 4-lane DSI panel
  with DSC (slice 1224x60). This matches the public FP5 resolution and the
  Linux `raydium,rm692e5` panel; it is the strongest local panel candidate,
  but the selected panel is not device-verified.
- `uefiplat.cfg` (Version 3) is the stock UEFI memory map. Relevant entries:
  `UEFI FD` `0x9fc00000` + `0x300000`, `SEC Heap` `0x9ff00000` + `0x8c000`,
  `UEFI Stack` `0x9ff90000` + `0x40000`, `DXE Heap` (Conv) `0x9c700000` +
  `0x3100000`, `ABOOT FV` `0x9fa00000` + `0x200000`, `Kernel` `0xa0000000` +
  `0x10000000`, `Display Reserved` `0xe1000000` + `0x2400000` (splash 35 MiB
  plus the 1-MiB dfps block from DTB 16).
- `scripts/check-fp5-uefiplat.py` confirms the 26 entries do not overlap, lie
  inside the 8-GiB reference aperture and that no Conv region intersects a
  fixed DTB reservation in `memory.toml`.

Consequences: the FP5 FD candidate is now `0x9fc00000`, maximum `0x300000`
bytes (stock UEFI FD region), instead of a borrowed `lisa` value. The
`0x9fc00000–0x9fe71000` XBL load segment flagged in the ELF audit *is* this FV,
so it is the stock UEFI's own region, not an unrelated conflict. Still
unverified: that this region is free when ABL starts a `fastboot boot` image.
(The VT31 map was checked afterwards, see below.) The extracted binaries stay in the ignored
`out/fp5-uefi-inputs/xbl-fv/` tree with SHA-256 values in `inventory.json`.

### VT31 comparison (2026-11-22)

`FP5-VT31-factory.zip` was fetched from
`https://android-builds.fairphone.com/FP5/A15/FP5-VT31-factory.zip`
(3,112,038,644 bytes; SHA-256 `478bf3f246ef0a9d6a8fab279cf8dd712cb6f353e520f1977c6edbaede3880f8`,
identical to the value Fairphone published for FP5.VT31.C.114). All eight
used images passed `sha256sum -c` against the package's `SHA256SUMS`.

- The firmware files themselves differ in hash between VT31 and VT32.
- The XBL FV has the same location (`0x9fc00000`, `0x271000`) and the same
  127 FFS files. 124 files are byte-identical, including `uefiplat.cfg`
  and every DXE driver; only the SEC core and `Ebl` differ.
- `scripts/compare-fp5-factory-dt.py`: all 22 vendor_boot DTBs and all 68
  DTBO entries are byte-identical between VT31 and VT32 (DTB 16 and DTBOs
  32/55/63 additionally checked against the earlier VT32 extraction).

Therefore the memory map, FD region and DT reference values in this port
apply to the **VT31 factory package** as well. The installed /e/OS VT31 build
was not read out; it is assumed (not verified) to ship Fairphone's VT31
firmware.

## SoC package selection

The current Mu-Silicium tree has a Qualcomm `KodiakPkg`; its shipped `lisa`
platform DSC identifies the SoC as SM7325 and hard-codes SM7325 CPU marketing
data and platform settings. The FP5's public target is QCM6490/Yupik-IOT. The
uploaded runtime property reports `ro.soc.model=SM7325`, while its VT32 factory
DTB candidate identifies as QCM6490/Yupik-IOT. The selected runtime DTB/SoC ID
is not verified. `KodiakPkg` is **not accepted as an FP5 platform configuration
yet**. First compare its startup, memory map, timer, GIC, PSCI, clock and UFS
assumptions against the FP5 DTB, Fairphone sources and extracted FP5 firmware.
Do not copy another board's FD address, stack region, memory map, PMIC tables or
display settings.

Public source references: [Mu-Silicium supported-device status](https://github.com/Project-Silicium/Mu-Silicium/blob/main/Status.md),
[Mu-Silicium `lisa.dsc`](https://raw.githubusercontent.com/Project-Silicium/Mu-Silicium/main/Platforms/Xiaomi/lisaPkg/lisa.dsc),
[Mu-Silicium `KodiakPkg.dsc.inc`](https://raw.githubusercontent.com/Project-Silicium/Mu-Silicium/main/Silicon/Qualcomm/KodiakPkg/KodiakPkg.dsc.inc),
and [Mu-Silicium build instructions](https://github.com/Project-Silicium/Mu-Silicium/blob/main/Building.md).
The [QCM6490 U-Boot board page](https://docs.u-boot.org/en/stable/board/qualcomm/rb3gen2.html)
is a SoC-level reference, not an FP5 firmware configuration.

## Required implementation stages

1. Inspect the complete factory `xbl.elf`, `abl.elf`, `uefi_sec.mbn` and
   `imagefv.elf`; identify reusable signed DXE binaries and record hashes.
2. Create `fp5Pkg` with SEC/PEI entry and memory HOBs consistent with the
   Android boot shim handoff, 8-GB reference DRAM and firmware-reserved map.
   Preserve secure, modem, DSP and display carveouts in the UEFI memory map.
3. Add a QCM6490/Yupik SoC layer or prove the exact Kodiak code paths that are
   shared. Establish the EL at entry and exit, GICv3, PSCI, architectural timer,
   clocks, UFS, USB device mode and GOP before adding UniXNU modules.
4. Add the UniXNU, UniXNUDxe, DarwinBoot and initrd RAM-disk modules to the DSC
   and FDF. Confirm the incoming FDT/initrd HOB reaches `UniXNURamDiskDxe`.
5. Set the FP5 FD base and size only after deriving a safe load/execute region
   from the FP5 firmware memory map. Build and round-trip the v3 boot image,
   then verify bootloader-mode `fastboot boot` without flashing any partition.

## Current stop point

Mu-Silicium, its submodules, the active UniXNU modules and the XNU build
references are staged under `/tmp/fp5-port/`. The host dependency check now
passes, including NASM, LLD and the AArch64 GCC cross compiler. Mu's
`build_uefi.py -d lisa -r DEBUG` successfully compiled `BootShim.elf` and
`BootShim.bin`, then stopped while resolving three upstream binary
dependencies (OneCrypto, Mu-Basetools release archive and Mu NASM NuGet
package); this environment cannot resolve the package hosts. The separate,
pinned Mu BaseTools C utilities were built locally, but that does not satisfy
Mu's SDE release-artifact dependencies. The `lisa` target is only a toolchain
smoke reference and its SM7325 board configuration is not an FP5 build.

As a separate local EDK check, Mu's nested BaseTools C utilities were built
from source and the `lisa` DSC was built with the local `CLANGPDB` toolchain,
explicitly supplying the **lisa reference** FD values and disabling secure
boot. That produced a 2-MiB `SILICIUM_UEFI.fd` under the ignored Mu build tree.
It confirms the compiler, assembler, linker and FV tools can create a Mu FD;
it does not validate the Mu SDE packaging flow or any FP5 code. An initial
direct `CLANGDWARF` attempt exposed an upstream warning-as-error and unresolved
stack-check symbols; the successful `CLANGPDB` build used the toolchain Mu
selects. No Mu source changes were retained.

The factory package has no Mu source tree, and FMMT cannot expand the XBL
compressed section without its GUID-tool mapping. Most importantly, the FP5 FD
load/execute base and size remain unverified. The ELF audit shows why the
generic `lisa` base cannot be accepted as an FP5 value. No placeholder firmware
image is generated from guessed addresses. The target remains RAM-only and
requires an FP5 platform package plus a validated FD interval before a
`fastboot boot` image can be produced.

The staged `GopFramebuffer` source is an XNU-side consumer of UEFI GOP. It can
present XNU frames through a GOP framebuffer, but it does not initialize the
FP5 DSI panel. Mu already contains a generic `SimpleFbDxe` that publishes GOP
from a platform `Display Reserved` range and width/height/depth PCDs. The FP5
reference supplies a 1224x2700, 32-bit scanout in the `0xe1000000` splash
reservation, so this generic path is a plausible way to retain the
bootloader-initialized display without writing a new DSI driver. The FP5 Mu
memory map still has to preserve that reservation and configure the matching
mode; whether the scanout remains active through `fastboot boot` needs a device
check. The XNU GOP driver is useful after that firmware GOP exists, but it is
not required for the first serially observable kernel handoff.
