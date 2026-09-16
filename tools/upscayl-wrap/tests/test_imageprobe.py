"""Tests for reading image headers with no third-party library."""

from __future__ import annotations

import os
import unittest

from support import Workspace, make_bmp, make_gif, make_jpeg, make_png, make_webp_lossy

from upscaylwrap import imageprobe


class SniffFormat(Workspace):
    def test_identifies_each_format_by_content(self):
        cases = [
            (make_png(os.path.join(self.root, "a.png"), 8, 6), "png", 8, 6),
            (make_jpeg(os.path.join(self.root, "b.jpg"), 16, 9), "jpeg", 16, 9),
            (make_webp_lossy(os.path.join(self.root, "c.webp"), 20, 10), "webp", 20, 10),
            (make_gif(os.path.join(self.root, "d.gif"), 12, 7), "gif", 12, 7),
            (make_bmp(os.path.join(self.root, "e.bmp"), 14, 11), "bmp", 14, 11),
        ]
        for path, expected_format, width, height in cases:
            with self.subTest(fmt=expected_format):
                info = imageprobe.probe(path)
                self.assertIsNone(info.error, info.error)
                self.assertEqual(info.fmt, expected_format)
                self.assertEqual((info.width, info.height), (width, height))

    def test_extension_is_never_trusted(self):
        # A PNG named .jpg must still be identified as a PNG.
        path = make_png(os.path.join(self.root, "lying.jpg"), 4, 4)
        info = imageprobe.probe(path)
        self.assertEqual(info.fmt, "png")

    def test_jpeg_dimensions_survive_a_leading_segment(self):
        # The helper writes an application segment before the frame header.
        # A parser reading a fixed offset would get this wrong.
        path = make_jpeg(os.path.join(self.root, "padded.jpg"), 640, 480)
        info = imageprobe.probe(path)
        self.assertEqual((info.width, info.height), (640, 480))

    def test_unknown_bytes_are_an_error_not_a_guess(self):
        path = os.path.join(self.root, "junk.png")
        with open(path, "wb") as handle:
            handle.write(b"this is not an image at all")
        info = imageprobe.probe(path)
        self.assertIsNotNone(info.error)
        self.assertFalse(info.ok)


class Completeness(Workspace):
    def test_whole_png_is_complete(self):
        info = imageprobe.probe(make_png(os.path.join(self.root, "whole.png")))
        self.assertTrue(info.complete)

    def test_truncated_png_is_caught(self):
        path = make_png(os.path.join(self.root, "cut.png"), 40, 40)
        with open(path, "rb") as handle:
            data = handle.read()
        with open(path, "wb") as handle:
            handle.write(data[: len(data) // 2])
        info = imageprobe.probe(path)
        self.assertIs(info.complete, False)

    def test_truncated_jpeg_is_caught(self):
        path = make_jpeg(os.path.join(self.root, "cut.jpg"))
        with open(path, "rb") as handle:
            data = handle.read()
        with open(path, "wb") as handle:
            handle.write(data[:-4])
        info = imageprobe.probe(path)
        self.assertIs(info.complete, False)

    def test_webp_truncation_is_caught_by_its_declared_size(self):
        path = make_webp_lossy(os.path.join(self.root, "cut.webp"))
        with open(path, "rb") as handle:
            data = handle.read()
        with open(path, "wb") as handle:
            handle.write(data[:-6])
        info = imageprobe.probe(path)
        self.assertIs(info.complete, False)

    def test_empty_file_is_an_error(self):
        path = os.path.join(self.root, "empty.png")
        open(path, "wb").close()
        info = imageprobe.probe(path)
        self.assertIsNotNone(info.error)
        self.assertIs(info.complete, False)

    def test_missing_file_does_not_raise(self):
        info = imageprobe.probe(os.path.join(self.root, "nope.png"))
        self.assertIsNotNone(info.error)


class Checksums(Workspace):
    def test_checksum_is_stable_and_content_dependent(self):
        first = make_png(os.path.join(self.root, "one.png"), 5, 5, value=10)
        same = make_png(os.path.join(self.root, "two.png"), 5, 5, value=10)
        different = make_png(os.path.join(self.root, "three.png"), 5, 5, value=250)
        self.assertEqual(imageprobe.sha256_file(first), imageprobe.sha256_file(same))
        self.assertNotEqual(imageprobe.sha256_file(first), imageprobe.sha256_file(different))


class Megapixels(Workspace):
    def test_megapixels_are_computed_from_dimensions(self):
        info = imageprobe.probe(make_png(os.path.join(self.root, "big.png"), 1000, 1000))
        self.assertAlmostEqual(info.megapixels, 1.0, places=3)


if __name__ == "__main__":
    unittest.main()
