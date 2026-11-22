#!/usr/bin/env python3
"""Report PT_LOAD memory ranges in staged FP5 factory firmware ELF files."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


def parse_elf(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    if data[:4] != b"\x7fELF":
        return {"name": path.name, "sha256": hashlib.sha256(data).hexdigest(), "elf": False}
    elf_class, encoding = data[4], data[5]
    if elf_class not in (1, 2) or encoding not in (1, 2):
        raise ValueError(f"unsupported ELF class or byte order: {path}")
    endian = "<" if encoding == 1 else ">"
    if elf_class == 1:
        header = struct.unpack_from(endian + "HHIIIIIHHHHHH", data, 16)
        elf_type, machine, entry, phoff = header[0], header[1], header[3], header[4]
        phentsize, phnum = header[8], header[9]
        phfmt = endian + "IIIIIIII"
    else:
        header = struct.unpack_from(endian + "HHIQQQIHHHHHH", data, 16)
        elf_type, machine, entry, phoff = header[0], header[1], header[3], header[4]
        phentsize, phnum = header[8], header[9]
        phfmt = endian + "IIQQQQQQ"
    expected_size = struct.calcsize(phfmt)
    if phentsize < expected_size or phoff + phentsize * phnum > len(data):
        raise ValueError(f"invalid program header table: {path}")

    loads = []
    firmware_volumes = []
    for index in range(phnum):
        fields = struct.unpack_from(phfmt, data, phoff + index * phentsize)
        if elf_class == 1:
            p_type, p_offset, vaddr, paddr, filesz, memsz, flags, align = fields
        else:
            p_type, flags, p_offset, vaddr, paddr, filesz, memsz, align = fields
        if p_type != 1:  # PT_LOAD
            continue
        loads.append({
            "program_header": index,
            "file_offset": hex(p_offset),
            "physical_start": hex(paddr),
            "physical_end_exclusive": hex(paddr + memsz),
            "virtual_start": hex(vaddr),
            "file_bytes": hex(filesz),
            "memory_bytes": hex(memsz),
            "flags": flags,
            "alignment": hex(align),
        })
        segment = data[p_offset:p_offset + filesz]
        marker = 0
        while True:
            signature = segment.find(b"_FVH", marker)
            if signature < 0:
                break
            marker = signature + 1
            fv_offset = signature - 0x28
            if fv_offset < 0 or fv_offset + 0x38 > len(segment):
                continue
            fv_size = struct.unpack_from(endian + "Q", segment, fv_offset + 0x20)[0]
            header_size = struct.unpack_from(endian + "H", segment, fv_offset + 0x30)[0]
            if fv_size < header_size or fv_offset + fv_size > len(segment):
                continue
            firmware_volumes.append({
                "program_header": index,
                "physical_start": hex(paddr + fv_offset),
                "physical_end_exclusive": hex(paddr + fv_offset + fv_size),
                "file_offset": hex(p_offset + fv_offset),
                "size": hex(fv_size),
                "header_size": hex(header_size),
            })
    return {
        "name": path.name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "elf": True,
        "elf_class_bits": 32 if elf_class == 1 else 64,
        "machine": machine,
        "type": elf_type,
        "entry": hex(entry),
        "pt_load": loads,
        "firmware_volumes": firmware_volumes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", type=Path, default=[
        Path("out/fp5-uefi-inputs/xbl.elf"),
        Path("out/fp5-uefi-inputs/abl.elf"),
        Path("out/fp5-uefi-inputs/uefi_sec.mbn"),
        Path("out/fp5-uefi-inputs/imagefv.elf"),
    ])
    parser.add_argument("--fd-base", type=lambda v: int(v, 0), default=0x9FD00000,
                        help="candidate interval start to report intersections (default: lisa reference)")
    parser.add_argument("--fd-size", type=lambda v: int(v, 0), default=0x200000,
                        help="candidate interval size to report intersections")
    parser.add_argument("--output", type=Path,
                        default=Path("out/fp5-uefi-inputs/elf-load-ranges.json"))
    args = parser.parse_args()

    start, end = args.fd_base, args.fd_base + args.fd_size
    result = {
        "notice": "ELF PT_LOAD ranges are image segment metadata, not a live free-memory map.",
        "comparison_candidate": {"base": hex(start), "end_exclusive": hex(end),
                                 "source": "Mu-Silicium lisa config; comparison only, not an FP5 recommendation"},
        "images": [],
    }
    for path in args.inputs:
        image = parse_elf(path)
        if image.get("elf"):
            intersections = []
            for segment in image["pt_load"]:
                seg_start = int(segment["physical_start"], 16)
                seg_end = int(segment["physical_end_exclusive"], 16)
                if seg_start < end and start < seg_end:
                    intersections.append({"program_header": segment["program_header"],
                                          "overlap_start": hex(max(seg_start, start)),
                                          "overlap_end_exclusive": hex(min(seg_end, end))})
            image["comparison_intersections"] = intersections
        result["images"].append(image)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {args.output}")
    for image in result["images"]:
        print(f"{image['name']}: entry={image.get('entry', 'not ELF')}")
        for segment in image.get("pt_load", []):
            print(f"  PT_LOAD {segment['physical_start']}..{segment['physical_end_exclusive']}")
        for volume in image.get("firmware_volumes", []):
            print(f"  FV {volume['physical_start']}..{volume['physical_end_exclusive']} ({volume['size']})")
        if image.get("comparison_intersections"):
            print(f"  intersects comparison FD range {start:#x}..{end:#x}")


if __name__ == "__main__":
    main()
