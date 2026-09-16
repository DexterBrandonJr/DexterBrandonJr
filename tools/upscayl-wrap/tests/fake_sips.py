#!/usr/bin/env python3
"""A stand-in for macOS's ``sips``, so the conversion path can be tested.

``sips`` is the image converter built in to macOS, and it is how this tool
turns a HEIC — what an iPhone photographs in, and a format the engine cannot
read at all — into something the engine can. On any other machine it does not
exist, so without this the entire conversion path would be exercised by
nothing.

Supports only the two invocations the tool actually makes:

    sips -s format png SOURCE --out TARGET
    sips --resampleWidth N SOURCE --out TARGET

Set ``FAKE_SIPS_MODE`` to make it misbehave:

  ok           convert properly (the default)
  fail         exit non-zero with a message
  garbage      exit 0 but write something that is not an image
  nothing      exit 0 and write no file at all
"""

from __future__ import annotations

import os
import struct
import sys
import zlib


def write_png(path: str, width: int, height: int, value: int = 160) -> None:
    row = b"\x00" + bytes([value, value, value]) * width
    compressed = zlib.compress(row * height, 6)

    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return (
            struct.pack(">I", len(payload))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += chunk(b"IDAT", compressed)
    data += chunk(b"IEND", b"")
    with open(path, "wb") as handle:
        handle.write(data)


def source_dimensions(path: str) -> "tuple[int, int]":
    """Read dimensions from the handful of formats the tests feed us."""
    with open(path, "rb") as handle:
        head = handle.read(65536)
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return struct.unpack(">II", head[16:24])
    # ISO Base Media File Format (HEIC, AVIF): the image's spatial extents.
    found = head.find(b"ispe")
    if found >= 0:
        return struct.unpack(">II", head[found + 8 : found + 16])
    if head[:6] in (b"GIF87a", b"GIF89a"):
        width, height = struct.unpack("<HH", head[6:10])
        return width, height
    raise ValueError("fake sips cannot read %s" % path)


def main(argv: "list[str]") -> int:
    mode = os.environ.get("FAKE_SIPS_MODE", "ok")

    target = None
    source = None
    resample_width = None
    index = 1
    while index < len(argv):
        token = argv[index]
        if token == "--out":
            target = argv[index + 1]
            index += 2
        elif token == "-s":
            index += 3            # -s format png
        elif token == "--resampleWidth":
            resample_width = int(argv[index + 1])
            index += 2
        elif token.startswith("-"):
            index += 1
        else:
            source = token
            index += 1

    if not source or not target:
        sys.stderr.write("fake sips: need a source and --out\n")
        return 1
    if not os.path.exists(source):
        sys.stderr.write("fake sips: %s does not exist\n" % source)
        return 1

    if mode == "fail":
        sys.stderr.write("Error: unable to render destination image\n")
        return 1
    if mode == "nothing":
        return 0
    if mode == "garbage":
        with open(target, "wb") as handle:
            handle.write(b"this is not an image")
        return 0

    width, height = source_dimensions(source)
    if resample_width:
        height = max(1, round(height * resample_width / width))
        width = resample_width
    write_png(target, width, height)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
