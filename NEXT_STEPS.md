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

## Noch offen (Blocker)
1. UEFI-Firmware (Mu-Silicium) für FP5/QCM6490 – existiert nicht, muss portiert werden. Ohne sie gibt es kein bootfähiges Image.
2. Speicherkarte: Bitte aus /e/OS liefern (Root nötig): `adb shell su -c 'cat /proc/iomem' > fp5-iomem.txt` und `adb shell su -c 'cat /sys/firmware/fdt' > fp5.dtb`.
