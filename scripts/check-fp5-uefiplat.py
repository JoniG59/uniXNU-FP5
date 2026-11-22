#!/usr/bin/env python3
"""Cross-check the stock FP5 uefiplat.cfg memory map against UniXNU-FP5/memory.toml.

Input: uefiplat.cfg as extracted by scripts/extract-fp5-xbl-uefi.py (VT32
reference). Read-only. Reports the [MemoryMap] table, overlaps inside it,
entries outside the DRAM aperture, and whether conventional (Conv) UEFI
regions intersect fixed DTB reservations from memory.toml.
"""
import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINE = re.compile(r'^\s*(0x[0-9A-Fa-f]+)\s*,\s*(0x[0-9A-Fa-f]+)\s*,\s*"([^"]*)"\s*,\s*(.*)$')


def find_uefiplat(default_dir):
    inv = json.loads((default_dir / "inventory.json").read_text())
    for f in inv["files"]:
        if f["name"] == "uefiplat.cfg":
            return default_dir / "files" / f["blobs"][0]
    raise SystemExit("uefiplat.cfg not in inventory; run scripts/extract-fp5-xbl-uefi.py first")


def parse(text):
    section, out = None, {}
    for raw in text.replace("\r", "").splitlines():
        s = raw.strip()
        if s.startswith("[") and s.endswith("]"):
            section = s[1:-1]
            continue
        m = LINE.match(s)
        if m and section in ("MemoryMap", "RegisterMap"):
            base, size = int(m[1], 16), int(m[2], 16)
            fields = [x.strip() for x in m[4].split(",")]
            out.setdefault(section, []).append(
                {"base": base, "size": size, "end": base + size, "label": m[3].strip(),
                 "hob": fields[0], "res": fields[1], "attr": fields[2], "type": fields[3], "cache": fields[4]})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("uefiplat", nargs="?")
    ap.add_argument("--memory", default=str(ROOT / "UniXNU-FP5/memory.toml"))
    a = ap.parse_args()
    path = Path(a.uefiplat) if a.uefiplat else find_uefiplat(ROOT / "out/fp5-uefi-inputs/xbl-fv")
    cfg = parse(path.read_text(errors="replace"))
    mem = tomllib.loads(Path(a.memory).read_text())
    dbase = int(mem["dram"]["base"], 16)
    dend = dbase + int(mem["dram"]["size"], 16)
    mm = sorted(cfg["MemoryMap"], key=lambda e: e["base"])
    errors, notes = [], []

    print(f"uefiplat.cfg: {path}")
    print(f"{'base':>12} {'end(excl)':>12} {'size':>12} {'MiB':>8}  type    label")
    for e in mm:
        print(f"{e['base']:#12x} {e['end']:#12x} {e['size']:#12x} {e['size'] / 2**20:8.3f}  {e['type']:<7} {e['label']}")
    for p, q in zip(mm, mm[1:]):
        if q["base"] < p["end"]:
            errors.append(f"uefiplat overlap: {p['label']} / {q['label']}")
    for e in mm:
        if e["base"] < dbase or e["end"] > dend:
            errors.append(f"{e['label']} outside DRAM aperture")

    fixed = [(r["name"], int(r["base"], 16), int(r["base"], 16) + int(r["size"], 16))
             for r in mem.get("fixed_reservation", [])]
    for e in mm:
        if e["type"] != "Conv":
            continue
        for name, b, en in fixed:
            if b < e["end"] and e["base"] < en:
                errors.append(f"Conv region {e['label']} intersects DTB reservation {name}")

    fd = next((e for e in mm if e["label"] == "UEFI FD"), None)
    if fd:
        notes.append(f"stock 'UEFI FD' region: base {fd['base']:#x}, size {fd['size']:#x} "
                     f"({fd['size'] // 2**20} MiB), end {fd['end']:#x}")
    kern = next((e for e in mm if e["label"] == "Kernel"), None)
    if kern:
        notes.append(f"stock 'Kernel' region: {kern['base']:#x}-{kern['end']:#x} ({kern['size'] // 2**20} MiB)")
    disp = next((e for e in mm if e["label"] == "Display Reserved"), None)
    if disp:
        notes.append(f"'Display Reserved': {disp['base']:#x}-{disp['end']:#x} ({disp['size'] // 2**20} MiB)")

    for n in notes:
        print("NOTE:", n)
    for err in errors:
        print("FAIL:", err)
    if errors:
        sys.exit(1)
    print(f"PASS: {len(mm)} memory-map entries, no overlaps, inside DRAM, no Conv/DTB-reservation conflicts")


if __name__ == "__main__":
    main()
