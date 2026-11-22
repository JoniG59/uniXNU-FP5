#!/usr/bin/env python3
"""Read-only extraction of the UEFI firmware volume embedded in an FP5 xbl.elf.

Parses the ELF program headers, locates the PT_LOAD segment that starts with an
EFI firmware volume (_FVH), walks FFS files and sections recursively and
decompresses EDK2 LZMA GUIDed sections. Writes every file's raw/PE/UI data and a
JSON inventory to an output directory (default: out/fp5-uefi-inputs/xbl-fv/).

The input is never modified. Output is VT32 reference data and stays in the
git-ignored out/ tree.
"""
import argparse
import gzip
import hashlib
import json
import lzma
import struct
import sys
import uuid
from pathlib import Path

LZMA_GUID = uuid.UUID("ee4e5898-3914-4259-9d6e-dc7bd79403cf")
# Qualcomm gzip-compressed GUIDed section (payload starts with 1f 8b)
QCOM_GZIP_GUID = uuid.UUID("1d301fe9-be79-4353-91c2-d23bc959ae0c")
FFS_TYPES = {0x01: "RAW", 0x02: "FREEFORM", 0x03: "SECURITY_CORE", 0x04: "PEI_CORE",
             0x05: "DXE_CORE", 0x06: "PEIM", 0x07: "DRIVER", 0x08: "COMBINED_PEIM_DRIVER",
             0x09: "APPLICATION", 0x0A: "MM", 0x0B: "FV_IMAGE", 0xF0: "PAD"}
SEC_TYPES = {0x01: "COMPRESSION", 0x02: "GUID_DEFINED", 0x03: "DISPOSABLE", 0x10: "PE32",
             0x11: "PIC", 0x12: "TE", 0x13: "DXE_DEPEX", 0x14: "VERSION", 0x15: "USER_INTERFACE",
             0x16: "COMPATIBILITY16", 0x17: "FV_IMAGE", 0x18: "FREEFORM_SUBTYPE_GUID", 0x19: "RAW",
             0x1B: "PEI_DEPEX", 0x1C: "MM_DEPEX"}


def guid(b, o=0):
    return uuid.UUID(bytes_le=bytes(b[o:o + 16]))


def elf_fv_segments(d):
    if d[:4] != b"\x7fELF" or d[4] != 2:
        raise SystemExit("expected ELF64 input")
    phoff = struct.unpack_from("<Q", d, 0x20)[0]
    phentsize, phnum = struct.unpack_from("<HH", d, 0x36)
    for i in range(phnum):
        p_type, _f, off, _v, paddr, filesz, _m, _a = struct.unpack_from("<IIQQQQQQ", d, phoff + i * phentsize)
        if p_type == 1 and filesz > 0x48 and d[off + 40:off + 44] == b"_FVH":
            yield i, off, paddr, filesz


class Walker:
    def __init__(self, outdir):
        self.out = outdir
        self.files = []
        self.blobs = {}

    def fv(self, b, depth, path):
        length = struct.unpack_from("<Q", b, 32)[0]
        hdrlen = struct.unpack_from("<H", b, 48)[0]
        ext = struct.unpack_from("<H", b, 52)[0]
        o = hdrlen
        if ext:
            o = ext + struct.unpack_from("<I", b, ext + 16)[0]
        o = (o + 7) & ~7
        end = min(length, len(b))
        while o + 24 <= end:
            if b[o:o + 24] == b"\xff" * 24:
                break
            fguid = guid(b, o)
            ftype = b[o + 18]
            attr = b[o + 19]
            size = int.from_bytes(b[o + 20:o + 23], "little")
            hsz = 24
            if attr & 0x01 and size == 0:  # FFS_ATTRIB_LARGE_FILE
                size = struct.unpack_from("<Q", b, o + 24)[0]
                hsz = 32
            if size < hsz:
                break
            body = b[o + hsz:o + size]
            rec = {"guid": str(fguid), "type": FFS_TYPES.get(ftype, hex(ftype)), "size": size,
                   "fv_path": path, "depth": depth, "name": None, "sections": []}
            if ftype != 0xF0:
                self.files.append(rec)
                if ftype == 0x01:  # raw file: keep data
                    self.blobs[f"{fguid}.raw"] = bytes(body)
                    rec["sections"].append("RAW_FILE")
                else:
                    self.sections(body, rec, depth, path)
            o = (o + size + 7) & ~7

    def sections(self, b, rec, depth, path):
        o = 0
        while o + 4 <= len(b):
            size = int.from_bytes(b[o:o + 3], "little")
            stype = b[o + 3]
            hsz = 4
            if size == 0xFFFFFF:
                size = struct.unpack_from("<I", b, o + 4)[0]
                hsz = 8
            if size < hsz:
                break
            data = b[o + hsz:o + size]
            name = SEC_TYPES.get(stype, hex(stype))
            rec["sections"].append(name)
            if stype == 0x02:
                g = guid(data, 0)
                doff = struct.unpack_from("<H", data, 16)[0] - hsz
                payload = data[doff:]
                if g == LZMA_GUID:
                    self.sections(lzma.decompress(payload, format=lzma.FORMAT_ALONE), rec, depth, path)
                elif g == QCOM_GZIP_GUID and payload[:2] == b"\x1f\x8b":
                    self.sections(gzip.decompress(payload), rec, depth, path)
                else:
                    rec.setdefault("unhandled_guid_sections", []).append(str(g))
            elif stype == 0x17:
                self.fv(data, depth + 1, f"{path}/{rec['guid']}")
            elif stype == 0x15:
                rec["name"] = data.decode("utf-16-le", "replace").rstrip("\x00")
            elif stype in (0x10, 0x12, 0x19):
                ext = {0x10: "efi", 0x12: "te", 0x19: "bin"}[stype]
                self.blobs[f"{rec['guid']}.{ext}"] = bytes(data)
            o = (o + size + 3) & ~3


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("xbl", nargs="?", default="out/fp5-uefi-inputs/xbl.elf")
    ap.add_argument("-o", "--out", default="out/fp5-uefi-inputs/xbl-fv")
    a = ap.parse_args()
    src = Path(a.xbl)
    d = src.read_bytes()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    w = Walker(out)
    segs = []
    for idx, off, paddr, size in elf_fv_segments(d):
        fv = d[off:off + size]
        segs.append({"phdr": idx, "file_offset": hex(off), "paddr": hex(paddr), "size": hex(size)})
        w.fv(fv, 0, hex(paddr))
    if not segs:
        sys.exit("no firmware volume segment found")
    for fname, blob in w.blobs.items():
        (out / "files").mkdir(exist_ok=True)
        (out / "files" / fname).write_bytes(blob)
    for r in w.files:
        r["blobs"] = sorted(k for k in w.blobs if k.startswith(r["guid"]))
        r["sha256"] = {k: hashlib.sha256(w.blobs[k]).hexdigest() for k in r["blobs"]}
    inv = {"source": str(src), "source_sha256": hashlib.sha256(d).hexdigest(),
           "fv_segments": segs, "files": w.files,
           "notice": "VT32 factory reference; analysis only, not the installed VT31 firmware."}
    (out / "inventory.json").write_text(json.dumps(inv, indent=1))
    print(f"FV segments: {segs}")
    print(f"FFS files: {len(w.files)}  blobs: {len(w.blobs)}  -> {out}")


if __name__ == "__main__":
    main()
