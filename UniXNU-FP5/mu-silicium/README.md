# Mu-Silicium für das Fairphone 5

Patches gegen Mu-Silicium `cc64daf0e05b7533995e4fd01e0f5043ec26c137` (Branch `fp5`).

| Patch | Inhalt |
|---|---|
| 0001 | SEC reicht das ABL-Einsprungsargument (x0 = FDT-Zeiger) als GUID-HOB `DAEE82E6-8090-4E72-BFB9-78C13CD4E359` weiter (für UniXNURamDiskDxe). |
| 0002 | `Platforms/Fairphone/fp5Pkg` + `Resources/Configs/fp5.toml`. |
| 0003 | `fp5.dsc`: im `!ifdef UNIXNU`-Block die LibraryClasses `UniXNULib` (UniXNUPkg) und `FdtLib` (MdePkg/BaseFdtLib) eintragen; nötig für den Build mit `BLD_*_UNIXNU=1`. |
| 0004 | `Resources/Configs/fp5.toml`: Boot-Image-Header v3 statt v1 (wie FP5-Stock-`boot.img` und Mu-`spacewar`, gleicher Kodiak-SoC); passt zu `board.toml [bootimg.image] header_version = 3`. |
| 0005 | `fp5.dsc`/`MemoryMapLib.c`: optionale Diagnose-Schalter `FB_DELAY` (Pause pro Framebuffer-Logzeile) und `DXE_HEAP_HIGH` (DXE Heap bei 0xE3400000 wie spacewar). Standard-Build unverändert. |
| 0006 | `Include/APRIORI.inc`/`DXE.inc`: optionaler Schalter `NO_TZDXE` lässt `TzDxeLA` weg (Video zeigt `ASSERT_EFI_ERROR (Out of Resources)` direkt nach dem Laden von TzDxeLA). Standard-Build unverändert. |

## Tools

- `tools/build-boot-diag.sh`: baut boot_a..d (siehe unten). `tools/mkboot-diag.py`: packt ein FD zum boot.img. `tools/extract-fp5-dtb.py`: DTB aus vendor_boot.img.
- `tools/patch-tzdxe.py <Binaries-fp5>`: erzeugt `TzDxeLA.patched.efi` (1 Byte, wie spacewar-Patch von N1kroks)
  und lässt die INF darauf zeigen. Vor dem Build ausführen. Original bleibt unverändert; Binärdateien nicht committen.

## Anwenden

```sh
git clone https://github.com/Project-Silicium/Mu-Silicium && cd Mu-Silicium
git checkout cc64daf0e05b7533995e4fd01e0f5043ec26c137 -b fp5
git am --keep-cr /pfad/zu/UniXNU-FP5/mu-silicium/patches/*.patch   # Mu-Silicium nutzt CRLF
```

## boot_a..d selbst bauen (Debian/Ubuntu, Python ≥ 3.11)

Getestet in der Build-VM (Debian 12, clang 14), nicht auf Hardware. Benötigt die eigene FP5-Factory-ZIP
(gleiche Version wie der Bootloader am Gerät, hier VT31); daraus kommen Binaries-fp5 und DTB.

```sh
# 1. Werkzeuge
sudo apt-get install -y git python3-venv nasm acpica-tools mono-devel uuid-dev gcc-aarch64-linux-gnu \
    clang-14 lld-14 llvm-14 device-tree-compiler unzip
export CLANG_BIN=/usr/lib/llvm-14/bin/ PATH=/usr/lib/llvm-14/bin:$PATH

# 2. Repos
mkdir -p ~/fp5 && cd ~/fp5
git clone https://github.com/JoniG59/uniXNU-FP5.git
git clone https://github.com/Project-Silicium/Mu-Silicium.git && cd Mu-Silicium
git checkout cc64daf0e05b7533995e4fd01e0f5043ec26c137 -b fp5
git submodule update --init --recursive
git -c user.name=fp5 -c user.email=fp5@localhost am --keep-cr ../uniXNU-FP5/UniXNU-FP5/mu-silicium/patches/*.patch
printf '/Binaries-fp5/\n/Resources/DTBs/fp5.dtb\n' >> .git/info/exclude
python3 -m venv ../venv && ../venv/bin/pip install -r pip-requirements.txt
cd ../uniXNU-FP5

# 3. Proprietäre Teile aus der Factory-ZIP (bleiben lokal)
python3 scripts/extract-fp5-uefi-inputs.py ~/Downloads/FP5-VT31-factory.zip
python3 scripts/extract-fp5-xbl-uefi.py out/fp5-uefi-inputs/xbl.elf -o out/fp5-uefi-inputs/xbl-fv
python3 scripts/gen-fp5-mu-binaries.py out/fp5-uefi-inputs/xbl-fv/inventory.json -o ../Mu-Silicium/Binaries-fp5
unzip -p ~/Downloads/FP5-VT31-factory.zip '*/images/vendor_boot.img' > out/vendor_boot.img
python3 UniXNU-FP5/mu-silicium/tools/extract-fp5-dtb.py out/vendor_boot.img -o ../Mu-Silicium/Resources/DTBs/fp5.dtb

# 4. Einmal Mu-Setup (Stuart setup/update + Mu_Basecore-Patches); baut nebenbei Mu-fp5.img
(cd ../Mu-Silicium && source ../venv/bin/activate && python3 build_uefi.py -d fp5 -r DEBUG)

# 5. boot_a..d bauen -> out/fp5-mu/boot/boot_{a,b,c,d}.img + SHA256SUMS
MU=../Mu-Silicium VENV=../venv UniXNU-FP5/mu-silicium/tools/build-boot-diag.sh a b c d

# 6. Nur in den RAM laden, nie flashen
fastboot boot out/fp5-mu/boot/boot_b.img
```

- `build-boot-diag.sh` patcht TzDxeLA (`patch-tzdxe.py`, prüft die SHA256 des Originals), baut je Variante das FD
  mit `FB_DELAY=150000` (c: `UNIXNU=1`, d: `DXE_HEAP_HIGH=1`) und packt mit `tools/mkboot-diag.py` (b: Header v1).
  Jedes Image wird zurückgeprüft (FD + DTB im Kernel).
- Die FDs sind nicht bit-reproduzierbar (ca. 80 Byte Unterschied zwischen zwei Builds, vermutlich Zeitstempel),
  daher weichen die SHA256 von den VM-Builds ab.
- DTB 1:1 aus `vendor_boot.img` kopieren, nicht über dtc (dts → dtb) laufen lassen: dtc macht aus
  `qcom,init-voltage = "\02K"` die falschen Bytes `02 4b 00` statt `00 32 4b 00`.

## Proprietäre Treiber (nicht im Repo)

Die Qualcomm-DXE-Treiber stammen aus dem Stock-`xbl.elf` und dürfen nicht weitergegeben werden.
Sie werden lokal erzeugt:

```sh
python3 scripts/extract-fp5-xbl-uefi.py <factory>/images/xbl.elf -o out/fp5-uefi-inputs/xbl-fv
python3 scripts/gen-fp5-mu-binaries.py out/fp5-uefi-inputs/xbl-fv/inventory.json -o <Mu-Silicium>/Binaries-fp5
```

`Binaries-fp5/` gehört in `.git/info/exclude` des Mu-Silicium-Checkouts.

## Stand / offene Punkte

- **Erster Hardware-Bericht (2026-11-22):** `boot-unixnu.img` zeigt ca. 1 s Log, danach schwarzer Bildschirm.
  Patch 0005 fügt Diagnose-Schalter hinzu (`BLD_*_FB_DELAY=<µs>`, `BLD_*_DXE_HEAP_HIGH=1`); Diagnose-Images und
  Testplan: `docs/devices/fp5-diag-test.md`. Ohne die Schalter ist der Build unverändert.
- **UniXNU-Build (2026-11-22), nicht auf Hardware getestet.** FD mit `BLD_*_UNIXNU=1` (UniXNU, UniXNUDxe,
  UniXNURamDiskDxe, DarwinBoot), gepackt mit `scripts/unixnu/bootimg.py` → `out/fp5-mu/boot-unixnu.img`
  (Header v3, gzip(BootShim+FD)+DTB, leere Ramdisk). Enthält **keinen** XNU-Kernel und kein iOS.
- **Erster Build ohne UniXNU (2026-11-22), nicht auf Hardware getestet.** `python3 build_uefi.py -d fp5 -r DEBUG` → `Mu-fp5.img`
  (damals Android-Boot-Header v1, seit Patch 0004 v3; FD 0x200000 Bytes, DTB = `vendor_boot` DTB 16 „YUPIK-IOT“ aus der VT32-Analyse, lokal nach
  `Resources/DTBs/fp5.dtb` kompiliert und nicht im Repo).
  Lokale Prüfsummen: `noot.img` c185eb2b…2158, `SILICIUM_UEFI.fd` d9f48dcd…8b68 (Stand ohne UniXNU-Module).
- Build-Abhängigkeiten: nasm, iasl (acpica-tools), mono-devel, uuid-dev, gcc-aarch64-linux-gnu, venv mit `pip-requirements.txt`.
- `build_uefi.py` verändert beim Setup Dateien im Submodul `Mu_Basecore` (Mu-eigener Ablauf, nicht Teil dieser Patches).
- FD liegt bei 0x9FD00000 (2 MiB); 0x9FC00000–0x9FD00000 bleibt „FD Reserved“ (Stock-FD im RAM, wie bei lisa).
- Framebuffer 1224×2700 ist eine Annahme und nicht gegen den ABL-Framebuffer geprüft.
- TzDxeLA ist ungepatcht (lisa nutzt eine gepatchte Variante); Absturz möglich.
- Kein ProjectInfoDxe auf dem FP5, keine ACPI-Tabellen (UniXNU bootet per Device Tree).
- Boot nur per `fastboot boot` (RAM), nie flashen.
