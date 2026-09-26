"""Tests for the record, and for the review built from it."""

from __future__ import annotations

import json
import os
import unittest

from support import Workspace

from upscaylwrap import review as review_module
from upscaylwrap.ledger import (
    Ledger,
    Row,
    STATUS_FAILED,
    STATUS_OK,
    STATUS_REJECTED,
    new_id,
    now_iso,
    summarize,
)


def a_row(**overrides) -> Row:
    values = dict(
        id=new_id(),
        run_id="run_test",
        status=STATUS_OK,
        ts_start=now_iso(),
        model="upscayl-standard-4x",
        scale=4,
        input_path="/photos/a.png",
        output_path="/out/a_4x.png",
        input_width=100,
        input_height=100,
        output_width=400,
        output_height=400,
        output_bytes=1000,
        duration_seconds=2.0,
    )
    values.update(overrides)
    return Row(**values)


class Appending(Workspace):
    def setUp(self):
        super().setUp()
        self.ledger = Ledger(os.path.join(self.root, "ledger.jsonl"))

    def test_a_row_survives_a_round_trip(self):
        self.ledger.append(a_row(input_path="/photos/zebra.png"))
        rows = self.ledger.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["input_path"], "/photos/zebra.png")
        self.assertEqual(rows[0]["schema"], 1)

    def test_rows_accumulate_and_keep_their_order(self):
        for index in range(5):
            self.ledger.append(a_row(input_path="/photos/%d.png" % index))
        rows = self.ledger.rows()
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["input_path"], "/photos/0.png")
        self.assertEqual(rows[-1]["input_path"], "/photos/4.png")

    def test_the_parent_directory_is_created(self):
        nested = Ledger(os.path.join(self.root, "deep", "deeper", "ledger.jsonl"))
        nested.append(a_row())
        self.assertTrue(os.path.isfile(nested.path))

    def test_each_row_is_one_line(self):
        self.ledger.append(a_row(stderr_tail="a message\nwith a newline in it"))
        with open(self.ledger.path, "r", encoding="utf-8") as handle:
            self.assertEqual(len(handle.readlines()), 1)

    def test_a_damaged_line_is_skipped_not_fatal(self):
        self.ledger.append(a_row(input_path="/photos/good1.png"))
        with open(self.ledger.path, "a", encoding="utf-8") as handle:
            handle.write("{this is not json\n")
        self.ledger.append(a_row(input_path="/photos/good2.png"))
        rows = self.ledger.rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(self.ledger.damaged_line_count(), 1)

    def test_tail_limits_what_comes_back(self):
        for index in range(10):
            self.ledger.append(a_row(input_path="/photos/%d.png" % index))
        self.assertEqual(len(self.ledger.rows(limit=3)), 3)

    def test_an_empty_ledger_reads_as_nothing(self):
        self.assertEqual(self.ledger.rows(), [])
        self.assertEqual(self.ledger.consecutive_failures(), 0)


class ConsecutiveFailures(Workspace):
    def setUp(self):
        super().setUp()
        self.ledger = Ledger(os.path.join(self.root, "ledger.jsonl"))

    def test_failures_in_a_row_are_counted(self):
        for _ in range(3):
            self.ledger.append(a_row(status=STATUS_FAILED))
        self.assertEqual(self.ledger.consecutive_failures(), 3)

    def test_a_success_resets_the_count(self):
        self.ledger.append(a_row(status=STATUS_FAILED))
        self.ledger.append(a_row(status=STATUS_FAILED))
        self.ledger.append(a_row(status=STATUS_OK))
        self.assertEqual(self.ledger.consecutive_failures(), 0)

    def test_a_refusal_neither_counts_nor_resets(self):
        self.ledger.append(a_row(status=STATUS_FAILED))
        self.ledger.append(a_row(status=STATUS_REJECTED))
        self.ledger.append(a_row(status=STATUS_FAILED))
        self.assertEqual(self.ledger.consecutive_failures(), 2)


class Summary(unittest.TestCase):
    def test_counts_and_rates(self):
        rows = [a_row().as_dict() for _ in range(3)]
        rows.append(a_row(status=STATUS_FAILED, reason="boom").as_dict())
        stats = summarize(rows)
        self.assertEqual(stats["counts"][STATUS_OK], 3)
        self.assertEqual(stats["counts"][STATUS_FAILED], 1)
        self.assertAlmostEqual(stats["success_rate"], 0.75)
        self.assertEqual(len(stats["recent_failures"]), 1)

    def test_speed_is_reported_per_megapixel(self):
        rows = [
            a_row(output_width=1000, output_height=1000, duration_seconds=2.0).as_dict()
            for _ in range(3)
        ]
        stats = summarize(rows)
        entry = stats["by_model"]["upscayl-standard-4x"]
        self.assertAlmostEqual(entry["seconds_per_output_megapixel"], 2.0, places=2)

    def test_an_empty_set_does_not_divide_by_zero(self):
        stats = summarize([])
        self.assertEqual(stats["rows"], 0)
        self.assertIsNone(stats["success_rate"])


class Review(Workspace):
    def test_a_wrong_size_lands_in_the_wrong_list(self):
        rows = [
            a_row(
                score={"verdict": "wrong", "dimensions": {"verdict": "wrong"}}
            ).as_dict()
        ]
        built = review_module.build(rows, window_label="test")
        self.assertTrue(built["wrong"])
        self.assertTrue(any("did not match" in line for line in built["wrong"]))
        self.assertTrue(built["will_do_differently"])

    def test_a_corrupt_input_is_not_blamed_on_the_tool(self):
        rows = [
            a_row(status=STATUS_FAILED, reason="input file is truncated or incomplete").as_dict()
        ]
        built = review_module.build(rows, window_label="test")
        self.assertTrue(built["could_not_have_known"])
        self.assertFalse(built["wrong"])

    def test_a_real_failure_is_blamed_on_the_tool(self):
        rows = [a_row(status=STATUS_FAILED, reason="the engine exited with status 1").as_dict()]
        built = review_module.build(rows, window_label="test")
        self.assertTrue(built["wrong"])
        self.assertFalse(built["could_not_have_known"])

    def test_a_success_reported_with_no_usable_output_is_called_out(self):
        rows = [
            a_row(
                status=STATUS_FAILED,
                exit_code=0,
                reason="the engine reported success but wrote no output file",
            ).as_dict()
            for _ in range(2)
        ]
        built = review_module.build(rows, window_label="test")
        self.assertTrue(any("exited with status 0" in line for line in built["wrong"]))

    def test_an_empty_window_still_produces_a_review(self):
        built = review_module.build([], window_label="nothing")
        markdown = review_module.render_markdown(built, generated_at=now_iso())
        self.assertIn("Right", markdown)
        self.assertIn("Will do differently", markdown)

    def test_the_review_writes_a_dated_file_and_a_pointer(self):
        built = review_module.build([a_row().as_dict()], window_label="test")
        markdown = review_module.render_markdown(built, generated_at=now_iso())
        dated, latest = review_module.write(
            os.path.join(self.root, "reviews"), markdown, date_stamp="2026-09-16"
        )
        self.assertTrue(os.path.isfile(dated))
        self.assertTrue(os.path.isfile(latest))
        self.assertEqual(review_module.read_latest(os.path.join(self.root, "reviews")), markdown)

    def test_proposals_are_never_applied_automatically(self):
        # The review returns proposals as text. Nothing in this module writes
        # to a config file, and this test exists so that stays true.
        source = open(review_module.__file__, "r", encoding="utf-8").read()
        self.assertNotIn("config.save", source)
        self.assertNotIn("setattr(config", source)


if __name__ == "__main__":
    unittest.main()
