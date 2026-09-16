"""Tests for the command surface and output naming."""

from __future__ import annotations

import io
import json
import os
import unittest
from contextlib import redirect_stdout

from support import Workspace, make_png

from upscaylwrap import cli


def run(arguments):
    """Run a command, returning its exit code and whatever it printed."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = cli.main(arguments)
    return code, buffer.getvalue()


class OutputNaming(unittest.TestCase):
    def test_the_scale_is_in_the_name(self):
        path = cli.output_path_for("/in/photo.jpg", "/out", 4, "png")
        self.assertEqual(path, os.path.join("/out", "photo_4x.png"))

    def test_the_format_decides_the_extension(self):
        path = cli.output_path_for("/in/photo.png", "/out", 2, "webp")
        self.assertTrue(path.endswith("photo_2x.webp"))

    def test_two_inputs_sharing_a_stem_do_not_collide(self):
        # The engine's own batch mode gets this wrong; this must not.
        taken = set()
        first = cli.output_path_for("/in/a.jpg", "/out", 4, "png", taken=taken)
        second = cli.output_path_for("/in/a.png", "/out", 4, "png", taken=taken)
        self.assertNotEqual(first, second)
        self.assertEqual(len(taken), 2)

    def test_three_way_collisions_still_resolve(self):
        taken = set()
        paths = [
            cli.output_path_for("/in/a.%s" % extension, "/out", 4, "png", taken=taken)
            for extension in ("jpg", "png", "webp", "jpg")
        ]
        self.assertEqual(len(set(paths)), 4)

    def test_subdirectories_are_preserved_in_a_recursive_run(self):
        path = cli.output_path_for(
            "/in/holiday/beach.jpg", "/out", 4, "png", relative_to="/in"
        )
        self.assertEqual(path, os.path.join("/out", "holiday", "beach_4x.png"))


class Doctor(Workspace):
    def test_it_reports_ready_when_everything_is_present(self):
        code, output = run(["--json", "doctor"])
        payload = json.loads(output)
        self.assertTrue(payload["ready"])
        self.assertEqual(code, cli.EXIT_OK)

    def test_it_reports_not_ready_with_no_engine(self):
        os.environ["UPSCAYL_BIN"] = os.path.join(self.root, "nothing-here")
        code, output = run(["--json", "doctor"])
        self.assertEqual(code, cli.EXIT_NOT_READY)
        self.assertFalse(json.loads(output)["ready"])

    def test_it_lists_where_it_looked(self):
        os.environ["UPSCAYL_BIN"] = os.path.join(self.root, "nothing-here")
        _, output = run(["--json", "doctor"])
        self.assertTrue(len(json.loads(output)["searched_bin"]) > 3)


class Models(Workspace):
    def test_all_seven_are_listed_with_their_scale(self):
        code, output = run(["--json", "models"])
        payload = json.loads(output)
        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(len(payload["models"]), 7)
        self.assertTrue(all(m["native_scale"] == 4 for m in payload["models"]))

    def test_the_default_is_the_standard_model(self):
        _, output = run(["--json", "models"])
        self.assertEqual(json.loads(output)["default"], "upscayl-standard-4x")

    def test_a_half_copied_model_is_reported_as_unusable(self):
        with open(os.path.join(self.models_dir, "broken-4x.param"), "wb") as handle:
            handle.write(b"only one of the pair")
        _, output = run(["--json", "models"])
        broken = [m for m in json.loads(output)["models"] if m["name"] == "broken-4x"]
        self.assertEqual(len(broken), 1)
        self.assertFalse(broken[0]["usable"])


class Upscaling(Workspace):
    def test_one_image_end_to_end(self):
        source = make_png(os.path.join(self.inputs, "a.png"), 64, 48)
        code, output = run(["--json", "up", source, "-o", self.outputs, "-y"])
        payload = json.loads(output)
        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(payload["counts"]["ok"], 1)
        self.assertTrue(os.path.isfile(os.path.join(self.outputs, "a_4x.png")))

    def test_a_folder_end_to_end(self):
        for index in range(3):
            make_png(os.path.join(self.inputs, "p%d.png" % index), 64, 48)
        code, output = run(["--json", "batch", self.inputs, "-o", self.outputs, "-y"])
        self.assertEqual(json.loads(output)["counts"]["ok"], 3)

    def test_non_images_in_the_folder_are_ignored(self):
        make_png(os.path.join(self.inputs, "real.png"), 64, 48)
        with open(os.path.join(self.inputs, "notes.txt"), "w") as handle:
            handle.write("not an image")
        _, output = run(["--json", "batch", self.inputs, "-o", self.outputs, "-y"])
        self.assertEqual(json.loads(output)["counts"]["ok"], 1)

    def test_a_dry_run_writes_nothing(self):
        source = make_png(os.path.join(self.inputs, "a.png"), 64, 48)
        run(["--json", "up", source, "-o", self.outputs, "-y", "--dry-run"])
        self.assertEqual(os.listdir(self.outputs), [])

    def test_stage_one_refuses_without_approval(self):
        source = make_png(os.path.join(self.inputs, "a.png"), 64, 48)
        code, output = run(["--json", "up", source, "-o", self.outputs])
        self.assertEqual(code, cli.EXIT_REFUSED)
        self.assertEqual(json.loads(output)["counts"]["rejected"], 1)

    def test_a_second_batch_does_not_eat_its_own_output(self):
        # Output goes inside the input folder here, which is the shape that
        # would loop forever if the walk did not skip it.
        make_png(os.path.join(self.inputs, "a.png"), 64, 48)
        nested = os.path.join(self.inputs, "upscaled")
        run(["--json", "batch", self.inputs, "-o", nested, "-y"])
        _, output = run(["--json", "batch", self.inputs, "-o", nested, "-y"])
        payload = json.loads(output)
        self.assertEqual(payload["counts"]["ok"], 0)
        self.assertEqual(payload["counts"]["rejected"], 0)
        self.assertEqual(payload["counts"]["skipped"], 1)


class ReportingCommands(Workspace):
    def test_report_summarises_the_record(self):
        source = make_png(os.path.join(self.inputs, "a.png"), 64, 48)
        run(["up", source, "-o", self.outputs, "-y", "--quiet"])
        code, output = run(["--json", "report"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(json.loads(output)["stats"]["counts"]["ok"], 1)

    def test_compact_report_is_one_line(self):
        _, output = run(["report", "--compact"])
        self.assertEqual(len(output.strip().splitlines()), 1)

    def test_review_produces_the_four_headings(self):
        _, output = run(["review"])
        for heading in ("Right", "Wrong", "Could not have known", "Will do differently"):
            self.assertIn(heading, output)

    def test_review_can_write_itself_to_disk(self):
        code, output = run(["--json", "review", "--write"])
        written = json.loads(output)["written"]
        self.assertTrue(all(os.path.isfile(path) for path in written))

    def test_ledger_shows_rows(self):
        source = make_png(os.path.join(self.inputs, "a.png"), 64, 48)
        run(["up", source, "-o", self.outputs, "-y", "--quiet"])
        code, output = run(["--json", "ledger"])
        self.assertEqual(len(json.loads(output)), 1)


class StageCommands(Workspace):
    def test_stage_starts_at_one(self):
        _, output = run(["--json", "stage"])
        self.assertEqual(json.loads(output)["stage"], 1)

    def test_raising_the_stage_records_an_envelope(self):
        _, output = run(["--json", "stage", "--set", "2"])
        state = json.loads(output)["state"]
        self.assertEqual(state["stage"], 2)
        self.assertEqual(len(state["approved_models"]), 7)

    def test_halt_and_resume(self):
        run(["halt", "--reason", "testing"])
        _, output = run(["--json", "stage"])
        self.assertTrue(json.loads(output)["halted"])
        run(["resume"])
        _, output = run(["--json", "stage"])
        self.assertFalse(json.loads(output)["halted"])


class ConfigCommand(Workspace):
    def test_settings_round_trip(self):
        run(["config", "--set", "default_scale=2"])
        _, output = run(["--json", "config"])
        self.assertEqual(json.loads(output)["config"]["default_scale"], 2)

    def test_an_unknown_setting_is_rejected(self):
        code, _ = run(["config", "--set", "not_a_setting=1"])
        self.assertEqual(code, cli.EXIT_ERROR)

    def test_a_malformed_assignment_is_rejected(self):
        code, _ = run(["config", "--set", "just-a-word"])
        self.assertEqual(code, cli.EXIT_ERROR)


class Parsing(unittest.TestCase):
    def test_no_command_prints_help_without_failing(self):
        code, _ = run([])
        self.assertEqual(code, cli.EXIT_OK)


if __name__ == "__main__":
    unittest.main()
