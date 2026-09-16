"""Predict before, score after.

Before a job runs, the tool writes down what it expects: the output's exact
dimensions, roughly how many bytes it will take, and roughly how long it will
take. After the job, it compares each prediction to what actually happened and
records the error.

This is not bookkeeping for its own sake. The dimension prediction is exact
and therefore falsifiable, and it catches the failure that is otherwise
invisible: an engine asked for 4x that quietly produces 2x, or applies a
model's native scale instead of the one requested. Both leave a perfectly
valid image file on disk. Only a prediction written down beforehand turns
that into a caught error instead of a photo that is mysteriously soft.

Timing predictions start out bad and improve, because they are derived from
this machine's own history in the ledger rather than from a number someone
guessed at build time.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Any, Dict, Iterable, List, Optional

# Used only until the ledger has enough history to say better. Deliberately
# labelled in the output so nobody mistakes it for a measurement.
FALLBACK_SECONDS_PER_OUTPUT_MEGAPIXEL = 0.6

# How many past jobs to learn timing from. Recent history beats all history:
# a machine that has just been plugged in runs faster than the same machine on
# battery, and a model that was updated behaves differently than it used to.
TIMING_WINDOW = 25

# A timing prediction inside this band counts as a hit. Upscaling time varies
# with thermal state and what else the graphics processor is doing, so a tight
# band would just record noise as error.
TIMING_TOLERANCE = 0.5      # plus or minus 50 per cent
SIZE_TOLERANCE = 0.75       # plus or minus 75 per cent; file size is guesswork


@dataclass
class Prediction:
    """What we expect, written down before the work starts."""

    made_at: str
    output_width: Optional[int]
    output_height: Optional[int]
    output_megapixels: Optional[float]
    output_bytes: Optional[int]
    duration_seconds: Optional[float]
    basis: str  # Where the timing number came from, in plain words.
    samples: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "made_at": self.made_at,
            "output_width": self.output_width,
            "output_height": self.output_height,
            "output_megapixels": self.output_megapixels,
            "output_bytes": self.output_bytes,
            "duration_seconds": self.duration_seconds,
            "basis": self.basis,
            "samples": self.samples,
        }


def seconds_per_output_megapixel(
    rows: Iterable[Dict[str, Any]], model: Optional[str]
) -> "tuple[Optional[float], int]":
    """Learn this machine's speed for a model from the record.

    Returns the rate and how many successful jobs it was measured from, so the
    caller can say "measured from 12 jobs" rather than presenting a guess and
    a measurement in the same voice.
    """
    rates: List[float] = []
    for row in rows:
        if row.get("status") != "ok":
            continue
        if model and row.get("model") != model:
            continue
        # Prefer the engine-only time. Rows written before that was recorded
        # fall back to the whole-job time, which is close enough for a
        # starting estimate and is replaced as new rows accumulate.
        duration = row.get("engine_seconds") or row.get("duration_seconds")
        width, height = row.get("output_width"), row.get("output_height")
        if not duration or not width or not height:
            continue
        megapixels = (int(width) * int(height)) / 1_000_000.0
        if megapixels <= 0 or duration <= 0:
            continue
        rates.append(float(duration) / megapixels)
    if not rates:
        return None, 0
    recent = rates[-TIMING_WINDOW:]
    return median(recent), len(recent)


def predict(
    *,
    made_at: str,
    input_width: Optional[int],
    input_height: Optional[int],
    input_bytes: int,
    scale: int,
    output_format: str,
    model: Optional[str],
    history: Iterable[Dict[str, Any]],
) -> Prediction:
    """Write down what we expect before running the engine."""
    output_width = input_width * scale if input_width else None
    output_height = input_height * scale if input_height else None
    megapixels = (
        (output_width * output_height) / 1_000_000.0
        if output_width and output_height
        else None
    )

    # Bytes: scale the input by the pixel ratio, then adjust for the fact that
    # a lossless format stores far more than a lossy one, and that upscaled
    # images compress better than their originals because the model smooths
    # sensor noise away.
    format_multiplier = {"png": 2.2, "webp": 0.9, "jpg": 0.7}.get(output_format, 1.5)
    output_bytes = (
        int(input_bytes * (scale ** 2) * format_multiplier * 0.55)
        if input_bytes
        else None
    )

    rate, samples = seconds_per_output_megapixel(history, model)
    if rate is None:
        rate = FALLBACK_SECONDS_PER_OUTPUT_MEGAPIXEL
        basis = "built-in default; this machine has no measured history for this model yet"
    else:
        basis = "measured from %d past job%s with this model on this machine" % (
            samples,
            "" if samples == 1 else "s",
        )

    duration = round(rate * megapixels, 2) if megapixels else None

    return Prediction(
        made_at=made_at,
        output_width=output_width,
        output_height=output_height,
        output_megapixels=round(megapixels, 3) if megapixels else None,
        output_bytes=output_bytes,
        duration_seconds=duration,
        basis=basis,
        samples=samples,
    )


def _relative_error(predicted: Optional[float], actual: Optional[float]) -> Optional[float]:
    if not predicted or actual is None:
        return None
    if predicted == 0:
        return None
    return round((actual - predicted) / predicted, 4)


def score(
    prediction: Optional[Prediction | Dict[str, Any]],
    *,
    actual_width: Optional[int],
    actual_height: Optional[int],
    actual_bytes: Optional[int],
    actual_duration: Optional[float],
    scored_at: str,
) -> Dict[str, Any]:
    """Compare the prediction to what happened.

    ``dimensions`` is the one that matters. It is an exact prediction, so a
    miss is never noise — it means the engine did not do what it was told, and
    the resulting file is not the thing that was asked for.
    """
    if prediction is None:
        return {"scored_at": scored_at, "verdict": "unscored", "note": "no prediction was made"}

    values = prediction.as_dict() if isinstance(prediction, Prediction) else dict(prediction)

    results: Dict[str, Any] = {"scored_at": scored_at}
    findings: List[str] = []

    expected_w = values.get("output_width")
    expected_h = values.get("output_height")
    if expected_w and expected_h and actual_width and actual_height:
        exact = (expected_w == actual_width) and (expected_h == actual_height)
        results["dimensions"] = {
            "predicted": [expected_w, expected_h],
            "actual": [actual_width, actual_height],
            "verdict": "right" if exact else "wrong",
        }
        if not exact:
            # Work out what the engine actually did, which is more useful than
            # only reporting that it disagreed.
            actual_scale_w = actual_width / (expected_w / 1.0) if expected_w else None
            findings.append(
                "the engine produced %dx%d, not the %dx%d that was asked for "
                "(%.2f of the requested width)"
                % (
                    actual_width,
                    actual_height,
                    expected_w,
                    expected_h,
                    actual_scale_w or 0.0,
                )
            )
    else:
        results["dimensions"] = {"verdict": "unscored", "note": "dimensions unavailable"}

    expected_bytes = values.get("output_bytes")
    if expected_bytes and actual_bytes:
        error = _relative_error(expected_bytes, actual_bytes)
        results["size"] = {
            "predicted": expected_bytes,
            "actual": actual_bytes,
            "relative_error": error,
            "verdict": "right" if error is not None and abs(error) <= SIZE_TOLERANCE else "wrong",
        }

    expected_duration = values.get("duration_seconds")
    if expected_duration and actual_duration:
        error = _relative_error(expected_duration, actual_duration)
        verdict = "right" if error is not None and abs(error) <= TIMING_TOLERANCE else "wrong"
        results["duration"] = {
            "predicted": expected_duration,
            "actual": round(actual_duration, 2),
            "relative_error": error,
            "verdict": verdict,
            "basis": values.get("basis"),
        }
        if verdict == "wrong" and error is not None and error > 0:
            findings.append(
                "took %.0f%% longer than predicted; if this repeats, the machine "
                "is slower than its own history says" % (error * 100)
            )

    # The overall verdict is dominated by dimensions. A job can be slow and
    # still correct; it cannot be the wrong size and still correct.
    dimension_verdict = results.get("dimensions", {}).get("verdict")
    if dimension_verdict == "wrong":
        results["verdict"] = "wrong"
    elif dimension_verdict == "right":
        results["verdict"] = "right"
    else:
        results["verdict"] = "unscored"

    results["findings"] = findings
    return results
