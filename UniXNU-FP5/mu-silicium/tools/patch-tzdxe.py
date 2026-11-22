#!/usr/bin/env python3
"""Erzeugt eine gepatchte Kopie von TzDxeLA.efi für den FP5-Mu-Build.

Vorbild: Mu-Silicium spacewar (gleicher Kodiak-SoC), Patch von N1kroks:
"Die globale TZ-Applet-Variable wird von FALSE auf TRUE gesetzt", damit UEFI
beim Laden von TzDxeLA nicht abstürzt. Bei spacewar ist das genau ein Byte in
.data (RVA 0xD46C, 0x00 -> 0x01). Die FP5-Datei (VT31, BOOT.MXF.1.0-01040) hat
dieselbe Variable an derselben Adresse mit identischem Zugriffsmuster
(2x ldrb, 2x "bl init; cbnz; mov w8,#1; strb"); das prüft dieses Skript, bevor
es schreibt.

Das Original bleibt unverändert. Geschrieben wird nur
  <Binaries-fp5>/QcomPkg/Drivers/TzDxe/TzDxeLA.patched.efi
und die INF zeigt danach auf diese Kopie. Binärdateien nie committen/pushen.

Aufruf: patch-tzdxe.py <pfad/zu/Binaries-fp5> [--revert]
"""
import hashlib
import pathlib
import re
import sys

ORIG_SHA256 = "86e7e702bc12916bee504ec06aa38a3c4bf2fc7ed19f401455498c179fcc0e65"
FLAG_RVA = 0xD46C
# Befehle (little endian) an den bekannten Stellen in der FP5-Datei
EXPECTED = {
    0x3044: "c8b25139",  # ldrb w8, [x22, #0x46c]
    0x30AC: "28008052",  # mov  w8, #1
    0x30B0: "c8b21139",  # strb w8, [x22, #0x46c]
    0x3518: "c8b25139",  # ldrb w8, [x22, #0x46c]
    0x3564: "28008052",  # mov  w8, #1
    0x3568: "c8b21139",  # strb w8, [x22, #0x46c]
}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    d = pathlib.Path(sys.argv[1]) / "QcomPkg/Drivers/TzDxe"
    orig, patched, inf = d / "TzDxeLA.efi", d / "TzDxeLA.patched.efi", d / "TzDxeLA.inf"
    text = inf.read_text()
    if "--revert" in sys.argv:
        inf.write_text(re.sub(r"PE32\|TzDxeLA(\.patched)?\.efi", "PE32|TzDxeLA.efi", text))
        print("INF zeigt wieder auf das Original.")
        return 0

    data = bytearray(orig.read_bytes())
    sha = hashlib.sha256(data).hexdigest()
    if sha != ORIG_SHA256:
        print(f"FEHLER: unerwartete TzDxeLA.efi (sha256 {sha}) – nicht gepatcht.")
        return 1
    for off, hx in EXPECTED.items():
        if data[off:off + 4].hex() != hx:
            print(f"FEHLER: Befehl bei 0x{off:x} passt nicht ({data[off:off+4].hex()} != {hx}).")
            return 1
    if data[FLAG_RVA] != 0:
        print(f"FEHLER: Byte bei 0x{FLAG_RVA:x} ist nicht 0.")
        return 1
    data[FLAG_RVA] = 1
    patched.write_bytes(data)
    inf.write_text(re.sub(r"PE32\|TzDxeLA(\.patched)?\.efi", "PE32|TzDxeLA.patched.efi", text))
    print(f"OK: {patched.name} geschrieben (sha256 {hashlib.sha256(data).hexdigest()}), INF angepasst.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
