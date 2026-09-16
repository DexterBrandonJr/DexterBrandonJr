"""Tests for the rules that decide whether a job may run.

The gate is pure, so none of these tests touch a disk or an engine.
"""

from __future__ import annotations

import unittest

from support import Workspace

from upscaylwrap import gate
from upscaylwrap.imageprobe import READABLE_FORMATS, WRITABLE_FORMATS


def facts(**overrides) -> gate.JobFacts:
    """A job that passes every rule, so each test changes exactly one thing."""
    defaults = dict(
        input_path="/photos/a.png",
        output_path="/out/a_4x.png",
        output_root="/out",
        input_format="png",
        input_width=1000,
        input_height=800,
        input_complete=True,
        input_error=None,
        input_bytes=500_000,
        scale=4,
        model_name="upscayl-standard-4x",
        model_usable=True,
        model_native_scale=4,
        output_format="png",
        output_exists=False,
        free_disk_bytes=500 * 1024 * 1024 * 1024,
        engine_present=True,
        engine_executable=True,
        readable_formats=READABLE_FORMATS,
        writable_formats=WRITABLE_FORMATS,
        stage=3,
        halted=False,
        human_approved=False,
        case_insensitive_paths=False,
        models_dir="/Applications/Upscayl.app/Contents/Resources/models",
        input_has_alpha=False,
    )
    defaults.update(overrides)
    return gate.JobFacts(**defaults)


def failed(decision, name):
    return any(c.name == name and not c.passed for c in decision.checks)


class BaselineAllows(unittest.TestCase):
    def test_a_sane_job_is_allowed(self):
        decision = gate.evaluate(facts())
        self.assertTrue(decision.allowed, decision.reason)
        self.assertEqual(decision.denials, [])


class InputRules(unittest.TestCase):
    def test_unreadable_input_is_refused(self):
        decision = gate.evaluate(facts(input_error="cannot read"))
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "input_readable"))

    def test_truncated_input_is_refused(self):
        decision = gate.evaluate(facts(input_complete=False))
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "input_not_truncated"))

    def test_unknown_input_completeness_is_allowed(self):
        # Some formats give us no cheap way to tell. Refusing them all would
        # make the tool useless on those formats.
        decision = gate.evaluate(facts(input_complete=None))
        self.assertTrue(decision.allowed, decision.reason)

    def test_missing_dimensions_are_refused(self):
        decision = gate.evaluate(facts(input_width=None, input_height=None))
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "input_has_dimensions"))


class PathRules(unittest.TestCase):
    def test_writing_over_the_original_is_refused(self):
        decision = gate.evaluate(
            facts(input_path="/out/a.png", output_path="/out/a.png", output_root="/out")
        )
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "output_is_not_input"))

    def test_output_escaping_its_root_is_refused(self):
        decision = gate.evaluate(facts(output_path="/somewhere/else.png"))
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "output_within_root"))

    def test_input_inside_the_output_root_is_refused(self):
        # This is the rule that stops a watch folder eating its own results.
        decision = gate.evaluate(facts(input_path="/out/previous_4x.png"))
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "input_outside_output_root"))

    def test_a_sibling_directory_sharing_a_prefix_is_not_inside(self):
        # /output-archive must not count as being inside /output.
        self.assertFalse(gate.is_within("/output-archive/a.png", "/output"))
        self.assertTrue(gate.is_within("/output/a.png", "/output"))
        self.assertTrue(gate.is_within("/output", "/output"))

    def test_case_differences_still_count_as_the_same_place(self):
        # A Mac is normally case-insensitive, so this must not be an escape.
        self.assertTrue(gate.is_within("/Out/A.png", "/out", case_insensitive=True))
        self.assertFalse(gate.is_within("/Out/A.png", "/out", case_insensitive=False))

    def test_existing_output_is_refused_unless_forced(self):
        decision = gate.evaluate(facts(output_exists=True))
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "output_free_or_forced"))
        self.assertTrue(gate.evaluate(facts(output_exists=True, force_overwrite=True)).allowed)


class BudgetRules(unittest.TestCase):
    def test_a_huge_output_is_refused(self):
        # 8000x6000 at 4x is 768 megapixels, over the default budget.
        decision = gate.evaluate(facts(input_width=8000, input_height=6000))
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "within_pixel_budget"))

    def test_a_full_disk_is_refused(self):
        decision = gate.evaluate(facts(free_disk_bytes=1024))
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "within_disk_budget"))

    def test_unknown_free_space_warns_rather_than_refusing(self):
        decision = gate.evaluate(facts(free_disk_bytes=None))
        self.assertTrue(decision.allowed)

    def test_predicted_size_grows_with_the_square_of_the_scale(self):
        two = gate.predicted_output_megapixels(facts(scale=2))
        four = gate.predicted_output_megapixels(facts(scale=4))
        self.assertAlmostEqual(four / two, 4.0, places=6)


class ModelRules(unittest.TestCase):
    def test_an_incomplete_model_is_refused(self):
        decision = gate.evaluate(facts(model_usable=False))
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "model_usable"))

    def test_a_scale_the_model_was_not_trained_for_only_warns(self):
        decision = gate.evaluate(facts(scale=2, model_native_scale=4))
        self.assertTrue(decision.allowed, decision.reason)
        self.assertTrue(any(c.name == "scale_matches_model" for c in decision.warnings))

    def test_strict_policy_turns_that_warning_into_a_refusal(self):
        decision = gate.evaluate(facts(scale=2, model_native_scale=4, scale_policy="strict"))
        self.assertFalse(decision.allowed)

    def test_an_unwritable_output_format_is_refused(self):
        decision = gate.evaluate(facts(output_format="tiff"))
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "output_format_writable"))


class RulesFromKnownEngineFailures(unittest.TestCase):
    """Each of these prevents a specific, documented way the engine breaks."""

    def test_a_models_directory_without_the_word_models_is_refused(self):
        # The engine checks its own models path for that word and refuses to
        # start without it, with an error that explains nothing.
        decision = gate.evaluate(facts(models_dir="/opt/weights"))
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "models_dir_accepted"))

    def test_the_models_check_is_case_sensitive_like_the_engines(self):
        # The engine's search is case-sensitive even though a Mac's filesystem
        # is not, so a directory called "Models" really does fail there. A
        # looser check here would pass a job the engine then rejects.
        self.assertFalse(gate.evaluate(facts(models_dir="/opt/Models")).allowed)
        self.assertTrue(gate.evaluate(facts(models_dir="/opt/models2")).allowed)

    def test_a_normal_models_directory_passes(self):
        self.assertTrue(gate.evaluate(facts(models_dir="/Applications/Upscayl.app/Contents/Resources/models")).allowed)

    def test_a_tiny_image_is_refused(self):
        # A four-pixel-wide image resets the graphics device as reliably as an
        # enormous one does.
        decision = gate.evaluate(facts(input_width=4, input_height=44))
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "input_large_enough"))

    def test_transparency_into_a_jpeg_is_refused(self):
        # The engine says it is converting transparency away, then does not,
        # and every transparent area comes out black.
        decision = gate.evaluate(facts(input_has_alpha=True, output_format="jpg"))
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "alpha_survives_format"))

    def test_transparency_into_png_or_webp_is_fine(self):
        for fmt in ("png", "webp"):
            self.assertTrue(gate.evaluate(facts(input_has_alpha=True, output_format=fmt)).allowed, fmt)

    def test_opaque_into_a_jpeg_is_fine(self):
        self.assertTrue(gate.evaluate(facts(input_has_alpha=False, output_format="jpg")).allowed)

    def test_an_output_past_the_encoders_own_limit_is_refused(self):
        # This ceiling is the encoder's 32-bit arithmetic, not this machine's
        # memory, so a bigger Mac does not make it go away.
        decision = gate.evaluate(
            facts(input_width=20000, input_height=20000, scale=4, max_output_megapixels=10_000_000)
        )
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "within_encoder_limit"))

    def test_that_limit_does_not_apply_to_other_formats(self):
        decision = gate.evaluate(
            facts(
                input_width=20000, input_height=20000, scale=4,
                output_format="webp", max_output_megapixels=10_000_000,
            )
        )
        self.assertFalse(failed(decision, "within_encoder_limit"))


class EngineRules(unittest.TestCase):
    def test_a_missing_engine_is_refused(self):
        decision = gate.evaluate(facts(engine_present=False))
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "engine_present"))

    def test_a_non_executable_engine_is_refused(self):
        decision = gate.evaluate(facts(engine_executable=False))
        self.assertFalse(decision.allowed)


class AutonomyRules(unittest.TestCase):
    def test_a_halt_refuses_everything(self):
        decision = gate.evaluate(facts(halted=True))
        self.assertFalse(decision.allowed)
        self.assertTrue(failed(decision, "not_halted"))

    def test_stage_one_needs_explicit_approval(self):
        self.assertFalse(gate.evaluate(facts(stage=1)).allowed)
        self.assertTrue(gate.evaluate(facts(stage=1, human_approved=True)).allowed)

    def test_stage_two_acts_inside_its_envelope(self):
        inside = facts(
            stage=2,
            approved_models=("upscayl-standard-4x",),
            approved_max_scale=4,
            approved_roots=("/photos",),
        )
        self.assertTrue(gate.evaluate(inside).allowed)

    def test_stage_two_refuses_a_model_outside_its_envelope(self):
        decision = gate.evaluate(
            facts(stage=2, model_name="remacri-4x", approved_models=("upscayl-standard-4x",))
        )
        self.assertFalse(decision.allowed)

    def test_stage_two_refuses_a_scale_above_its_envelope(self):
        decision = gate.evaluate(
            facts(stage=2, scale=8, approved_models=("upscayl-standard-4x",), approved_max_scale=4)
        )
        self.assertFalse(decision.allowed)

    def test_stage_three_needs_no_approval(self):
        self.assertTrue(gate.evaluate(facts(stage=3)).allowed)


class Reporting(unittest.TestCase):
    def test_a_refusal_explains_itself(self):
        decision = gate.evaluate(facts(engine_present=False, halted=True))
        self.assertFalse(decision.allowed)
        self.assertIn("engine", decision.reason.lower())
        self.assertTrue(len(decision.denials) >= 2)

    def test_every_check_is_recorded_even_when_it_passes(self):
        decision = gate.evaluate(facts())
        names = {c["name"] for c in decision.as_dicts()}
        self.assertIn("within_pixel_budget", names)
        self.assertIn("input_outside_output_root", names)


if __name__ == "__main__":
    unittest.main()
