# Mu-Silicium für das Fairphone 5

Patches gegen Mu-Silicium `cc64daf0e05b7533995e4fd01e0f5043ec26c137` (Branch `fp5`).

| Patch | Inhalt |
|---|---|
| 0001 | SEC reicht das ABL-Einsprungsargument (x0 = FDT-Zeiger) als GUID-HOB `DAEE82E6-8090-4E72-BFB9-78C13CD4E359` weiter (für UniXNURamDiskDxe). |
| 0002 | `Platforms/Fairphone/fp5Pkg` + `Resources/Configs/fp5.toml`. |

## Anwenden

```sh
git clone https://github.com/Project-Silicium/Mu-Silicium && cd Mu-Silicium
git checkout cc64daf0e05b7533995e4fd01e0f5043ec26c137 -b fp5
git am --keep-cr /pfad/zu/UniXNU-FP5/mu-silicium/patches/*.patch   # Mu-Silicium nutzt CRLF
```

## Proprietäre Treiber (nicht im Repo)

Die Qualcomm-DXE-Treiber stammen aus dem Stock-`xbl.elf` und dürfen nicht weitergegeben werden.
Sie werden lokal erzeugt:

```sh
python3 scripts/extract-fp5-xbl-uefi.py <factory>/images/xbl.elf -o out/fp5-uefi-inputs/xbl-fv
python3 scripts/gen-fp5-mu-binaries.py out/fp5-uefi-inputs/xbl-fv/inventory.json -o <Mu-Silicium>/Binaries-fp5
```

`Binaries-fp5/` gehört in `.git/info/exclude` des Mu-Silicium-Checkouts.

## Stand / offene Punkte

- **Gebaut (2026-11-22), nicht auf Hardware getestet.** `python3 build_uefi.py -d fp5 -r DEBUG` → `Mu-fp5.img`
  (Android-Boot-Header v1, FD 0x200000 Bytes, DTB = `vendor_boot` DTB 16 „YUPIK-IOT“ aus der VT32-Analyse, lokal nach
  `Resources/DTBs/fp5.dtb` kompiliert und nicht im Repo).
  Lokale Prüfsummen: `noot.img` c185eb2b…2158, `SILICIUM_UEFI.fd` d9f48dcd…8b68 (Stand ohne UniXNU-Module).
- Build-Abhängigkeiten: nasm, iasl (acpica-tools), mono-devel, uuid-dev, gcc-aarch64-linux-gnu, venv mit `pip-requirements.txt`.
- `build_uefi.py` verändert beim Setup Dateien im Submodul `Mu_Basecore` (Mu-eigener Ablauf, nicht Teil dieser Patches).
- FD liegt bei 0x9FD00000 (2 MiB); 0x9FC00000–0x9FD00000 bleibt „FD Reserved“ (Stock-FD im RAM, wie bei lisa).
- Framebuffer 1224×2700 ist eine Annahme und nicht gegen den ABL-Framebuffer geprüft.
- TzDxeLA ist ungepatcht (lisa nutzt eine gepatchte Variante); Absturz möglich.
- Kein ProjectInfoDxe auf dem FP5, keine ACPI-Tabellen (UniXNU bootet per Device Tree).
- Boot nur per `fastboot boot` (RAM), nie flashen.
