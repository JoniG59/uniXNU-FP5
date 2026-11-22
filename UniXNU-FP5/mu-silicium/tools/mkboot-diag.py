#!/usr/bin/env python3
"""Pack one FP5 diagnostic boot image (fastboot boot only) and verify it.

Usage: mkboot-diag.py <Mu-Silicium> <fd> <dtb> <out.img> [--v1]
--v1 uses Android boot header v1 (pagesize 2048, Mu default offsets) instead of
the header v3 from UniXNU-FP5/board.toml.
"""
import copy
import hashlib
import struct
import sys
import tempfile
import types
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'scripts'))
from unixnu import bootimg  # noqa: E402
from unixnu.config import load_toml  # noqa: E402

V1 = {'header_version': 1, 'pagesize': 2048, 'base': 0x10000000, 'kernel_offset': 0x8000,
      'tags_offset': 0x100, 'ramdisk_offset': 0x01000000}


def check(img, fd):
    d = img.read_bytes()
    ver = struct.unpack_from('<I', d, 40)[0]
    ksize = struct.unpack_from('<I', d, 8)[0]
    hdr = 4096 if ver >= 3 else struct.unpack_from('<I', d, 36)[0]
    o = zlib.decompressobj(31)
    raw = o.decompress(d[hdr:hdr + ksize])
    if raw[-len(fd):] != fd or o.unused_data[:4] != b'\xd0\x0d\xfe\xed':
        sys.exit(f'{img}: FD/DTB check failed')
    return ver


def main():
    args = [a for a in sys.argv[1:] if a != '--v1']
    if len(args) != 4:
        sys.exit(__doc__)
    mu, fd, dtb, out = map(Path, args)
    board = copy.deepcopy(load_toml(REPO / 'UniXNU-FP5/board.toml'))
    if '--v1' in sys.argv:
        board.setdefault('bootimg', {})['image'] = dict(board['bootimg'].get('image', {}), **V1)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='fp5-diag-') as work:
        ctx = types.SimpleNamespace(board=board, work=Path(work))
        bootimg.build(ctx, mu.resolve(), fd, dtb, None, out)
        (out.parent / 'boot.json').replace(out.with_suffix('.json'))
    ver = check(out, fd.read_bytes())
    print(f'{out.name}: header v{ver}, {out.stat().st_size} bytes, sha256 {hashlib.sha256(out.read_bytes()).hexdigest()}')


if __name__ == '__main__':
    main()
