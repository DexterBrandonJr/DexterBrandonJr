"""Shared test scaffolding.

Two things matter here. Every test gets its own temporary home, so nothing
ever reads or writes the real ledger or config. And the fake engine is
installed as a directory that looks exactly like a real Upscayl models folder,
so discovery is exercised rather than bypassed.
"""

from __future__ import annotations

import os
import struct
import sys
import tempfile
import unittest
import zlib

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

FAKE_ENGINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_upscayl.py")

SHIPPED_MODELS = (
    "upscayl-standard-4x",
    "upscayl-lite-4x",
    "high-fidelity-4x",
    "remacri-4x",
    "ultramix-balanced-4x",
    "ultrasharp-4x",
    "digital-art-4x",
)


def make_png(path: str, width: int = 8, height: int = 6, value: int = 200) -> str:
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
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)
    return path


def make_jpeg(path: str, width: int = 16, height: int = 9) -> str:
    """A JPEG with a real marker structure, not a stub.

    Includes an application segment before the frame header so that a parser
    using a fixed offset instead of walking the segments fails this test.
    """
    data = b"\xff\xd8"                                   # start of image
    comment = b"padding-that-must-be-skipped"
    data += b"\xff\xe0" + struct.pack(">H", len(comment) + 2) + comment
    sof = struct.pack(">BHHB", 8, height, width, 3) + b"\x01\x11\x00\x02\x11\x01\x03\x11\x01"
    data += b"\xff\xc0" + struct.pack(">H", len(sof) + 2) + sof
    data += b"\xff\xda" + struct.pack(">H", 8) + b"\x01\x01\x00\x00\x3f\x00"
    data += b"\x00" * 16
    data += b"\xff\xd9"                                  # end of image
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)
    return path


def make_webp_lossy(path: str, width: int = 20, height: int = 10) -> str:
    payload = b"\x00\x00\x00" + b"\x9d\x01\x2a"
    payload += struct.pack("<HH", width & 0x3FFF, height & 0x3FFF)
    payload += b"\x00" * 8
    chunk = b"VP8 " + struct.pack("<I", len(payload)) + payload
    body = b"WEBP" + chunk
    data = b"RIFF" + struct.pack("<I", len(body)) + body
    with open(path, "wb") as handle:
        handle.write(data)
    return path


def make_gif(path: str, width: int = 12, height: int = 7) -> str:
    data = b"GIF89a" + struct.pack("<HH", width, height) + b"\x00\x00\x00"
    with open(path, "wb") as handle:
        handle.write(data)
    return path


def make_bmp(path: str, width: int = 14, height: int = 11) -> str:
    header = b"BM" + struct.pack("<IHHI", 54 + width * height * 3, 0, 0, 54)
    dib = struct.pack("<IiiHH", 40, width, height, 1, 24) + b"\x00" * 24
    with open(path, "wb") as handle:
        handle.write(header + dib)
    return path


class Workspace(unittest.TestCase):
    """A test case with an isolated home, config, ledger and fake engine."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = self.temporary.name
        self.addCleanup(self.temporary.cleanup)

        self.config_home = os.path.join(self.root, "config")
        self.data_home = os.path.join(self.root, "data")
        self.inputs = os.path.join(self.root, "in")
        self.outputs = os.path.join(self.root, "out")
        self.models_dir = os.path.join(self.root, "engine", "models")
        for directory in (self.config_home, self.data_home, self.inputs, self.outputs, self.models_dir):
            os.makedirs(directory, exist_ok=True)

        self._saved_environment = {}
        for key, value in (
            ("XDG_CONFIG_HOME", self.config_home),
            ("XDG_DATA_HOME", self.data_home),
            ("UPSCAYL_BIN", self.engine_path()),
            ("UPSCAYL_MODELS", self.models_dir),
            ("FAKE_UPSCAYL_MODE", "ok"),
        ):
            self._saved_environment[key] = os.environ.get(key)
            os.environ[key] = value
        self.addCleanup(self._restore_environment)

        self.write_models()
        self.make_engine()

    def _restore_environment(self) -> None:
        for key, value in self._saved_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def engine_path(self) -> str:
        return os.path.join(self.root, "engine", "upscayl-bin")

    def make_engine(self) -> str:
        """A shell wrapper so the engine is an executable file, as it would be."""
        path = self.engine_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\nexec %s %s \"$@\"\n" % (sys.executable, FAKE_ENGINE))
        os.chmod(path, 0o755)
        return path

    def write_models(self, names=SHIPPED_MODELS) -> None:
        for name in names:
            for extension in (".param", ".bin"):
                with open(os.path.join(self.models_dir, name + extension), "wb") as handle:
                    handle.write(b"fake model data")

    def set_mode(self, mode: str) -> None:
        os.environ["FAKE_UPSCAYL_MODE"] = mode

    def an_image(self, name: str = "photo.png", width: int = 8, height: int = 6) -> str:
        return make_png(os.path.join(self.inputs, name), width, height)
