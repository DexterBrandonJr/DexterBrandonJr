"""End-to-end tests against a fake engine.

These are the tests that matter most, because they cover the thing the
wrapper exists to do: notice when the engine has not actually worked. Each
failure mode below is one the real engine is known to produce.
"""

from __future__ import annotations

import os
import unittest

from support import Workspace, make_png

from upscaylwrap.autonomy import Autonomy
from upscaylwrap.config import Config, discover, paths
from upscaylwrap.ledger import Ledger, STATUS_FAILED, STATUS_OK, STATUS_REJECTED, STATUS_SKIPPED
from upscaylwrap.runner import JobRequest, Runner, _valid_jobs_spec, build_command


class RunnerCase(Workspace):
    def setUp(self):
        super().setUp()
        self.app_paths = paths()
        self.app_paths.ensure()
        self.config = Config.load()
        self.config.default_scale = 4
        self.discovery = discover(self.config)
        self.ledger = Ledger(self.app_paths.ledger)
        self.autonomy = Autonomy(self.app_paths.state_file, self.app_paths.halt_file)
        self.autonomy.set_stage(3)

    def runner(self, **kwargs) -> Runner:
        return Runner(
            self.config,
            self.discovery,
            self.ledger,
            self.autonomy,
            self.app_paths.quarantine_dir,
            **kwargs,
        )

    def request(self, name="photo.png", width=8, height=6, **overrides) -> JobRequest:
        source = make_png(os.path.join(self.inputs, name), width, height)
        values = dict(
            input_path=source,
            output_path=os.path.join(self.outputs, name.replace(".png", "_4x.png")),
            output_root=self.outputs,
            scale=4,
            model_name="upscayl-standard-4x",
            output_format="png",
            human_approved=True,
        )
        values.update(overrides)
        return JobRequest(**values)


class Discovery(RunnerCase):
    def test_the_engine_and_models_are_found(self):
        self.assertTrue(self.discovery.bin_path)
        self.assertEqual(len(self.discovery.usable_models), 7)

    def test_every_shipped_model_reads_as_four_times(self):
        for model in self.discovery.usable_models:
            self.assertEqual(model.native_scale, 4, model.name)


class HappyPath(RunnerCase):
    def test_a_job_produces_an_image_of_the_predicted_size(self):
        result = self.runner().run(self.request(width=10, height=5))
        self.assertEqual(result.status, STATUS_OK, result.message)
        self.assertTrue(os.path.isfile(result.row.output_path))
        self.assertEqual(result.row.output_width, 40)
        self.assertEqual(result.row.output_height, 20)

    def test_the_row_records_the_whole_job(self):
        result = self.runner().run(self.request())
        row = self.ledger.rows()[-1]
        for field in (
            "id", "run_id", "input_path", "output_path", "model", "scale",
            "input_sha256", "output_sha256", "duration_seconds", "command",
            "prediction", "score", "gate_checks",
        ):
            self.assertIsNotNone(row.get(field), "missing %s" % field)

    def test_the_prediction_is_scored_right(self):
        result = self.runner().run(self.request())
        self.assertEqual(result.row.score["verdict"], "right")

    def test_no_temporary_file_is_left_behind(self):
        self.runner().run(self.request())
        leftovers = [n for n in os.listdir(self.outputs) if n.startswith(".upscayl-wrap-tmp-")]
        self.assertEqual(leftovers, [])

    def test_a_second_run_skips_work_already_done(self):
        self.runner().run(self.request())
        second = self.runner().run(self.request())
        self.assertEqual(second.status, STATUS_SKIPPED)

    def test_force_redoes_it(self):
        self.runner().run(self.request())
        again = self.runner().run(self.request(force=True))
        self.assertEqual(again.status, STATUS_OK)


class TheEngineLies(RunnerCase):
    """Every one of these exits 0 or leaves something that looks like output."""

    def test_success_with_no_output_file_is_a_failure(self):
        self.set_mode("silent-failure")
        result = self.runner().run(self.request())
        self.assertEqual(result.status, STATUS_FAILED)
        self.assertIn("wrote no output", result.message)

    def test_an_empty_output_is_a_failure(self):
        self.set_mode("empty")
        result = self.runner().run(self.request())
        self.assertEqual(result.status, STATUS_FAILED)

    def test_a_truncated_output_is_a_failure(self):
        self.set_mode("truncated")
        result = self.runner().run(self.request())
        self.assertEqual(result.status, STATUS_FAILED)
        self.assertIn("truncated", result.message)

    def test_a_failed_job_leaves_no_file_where_the_result_belongs(self):
        self.set_mode("truncated")
        request = self.request()
        self.runner().run(request)
        self.assertFalse(os.path.exists(request.output_path))

    def test_the_partial_output_is_kept_for_inspection(self):
        self.set_mode("truncated")
        self.runner().run(self.request())
        quarantined = os.listdir(self.app_paths.quarantine_dir)
        self.assertEqual(len(quarantined), 1)

    def test_a_start_up_failure_is_reported_as_one(self):
        # A non-zero exit can only come from start-up validation, so the
        # message should say that rather than blaming the picture.
        self.set_mode("crash")
        result = self.runner().run(self.request())
        self.assertEqual(result.status, STATUS_FAILED)
        self.assertIn("refused to start", result.message)
        self.assertIn("vkEnumeratePhysicalDevices", result.row.stderr_tail or "")

    def test_the_wrong_scale_is_caught_by_the_score(self):
        # The output here is a perfectly valid PNG. Only the prediction made
        # before the run reveals that it is half the size it should be.
        self.set_mode("wrong-scale")
        result = self.runner().run(self.request(width=10, height=10))
        self.assertEqual(result.status, STATUS_OK)
        self.assertEqual(result.row.score["verdict"], "wrong")
        self.assertIn("WARNING", result.message)

    def test_a_hang_is_stopped_by_the_timeout(self):
        self.set_mode("hang")
        self.config.timeout_seconds = 2
        result = self.runner().run(self.request())
        self.assertEqual(result.status, STATUS_FAILED)
        self.assertIn("timed out", result.message)


class TheGateStopsIt(RunnerCase):
    def test_a_corrupt_input_is_refused_before_the_engine_runs(self):
        path = os.path.join(self.inputs, "broken.png")
        with open(path, "wb") as handle:
            handle.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10)
        result = self.runner().run(self.request(input_path=path))
        self.assertEqual(result.status, STATUS_REJECTED)

    def test_re_upscaling_its_own_output_is_refused(self):
        first = self.runner().run(self.request())
        result = self.runner().run(
            self.request(input_path=first.row.output_path, name="again.png")
        )
        self.assertEqual(result.status, STATUS_REJECTED)
        self.assertIn("re-upscale its own results", result.message)

    def test_an_oversized_job_is_refused(self):
        self.config.max_output_megapixels = 0.001
        result = self.runner().run(self.request(width=100, height=100))
        self.assertEqual(result.status, STATUS_REJECTED)
        self.assertIn("megapixel budget", result.message)

    def test_stage_one_refuses_an_unapproved_job(self):
        self.autonomy.set_stage(1)
        result = self.runner().run(self.request(human_approved=False))
        self.assertEqual(result.status, STATUS_REJECTED)

    def test_a_refusal_is_still_recorded(self):
        self.autonomy.set_stage(1)
        self.runner().run(self.request(human_approved=False))
        rows = self.ledger.rows()
        self.assertEqual(rows[-1]["status"], STATUS_REJECTED)
        self.assertTrue(rows[-1]["gate_checks"])


class FailuresHalt(RunnerCase):
    def test_repeated_failures_trip_the_halt(self):
        self.set_mode("crash")
        self.config.failure_halt_threshold = 3
        for index in range(3):
            self.runner().run(self.request(name="p%d.png" % index))
        self.assertTrue(
            Autonomy(self.app_paths.state_file, self.app_paths.halt_file).state.halted
        )

    def test_the_halt_drops_the_stage_and_survives_a_reload(self):
        self.set_mode("crash")
        self.config.failure_halt_threshold = 2
        for index in range(2):
            self.runner().run(self.request(name="q%d.png" % index))
        reloaded = Autonomy(self.app_paths.state_file, self.app_paths.halt_file)
        self.assertTrue(reloaded.state.halted)
        self.assertEqual(reloaded.state.stage, 1)

    def test_only_a_person_can_clear_it(self):
        autonomy = Autonomy(self.app_paths.state_file, self.app_paths.halt_file)
        autonomy.halt("test")
        ok, message = autonomy.set_stage(3)
        self.assertFalse(ok)
        self.assertIn("halted", message)
        autonomy.resume()
        ok, _ = autonomy.set_stage(3)
        self.assertTrue(ok)


class DryRun(RunnerCase):
    def test_nothing_is_written(self):
        request = self.request()
        result = self.runner(dry_run=True).run(request)
        self.assertEqual(result.status, STATUS_SKIPPED)
        self.assertFalse(os.path.exists(request.output_path))

    def test_the_prediction_is_still_recorded(self):
        self.runner(dry_run=True).run(self.request())
        self.assertIsNotNone(self.ledger.rows()[-1]["prediction"])


class Command(RunnerCase):
    def test_the_output_scale_flag_is_omitted_when_it_would_do_nothing(self):
        # A 4x model asked for 4x needs no resample. Passing -s would make the
        # engine resample the result to the size it already is.
        command = build_command(
            "engine", self.request(), self.models_dir, "/tmp/out.png", model_native_scale=4
        )
        self.assertNotIn("-s", command)

    def test_the_output_scale_flag_is_passed_when_it_changes_the_result(self):
        command = build_command(
            "engine", self.request(scale=2), self.models_dir, "/tmp/out.png", model_native_scale=4
        )
        self.assertIn("-s", command)
        self.assertEqual(command[command.index("-s") + 1], "2")

    def test_an_unknown_native_scale_forces_the_flag(self):
        command = build_command(
            "engine", self.request(), self.models_dir, "/tmp/out.png", model_native_scale=None
        )
        self.assertIn("-s", command)

    def test_the_models_path_is_absolute(self):
        command = build_command(
            "engine", self.request(), "relative/models", "/tmp/out.png", model_native_scale=4
        )
        self.assertTrue(os.path.isabs(command[command.index("-m") + 1]))

    def test_the_flags_that_silently_disable_the_scale_are_never_sent(self):
        command = build_command(
            "engine", self.request(scale=2), self.models_dir, "/tmp/out.png", model_native_scale=4
        )
        self.assertNotIn("-r", command)
        self.assertNotIn("-w", command)
        self.assertNotIn("-z", command)

    def test_compression_is_rounded_the_way_the_engine_rounds_it(self):
        command = build_command(
            "engine", self.request(compression=23), self.models_dir, "/tmp/out.png",
            model_native_scale=4,
        )
        self.assertEqual(command[command.index("-c") + 1], "20")


if __name__ == "__main__":
    unittest.main()


class TheWorstFailure(RunnerCase):
    """A complete, valid image file that is not a picture of anything.

    When the graphics device fails part-way, the half-finished buffer is
    encoded and written out anyway. The file is the right size, opens fine,
    and is usually solid black. Nothing about the file is detectably wrong, so
    the only evidence is what the engine printed while it ran.
    """

    def test_a_valid_but_garbage_output_is_still_a_failure(self):
        self.set_mode("black-image")
        result = self.runner().run(self.request(width=10, height=10))
        self.assertEqual(result.status, STATUS_FAILED)
        self.assertEqual(result.row.reason_key, "gpu_out_of_memory")

    def test_that_output_is_not_left_where_a_result_belongs(self):
        self.set_mode("black-image")
        request = self.request()
        self.runner().run(request)
        self.assertFalse(os.path.exists(request.output_path))

    def test_the_failure_names_the_remedy(self):
        self.set_mode("black-image")
        result = self.runner().run(self.request())
        self.assertIn("--tile", result.message)

    def test_a_success_banner_does_not_override_the_error(self):
        # The fake engine prints both, exactly as the real one does.
        self.set_mode("black-image")
        result = self.runner().run(self.request())
        self.assertIn("Upscayled Successfully", result.row.stderr_tail or "")
        self.assertEqual(result.status, STATUS_FAILED)


class RetryLadder(RunnerCase):
    def test_it_retries_smaller_and_recovers(self):
        self.set_mode("oom-until-tile")
        os.environ["FAKE_UPSCAYL_OK_TILE"] = "128"
        self.addCleanup(os.environ.pop, "FAKE_UPSCAYL_OK_TILE", None)
        result = self.runner().run(self.request(tile_size=512))
        self.assertEqual(result.status, STATUS_OK, result.message)
        self.assertGreater(len(result.row.attempts), 1)
        self.assertEqual(result.row.tile_size, 128)

    def test_every_attempt_is_recorded(self):
        self.set_mode("oom-until-tile")
        os.environ["FAKE_UPSCAYL_OK_TILE"] = "128"
        self.addCleanup(os.environ.pop, "FAKE_UPSCAYL_OK_TILE", None)
        result = self.runner().run(self.request(tile_size=512))
        tiles = [attempt["tile_size"] for attempt in result.row.attempts]
        self.assertEqual(tiles, [512, 256, 128])
        self.assertEqual(result.row.attempts[0]["fault"], "gpu_out_of_memory")
        self.assertIsNone(result.row.attempts[-1]["fault"])

    def test_it_gives_up_rather_than_retrying_forever(self):
        self.set_mode("black-image")
        result = self.runner().run(self.request(tile_size=512))
        self.assertEqual(result.status, STATUS_FAILED)
        self.assertLessEqual(len(result.row.attempts), self.config.tile_retry_attempts + 1)

    def test_a_failure_that_smaller_tiles_cannot_fix_is_not_retried(self):
        # No graphics device at all is not a memory problem; retrying at a
        # smaller tile just wastes time.
        self.set_mode("crash")
        result = self.runner().run(self.request())
        self.assertEqual(len(result.row.attempts), 1)

    def test_a_timeout_is_not_retried(self):
        # Each further attempt would cost another full timeout.
        self.set_mode("hang")
        self.config.timeout_seconds = 2
        result = self.runner().run(self.request(tile_size=512))
        self.assertEqual(result.status, STATUS_FAILED)
        self.assertEqual(len(result.row.attempts), 1)


class ThreadFlagSafety(RunnerCase):
    """The -j flag crashes the engine outright if it is malformed."""

    def test_a_complete_triple_is_accepted(self):
        self.assertTrue(_valid_jobs_spec("1:2:2"))
        self.assertTrue(_valid_jobs_spec("1:2,2,2:2"))

    def test_anything_without_two_colons_is_rejected(self):
        # The engine looks for a colon and adds one to the result without
        # checking it found anything, so this is a signal death, not an error.
        for bad in ("4", "1:2", "", "abc", "1:2:2:2", "1::2"):
            self.assertFalse(_valid_jobs_spec(bad), bad)

    def test_a_malformed_value_is_never_put_on_the_command_line(self):
        command = build_command(
            "engine", self.request(), self.models_dir, "/tmp/out.png",
            model_native_scale=4, jobs_spec="4",
        )
        self.assertNotIn("-j", command)


class SmallAndTransparentInputs(RunnerCase):
    def test_a_tiny_image_is_refused_before_the_engine_runs(self):
        result = self.runner().run(self.request(name="tiny.png", width=4, height=4))
        self.assertEqual(result.status, STATUS_REJECTED)
        self.assertIn("pixels on a side", result.message)
