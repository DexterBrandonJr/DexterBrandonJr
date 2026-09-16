"""Image inspection with zero third-party dependencies.

Everything here reads header bytes directly. That is a deliberate constraint:
the tool has to run on a stock Mac with nothing installed but the Python that
ships with Apple's Command Line Tools, so Pillow is not available and cannot
be assumed.

Two jobs:

1. ``probe`` — what is this file, and how many pixels does it have. Needed
   before a job (to predict the output and to budget memory) and after a job
   (to prove the upscaler actually scaled by the factor it was asked for).

2. ``completeness`` — is this file whole, or is it a truncated carcass left
   behind by a crashed encoder. This matters more than it looks: an upscaler
   killed part-way through leaves a plausible-looking file on disk, and a
   wrapper that only checks "does the output exist" will record that as a
   success forever.

``imghdr`` is deliberately not used. It was deprecated in Python 3.11 and
removed in 3.13 (PEP 594), so depending on it would break the tool on any
modern interpreter.
"""

from __future__ import annotations

import hashlib
import os
import struct
from dataclasses import dataclass, field
from typing import Optional, Tuple

# How much of the file head we are willing to read for format sniffing and
# dimension parsing. JPEG comment/EXIF segments can be large, so this is not
# as generous as it looks.
HEAD_BYTES = 256 * 1024

# Magic numbers. Order matters only in that longer/more specific prefixes are
# checked before shorter ones.
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_GIF_MAGICS = (b"GIF87a", b"GIF89a")
_BMP_MAGIC = b"BM"
_TIFF_LE_MAGIC = b"II\x2a\x00"
_TIFF_BE_MAGIC = b"MM\x00\x2a"
_RIFF_MAGIC = b"RIFF"
_WEBP_MAGIC = b"WEBP"

# A complete PNG always ends with a zero-length IEND chunk: length(4 zero
# bytes) + "IEND" + its CRC, which is constant because the payload is empty.
PNG_IEND = b"\x00\x00\x00\x00IEND\xaeB\x60\x82"

# A complete JPEG ends with the End Of Image marker.
JPEG_EOI = b"\xff\xd9"

# ISO Base Media File Format brands that mean "this box structure holds a
# still image" — HEIC from an iPhone, AVIF from a modern encoder.
_HEIF_BRANDS = {
    b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"hevm", b"hevs",
    b"mif1", b"msf1", b"miaf",
}
_AVIF_BRANDS = {b"avif", b"avis"}

# JPEG Start Of Frame markers that carry dimensions. C4 (define Huffman
# table), C8 (reserved) and CC (define arithmetic coding) look like SOF
# markers but are not, which is the classic bug in hand-rolled JPEG parsers.
_JPEG_SOF_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
}
# Markers that stand alone — they carry no length field to skip over.
_JPEG_STANDALONE = {0x01, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8}

# What the engine can actually decode. This is a short list, and shorter than
# it looks: it has no decoder for HEIC, AVIF, TIFF or GIF, and in its own
# directory mode it skips them without saying so. Anything outside this set
# has to be converted before it reaches the engine — see transcode.py, which
# does exactly that, because HEIC is what an iPhone photographs in.
ENGINE_READABLE_FORMATS = frozenset({"png", "jpeg", "webp", "bmp"})

# What this tool accepts from a person, which is larger, because it converts
# the difference rather than refusing it.
READABLE_FORMATS = frozenset(
    {"png", "jpeg", "webp", "bmp", "tiff", "heif", "avif", "gif"}
)

# The engine writes three formats. Note the asymmetry: BMP goes in but never
# comes out.
WRITABLE_FORMATS = frozenset({"png", "jpg", "webp"})

# Extension the tool writes for each output format keyword.
OUTPUT_EXTENSION = {"png": ".png", "jpg": ".jpg", "webp": ".webp"}


@dataclass
class ImageInfo:
    """What we could learn about a file without decoding it."""

    path: str
    size_bytes: int = 0
    fmt: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    # True = provably whole, False = provably truncated, None = this format
    # has no cheap end-of-file marker so we cannot say either way.
    complete: Optional[bool] = None
    # True/False when the format lets us tell cheaply, None when it does not.
    # This matters because writing an image with transparency out as a JPEG
    # loses the transparency, and the engine does it silently.
    has_alpha: Optional[bool] = None
    notes: list = field(default_factory=list)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        """Readable, identified, and with dimensions we trust."""
        return (
            self.error is None
            and self.fmt is not None
            and bool(self.width)
            and bool(self.height)
        )

    @property
    def megapixels(self) -> float:
        if not self.width or not self.height:
            return 0.0
        return (self.width * self.height) / 1_000_000.0

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "format": self.fmt,
            "width": self.width,
            "height": self.height,
            "complete": self.complete,
            "has_alpha": self.has_alpha,
            "megapixels": round(self.megapixels, 3),
            "notes": list(self.notes),
            "error": self.error,
        }


def sniff_format(head: bytes) -> Optional[str]:
    """Identify a format from its leading bytes. Never trusts the extension."""
    if head.startswith(_PNG_MAGIC):
        return "png"
    if head[:2] == b"\xff\xd8":
        return "jpeg"
    if head.startswith(_RIFF_MAGIC) and head[8:12] == _WEBP_MAGIC:
        return "webp"
    if head.startswith(_TIFF_LE_MAGIC) or head.startswith(_TIFF_BE_MAGIC):
        return "tiff"
    if head[:6] in _GIF_MAGICS:
        return "gif"
    if head.startswith(_BMP_MAGIC):
        return "bmp"
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        compatible = head[16:64]
        if brand in _AVIF_BRANDS or any(b in compatible for b in _AVIF_BRANDS):
            return "avif"
        if brand in _HEIF_BRANDS or any(b in compatible for b in _HEIF_BRANDS):
            return "heif"
    return None


def _png_dimensions(head: bytes) -> Optional[Tuple[int, int]]:
    # IHDR is required by the spec to be the first chunk, so its payload sits
    # at a fixed offset: 8 magic + 4 length + 4 type = 16.
    if len(head) < 24:
        return None
    if head[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", head[16:24])
    return width, height


def _jpeg_dimensions(head: bytes) -> Optional[Tuple[int, int]]:
    # Walk the marker segments rather than guessing an offset. Progressive
    # JPEGs and anything with a large EXIF block put the frame header well
    # past where a fixed offset would look.
    pos = 2
    end = len(head)
    while pos < end - 1:
        if head[pos] != 0xFF:
            # Resynchronise: padding between segments is legal.
            pos += 1
            continue
        # A run of 0xFF bytes is fill; the marker is the first non-FF byte.
        while pos < end and head[pos] == 0xFF:
            pos += 1
        if pos >= end:
            return None
        marker = head[pos]
        pos += 1
        if marker in _JPEG_STANDALONE:
            continue
        if marker == 0xD9:  # End of image before any frame header.
            return None
        if pos + 2 > end:
            return None
        (seg_len,) = struct.unpack(">H", head[pos : pos + 2])
        if seg_len < 2:
            return None
        if marker in _JPEG_SOF_MARKERS:
            # precision(1) height(2) width(2) — height really does come first.
            if pos + 7 > end:
                return None
            height, width = struct.unpack(">HH", head[pos + 3 : pos + 7])
            return width, height
        pos += seg_len
    return None


def _webp_dimensions(head: bytes) -> Optional[Tuple[int, int]]:
    if len(head) < 30:
        return None
    chunk = head[12:16]
    data = head[20:]
    if chunk == b"VP8 ":
        # Lossy: 3-byte frame tag, 3-byte sync code, then 14-bit dimensions.
        if len(data) < 10 or data[3:6] != b"\x9d\x01\x2a":
            return None
        width = struct.unpack("<H", data[6:8])[0] & 0x3FFF
        height = struct.unpack("<H", data[8:10])[0] & 0x3FFF
        return width, height
    if chunk == b"VP8L":
        # Lossless: 1-byte signature then 28 bits of packed dimensions.
        if len(data) < 5 or data[0] != 0x2F:
            return None
        (bits,) = struct.unpack("<I", data[1:5])
        width = (bits & 0x3FFF) + 1
        height = ((bits >> 14) & 0x3FFF) + 1
        return width, height
    if chunk == b"VP8X":
        # Extended: canvas size as two 24-bit little-endian values, minus one.
        if len(data) < 10:
            return None
        width = int.from_bytes(data[4:7], "little") + 1
        height = int.from_bytes(data[7:10], "little") + 1
        return width, height
    return None


def _tiff_dimensions(head: bytes) -> Optional[Tuple[int, int]]:
    if len(head) < 8:
        return None
    endian = "<" if head.startswith(_TIFF_LE_MAGIC) else ">"
    (ifd_offset,) = struct.unpack(endian + "I", head[4:8])
    if ifd_offset + 2 > len(head):
        return None
    (entry_count,) = struct.unpack(endian + "H", head[ifd_offset : ifd_offset + 2])
    width = height = None
    for index in range(entry_count):
        entry = ifd_offset + 2 + index * 12
        if entry + 12 > len(head):
            break
        tag, field_type = struct.unpack(endian + "HH", head[entry : entry + 4])
        if tag not in (256, 257):
            continue
        if field_type == 3:  # SHORT, left-justified in the 4-byte value slot.
            (value,) = struct.unpack(endian + "H", head[entry + 8 : entry + 10])
        elif field_type == 4:  # LONG
            (value,) = struct.unpack(endian + "I", head[entry + 8 : entry + 12])
        else:
            continue
        if tag == 256:
            width = value
        else:
            height = value
    if width and height:
        return width, height
    return None


def _heif_dimensions(head: bytes) -> Optional[Tuple[int, int]]:
    """Best-effort ISO Base Media File Format dimensions.

    Walking the full box tree (meta > iprp > ipco > ispe) is a lot of code for
    a format this tool only ever reads as input. Instead we scan for every
    ``ispe`` (image spatial extents) box and take the largest, because a HEIC
    from a phone contains extra ``ispe`` boxes for its thumbnail and any
    auxiliary depth map. The main image is always the biggest of them.
    """
    best: Optional[Tuple[int, int]] = None
    start = 0
    while True:
        found = head.find(b"ispe", start)
        if found < 0:
            break
        start = found + 4
        payload = found + 4
        if payload + 12 > len(head):
            break
        # 4 bytes of version+flags, then width and height as 32-bit big-endian.
        width, height = struct.unpack(">II", head[payload + 4 : payload + 12])
        if not (0 < width <= 100_000 and 0 < height <= 100_000):
            continue
        if best is None or width * height > best[0] * best[1]:
            best = (width, height)
    return best


def _bmp_dimensions(head: bytes) -> Optional[Tuple[int, int]]:
    if len(head) < 26:
        return None
    width, height = struct.unpack("<ii", head[18:26])
    # A negative height means the rows are stored top-down; the pixel count is
    # the same either way.
    return abs(width), abs(height)


def _gif_dimensions(head: bytes) -> Optional[Tuple[int, int]]:
    if len(head) < 10:
        return None
    width, height = struct.unpack("<HH", head[6:10])
    return width, height


_DIMENSION_PARSERS = {
    "png": _png_dimensions,
    "jpeg": _jpeg_dimensions,
    "webp": _webp_dimensions,
    "tiff": _tiff_dimensions,
    "heif": _heif_dimensions,
    "avif": _heif_dimensions,
    "bmp": _bmp_dimensions,
    "gif": _gif_dimensions,
}


def detect_alpha(head: bytes, fmt: Optional[str]) -> Optional[bool]:
    """Does this image carry transparency?

    Worth knowing before a job rather than after. The engine will happily
    write a transparent image out as a JPEG, a format with no transparency at
    all; it prints a note saying it is converting, then does not convert, and
    every transparent area comes out black.

    Returns None where the format gives no cheap answer, which the gate treats
    as "cannot confirm" rather than "no".
    """
    if fmt == "png":
        if len(head) < 26:
            return None
        colour_type = head[25]
        if colour_type in (4, 6):      # grey+alpha, and red-green-blue+alpha
            return True
        if colour_type == 3:           # palette; transparency lives in tRNS
            return b"tRNS" in head
        return b"tRNS" in head
    if fmt == "webp":
        chunk = head[12:16]
        if chunk == b"VP8X":
            # Bit 4 of the flags byte marks an alpha channel.
            return bool(head[20] & 0x10) if len(head) > 20 else None
        if chunk == b"VP8L":
            # Bit 28 of the packed header marks alpha.
            if len(head) < 25:
                return None
            (bits,) = struct.unpack("<I", head[21:25])
            return bool((bits >> 28) & 1)
        if chunk == b"VP8 ":
            return False               # Plain lossy WebP has no alpha.
        return None
    if fmt in ("jpeg", "bmp"):
        return False
    return None


def _tail(path: str, count: int) -> bytes:
    """Read the last ``count`` bytes without pulling the file into memory."""
    size = os.path.getsize(path)
    with open(path, "rb") as handle:
        handle.seek(max(0, size - count))
        return handle.read()


def check_complete(path: str, fmt: Optional[str], size_bytes: int) -> Tuple[Optional[bool], Optional[str]]:
    """Is this file whole?

    Returns ``(verdict, note)`` where verdict is True (provably complete),
    False (provably truncated) or None (this format gives us no cheap way to
    tell, so we refuse to guess).
    """
    if size_bytes == 0:
        return False, "file is zero bytes"
    try:
        if fmt == "png":
            tail = _tail(path, len(PNG_IEND))
            if tail == PNG_IEND:
                return True, None
            return False, "PNG is missing its IEND end-of-file chunk"
        if fmt == "jpeg":
            # Some cameras and editors append padding after the end marker, so
            # look in the last stretch rather than only at the final two bytes.
            tail = _tail(path, 64)
            if JPEG_EOI in tail:
                return True, None
            return False, "JPEG is missing its end-of-image marker"
        if fmt == "webp":
            with open(path, "rb") as handle:
                header = handle.read(12)
            if len(header) < 12:
                return False, "WebP header is truncated"
            (declared,) = struct.unpack("<I", header[4:8])
            # The RIFF size counts everything after the first 8 bytes.
            actual = size_bytes - 8
            if actual < declared:
                return False, (
                    "WebP is truncated: RIFF header declares %d bytes, file has %d"
                    % (declared, actual)
                )
            return True, None
    except OSError as exc:
        return None, "could not read file tail: %s" % exc
    return None, None


def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    """Streaming checksum. Photos can be large; never read one whole."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: str, want_complete: bool = True) -> ImageInfo:
    """Identify a file, read its dimensions, and judge whether it is whole.

    Never raises for an unreadable or nonsense file — the failure lands in
    ``info.error`` so the caller can record it and move to the next job.
    """
    info = ImageInfo(path=path)
    try:
        stat = os.stat(path)
    except OSError as exc:
        info.error = "cannot stat: %s" % exc
        return info

    if not os.path.isfile(path):
        info.error = "not a regular file"
        return info

    info.size_bytes = stat.st_size
    if stat.st_size == 0:
        info.error = "file is empty"
        info.complete = False
        return info

    try:
        with open(path, "rb") as handle:
            head = handle.read(HEAD_BYTES)
    except OSError as exc:
        info.error = "cannot read: %s" % exc
        return info

    info.fmt = sniff_format(head)
    if info.fmt is None:
        info.error = "unrecognised image format (first bytes: %s)" % head[:12].hex()
        return info

    parser = _DIMENSION_PARSERS.get(info.fmt)
    dimensions = None
    if parser is not None:
        try:
            dimensions = parser(head)
        except (struct.error, IndexError, ValueError) as exc:
            info.notes.append("dimension parse failed: %s" % exc)
    if dimensions:
        info.width, info.height = dimensions
    else:
        info.error = "could not read %s dimensions from the header" % info.fmt

    try:
        info.has_alpha = detect_alpha(head, info.fmt)
    except (struct.error, IndexError, ValueError):
        info.has_alpha = None

    if want_complete:
        verdict, note = check_complete(path, info.fmt, info.size_bytes)
        info.complete = verdict
        if note:
            info.notes.append(note)

    return info
