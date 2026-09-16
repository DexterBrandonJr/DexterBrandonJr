#!/usr/bin/env python3
"""A stand-in for ``upscayl-bin``, for testing without a graphics processor.

It accepts the same flags as the real engine and reproduces its behaviour
closely enough to exercise every path in the wrapper:

* the model's native scale is read from the model *name*, and ``-s`` is a
  resample applied afterwards, exactly as the real engine does it;
* ``-h`` prints the usage banner and exits non-zero, which is also what the
  real one does and which any code checking exit codes gets wrong.

Its failure modes are what make it worth having. Set ``FAKE_UPSCAYL_MODE``:

  ok              behave correctly (the default)
  silent-failure  print an error, write nothing, and exit 0 — the failure
                  that a wrapper trusting exit codes reports as a success
  truncated       write a PNG with its ending cut off
  wrong-scale     quietly produce 2x when asked for 4x
  empty           create the output file with nothing in it
  crash           fail during start-up: a graphics-device error and a
                  non-zero exit, which is the only way the real engine can
                  exit non-zero
  hang            sleep far longer than any sane timeout
  black-image     the worst one: print a graphics-memory error, then write a
                  complete, structurally valid image anyway, and exit 0. No
                  amount of inspecting the file reveals the problem.
  oom-until-tile  fail the same way until the tile size drops to
                  FAKE_UPSCAYL_OK_TILE (default 128), then succeed — which is
                  what the retry ladder is for.
"""

from __future__ import annotations

import getopt
import os
import re
import struct
import sys
import time
import zlib

USAGE = """Usage: upscayl-bin -i infile -o outfile [options]...

  -h                   show this help
  -i input-path        input image path (jpg/png/webp) or directory
  -o output-path       output image path (jpg/png/webp) or directory
  -z model-scale       scale according to the model (can be 2, 3, 4. default=4)
  -s output-scale      custom output scale (can be 2, 3, 4. default=4)
  -t tile-size         tile size (>=32/0=auto, default=0) can be 0,0,0 for multi-gpu
  -m model-path        folder path to the pre-trained models. default=models
  -n model-name        model name (default=realesrgan-x4plus)
  -g gpu-id            gpu device to use (default=auto) can be 0,1,2 for multi-gpu
  -j load:proc:save    thread count for load/proc/save (default=1:2:2)
  -x                   enable tta mode
  -f format            output image format (jpg/png/webp, default=ext/png)
  -v                   verbose output
"""


def write_png(path: str, width: int, height: int, value: int = 128) -> bytes:
    """Write a valid greyscale-ish PNG using only the standard library."""
    row = b"\x00" + bytes([value, value, value]) * width
    raw = row * height
    compressed = zlib.compress(raw, 6)

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
    return data


def read_png_size(path: str) -> "tuple[int, int]":
    with open(path, "rb") as handle:
        head = handle.read(24)
    if not head.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("fake engine only reads PNG inputs")
    return struct.unpack(">II", head[16:24])


def native_scale_from_name(name: str) -> int:
    """The real engine does exactly this: substring-match the model name."""
    for candidate in (1, 2, 3, 4, 8, 16):
        if ("x%d" % candidate) in name or ("%dx" % candidate) in name:
            return candidate
    return 4


def main(argv: "list[str]") -> int:
    mode = os.environ.get("FAKE_UPSCAYL_MODE", "ok")

    try:
        options, _ = getopt.getopt(argv[1:], "i:o:z:s:r:w:t:c:m:n:g:j:f:vxh")
    except getopt.GetoptError as exc:
        sys.stderr.write("🚨 Error: %s\n" % exc)
        return -1 & 0xFF

    input_path = output_path = ""
    model_name = "realesrgan-x4plus"
    model_path = "models"
    output_scale = None
    output_format = "png"
    verbose = False
    tile_size = 0

    for flag, value in options:
        if flag == "-h":
            sys.stderr.write(USAGE)
            return 255
        elif flag == "-i":
            input_path = value
        elif flag == "-o":
            output_path = value
        elif flag == "-s":
            output_scale = int(value)
        elif flag == "-n":
            model_name = value
        elif flag == "-m":
            model_path = value
        elif flag == "-f":
            output_format = value
        elif flag == "-t":
            tile_size = int(value.split(",")[0])
        elif flag == "-v":
            verbose = True

    if not input_path or not output_path:
        sys.stderr.write(USAGE)
        return 255

    if not os.path.exists(input_path):
        sys.stderr.write("🚨 Error: input %s does not exist\n" % input_path)
        return 255

    # The real engine needs both files of the pair to be present.
    for extension in (".param", ".bin"):
        expected = os.path.join(model_path, model_name + extension)
        if not os.path.exists(expected):
            sys.stderr.write("🚨 Error: missing model file %s\n" % expected)
            return 255

    native = native_scale_from_name(model_name)
    if verbose:
        sys.stderr.write("✨ Detected scale x%d\n" % native)

    width, height = read_png_size(input_path)
    effective = output_scale if output_scale is not None else native
    target_width, target_height = width * effective, height * effective

    if mode == "hang":
        time.sleep(3600)
        return 0
    if mode == "crash":
        # Start-up failures are the only ones the real engine can signal with
        # an exit code, and they happen before any image is read.
        sys.stderr.write("🚨 Error: vkEnumeratePhysicalDevices failed -3\n")
        return 1
    if mode == "silent-failure":
        sys.stderr.write("🚨 Error: could not process image\n")
        return 0  # The dangerous one: an error message and a success code.
    if mode == "empty":
        open(output_path, "wb").close()
        return 0
    if mode == "wrong-scale":
        write_png(output_path, width * 2, height * 2)
        return 0
    if mode == "black-image":
        # Structurally perfect output, garbage content, success exit code.
        # Only the error stream gives it away.
        sys.stderr.write("vkAllocateMemory failed -2\n")
        sys.stderr.write("100.00%\n🙌 Upscayled Successfully!\n")
        write_png(output_path, target_width, target_height, value=0)
        return 0
    if mode == "oom-until-tile":
        threshold = int(os.environ.get("FAKE_UPSCAYL_OK_TILE", "128"))
        if tile_size == 0 or tile_size > threshold:
            sys.stderr.write("vkAllocateMemory failed -2\n")
            write_png(output_path, target_width, target_height, value=0)
            return 0
        sys.stderr.write("recovered at tile %d\n" % tile_size)
        write_png(output_path, target_width, target_height)
        return 0
    if mode == "truncated":
        data = write_png(output_path, target_width, target_height)
        with open(output_path, "wb") as handle:
            handle.write(data[: max(16, len(data) // 2)])
        return 0

    write_png(output_path, target_width, target_height)
    if verbose:
        sys.stderr.write("%s -> %s done\n" % (input_path, output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
