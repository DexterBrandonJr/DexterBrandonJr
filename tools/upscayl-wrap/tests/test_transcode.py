"""Tests for converting formats the engine cannot read.

The engine decodes JPEG, PNG, WebP and BMP and nothing else. HEIC is what an
iPhone photographs in, so this path is not an edge case on a Mac.
"""

from __future__ import annotations

import unittest

from support import Workspace  # noqa: F401

from upscaylwrap import imageprobe, transcode
from upscaylwrap.config import native_scale_of


class WhatTheEngineCanRead(unittest.TestCase):
    def test_the_four_formats_it_decodes_need_no_conversion(self):
        for fmt in ("png", "jpeg", "webp", "bmp"):
            self.assertFalse(transcode.needed(fmt), fmt)

    def test_the_formats_it_cannot_decode_need_conversion(self):
        for fmt in ("heif", "avif", "tiff", "gif"):
            self.assertTrue(transcode.needed(fmt), fmt)

    def test_heic_is_in_the_convertible_set(self):
        # The one that matters: an iPhone photograph.
        self.assertIn("heif", transcode.TRANSCODABLE)

    def test_the_accepted_set_is_larger_than_the_engines(self):
        # We accept more than the engine can read, because we convert the gap.
        self.assertTrue(
            imageprobe.ENGINE_READABLE_FORMATS < imageprobe.READABLE_FORMATS
        )

    def test_bmp_goes_in_but_never_comes_out(self):
        self.assertIn("bmp", imageprobe.ENGINE_READABLE_FORMATS)
        self.assertNotIn("bmp", imageprobe.WRITABLE_FORMATS)

    def test_an_unknown_format_needs_conversion_but_cannot_have_it(self):
        self.assertTrue(transcode.needed("postscript"))
        self.assertFalse(transcode.can_convert("postscript"))

    def test_the_remedy_names_a_real_command(self):
        self.assertIn("sips", transcode.remedy("heif"))


class EngineScaleDetection(unittest.TestCase):
    """The tool must predict what the engine will do, not what a name means."""

    def test_the_seven_shipped_models_all_read_as_four(self):
        for name in (
            "upscayl-standard-4x", "upscayl-lite-4x", "high-fidelity-4x",
            "remacri-4x", "ultramix-balanced-4x", "ultrasharp-4x", "digital-art-4x",
        ):
            self.assertEqual(native_scale_of(name), 4, name)

    def test_both_spellings_are_understood(self):
        self.assertEqual(native_scale_of("realesrgan-x4plus"), 4)
        self.assertEqual(native_scale_of("something-4x"), 4)

    def test_x16_reads_as_one_because_that_is_what_the_engine_does(self):
        # The engine tests "x1" before "x16", and "x16" contains "x1". Saying
        # 16 here would be more correct and less useful: the prediction would
        # disagree with reality on every job with such a model.
        self.assertEqual(native_scale_of("fancy-x16"), 1)

    def test_the_other_spelling_of_sixteen_does_reach_sixteen(self):
        self.assertEqual(native_scale_of("fancy-16x"), 16)

    def test_a_name_with_no_scale_token_gives_nothing(self):
        self.assertIsNone(native_scale_of("mystery-model"))


if __name__ == "__main__":
    unittest.main()
