"""Tests for predicting before, and scoring after."""

from __future__ import annotations

import unittest

from support import Workspace

from upscaylwrap import scorer
from upscaylwrap.ledger import now_iso


def history_rows(count, seconds_per_megapixel=1.0, model="upscayl-standard-4x"):
    rows = []
    for _ in range(count):
        rows.append(
            {
                "status": "ok",
                "model": model,
                "duration_seconds": seconds_per_megapixel * 4.0,
                "output_width": 2000,
                "output_height": 2000,
            }
        )
    return rows


class Predicting(unittest.TestCase):
    def test_dimensions_are_the_input_times_the_scale(self):
        prediction = scorer.predict(
            made_at=now_iso(), input_width=1000, input_height=800, input_bytes=100,
            scale=4, output_format="png", model="m", history=[],
        )
        self.assertEqual(prediction.output_width, 4000)
        self.assertEqual(prediction.output_height, 3200)

    def test_with_no_history_it_says_so(self):
        prediction = scorer.predict(
            made_at=now_iso(), input_width=100, input_height=100, input_bytes=100,
            scale=4, output_format="png", model="m", history=[],
        )
        self.assertEqual(prediction.samples, 0)
        self.assertIn("no measured history", prediction.basis)

    def test_history_replaces_the_default_and_is_counted(self):
        prediction = scorer.predict(
            made_at=now_iso(), input_width=500, input_height=500, input_bytes=1000,
            scale=4, output_format="png", model="upscayl-standard-4x",
            history=history_rows(5, seconds_per_megapixel=2.0),
        )
        self.assertEqual(prediction.samples, 5)
        self.assertIn("measured from 5", prediction.basis)
        # 500x500 at 4x is 4 megapixels, at 2 seconds each.
        self.assertAlmostEqual(prediction.duration_seconds, 8.0, places=1)

    def test_another_models_history_is_not_borrowed(self):
        prediction = scorer.predict(
            made_at=now_iso(), input_width=500, input_height=500, input_bytes=1000,
            scale=4, output_format="png", model="remacri-4x",
            history=history_rows(5, model="upscayl-standard-4x"),
        )
        self.assertEqual(prediction.samples, 0)

    def test_failed_jobs_are_not_learned_from(self):
        rows = history_rows(4)
        for row in rows:
            row["status"] = "failed"
        prediction = scorer.predict(
            made_at=now_iso(), input_width=100, input_height=100, input_bytes=100,
            scale=4, output_format="png", model="upscayl-standard-4x", history=rows,
        )
        self.assertEqual(prediction.samples, 0)


class Scoring(unittest.TestCase):
    def make(self, scale=4, width=1000, height=800):
        return scorer.predict(
            made_at=now_iso(), input_width=width, input_height=height, input_bytes=500_000,
            scale=scale, output_format="png", model="upscayl-standard-4x",
            history=history_rows(3, seconds_per_megapixel=1.0),
        )

    def test_exact_dimensions_score_right(self):
        prediction = self.make()
        result = scorer.score(
            prediction, actual_width=4000, actual_height=3200,
            actual_bytes=None, actual_duration=None, scored_at=now_iso(),
        )
        self.assertEqual(result["dimensions"]["verdict"], "right")
        self.assertEqual(result["verdict"], "right")

    def test_the_engine_quietly_doing_2x_is_caught(self):
        # This is the failure the whole prediction step exists to catch: a
        # perfectly valid image file that is not the size that was asked for.
        prediction = self.make()
        result = scorer.score(
            prediction, actual_width=2000, actual_height=1600,
            actual_bytes=None, actual_duration=None, scored_at=now_iso(),
        )
        self.assertEqual(result["dimensions"]["verdict"], "wrong")
        self.assertEqual(result["verdict"], "wrong")
        self.assertTrue(result["findings"])

    def test_timing_within_tolerance_is_a_hit(self):
        prediction = self.make()
        result = scorer.score(
            prediction, actual_width=4000, actual_height=3200, actual_bytes=1000,
            actual_duration=(prediction.duration_seconds or 1) * 1.2, scored_at=now_iso(),
        )
        self.assertEqual(result["duration"]["verdict"], "right")

    def test_being_much_slower_than_predicted_is_a_miss(self):
        prediction = self.make()
        result = scorer.score(
            prediction, actual_width=4000, actual_height=3200, actual_bytes=1000,
            actual_duration=(prediction.duration_seconds or 1) * 5, scored_at=now_iso(),
        )
        self.assertEqual(result["duration"]["verdict"], "wrong")
        self.assertTrue(any("longer than predicted" in f for f in result["findings"]))

    def test_a_slow_but_correctly_sized_job_is_still_right_overall(self):
        prediction = self.make()
        result = scorer.score(
            prediction, actual_width=4000, actual_height=3200, actual_bytes=1000,
            actual_duration=(prediction.duration_seconds or 1) * 5, scored_at=now_iso(),
        )
        self.assertEqual(result["verdict"], "right")

    def test_scoring_without_a_prediction_does_not_raise(self):
        result = scorer.score(
            None, actual_width=1, actual_height=1, actual_bytes=1,
            actual_duration=1.0, scored_at=now_iso(),
        )
        self.assertEqual(result["verdict"], "unscored")

    def test_a_prediction_stored_as_a_dictionary_still_scores(self):
        # Rows come back from the ledger as plain dictionaries, not objects.
        prediction = self.make().as_dict()
        result = scorer.score(
            prediction, actual_width=4000, actual_height=3200, actual_bytes=None,
            actual_duration=None, scored_at=now_iso(),
        )
        self.assertEqual(result["verdict"], "right")


if __name__ == "__main__":
    unittest.main()
