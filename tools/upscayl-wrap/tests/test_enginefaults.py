"""Tests for reading failure out of the engine's error stream.

These matter because the engine's exit code is a constant zero once it has
started processing, so its error output is the only evidence there is.
"""

from __future__ import annotations

import unittest

from support import Workspace  # noqa: F401  (keeps the import path consistent)

from upscaylwrap import enginefaults

FAULT_OOM = next(f for f in enginefaults.FAULTS if f.key == "gpu_out_of_memory")


class Recognising(unittest.TestCase):
    def test_out_of_memory(self):
        fault = enginefaults.find_fault("... vkAllocateMemory failed -2\n")
        self.assertIsNotNone(fault)
        self.assertEqual(fault.key, "gpu_out_of_memory")
        self.assertTrue(fault.retry_smaller_tile)

    def test_device_lost_in_both_spellings(self):
        for text in ("vkQueueSubmit failed -4", "vkWaitForFences failed -4"):
            fault = enginefaults.find_fault(text)
            self.assertEqual(fault.key, "gpu_lost", text)
            self.assertTrue(fault.retry_smaller_tile)

    def test_no_graphics_device(self):
        fault = enginefaults.find_fault("vkEnumeratePhysicalDevices failed -3")
        self.assertEqual(fault.key, "no_gpu")
        self.assertFalse(fault.retry_smaller_tile)

    def test_unreadable_model_is_recognised(self):
        # This is what produces a black image with a success banner.
        fault = enginefaults.find_fault("fopen /models/x.param failed")
        self.assertEqual(fault.key, "model_unreadable")

    def test_the_real_model_load_failures_are_recognised(self):
        # These are the exact shapes the neural-network library prints, taken
        # from its source. Earlier patterns here matched strings it never
        # emits, which is the same as having no check at all: the engine
        # discards the load return codes, so these lines are the only sign
        # that a model failed and the picture is about to be black.
        for line in (
            "layer load_model 12 conv_first failed",
            "layer load_param 3 conv failed",
            "ParamDict load_param 7 body.0 failed",
            "ParamDict load_param_bin 2 failed",
            "load_model error at layer 4, parameter file has inconsistent content.",
            "layer create_pipeline 9 conv failed",
            "layer upload_model 1 conv failed",
            "find_blob_index_by_name data failed",
            "find_layer_index_by_name out failed",
            "compile spir-v module failed",
            "fopen /models/upscayl-standard-4x.param failed",
        ):
            fault = enginefaults.find_fault(line)
            self.assertIsNotNone(fault, line)
            self.assertEqual(fault.key, "model_unreadable", line)

    def test_encoder_refusal(self):
        fault = enginefaults.find_fault("🚨 Error: Couldn't write the image /tmp/a.png")
        self.assertEqual(fault.key, "write_failed")

    def test_decode_refusal(self):
        fault = enginefaults.find_fault("🚨 Error: Couldn't read the image '/tmp/a.png'! (channels: 0)")
        self.assertEqual(fault.key, "read_failed")

    def test_bad_models_directory(self):
        fault = enginefaults.find_fault("🚨 Error: Unknown model dir type.")
        self.assertEqual(fault.key, "bad_model_dir")


class NotConfused(unittest.TestCase):
    def test_a_clean_run_has_no_fault(self):
        self.assertIsNone(enginefaults.find_fault("100.00%\n🙌 Upscayled Successfully!\n"))

    def test_nothing_at_all_has_no_fault(self):
        self.assertIsNone(enginefaults.find_fault(""))
        self.assertIsNone(enginefaults.find_fault(None))

    def test_the_ordinary_progress_chatter_is_not_a_fault(self):
        chatter = "✨ Detected scale x4\n📂 Creating directory: /out\n100.00%\n"
        self.assertIsNone(enginefaults.find_fault(chatter))

    def test_the_alpha_notice_is_not_a_fault(self):
        # The engine prints this as information, not as an error.
        notice = "ℹ️ Info: Image /a.png has alpha channel! Converting to RGB for JPEG output.\n"
        self.assertIsNone(enginefaults.find_fault(notice))

    def test_a_success_banner_does_not_cancel_an_error(self):
        # Both appear together in the black-image failure, and the error wins.
        both = "vkAllocateMemory failed -2\n100.00%\n🙌 Upscayled Successfully!\n"
        self.assertEqual(enginefaults.find_fault(both).key, "gpu_out_of_memory")


class Explaining(unittest.TestCase):
    def test_the_description_names_the_cause_and_the_fix(self):
        fault = enginefaults.find_fault("vkAllocateMemory failed -2")
        text = enginefaults.describe(fault, "vkAllocateMemory failed -2")
        self.assertIn("memory", text)
        self.assertIn("--tile", text)

    def test_the_matching_line_is_quoted(self):
        lines = enginefaults.matching_lines(
            "noise\nvkAllocateMemory failed -2\nmore noise", FAULT_OOM
        )
        self.assertEqual(len(lines), 1)
        self.assertIn("vkAllocateMemory", lines[0])



class TileLadder(unittest.TestCase):
    def test_it_halves(self):
        self.assertEqual(enginefaults.next_tile_size(512), 256)
        self.assertEqual(enginefaults.next_tile_size(256), 128)

    def test_automatic_starts_from_the_engines_own_cap(self):
        # Zero means the engine chooses, and its choice never exceeds 200.
        self.assertEqual(enginefaults.next_tile_size(0), 100)

    def test_it_stops_before_the_tiles_get_useless(self):
        self.assertIsNone(enginefaults.next_tile_size(32))
        self.assertIsNone(enginefaults.next_tile_size(63))

    def test_the_ladder_terminates(self):
        size = 512
        steps = 0
        while size is not None:
            size = enginefaults.next_tile_size(size)
            steps += 1
            self.assertLess(steps, 20, "the ladder should not run forever")


if __name__ == "__main__":
    unittest.main()
