#!/usr/bin/env python3
"""
THE WORLD IN A DAY -- runtime program (stdlib only).

Copies the pre-rendered entry.png (drawn at build time by draw.py)
to the competition output path. The competition's program/v1 runtime
has only the Python standard library -- no Pillow, no system fonts --
so this file does no drawing at all: it verifies the committed
entry.png (PNG signature, 1024x1024 dimensions, the 1 MiB
competition cap), copies it to the output path, verifies the copy
byte-for-byte, and exits 0.

Usage:

    python3 main.py

Writes /output/entry.png (override with the MAKEFUN_OUT environment
variable). Needs nothing beyond Python 3's standard library.
"""

import hashlib
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "entry.png")
DEFAULT_OUT = "/output/entry.png"
MAX_BYTES = 1048576  # the competition's 1 MiB cap
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def fail(message):
    print("main.py: error:", message, file=sys.stderr)
    return 1


def read_png_header(path):
    """Return (width, height) from a PNG file's IHDR chunk."""
    with open(path, "rb") as fh:
        head = fh.read(33)
    if len(head) < 33 or head[:8] != PNG_SIGNATURE:
        raise ValueError("not a PNG file (bad signature)")
    if head[12:16] != b"IHDR":
        raise ValueError("not a PNG file (missing IHDR)")
    width, height = struct.unpack(">II", head[16:24])
    return width, height


def main():
    out_path = os.environ.get("MAKEFUN_OUT") or DEFAULT_OUT
    if not os.path.isfile(SRC):
        return fail("entry.png not found next to main.py")
    size = os.path.getsize(SRC)
    if size > MAX_BYTES:
        return fail("entry.png is %d bytes, over the 1 MiB cap" % size)
    try:
        width, height = read_png_header(SRC)
    except (OSError, ValueError) as exc:
        return fail("entry.png failed verification: %s" % exc)
    if (width, height) != (1024, 1024):
        return fail("entry.png is %dx%d, expected 1024x1024"
                    % (width, height))
    # The file must end with a complete IEND chunk, so a truncated
    # PNG can never pass verification even if its header is intact.
    with open(SRC, "rb") as fh:
        fh.seek(-12, os.SEEK_END)
        tail = fh.read(12)
    if len(tail) != 12 or tail[4:8] != b"IEND":
        return fail("entry.png is truncated (no IEND chunk)")
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    shutil.copyfile(SRC, out_path)
    with open(SRC, "rb") as fh:
        src_hash = hashlib.sha256(fh.read()).hexdigest()
    with open(out_path, "rb") as fh:
        out_hash = hashlib.sha256(fh.read()).hexdigest()
    if src_hash != out_hash:
        return fail("output copy does not match entry.png")
    print("wrote %s (%d bytes, sha256 %s)" % (out_path, size, src_hash))
    return 0


if __name__ == "__main__":
    sys.exit(main())
