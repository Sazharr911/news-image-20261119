#!/usr/bin/env python3
"""Deliver the finished front page to the competition output folder.

The artwork itself is rendered ahead of time by draw.py and committed
to this repository as entry.png.  The program/v1 sandbox that runs
this file offers nothing but the Python standard library, so there is
no drawing to do here: the job is simply to place entry.png at the
output location, carefully.

Before anything is written, the source image is sanity-checked (real
PNG, 1024 x 1024, inside the 1 MiB size limit, not truncated).  The
copy is then staged under a temporary name inside the destination
directory and renamed over the final path, so a reader can never
catch a half-written file.  Finally the delivered bytes are compared
against the source to prove the copy is exact.

Run it with:  python3 main.py
Output:       /output/entry.png  (MAKEFUN_OUT overrides the path)
"""

import os
import shutil
import sys

IMAGE_NAME = "entry.png"
DEST_PATH = "/output/entry.png"
SIZE_LIMIT = 1024 * 1024          # competition cap: 1 MiB
EXPECTED_SIDE = 1024              # the page is square, 1024 x 1024
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def bail(reason):
    """Print a clear failure message and hand back a nonzero code."""
    sys.stderr.write("main.py: cannot deliver the page: %s\n" % reason)
    return 1


def png_dimensions(path):
    """Read the (width, height) pair out of the PNG IHDR header."""
    with open(path, "rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or not header.startswith(PNG_MAGIC):
        raise ValueError("the file does not start with a PNG signature")
    if header[12:16] != b"IHDR":
        raise ValueError("the first PNG chunk is not IHDR")
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    return width, height


def ends_with_iend(path):
    """True when the file's last chunk is IEND, i.e. not truncated."""
    with open(path, "rb") as handle:
        handle.seek(-12, os.SEEK_END)
        tail = handle.read(12)
    return len(tail) == 12 and tail[4:8] == b"IEND"


def deliver():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(script_dir, IMAGE_NAME)
    target = os.environ.get("MAKEFUN_OUT") or DEST_PATH

    if not os.path.isfile(source):
        return bail("%s is missing; it must sit next to main.py" % IMAGE_NAME)

    size = os.path.getsize(source)
    if size > SIZE_LIMIT:
        return bail("%s weighs %d bytes, over the 1 MiB limit"
                    % (IMAGE_NAME, size))

    try:
        width, height = png_dimensions(source)
        complete = ends_with_iend(source)
    except (OSError, ValueError) as problem:
        return bail("%s failed its checks (%s)" % (IMAGE_NAME, problem))
    if (width, height) != (EXPECTED_SIDE, EXPECTED_SIDE):
        return bail("%s is %d x %d, but the page must be %d x %d"
                    % (IMAGE_NAME, width, height,
                       EXPECTED_SIDE, EXPECTED_SIDE))
    if not complete:
        return bail("%s looks truncated; its IEND chunk is missing"
                    % IMAGE_NAME)

    folder = os.path.dirname(target)
    if folder:
        os.makedirs(folder, exist_ok=True)
    staging = target + ".part"
    shutil.copyfile(source, staging)
    os.replace(staging, target)  # atomic rename within the same folder

    with open(source, "rb") as handle:
        original = handle.read()
    with open(target, "rb") as handle:
        delivered = handle.read()
    if delivered != original:
        return bail("the delivered file differs from %s" % IMAGE_NAME)

    print("delivered %s (%d bytes, byte-identical to %s)"
          % (target, size, IMAGE_NAME))
    return 0


if __name__ == "__main__":
    sys.exit(deliver())
