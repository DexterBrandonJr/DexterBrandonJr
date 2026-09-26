"""Converting the formats the engine cannot read into one it can.

The engine decodes exactly five formats: JPEG, PNG, WebP, BMP and the JPEG
variants. It cannot read HEIC, AVIF, TIFF or GIF at all — there is no decoder
for them in it, and in its directory mode it silently skips them.

That matters more on a Mac than it sounds, because HEIC is what an iPhone
takes photographs in. A tool for upscaling photographs that refuses the format
most of the photographs are in would be a poor tool, so anything the engine
cannot read is converted to PNG first with ``sips``, the image converter built
in to macOS.

The conversion is lossless into PNG and happens on a copy. The original is
never touched, and the copy is deleted after the job whether it succeeded or
not. The ledger records that it happened, so a row always says what was
actually fed to the engine rather than only what was asked for.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from typing import Any, Dict, Optional, Tuple

from . import imageprobe

SIPS = "/usr/bin/sips"

# What the engine can decode directly. Anything else goes through sips first.
ENGINE_READABLE = frozenset({"png", "jpeg", "webp", "bmp"})

# What sips can convert for us. Everything the engine cannot read but a person
# plausibly has photographs in.
TRANSCODABLE = frozenset({"heif", "avif", "tiff", "gif"})


def available() -> bool:
    return os.path.isfile(SIPS) and os.access(SIPS, os.X_OK)


def needed(fmt: Optional[str]) -> bool:
    return fmt is not None and fmt not in ENGINE_READABLE


def can_convert(fmt: Optional[str]) -> bool:
    return fmt in TRANSCODABLE and available()


def to_png(
    source: str, *, work_dir: str, timeout: int = 300
) -> Tuple[Optional[str], Dict[str, Any]]:
    """Convert an image the engine cannot read into a PNG it can.

    Returns ``(path, record)``. ``path`` is None when the conversion failed,
    and ``record`` always describes what happened, for the ledger.

    The converted copy goes in a working directory the caller owns and is that
    caller's to delete — putting it beside the original would leave debris in
    the person's photo library.
    """
    record: Dict[str, Any] = {
        "converted": False,
        "tool": "sips",
        "source": source,
        # Recorded either way, so a row explains itself without the reader
        # having to know what the machine had installed at the time.
        "available": available(),
    }
    if not record["available"]:
        record["note"] = "sips is not available; the engine cannot read this format"
        return None, record

    os.makedirs(work_dir, exist_ok=True)
    handle, target = tempfile.mkstemp(
        prefix="upscayl-wrap-input-", suffix=".png", dir=work_dir
    )
    os.close(handle)

    started = time.monotonic()
    try:
        completed = subprocess.run(
            [SIPS, "-s", "format", "png", source, "--out", target],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        record["note"] = "conversion timed out after %d seconds" % timeout
        _remove(target)
        return None, record
    except OSError as exc:
        record["note"] = "conversion could not run: %s" % exc
        _remove(target)
        return None, record

    record["seconds"] = round(time.monotonic() - started, 3)
    record["exit_code"] = completed.returncode

    if completed.returncode != 0:
        record["note"] = (
            completed.stderr.decode("utf-8", "replace").strip()[-300:] or "sips failed"
        )
        _remove(target)
        return None, record

    # Trust nothing: confirm what came out is a whole PNG before handing it on.
    info = imageprobe.probe(target)
    if not info.ok or info.complete is False:
        record["note"] = "the converted copy is not a usable image: %s" % (
            info.error or "truncated"
        )
        _remove(target)
        return None, record

    record["converted"] = True
    record["target"] = target
    record["width"] = info.width
    record["height"] = info.height
    record["bytes"] = info.size_bytes
    return target, record


def _remove(path: Optional[str]) -> None:
    if not path:
        return
    try:
        os.unlink(path)
    except OSError:
        pass


def cleanup(record: Optional[Dict[str, Any]]) -> None:
    """Delete the converted copy. Safe to call more than once."""
    if record:
        _remove(record.get("target"))


def remedy(fmt: Optional[str]) -> str:
    """What to tell someone whose file cannot be used."""
    if fmt in TRANSCODABLE:
        return (
            "the engine cannot read %s; converting it first needs sips, which is "
            "part of macOS" % fmt
        )
    return (
        "the engine reads JPEG, PNG, WebP and BMP only. Convert it first, for "
        "example: sips -s format png input.%s --out output.png" % (fmt or "xxx")
    )
