# UniXNU auf dem Fairphone 5 – Stand und nächste Schritte

Die zusammengeführten, quellenkritischen Hardwarebefunde stehen in
[`docs/porting/fp5-hardware.md`](docs/porting/fp5-hardware.md). Der VT32-Fund
ist Referenzmaterial; das gemeldete Gerät lief auf VT31 und /e/OS.

## Wichtigste Korrektur
Das Fairphone 5 hat **keinen** SM7635- und keinen SM8550-Chip, sondern den **Qualcomm QCM6490** (Kryo 670, Adreno 643; Quellen: Fairphone-Reparaturdokument, LineageOS-Gerätebaum `android_device_fairphone_FP5`).

## Was geprüft wurde (verifiziert)
- UniXNU `main` geklont (Commit 62be7bc), README und Docs gelesen (`docs/building.md`, `docs/guide/boot.md`, `docs/guide/requirements.md`, `docs/porting/device-repository.md`, `docs/porting/soc-support.md`).
- In `devices.toml` / Device-Katalog: **kein Eintrag für FP5, Fairphone oder QCM6490/SC7280**. Offizielle SoC-Repos: nur `UniXNU-sm8550-common`. Community-Ports für SM7635 (Nothing Phone 3a, Redmi Note 14 Pro+) existieren – helfen dem FP5 aber nicht direkt (anderer SoC, andere GPU).
- Kein Mu-Silicium-UEFI-Port für das FP5 gefunden (nur ein Community-Fork für das FP4).

## Was NICHT gemacht/verifiziert wurde
- Build-Toolchain nicht installiert, kein Trockenlauf gebaut (Budget erschöpft).
- **Es gibt noch kein bootfähiges Image.** Das Gerüst in `UniXNU-FP5/` ist absichtlich mit `example = true` gesperrt.

## Warum noch kein Image möglich ist
UniXNU braucht laut Doku zwingend:
1. eine **Mu-Silicium-UEFI-Firmware für das Gerät** (fehlt für FP5),
2. ein **SoC-Repo** (QCM6490 fehlt),
3. Gerätedaten: Speicherkarte, Framebuffer, Board-DTB, Partitionslayout,
4. IPSW/Kernelcache (wird per `./unixnu ipsw fetch` geladen).

## Ablauf, sobald ein Image existiert
Gebaut wird in der VM; du lädst `boot.img` herunter und startest es auf deinem Kubuntu-Rechner:
```sh
sudo apt install android-sdk-platform-tools   # liefert adb + fastboot
adb reboot bootloader
fastboot devices
fastboot boot boot.img        # startet nur im RAM, nichts wird geschrieben
```
Neustart (Power lange drücken) → /e/OS startet wieder normal.

## Risiken
- **Niemals `fastboot flash …`** (insbesondere nicht `userdata` – löscht deine Daten) und kein `fastboot flashing lock`.
- A/B-Slots nicht wechseln (`fastboot set_active` nicht verwenden).
- Bootloader-Sperren mit Custom-OS kann das Gerät unbrauchbar machen.

## Was du jetzt liefern kannst (rein lesend, ungefährlich)
```sh
adb reboot bootloader
fastboot getvar all 2>&1 | tee fp5-getvar.txt
fastboot reboot
# Mit Root/Recovery-Shell optional:
adb shell cat /proc/iomem > fp5-iomem.txt
adb shell cat /sys/firmware/fdt > fp5.dtb
```
Bitte `fp5-getvar.txt` (Seriennummer vorher schwärzen) und ggf. die anderen Dateien hochladen.

## Auswertung deiner `fastboot getvar all` (2026-11-11)
- **Wichtig:** `is-userspace:yes` → du warst in **fastbootd** (Userspace-Fastboot von Android), nicht im echten Bootloader (ABL). `fastboot boot` funktioniert **nur im Bootloader**. Darum auch `version-bootloader:unknown`.
  Wechseln: `fastboot reboot bootloader`, danach muss `fastboot getvar is-userspace` → `no` liefern.
- Gerät `FP5`, entsperrt, aktiver Slot **b** – nicht ändern.
- `first-api-level:33` → Boot-Image-Header **v4** (GKI + `vendor_boot`). Unser `boot.img` muss dazu passen.
- `boot` = 96 MiB, `max-download-size` = 256 MiB → das RAM-Boot-Image darf höchstens 256 MiB groß sein.
- UFS-Speicher (sda–sdf), userdata ≈ 214 GiB – wird vom RAM-Boot nicht berührt.
- Deine Seriennummer stand unverschwärzt in der Ausgabe – unkritisch, aber künftig vorher entfernen.

## Neu: `UniXNU-qcm6490-common` (Gerüst)
Liegt jetzt als `UniXNU-qcm6490-common/` in diesem Repo. Hardwarewerte sind
noch TODO. Der aus SM8550 übernommene SMP-Patch bleibt ein ungeprüfter
Kandidat und ist deshalb nicht in der Patch-Serie aktiviert.

## Update 2026-11-22: Stock-UEFI aus VT32-`xbl.elf` entpackt
Geändert/neu: `scripts/extract-fp5-xbl-uefi.py`, `scripts/check-fp5-uefiplat.py`,
Abschnitt `[uefi_stock_map]` in `UniXNU-FP5/memory.toml`, Abschnitt in
`UniXNU-FP5/firmware/PORTING.md`. Bestehender Inhalt unverändert.

- **Verifiziert (VT32-Datei):** Die komprimierten XBL-Sektionen sind gzip
  (GUID `1d301fe9-…`), nicht LZMA – darum scheiterte FMMT. Entpackt: 127
  FFS-Dateien, darunter 90 DXE-Treiber (UFS, Clock, PMIC, RPMh, Display, USB …)
  und die Stock-Speicherkarte `uefiplat.cfg`.
- **`UEFI FD` = `0x9fc00000`, Größe `0x300000` (3 MiB)**; `Kernel`-Bereich
  `0xa0000000`, 256 MiB; `Display Reserved` `0xe1000000`, 36 MiB.
  Prüfskript: keine Überlappungen, alles im 8-GiB-Fenster, kein Konflikt mit
  den DTB-Reservierungen.
- **Wahrscheinlich:** Panel-Konfiguration `Panel_rm692e5_boe_amoled_cmd.xml`
  (1224×2700, DSI 4 Lanes, DSC) ist das FP5-Panel.
- **Nachtrag VT31 (selber Tag):** Das offizielle `FP5-VT31-factory.zip` ist
  noch öffentlich. SHA-256 stimmt mit dem Fairphone-Wert überein. Ergebnis:
  `uefiplat.cfg`, alle DXE-Treiber, alle 22 DTBs und alle 68 DTBOs sind
  **byteidentisch** zu VT32 (Skript `scripts/compare-fp5-factory-dt.py`).
  Die VT32-Werte gelten also auch für VT31. Annahme (nicht am Gerät geprüft):
  /e/OS VT31 nutzt Fairphones VT31-Firmware.
- **Offen:** ob der FD-Bereich nach ABL-Übergabe bei `fastboot boot` frei ist.
  Ein Mu-`fp5Pkg` existiert weiterhin nicht. 6-GB-Variante hat keine eigene
  Referenz (`uefiplat.cfg` enthält keine RAM-Größe; Qualcomm-UEFI liest sie
  zur Laufzeit über DDR-Info/SMEM).

## Stand 2026-11-22: UniXNU-boot.img gebaut (ungetestet)
- **Artefakt (nur lokal, nicht im Repo):** `out/fp5-mu/boot-unixnu.img`, 1 634 304 Bytes,
  sha256 `83789ac59e34d4e098360dbc828e9c138504935ed313ef5b797ded08d0c2317e` (auch in `out/fp5-mu/SHA256SUMS`),
  `boot.json` mit `hardware_tested: false`.
- Inhalt: Android-Boot-Header **v3** (Seitengröße 4096, Header 1580 Bytes, leere Ramdisk, leere Cmdline),
  Kernel-Segment = gzip(BootShim 112 Bytes + `SILICIUM_UEFI.fd` 0x200000 Bytes, FD_BASE 0x9FD00000) + angehängte
  `fp5.dtb` (vendor_boot-DTB 16 „YUPIK-IOT“ aus VT32). Gebaut mit `scripts/unixnu/bootimg.py`, Gegenprobe mit
  `unpack_bootimg` und Byte-Vergleich (FD und DTB identisch).
- Firmware: Mu-Silicium Branch `fp5` + Patches `UniXNU-FP5/mu-silicium/patches/0001–0004`, Build mit UNIXNU=1
  (Module UniXNU, UniXNUDxe, UniXNURamDiskDxe, DarwinBoot in `Guid.xref`).
- **Warum v3:** gleiche Version wie FP5-Stock-`boot.img`/`vendor_boot.img`; Mu-`spacewar` (Nothing Phone 1,
  gleicher Kodiak-SoC) packt ebenfalls v3 + angehängte DTB. Mu-`fp5.toml` (Patch 0004) und `board.toml` sind
  jetzt einheitlich. Folge (Annahme, nicht geprüft): Bei v3 kombiniert ABL das Image mit dem **geflashten
  `vendor_boot`** des aktiven Slots (Vendor-Ramdisk, Vendor-Cmdline, ggf. dessen DTB/DTBO statt der angehängten DTB).
  Fallback, falls ABL v3 ablehnt: v1 wie Mu-`lisa` (ebenfalls Kodiak).
- `board.toml`: `[firmware]` ausgefüllt (config `fp5`, dsc, fd, packages, `UNIXNU = "1"`),
  `os_profile = "ios-16.7.16-20H392"` (Profil aus `refs/unixnu-dragon` nach `profiles/os/` kopiert; es ist für
  ein anderes Gerät geschrieben und für FP5 nicht angepasst). `example = true` bleibt.

**Ehrlich:** Das Image startet höchstens die UEFI-Umgebung. Es enthält **keinen XNU-Kernel, kein iOS, keine
Payload/Ramdisk** – iOS kann damit nicht booten. Auf Hardware ist nichts getestet.

**Risiken beim späteren Test** (nur `fastboot boot`, nie `flash`, kein Slot-Wechsel):
- ABL lehnt das Image ab oder hängt; FD-Bereich 0x9FD00000 könnte nach ABL-Übergabe belegt sein.
- Framebuffer 1224×2700 und Speicherkarte sind nicht am Gerät geprüft; TzDxeLA ungepatcht → Absturz möglich.
- Qualcomm-DXE-Treiber stammen aus dem VT32-`xbl.elf`, das Gerät läuft mit VT31-Bootloader.
- Ein Absturz in UEFI erfordert einen Neustart per Taste (Power lange drücken); Daten bleiben bei RAM-Boot
  voraussichtlich unberührt (nicht garantiert → Backup).

## Noch offen (Blocker)
1. ~~UEFI-Firmware (Mu-Silicium) für FP5/QCM6490~~ – seit 2026-11-22 als `fp5Pkg` gebaut (Patches 0001–0004), **auf Hardware ungetestet**.
1a. XNU-Kernel (QCM6490-Maschinenkonfiguration), Payload und iOS-Ramdisk fehlen noch.
2. ~~Speicherkarte~~ – seit 2026-11-22 optional: `uefiplat.cfg` (VT31 = VT32) liefert die UEFI-Karte; ein Root-Dump wäre nur noch eine Gegenprobe am Gerät (kein Root vorhanden). Ursprünglich: `adb shell su -c 'cat /proc/iomem' > fp5-iomem.txt` und `adb shell su -c 'cat /sys/firmware/fdt' > fp5.dtb`.
