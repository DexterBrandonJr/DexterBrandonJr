"""Tests for converting formats the engine cannot read.

The engine decodes JPEG, PNG, WebP and BMP and nothing else. HEIC is what an
iPhone photographs in, so this path is not an edge case on a Mac.
"""

from __future__ import annotations

import unittest

from support import Workspace, make_heif, make_png

import os

from upscaylwrap import counterfactual, imageprobe, transcode
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


class Converting(Workspace):
    """The path an iPhone photograph actually takes.

    Until these existed, to_png was called by nothing in the suite — the whole
    conversion path was shipped untested.
    """

    def work_dir(self) -> str:
        return os.path.join(self.root, "convert-work")

    def test_a_heic_becomes_a_usable_png_of_the_same_size(self):
        source = make_heif(os.path.join(self.inputs, "iphone.heic"), 120, 90)
        converted, record = transcode.to_png(source, work_dir=self.work_dir())
        self.addCleanup(transcode.cleanup, record)

        self.assertIsNotNone(converted, record.get("note"))
        self.assertTrue(record["converted"])
        info = imageprobe.probe(converted)
        self.assertEqual(info.fmt, "png")
        self.assertEqual((info.width, info.height), (120, 90))
        self.assertIs(info.complete, True)

    def test_the_copy_goes_to_the_work_directory_not_beside_the_original(self):
        source = make_heif(os.path.join(self.inputs, "iphone.heic"))
        converted, record = transcode.to_png(source, work_dir=self.work_dir())
        self.addCleanup(transcode.cleanup, record)
        self.assertTrue(converted.startswith(self.work_dir()))
        self.assertEqual(os.listdir(self.inputs), ["iphone.heic"])

    def test_cleanup_removes_it(self):
        source = make_heif(os.path.join(self.inputs, "iphone.heic"))
        converted, record = transcode.to_png(source, work_dir=self.work_dir())
        self.assertTrue(os.path.exists(converted))
        transcode.cleanup(record)
        self.assertFalse(os.path.exists(converted))

    def test_cleanup_twice_is_harmless(self):
        source = make_heif(os.path.join(self.inputs, "iphone.heic"))
        _, record = transcode.to_png(source, work_dir=self.work_dir())
        transcode.cleanup(record)
        transcode.cleanup(record)

    def test_a_failed_conversion_reports_and_leaves_nothing(self):
        os.environ["FAKE_SIPS_MODE"] = "fail"
        self.addCleanup(os.environ.pop, "FAKE_SIPS_MODE", None)
        source = make_heif(os.path.join(self.inputs, "iphone.heic"))
        converted, record = transcode.to_png(source, work_dir=self.work_dir())
        self.assertIsNone(converted)
        self.assertFalse(record["converted"])
        self.assertIn("unable to render", record.get("note", ""))
        self.assertEqual(os.listdir(self.work_dir()), [])

    def test_a_conversion_that_writes_rubbish_is_caught(self):
        # Exit code 0 and a file on disk is not proof of anything, here as
        # much as with the engine itself.
        os.environ["FAKE_SIPS_MODE"] = "garbage"
        self.addCleanup(os.environ.pop, "FAKE_SIPS_MODE", None)
        source = make_heif(os.path.join(self.inputs, "iphone.heic"))
        converted, record = transcode.to_png(source, work_dir=self.work_dir())
        self.assertIsNone(converted)
        self.assertIn("not a usable image", record.get("note", ""))
        self.assertEqual(os.listdir(self.work_dir()), [])

    def test_a_conversion_that_writes_nothing_is_caught(self):
        os.environ["FAKE_SIPS_MODE"] = "nothing"
        self.addCleanup(os.environ.pop, "FAKE_SIPS_MODE", None)
        source = make_heif(os.path.join(self.inputs, "iphone.heic"))
        converted, record = transcode.to_png(source, work_dir=self.work_dir())
        self.assertIsNone(converted)

    def test_without_sips_it_says_so_rather_than_pretending(self):
        saved = transcode.SIPS
        transcode.SIPS = os.path.join(self.root, "no-such-sips")
        self.addCleanup(setattr, transcode, "SIPS", saved)
        source = make_heif(os.path.join(self.inputs, "iphone.heic"))
        converted, record = transcode.to_png(source, work_dir=self.work_dir())
        self.assertIsNone(converted)
        self.assertFalse(record["available"])
        self.assertIn("sips is not available", record.get("note", ""))


class AnIPhonePhotographEndToEnd(Workspace):
    def test_a_heic_is_converted_and_upscaled(self):
        from upscaylwrap.autonomy import Autonomy
        from upscaylwrap.config import Config, discover, paths
        from upscaylwrap.ledger import Ledger, STATUS_OK
        from upscaylwrap.runner import JobRequest, Runner

        app_paths = paths()
        app_paths.ensure()
        config = Config.load()
        autonomy = Autonomy(app_paths.state_file, app_paths.halt_file)
        autonomy.set_stage(3)
        runner = Runner(
            config, discover(config), Ledger(app_paths.ledger), autonomy,
            app_paths.quarantine_dir,
        )

        source = make_heif(os.path.join(self.inputs, "iphone.heic"), 100, 75)
        result = runner.run(
            JobRequest(
                input_path=source,
                output_path=os.path.join(self.outputs, "iphone_4x.png"),
                output_root=self.outputs,
                scale=4,
                model_name="upscayl-standard-4x",
                human_approved=True,
            )
        )
        self.assertEqual(result.status, STATUS_OK, result.message)
        self.assertEqual((result.row.output_width, result.row.output_height), (400, 300))
        # The row says what actually went into the engine, not only what was asked for.
        self.assertTrue(result.row.converted_input["converted"])
        self.assertEqual(result.row.input_format, "heif")

    def test_the_converted_copy_is_not_left_behind(self):
        from upscaylwrap.autonomy import Autonomy
        from upscaylwrap.config import Config, discover, paths
        from upscaylwrap.ledger import Ledger
        from upscaylwrap.runner import JobRequest, Runner

        app_paths = paths()
        app_paths.ensure()
        config = Config.load()
        autonomy = Autonomy(app_paths.state_file, app_paths.halt_file)
        autonomy.set_stage(3)
        runner = Runner(
            config, discover(config), Ledger(app_paths.ledger), autonomy,
            app_paths.quarantine_dir,
        )
        source = make_heif(os.path.join(self.inputs, "iphone.heic"), 100, 75)
        result = runner.run(
            JobRequest(
                input_path=source,
                output_path=os.path.join(self.outputs, "iphone_4x.png"),
                output_root=self.outputs, scale=4,
                model_name="upscayl-standard-4x", human_approved=True,
            )
        )
        target = (result.row.converted_input or {}).get("target")
        self.assertIsNotNone(target)
        self.assertFalse(os.path.exists(target), "the converted copy was left on disk")


class TheCheapAlternative(Workspace):
    """The counterfactual, which was also never executed by any test."""

    def test_the_baseline_runs_and_is_measured(self):
        source = make_png(os.path.join(self.inputs, "photo.png"), 100, 50)
        baseline = counterfactual.run_baseline(source, 400)
        self.assertTrue(baseline["available"])
        self.assertEqual(baseline["exit_code"], 0)
        self.assertEqual(baseline["output_width"], 400)
        self.assertIn("duration_seconds", baseline)

    def test_it_leaves_no_file_behind(self):
        source = make_png(os.path.join(self.inputs, "photo.png"), 100, 50)
        before = set(os.listdir(self.root))
        counterfactual.run_baseline(source, 400)
        self.assertEqual(set(os.listdir(self.root)), before)

    def test_the_comparison_expresses_the_upscale_as_a_multiple(self):
        source = make_png(os.path.join(self.inputs, "photo.png"), 100, 50)
        baseline = counterfactual.run_baseline(source, 400)
        comparison = counterfactual.compare(
            baseline,
            {"duration_seconds": (baseline["duration_seconds"] or 0.01) * 10,
             "output_bytes": (baseline["output_bytes"] or 1) * 3,
             "output_width": 400, "output_height": 200},
        )
        self.assertTrue(comparison["comparable"])
        self.assertGreater(comparison["times_slower"], 1)
        self.assertTrue(comparison["same_dimensions"])

    def test_a_failed_baseline_is_not_comparable(self):
        os.environ["FAKE_SIPS_MODE"] = "fail"
        self.addCleanup(os.environ.pop, "FAKE_SIPS_MODE", None)
        source = make_png(os.path.join(self.inputs, "photo.png"), 100, 50)
        baseline = counterfactual.run_baseline(source, 400)
        self.assertFalse(counterfactual.compare(baseline, {})["comparable"])


if __name__ == "__main__":
    unittest.main()
