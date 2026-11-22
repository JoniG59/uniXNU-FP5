#!/usr/bin/env python3
"""Compare device trees of two FP5 factory packages (read-only).

Splits the DTB section of each vendor_boot.img (header v3/v4) and the entries
of each dtbo.img, matches them by index, and compares the decompiled DTS text
(via `dtc -I dtb -O dts -s`). Prints which entries are identical, which differ
and the qcom,msm-id/board-id of every differing entry. Nothing is written back
to the images.

Usage: compare-fp5-factory-dt.py OLD_IMAGES_DIR NEW_IMAGES_DIR [-o OUTDIR]
"""
import argparse
import difflib
import struct
import subprocess
import sys
from pathlib import Path


def vendor_boot_dtbs(path):
    d = path.read_bytes()
    if d[:8] != b"VNDRBOOT":
        sys.exit(f"{path}: not a vendor_boot image")
    version, page = struct.unpack_from("<II", d, 8)
    ramdisk_size = struct.unpack_from("<I", d, 24)[0]
    header_size, dtb_size = struct.unpack_from("<II", d, 2048 + 28 + 4 + 16)
    pages = lambda n: (n + page - 1) // page * page
    off = pages(header_size) + pages(ramdisk_size)
    blob, dtbs, o = d[off:off + dtb_size], [], 0
    while o + 8 <= len(blob) and blob[o:o + 4] == b"\xd0\x0d\xfe\xed":
        size = struct.unpack_from(">I", blob, o + 4)[0]
        dtbs.append(blob[o:o + size])
        o += size
    return version, dtbs


def dtbo_entries(path):
    b = path.read_bytes()
    magic, _tot, _hs, es, cnt, eoff = struct.unpack_from(">6I", b, 0)
    if magic != 0xD7B7AB1E:
        sys.exit(f"{path}: not a DTBO image")
    out = []
    for k in range(cnt):
        size, off = struct.unpack_from(">II", b, eoff + k * es)
        out.append(b[off:off + size])
    return out


def dts(blob):
    r = subprocess.run(["dtc", "-q", "-I", "dtb", "-O", "dts", "-s", "-"], input=blob,
                       capture_output=True, check=True)
    return r.stdout.decode(errors="replace")


def ident(text):
    keys = ("model =", "qcom,msm-id =", "qcom,board-id =")
    found = []
    for line in text.splitlines()[:40]:
        s = line.strip()
        if s.startswith(keys):
            found.append(s.rstrip(";"))
    return "; ".join(found[:3])


def compare(kind, old, new, outdir):
    print(f"\n== {kind}: old {len(old)} entries, new {len(new)} entries")
    same = 0
    for i in range(max(len(old), len(new))):
        if i >= len(old) or i >= len(new):
            print(f"  [{i}] only in {'new' if i >= len(old) else 'old'}")
            continue
        if old[i] == new[i]:
            same += 1
            continue
        a, b = dts(old[i]), dts(new[i])
        if a == b:
            same += 1
            continue
        diff = list(difflib.unified_diff(a.splitlines(), b.splitlines(), "old", "new", lineterm="", n=1))
        changed = sum(1 for x in diff if x[:1] in "+-" and x[:3] not in ("+++", "---"))
        print(f"  [{i}] DIFFERENT ({changed} changed lines)  {ident(b)}")
        if outdir:
            (outdir / f"{kind}_{i}.diff").write_text("\n".join(diff) + "\n")
    print(f"  identical (binary or DTS): {same}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    outdir = Path(a.out) if a.out else None
    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)
    vo, old_dtbs = vendor_boot_dtbs(Path(a.old) / "vendor_boot.img")
    vn, new_dtbs = vendor_boot_dtbs(Path(a.new) / "vendor_boot.img")
    print(f"vendor_boot header: old v{vo}, new v{vn}")
    compare("vendor_boot_dtb", old_dtbs, new_dtbs, outdir)
    compare("dtbo", dtbo_entries(Path(a.old) / "dtbo.img"), dtbo_entries(Path(a.new) / "dtbo.img"), outdir)


if __name__ == "__main__":
    main()
