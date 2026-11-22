#!/usr/bin/env python3
"""Copy one DTB unchanged out of an FP5 vendor_boot.img (header v3/v4).

Default index 16 ("YUPIK-IOT"), as used for Mu-Silicium fp5. The bytes are written
1:1; do NOT round-trip through dtc (dts -> dtb), dtc turns the property
qcom,init-voltage = "\\0" "2K" "\\0" into the wrong bytes 02 4b 00.
Usage: extract-fp5-dtb.py <vendor_boot.img> -o <Mu-Silicium>/Resources/DTBs/fp5.dtb [-i 16]
"""
import argparse
import hashlib
import struct
import sys
from pathlib import Path


def vendor_boot_dtbs(data):
    if data[:8] != b'VNDRBOOT':
        sys.exit('not a vendor_boot image')
    page = struct.unpack_from('<I', data, 12)[0]
    ramdisk_size = struct.unpack_from('<I', data, 24)[0]
    header_size, dtb_size = struct.unpack_from('<II', data, 2048 + 28 + 4 + 16)
    pages = lambda n: (n + page - 1) // page * page
    off = pages(header_size) + pages(ramdisk_size)
    blob, dtbs, o = data[off:off + dtb_size], [], 0
    while o + 8 <= len(blob) and blob[o:o + 4] == b'\xd0\x0d\xfe\xed':
        size = struct.unpack_from('>I', blob, o + 4)[0]
        dtbs.append(blob[o:o + size])
        o += size
    return dtbs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('vendor_boot', type=Path)
    ap.add_argument('-o', '--out', type=Path, required=True)
    ap.add_argument('-i', '--index', type=int, default=16)
    a = ap.parse_args()
    dtbs = vendor_boot_dtbs(a.vendor_boot.read_bytes())
    if a.index >= len(dtbs):
        sys.exit(f'only {len(dtbs)} DTBs in {a.vendor_boot}')
    dtb = dtbs[a.index]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(dtb)
    print(f'{a.out}: DTB {a.index}/{len(dtbs)}, {len(dtb)} bytes, sha256 {hashlib.sha256(dtb).hexdigest()}')


if __name__ == '__main__':
    main()
