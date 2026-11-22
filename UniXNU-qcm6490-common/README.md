# UniXNU QCM6490 support (scaffold)

Gemeinsame Basis für QCM6490-Geräte (Fairphone 5). Struktur übernommen aus
`UniXNU-sm8550-common`; **Hardwarewerte stammen nicht aus SM8550** und sind als TODO markiert.

| Pfad | Stand |
| --- | --- |
| `soc.toml` | SoC-Profil; GPU bleibt bis zu einem passenden A6xx-Kerneltreiber unselektiert |
| `configs/qcm6490.config` | leer, TODO |
| `dts/qcm6490.dtsi` | erster SoC-Basisstand: CPU-MPIDRs, PSCI, GICv3 und Timer aus dem VT32 vendor_boot-DTB 16; gegen installierten Live-DTB zu prüfen |
| `patches/xnu/qcm6490-machine-target.patch` | XNU-Bauziel mit arm64v8.2, 8 CPU-Slots und 3 Affinity-Clustern; SMP-Start und Plattformexpert bleiben aus |
| `patches/xnu/native-smp-secondary.patch` | ungeprüfter Kandidat aus SM8550; nicht in `series` aktiviert, da MPIDR-Topologie und XNU-Änderung am QCM6490 nicht validiert sind. |

Das Bauziel ist für den FP5 in `UniXNU-FP5/board.toml` als `machine_config =
"QCM6490"` ausgewählt. Es benennt die CPU-Architektur und XNU-Kompilierung;
es behauptet noch keinen hardwarefähigen XNU-Plattformtreiber. Der FP5-DTB
startet weiterhin nur CPU0. Eine native Mach-O-Ausgabe verwendet vorerst
`native_only`, da kein passender FP5-Kernelcache samt Kext-Satz vorliegt.

Referenzen für die Gerätebeschreibung: Linux-Mainline-DTS
`qcm6490-fairphone-fp5.dts` und der [ursprüngliche FP5-Upstream-Patchsatz](https://lkml.indiana.edu/hypermail/linux/kernel/2309.2/02729.html).
Der Patchsatz dokumentiert teilweise Mainline-Unterstützung und ist kein
Nachweis, dass alle FP5-Peripheriegeräte unterstützt sind.

Nicht übernommen: `kits/Sm8550Platform` (GMU, GPU-SMMU, GCC, GENI-UART, QUP-DMA) – SoC-spezifische Register/Taktquellen.

## GPU: QCM6490 / FP5

Die VT32 vendor_boot-DTB 16 enthält folgenden GPU-Pfad. Diese Werte sind
Factory-Referenzdaten und müssen gegen den Live-FP5-DTB sowie die Fuse-Werte
des Geräts geprüft werden:

| Resource | Factory-DTB-Wert |
| --- | --- |
| KGSL core | `0x03d00000`, size `0x40000`; interrupt SPI `0x12c` |
| GMU | `0x03d6a000`, size `0x34000`; HFI/GMU interrupts SPI `0x130`/`0x131` |
| GMU PDC config | `0x0b290000`, size `0x10000` |
| GPU SMMU | `0x03da0000`; GPU/GMU IOMMU entries use args `0x02`/`0x05`, mask `0x400` |
| GPU chip ID | `0x06030500`; base model string `Adreno642Lv1` |
| GPU firmware | ZAP name `a660_zap`; reserved microcode range `0x8b71a000–0x8b71c000` |

The same DTB's fuse model table contains A643v1 entries (model IDs `0xac` and
`0xbe`), while Qualcomm's QCM6490 brief names Adreno 643. Therefore the target
is an A6xx/A650-family implementation, but the FP5's selected GPU model must be
read from the live fuse cells before choosing chip-specific policy. The
Qualcomm KGSL reference groups A642L and A643 with the A650 register
specification; that is a useful bring-up reference, not a drop-in UniXNU
driver.

Do not select `Adreno740`: it is an A7xx implementation. This checkout has no
QCM6490/A6xx kernel backend. Hardware acceleration remains disabled until the
matching XNU KMD, GMU/SMMU/power integration, compatible GPU firmware, and
Turnip/Metal user path are built and qualified. The VT32 factory `vendor_a`
GMU, SQE and ZAP inputs are staged under ignored `out/fp5-gpu-inputs/`; their
hashes and factory-version warning are in `manifest.json`. They are not
committed as board sources and are not yet verified against the installed
VT31 phone.

The VT32 DTB advertises the GMU register window as `0x03d6a000 + 0x34000`,
which overlaps the KGSL SMMU's `0x03da0000 + 0x20000` window. Do not map these
regions from the current record without resolving that overlap against the
installed tree or authoritative register documentation.

Sources: local VT32 `vendor_boot_dtb_16.dts`; [Qualcomm QCM6490 brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/qcs-qcm6490-soc-product-brief_87-28733-1-b.pdf);
[Qualcomm KGSL Adreno family checks](https://github.com/qualcomm-linux/kgsl/blob/gfx-kernel.le.0.0/adreno.h)
and [A6xx register programming](https://github.com/qualcomm-linux/kgsl/blob/gfx-kernel.le.0.0/adreno_a6xx.c).
