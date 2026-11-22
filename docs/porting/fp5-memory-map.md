# FP5 memory and MMIO map

This page records the memory layout used by the current UniXNU FP5 reference
configuration. Addresses use half-open intervals `[base, base + size)` except
where a source explicitly prints an inclusive end. `memory.toml` is the
machine-readable source record; `board.toml` and `dts/FP5.dts` carry the values
consumed by the current UniXNU build.

## Hardware variants and confidence

Fairphone has shipped both 6 GB / 128 GB and 8 GB / 256 GB FP5 variants. The
FOSDEM reference device and the uploaded device `MemTotal` (7,472,228 kB) are
consistent with the **8 GB** variant. The configured board therefore targets
that variant. Do not use its 8-GiB `/memory` range for the 6-GB SKU: the 6-GB
range and its firmware reservations still need their own reference DTS/map.
The 6-GB SKU also uses different RAM technology, so this is a real memory
variant rather than a cosmetic storage option.

The 8-GiB value is a public reference, not a live measurement of every VT31 or
VT32 phone:

| Fact | Value | Evidence class |
| --- | --- | --- |
| FP5 8-GB RAM SKU exists | 8 GB | Fairphone product specifications |
| Reference physical aperture | `0x80000000`–`0x27fffffff` inclusive (8 GiB) | FOSDEM slide showing edited `/proc/iomem` from `fairphone-fp5` |
| FP5 Android `MemTotal` | 7,472,228 kB | Uploaded device meminfo; kernel-usable pages after reservations |
| VT32 vendor DTB `/memory/reg` | zero | Bootloader placeholder; no RAM geometry encoded |
| 6-GB SKU physical aperture | not fixed here | SKU is public, but no matching iomem/live map in the inputs |

The FOSDEM dump is explicitly edited for simplicity. It proves the reference
8-GB System RAM aperture and selected MMIO resources, but does not enumerate all
memory carveouts. Fixed carveouts below come from the Fairphone VT32 DTB/DTBO;
the Linux mainline FP5 DTS is a separate cross-check. Treat VT32 firmware
reservations as reference values until matched to the installed firmware.

## Configured 8-GB DRAM range

```text
base:            0x0000000080000000
size:            0x0000000200000000  (8 GiB)
end inclusive:   0x000000027fffffff
end exclusive:   0x0000000280000000
```

The range is contiguous in the public `/proc/iomem` excerpt. `MemTotal` is not
the DRAM size: it is smaller because the OS cannot use secure, firmware, DSP,
modem, display and other reserved pages. The `reg` in `FP5.dts` and
`payload.dram_size` now use this 8-GB reference. The ADT converter needs one
contiguous range and checks that those two values agree.

## Fixed carveouts from VT32 vendor DTB 16

These entries have fixed `reg` values and lie inside the 8-GB aperture. Their
names and ranges are copied from the decompiled `vendor_boot_dtb_16.dts`; that
DTB matches the QCM6490/Yupik-IOT ID but is from the VT32 factory package, not a
live dump from the installed VT31 device.

| Interval | Size | DTB node / role | Confidence |
| --- | ---: | --- | --- |
| `0x80000000–0x80600000` | 6 MiB | `hyp`: EL2/hypervisor | VT32 DTB 16 |
| `0x80700000–0x80860000` | 1.375 MiB | `xbl_aop_mem`: XBL/AOP | VT32 DTB 16 |
| `0x80860000–0x80880000` | 128 KiB | `cmd_db` | VT32 DTB 16 |
| `0x80880000–0x80894000` | 80 KiB | `reserved_xbl_uefi` | VT32 DTB 16 |
| `0x808ff000–0x80900000` | 4 KiB | `secdata_apss` | VT32 DTB 16 |
| `0x80900000–0x80b00000` | 2 MiB | `smem` | VT32 DTB 16 |
| `0x80b00000–0x80c00000` | 1 MiB | firmware | VT32 DTB 16 |
| `0x80c00000–0x81800000` | 12 MiB | WLAN firmware | VT32 DTB 16 |
| `0x81800000–0x83600000` | 30 MiB | secure CDSP heap | VT32 DTB 16 |
| `0x86200000–0x86700000` | 5 MiB | camera firmware | VT32 DTB 16 |
| `0x86700000–0x88f00000` | 40 MiB | ADSP | VT32 DTB 16 |
| `0x88f00000–0x8ad00000` | 30 MiB | CDSP | VT32 DTB 16 |
| `0x8ad00000–0x8b200000` | 5 MiB | video firmware | VT32 DTB 16 |
| `0x8b200000–0x8b700000` | 5 MiB | CVP | VT32 DTB 16 |
| `0x8b700000–0x8b710000` | 64 KiB | IPA firmware | VT32 DTB 16 |
| `0x8b710000–0x8b71a000` | 40 KiB | IPA GSI | VT32 DTB 16 |
| `0x8b71a000–0x8b71c000` | 8 KiB | GPU microcode | VT32 DTB 16 |
| `0x8b800000–0x9ae00000` | 246 MiB | modem firmware (MPSS) | VT32 DTB 16 |
| `0x9ae00000–0x9c700000` | 25 MiB | WLAN remote processor | VT32 DTB 16 |
| `0xa9000000–0xa9200000` | 2 MiB | ramoops | VT32 DTB 16 |
| `0xc0000000–0xc5100000` | 81 MiB | removed/unavailable region | VT32 DTB 16 |
| `0xd0800000–0xd7ef7000` | 119.96 MiB | trusted VM / secure world | VT32 DTB 16 |
| `0xd7ef7000–0xd7f00000` | 36 KiB | QRTR shared memory | VT32 DTB 16 |
| `0xd7f00000–0xd7f80000` | 512 KiB | neuron shared memory 0 | VT32 DTB 16 |
| `0xd7f80000–0xd8000000` | 512 KiB | neuron shared memory 1 | VT32 DTB 16 |
| `0xe1000000–0xe3300000` | 35 MiB | continuous splash framebuffer | merged VT32 DTB 16 + DTBO 32 |
| `0xe3300000–0xe3400000` | 1 MiB | display FPS data | VT32 DTB 16 |

The current upstream [FP5 board DTS](https://github.com/torvalds/linux/blob/master/arch/arm64/boot/dts/qcom/qcm6490-fairphone-fp5.dts)
places `rmtfs_mem` at `0xf8500000–0xf8b00000` (6 MiB) and defines `cont_splash_mem`
at the same splash base/size. The analyzed VT32 vendor DTB does not encode a
fixed `rmtfs_mem` interval there. Keep this as **mainline-only reference data**,
not an asserted VT32/VT31 firmware reservation.

The upstream FP5 DTS added the `removed_mem` reservation at
`0xc0000000–0xc5100000` (81 MiB) after a Fairphone engineer reported
synchronous external aborts under high RAM use without it. This independently
supports treating the range as unavailable to the OS; its fixed address is
also present in the VT32 vendor DTB 16. See the [upstream patch and rationale](https://patchew.org/linux/20231229-fp5-reserved-mem-v1-1-87bb818f1397%40fairphone.com/).

The upstream DTS describes the expected boot scanout as 1224x2700, stride 4896,
format `a8r8g8b8`; the active pixels occupy `0xc9b580` bytes within the
`0x2300000` splash reservation. The UniXNU board DTS records this mode and
reservation. Mu-Silicium includes a generic `SimpleFbDxe` GOP provider that
uses a platform memory-map entry named `Display Reserved` plus width, height
and color-depth PCDs; for FP5, the public values provide a plausible
1224x2700x32 configuration at `0xe1000000`. Since the kernel-mode expected
stride equals the pixel width, this generic GOP layout is compatible with the
documented mode. It can reuse the bootloader's scanout if that display state
survives the one-shot boot handoff. This is a firmware-port candidate, not a
verified live GOP result; check the base, size, stride, pixel format and panel
state on the device before claiming display support.

## Dynamic reserved-memory pools

The VT32 DTB also declares size-only pools. Linux chooses physical placement at
boot; the addresses are not present in the source DTB and must not be invented.
The capacities below are pool declarations, not a claim that all pages are
permanently lost to the OS. Several are `reusable` and may back CMA or clients
on demand.

| Pool | Capacity | Alignment | Notes |
| --- | ---: | ---: | --- |
| `adsp_region` | 12 MiB | 4 MiB | reusable |
| `user_contig_region` | 16 MiB | 4 MiB | reusable |
| `qseecom_region` | 20 MiB | 4 MiB | reusable secure-service pool |
| `non_secure_display_region` | 100 MiB | 4 MiB | reusable |
| `qseecom_ta_region` | 16 MiB | 4 MiB | reusable trusted-app pool |
| `secure_display_region` | 140 MiB | 4 MiB | reusable secure display pool |
| `linux,cma` | 32 MiB | 4 MiB | default CMA |
| `mem_dump_region` | 44 MiB | unspecified | reusable dump buffer |
| `audio_cma_region` | 28 MiB | 4 MiB | reusable |
| `memshare_region` | 8 MiB | 1 MiB | `no-map` |
| `cnss_wlan_region` | 20 MiB | 4 MiB | reusable |

Do not add these capacities to the fixed-carveout total without examining
runtime allocator placement and reuse. The Linux `CmaTotal` in the supplied
meminfo is 438272 kB (~428 MiB); that runtime statistic includes more than the
32-MiB default CMA node in the factory DTB and is not a physical address map.

## MMIO: boot-relevant and public excerpt

The FOSDEM slide says its `/proc/iomem` entries were shortened with `[...]`.
The following is the visible subset, cross-checked where possible against the
VT32 vendor DTB and current Linux DTS. It is **not** a complete MMIO catalog.

| Physical interval | Device | Evidence |
| --- | --- | --- |
| `0x00100000–0x002f0000` | GCC clock controller | FOSDEM excerpt / QCM6490 DTS |
| `0x00408000–0x00409000` | IPCC mailbox | FOSDEM excerpt |
| `0x00636000–0x00637000` | GPU MX RDPM | VT32 DTB 16 |
| `0x00900000–0x00960000` | GPI DMA | FOSDEM excerpt |
| `0x00984000–0x00988000` | GENI I²C | FOSDEM excerpt |
| `0x00988000–0x00990000` | GENI I²C | FOSDEM excerpt |
| `0x00990000–0x00994000` | GENI I²C | FOSDEM excerpt |
| `0x00994000–0x00998000` | GENI UART (`serial0`) | vendor DTB 16; FOSDEM excerpt |
| `0x0099c000–0x009a0000` | GENI UART (`hsuart0`) | vendor DTB 16; FOSDEM excerpt |
| `0x009c0000–0x009c2000` | GENI QUP wrapper | FOSDEM excerpt |
| `0x03d00000–0x03d40000` | Adreno KGSL core register window | VT32 DTB 16; `qcom,chipid = 0x06030500` |
| `0x03d61000–0x03d61800` | GPU CX debug counter | VT32 DTB 16 |
| `0x03d6a000–0x03daa000` | Adreno GMU `reg` window | VT32 DTB 16; overlaps the listed KGSL SMMU range and needs source/live-tree resolution |
| `0x03d8b000–0x03d8d000` | GPU ISENSE control | VT32 DTB 16 |
| `0x03d90000–0x03d99000` | GPU clock controller (GPUCC) | VT32 DTB 16 |
| `0x03d9e000–0x03d9f000` | GPU CX misc registers | VT32 DTB 16 |
| `0x03da0000–0x03dc0000` | KGSL GPU SMMU | VT32 DTB 16; GPU and GMU IOMMU entries; overlaps GMU `reg` range |
| `0x03de0000–0x03df0000` | GPU RSCC | VT32 DTB 16 |
| `0x06900000–0x06980000` | GPU QDSS trace | VT32 DTB 16 |
| `0x0ae00000–0x0ae84000` | Qualcomm SDE / MDSS MDP registers | VT32 DTB 16; upstream FP5 DTS enables MDSS |
| `0x0ae94000–0x0ae94400` | DSI controller 0 | VT32 DTB 16; upstream FP5 DTS enables DSI |
| `0x0ae94400–0x0ae94c00` | DSI PHY 0 register window | VT32 DTB 16; upstream FP5 DTS enables the PHY |
| `0x0b220000–0x0b250000` | Yupik PDC | vendor DTB 16 |
| `0x0b290000–0x0b2a0000` | GPU GMU PDC configuration | VT32 DTB 16 |
| `0x17a00000–0x17a10000` | GICv3 distributor | vendor DTB 16 |
| `0x17a60000–0x17b60000` | GICv3 redistributor aperture | vendor DTB 16 |
| `0x17c10000–0x17c11000` | watchdog | vendor DTB 16 |
| `0x17c20000–0x17c21000` | memory-mapped architectural timer | vendor DTB 16 |
| `0x18592000–0x18593000` | CPU frequency resource | FOSDEM excerpt |
| `0x18593000–0x18594000` | CPU frequency resource | FOSDEM excerpt |

The UniXNU QCM6490 DTSI currently exports the GICv3 and architectural timer;
the UART is recorded as a follow-up because there is no QCM GENI UART XNU driver
or validated UniXNU serial binding yet. Do not map all 4 KiB pages as device
memory just because a Linux resource appears in `/proc/iomem`: each node's
register size, security state and access needs to be checked first.

## UniXNU allocation budget

`payload.dram_size = 0x200000000` describes the whole physical aperture, not
usable free memory. The current board asks DarwinBoot for a provisional
`owned_memory_size = 0x40000000` (1 GiB) contiguous initial XNU window. That is
a bring-up policy value, not a hardware carveout or a measured minimum. It
needs review once the FP5 UEFI port can report its memory map and XNU can emit
high-water diagnostics.

Indicative planning only:

- A 4-KiB-page mapping of the entire 8-GiB aperture needs about 16 MiB for leaf
  page-table pages, plus upper-level tables. 2-MiB block mappings need far
  fewer. This is an address-space sizing estimate, not a measured XNU use.
- Kernel image, early/secondary stacks, heap, page tables, payload and UEFI
  allocations must all fit in UEFI `ConventionalMemory` available to
  DarwinBoot; do not subtract Android/Linux kernel load locations from this
  map because they are not active when booting through the proposed UEFI path.
- XNU starts with CPU0 only. The seven remaining CPU nodes stay disabled until
  the XNU MPIDR/secondary-entry path is ported; this avoids claiming untested
  SMP support and reduces bootstrap stack allocations.
- The reserved-memory node list is not currently emitted by the common ADT
  converter. Firmware must preserve no-map/secure carveouts in its UEFI memory
  map; a future firmware port must verify this before it exposes conventional
  memory to DarwinBoot.

## Early-boot implementation status

Implemented in the current checkout:

1. Board DTS uses the public 8-GiB range and a matching payload size.
2. SoC DTSI includes the vendor-reference CPU affinity IDs, GICv3 ranges,
   redistributor stride, PSCI SMC method, and generic timer interrupts/frequency.
3. FP5's mixed A55/A78 topology is represented, but only CPU0 is enabled.
4. `memory.toml` records fixed reservations, dynamic pool sizes and confidence.
5. `scripts/check-fp5-memory-map.py` checks the DRAM arithmetic, board/DTS
   agreement, fixed reservation bounds/overlaps and CPU0-only bring-up policy.
6. The FP5 selects a new XNU `QCM6490` machine build target with 8 CPU slots,
   3 affinity clusters and an ARMv8.2-A baseline. The boot DTS still enables
   CPU0 only; this target does not enable or claim secondary-core startup.

The XNU target has not yet been compiled in this environment. Its FP5 board
configuration selects native-kernel staging because no matching FP5 Apple
kernelcache/Kext set is available. A first hardware boot still requires an
FP5 Mu-Silicium UEFI build, verification that its EL transition and memory map
match XNU's entry contract, and a compiled QCM6490 kernel with the selected
GIC/timer/PSCI resources. The board remains `example = true`, which permits a
kernel-only build but keeps firmware and boot-image packaging guarded. The UEFI
port scaffold and factory-input extraction workflow are recorded in
[`UniXNU-FP5/firmware/PORTING.md`](../../UniXNU-FP5/firmware/PORTING.md).

## Sources

- [FOSDEM 2024 slides, Luca Weiss, slide “How do we address anything? MMIO!”](https://archive.fosdem.org/2024/events/attachments/fosdem-2024-2234-from-phone-hardware-to-mobile-linux/slides/22077/FOSDEM_2024_-_From_phone_hardware_to_mobile_Lin_rNpTzUA.pdf): edited FP5 `/proc/iomem` excerpt; explicitly omits ranges.
- [Fairphone FP5 FAQ/specifications](https://support.fairphone.com/hc/en-us/articles/18020671537041-Fairphone-5-Frequently-Asked-Questions-FAQ): confirms 6-GB/128-GB and 8-GB/256-GB variants.
- [Fairphone Linux kernel source instructions](https://code.fairphone.com/projects/fairphone-5/kernel.html): public Android 15 kernel branch `kernel/15/fp5` and `vendor/fp5-qgki_defconfig`.
- [Linux mainline FP5 board DTS](https://github.com/torvalds/linux/blob/master/arch/arm64/boot/dts/qcom/qcm6490-fairphone-fp5.dts) and [Kodiak/QCM6490 DTSI](https://github.com/torvalds/linux/blob/master/arch/arm64/boot/dts/qcom/kodiak.dtsi): board-specific and shared device-tree cross-checks.
- Local read-only source inputs: `abacus-2/fp5_factory_analysis/dts/vendor_boot_dtb_16.dts`, `merged_dtb16_dtbo32.dts`, `reserved_memory_dtb16.txt`, and `abacus-2/mi/fp5-meminfo.txt`. Factory values are VT32 reference data.
- Local device CPU evidence: `abacus-2/dev_info/fp5-cpuinfo.txt`; `fp5-iomem.txt` is actually a copy of meminfo, not `/proc/iomem`.
