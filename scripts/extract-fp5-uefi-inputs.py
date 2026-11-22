#!/usr/bin/env python3
"""Extract only the Qualcomm boot-firmware inputs needed for FP5 UEFI analysis.

This does not flash, patch, or modify the source archive. The extracted files
are proprietary factory inputs and should stay in an ignored build directory.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
from zipfile import BadZipFile, ZipFile


INPUTS = (
    "xbl.elf",
    "abl.elf",
    "uefi_sec.mbn",
    "imagefv.elf",
    "xbl_config.elf",
    "devcfg.mbn",
)
MAX_INPUT_BYTES = 64 * 1024 * 1024


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="complete Fairphone FP5 factory ZIP")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("out/fp5-uefi-inputs"),
        help="private build directory for extracted inputs (default: out/fp5-uefi-inputs)",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="extract available inputs and report missing images without failing",
    )
    args = parser.parse_args()

    if not args.archive.is_file():
        parser.error(f"archive not found: {args.archive}")
    try:
        archive = ZipFile(args.archive)
    except BadZipFile as error:
        parser.error(f"not a readable ZIP archive: {error}")

    with archive:
        members: dict[str, list[str]] = {name: [] for name in INPUTS}
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            for wanted in INPUTS:
                if name.endswith(f"/images/{wanted}"):
                    members[wanted].append(name)

        ambiguous = [name for name, paths in members.items() if len(paths) > 1]
        missing = [name for name, paths in members.items() if not paths]
        if ambiguous:
            print("FAIL: duplicate firmware members: " + ", ".join(ambiguous), file=sys.stderr)
            return 2
        if missing and not args.allow_partial:
            print("FAIL: this is not a complete factory package; missing: " + ", ".join(missing), file=sys.stderr)
            return 2

        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=True)
        records = []
        for wanted, paths in members.items():
            if not paths:
                continue
            info = archive.getinfo(paths[0])
            if info.file_size <= 0 or info.file_size > MAX_INPUT_BYTES:
                print(f"FAIL: {wanted} has unexpected size {info.file_size}", file=sys.stderr)
                return 2
            destination = output / wanted
            digest = hashlib.sha256()
            written = 0
            with archive.open(info) as source, destination.open("wb") as sink:
                while chunk := source.read(1024 * 1024):
                    written += len(chunk)
                    if written > MAX_INPUT_BYTES:
                        destination.unlink(missing_ok=True)
                        print(f"FAIL: {wanted} exceeds extraction size limit", file=sys.stderr)
                        return 2
                    digest.update(chunk)
                    sink.write(chunk)
            if written != info.file_size:
                destination.unlink(missing_ok=True)
                print(f"FAIL: short extraction for {wanted}", file=sys.stderr)
                return 2
            records.append({
                "name": wanted,
                "archive_member": paths[0],
                "size": written,
                "sha256": digest.hexdigest(),
            })

    manifest = {
        "source_archive": str(args.archive.resolve()),
        "extracted_inputs": records,
        "missing_inputs": missing,
        "notice": "Factory firmware inputs; analysis only. Do not flash these files as a replacement boot chain.",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return 2 if missing and not args.allow_partial else 0


if __name__ == "__main__":
    raise SystemExit(main())
