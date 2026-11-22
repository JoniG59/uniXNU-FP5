# Fairphone 5 hardware notes

This page consolidates the three Abacus work folders into a project reference.
It distinguishes direct observations from conclusions drawn from the VT32
factory package. The installed device was reported as VT31 /e/OS, so VT32
details are reference data and must not be assumed to describe its boot chain.

## Confirmed project baseline

- Device: Fairphone 5 (FP5); SoC baseline: Qualcomm QCM6490 / Yupik-IOT.
- The device report identifies an 8-core CPU: four Cortex-A55 and four
  Cortex-A78 cores. The reference DTB describes eight `qcom,kryo` CPUs using
  PSCI.
- The existing device configuration is intentionally marked `example = true`.
  It is a scaffold, not a bootable configuration.
- A device-specific Mu-Silicium UEFI implementation and QCM6490 platform
  support are not present in these materials.

## First UniXNU device-tree pass

The SoC DTSI now records the eight CPU MPIDRs, PSCI SMC method, GICv3 ranges,
redistributor stride and 19.2 MHz timer frequency from vendor_boot DTB 16.
The FP5 board DTS identifies the board as `fairphone,fp5` and starts with only
CPU0 enabled while XNU secondary-core startup is unavailable. CPU types and
the E/P split combine the device's `cpuinfo` with the vendor DTB's CPU ordering;
confirm the mapping against the live FDT before treating it as final.

The factory DTB `/memory` entry is zero-filled, but the UniXNU board DTS now
uses the public 8-GiB reference aperture. See
[the FP5 memory map](fp5-memory-map.md) for the 6-GB variant distinction,
reservations and confidence labels. The supplied
`fp5-iomem.txt` is actually a Linux `meminfo` dump (`MemTotal: 7472228 kB`),
not `/proc/iomem`; it does not reveal physical RAM banks. The 8-GiB public
FOSDEM reference now supplies the provisional `reg` and `payload.dram_size`.
This permits reference ADT generation once the device-tree compiler is
available, but does not verify the installed phone's firmware memory map.

The public Linux FP5 DTS identifies a 1224x2700, 90 Hz BOE OLED using a
Raydium RM692E5 panel over four-lane DSI. It describes the firmware scanout as
`a8r8g8b8` with a 4896-byte stride in the `cont_splash_mem` reservation at
`0xe1000000` (35 MiB). The UniXNU board DTS now records that expected mode and
reservation. GOP still supplies the live scanout values at XNU handoff; they
must be checked against the UEFI GOP mode before relying on them.

The upstream Linux RM692E5 panel driver sets and reads brightness using the
DSI DCS large-brightness command (0–4095), so this OLED has no separate LED
backlight controller in that path. The DTS also identifies reset GPIO 44 and
the OLED VCI, VDDIO and DVDD supplies. These Linux details are hardware
references for a future native DSI path; the selected UniXNU `GopFramebuffer`
path presents through GOP and does not initialize the DSI controller or panel.

## VT32 factory package findings

The factory analysis checked image hashes and examined the VT32 package. Its
vendor boot image contains 22 concatenated DTBs; DTB 16 is the strongest
QCM6490 candidate (`qcom,yupik-iot`, `msm-id = <0x1f1 0x10000>`). Its root
memory node is a placeholder, so it does not establish the installed RAM map.

DTBO entries 32 and 63 are plausible IDP overlays for that DTB. The numeric
board ID/subtype on the installed device, PMIC matching, actual selected DTBO,
and the meaning of the reported `dtb_idx`/`dtbo_idx` remain unverified. Do not
turn either candidate overlay into the asserted board DTS without live evidence.

The VT32 GPT uses 4096-byte sectors and has a 6 GiB `super` partition. `userdata`
is a zero-size placeholder expanded during flashing. This is factory-package
layout data, not a verified partition map for the installed VT31 device. No
factory images, extracted binaries, raw partition tables, or personal device
dumps are required in this source repository.

## Device report and boot constraints

The uploaded device report says the phone was running VT31 vendor/bootloader
components and an /e/OS kernel, while the analyzed factory package is VT32.
The `fastboot getvar all` capture was made in fastbootd (`is-userspace:yes`),
so it does not confirm ABL-only bootloader behavior. Reported values include
active slot `b`, unlocked state, a 256 MiB max download size, and 96 MiB boot
partitions; preserve the active slot and treat these values as unverified until
captured from the bootloader. Never use flashing commands as a porting test.

## Public boot-image and UEFI evidence

The Fairphone/TeamWin FP5 recovery device tree publishes an Android boot
configuration with header v3, base `0`, 4096-byte pages, kernel offset
`0x8000`, tags offset `0x100`, and DTB offset `0x01f00000`. It also gives the
RAM-only `fastboot boot out/target/product/FP5/boot.img` test command. These are
image-build parameters; v3 does not carry physical load-address or standalone
DTB-address fields in `boot.img`. The stock factory image is also v3, with its
  DTB in `vendor_boot`. That recovery configuration also labels its Android
  platform `lahaina`; this legacy build setting is not used as evidence against
  the FP5 QCM6490 identity and is not copied into the UniXNU SoC configuration.

The U-Boot Qualcomm board guide separately has an FP5-specific Android
boot-image v2 example with a standalone DTB and DTB offset `0x01f00000`. The
guide currently describes its generic U-Boot target as SDM845-only; use its
FP5-specific commands as boot-image format evidence, not as evidence of a
QCM6490 U-Boot or UEFI board port. For v2, do not infer a safe physical DTB
address by adding this offset to DRAM base: that lands inside a VT32 secure
CDSP reservation.
However, the example is a flash workflow, omits the `mkbootimg --base` argument,
and does not establish that ABL accepts `fastboot boot`. FP5 community reports
and the published recovery build instructions do establish that the command
works for at least some FP5 devices, including a reported
`fastboot boot boot.img` test that reached TWRP 3.7.1. This is a one-shot RAM
boot; it does not validate our Mu/UniXNU image, all bootloader versions, or a
particular v2 DTB address. The v2 DTB address must not be inferred by adding
that offset to DRAM base: using the FOSDEM DRAM base would land inside a VT32
secure CDSP reservation.

Public FP5 community reports document successful `fastboot boot` use with
TWRP: one user resolved a USB transfer stall with an older hub, another
reported entering TWRP with the command, and a separate test explicitly says
`fastboot boot boot.img` reached TWRP 3.7.1. Thus RAM-only boot is demonstrated
for community recovery images on at least some FP5 bootloader/device states.
No public report found here demonstrates a Mu-Silicium/UniXNU image booting;
image format, load placement, UEFI initialization and XNU handoff remain to be
validated for this port.

## Open evidence needed

1. From the installed system: live FDT and memory map, plus numeric
   `/proc/device-tree/qcom,msm-id` and `qcom,board-id` values. The previously
   supplied file called `fp5-iomem.txt` is meminfo, so it does not close this.
2. Establish the installed vendor_boot/DTBO versions and identify the overlay
   selected by the boot chain.
3. Obtain bootloader-mode `fastboot getvar all` with serial numbers redacted.
4. Port and validate QCM6490 CPU startup, interrupt, timer, memory, and required
   peripheral support against device evidence.
5. Develop and validate FP5 UEFI firmware before changing the board from
   example status.
6. Compare UEFI GOP base, size, dimensions, stride and pixel format with the
   recorded splash framebuffer before enabling XNU presentation.

## External starting points

- Fairphone's [FP5 kernel source instructions](https://code.fairphone.com/projects/fairphone-5/kernel.html)
  describe the public kernel source on Gerrit branch `kernel/15/fp5` (with
  Android 14 and 13 branches also listed), built from `kernel/msm-5.4` using
  `vendor/fp5-qgki_defconfig`. The resulting artifact is a Linux `Image`, not
  an XNU kernel or a ready-made UniXNU boot image. This is the best official
  reference here for the vendor kernel configuration, source DTS files and
  platform-specific Linux changes.
- Fairphone's [ODM source page](https://code.fairphone.com/projects/fairphone-5/odm.html)
  points to Android 13/14/15 source branches and explicitly notes that the
  published ODM tree is incomplete for a standalone build because proprietary
  toolchains and components are absent. Its source is still useful for
  hardware references; proprietary blobs should not be assumed to be available
  as source.
- The [upstream FP5 DTS](https://code.googlesource.com/linux/torvalds/linux/+/7acf90feab8b009fde7def08ff2c622d0f10e99f/arch/arm64/boot/dts/qcom/qcm6490-fairphone-fp5.dts)
  records the RM692E5 panel, DSI wiring, OLED supplies and GOP framebuffer
  reservation. The [RM692E5 panel driver](https://linux.googlesource.com/linux/kernel/git/torvalds/linux/+/refs/heads/master/drivers/gpu/drm/panel/panel-raydium-rm692e5.c)
  records the 90-Hz mode and DSI DCS brightness path.
- The [U-Boot Qualcomm board guide](https://docs.u-boot.org/en/stable/board/qualcomm/board.html)
  documents the FP5-specific boot-image-v2/DTB example. Its instructions flash
  the image and its generic target is SDM845-only, so they do not prove a
  QCM6490 port or RAM-only `fastboot boot` path.
- The [Fairphone FP5 recovery device tree](https://github.com/Fairphone/android_device_fairphone_FP5/blob/android-12.1/BoardConfig.mk)
  publishes header-v3 image build parameters; the [TeamWin build instructions](https://github.com/TeamWin/android_device_fairphone_FP5)
  show the FP5 `fastboot boot` test command. These describe Android image packaging and do not establish a Mu/UniXNU firmware load address.
- The [Debian FP5 installation notes](https://wiki.debian.org/InstallingDebianOn/Fairphone/Fairphone5)
  document community Linux installs using bootloader fastboot. They are useful
  for confirming the accessible Linux bring-up path, not UEFI or one-shot boot.
- FP5 users in the [Fairphone TWRP thread](https://forum.fairphone.com/t/twrp-for-fairphone-5/99368?page=2)
  report successfully starting TWRP with `fastboot boot`, including an explicit
  `fastboot boot boot.img` test. This establishes RAM boot on some FP5 setups,
  while leaving custom firmware compatibility open.
- [Project-Silicium Mu-Silicium](https://github.com/Project-Silicium/Mu-Silicium)
  is a general Project Mu UEFI port collection. Its current
  [device status](https://github.com/Project-Silicium/Mu-Silicium/blob/main/Status.md)
  does not list FP5 or QCM6490, so it is a porting framework/reference and does
  not establish that FP5 firmware already exists.
- Luca Weiss's [initial Linux support series for Fairphone 5](https://lkml.indiana.edu/hypermail/linux/kernel/2309.2/02729.html)
  targets the QCM6490 FP5 and includes `qcm6490-fairphone-fp5.dts`. The cover
  letter explicitly says it brings up only part of the hardware; other device
  tree and driver changes were still needed. Use that board DTS and its
  companion `sc7280.dtsi` changes as references when completing the UniXNU
  description, then reconcile them against the installed live DTB and factory
  analysis. A Linux DTS is useful hardware documentation, not a drop-in UniXNU
  device tree.

The local Abacus input folders supplied the factory-image report, device
captures, and DTB/DTBO and GPT cross-checks. They are excluded from version
control because they contain large factory binaries and raw device data; this
page preserves the conclusions needed for porting.
