"""The path not taken, measured rather than assumed.

For every upscale there is an obvious cheaper alternative: resample the image
the ordinary way, with no machine learning involved at all. macOS has that
built in as ``sips``, so the comparison costs nothing but a few seconds.

Recording it turns a claim into a number. "The model is worth it" is an
opinion; "the model took 41 seconds where a plain resample took 0.4, and the
result is 3.1 times the file size" is something you can argue with. Over a few
hundred jobs the ledger can answer the question that actually matters — which
kinds of photo justify the cost and which ones may as well be resampled.

Sampled rather than run every time, because doubling the work on every job to
maintain a baseline would be its own kind of waste.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, Optional

from . import imageprobe

# The macOS built-in. Absent everywhere else, which is handled rather than
# treated as an error.
SIPS = "/usr/bin/sips"


def available() -> bool:
    return os.path.isfile(SIPS) and os.access(SIPS, os.X_OK)


def should_run(job_index: int, every: int) -> bool:
    """Run the baseline on every Nth job. ``every`` of 0 disables it."""
    if every <= 0:
        return False
    return job_index % every == 0


def run_baseline(
    input_path: str,
    target_width: int,
    *,
    timeout: int = 120,
) -> Dict[str, Any]:
    """Resample the input the ordinary way and measure what it cost.

    Writes to a temporary file that is always deleted — the baseline exists to
    be measured, not kept. Never raises: a failed baseline is recorded as
    unavailable and the real job carries on.
    """
    result: Dict[str, Any] = {
        "method": "sips --resampleWidth (Lanczos-style resample, no machine learning)",
        "available": available(),
    }
    if not result["available"]:
        result["note"] = "sips is only present on macOS; no baseline was measured"
        return result
    if target_width <= 0:
        result["note"] = "target width unknown"
        return result

    handle, temporary = tempfile.mkstemp(prefix="upscayl-wrap-baseline-", suffix=".png")
    os.close(handle)
    try:
        started = time.monotonic()
        completed = subprocess.run(
            [SIPS, "--resampleWidth", str(target_width), input_path, "--out", temporary],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        duration = time.monotonic() - started
        result["duration_seconds"] = round(duration, 3)
        result["exit_code"] = completed.returncode
        if completed.returncode != 0:
            result["note"] = (
                completed.stderr.decode("utf-8", "replace").strip()[-400:] or "sips failed"
            )
            return result
        info = imageprobe.probe(temporary)
        result["output_bytes"] = info.size_bytes
        result["output_width"] = info.width
        result["output_height"] = info.height
    except subprocess.TimeoutExpired:
        result["note"] = "baseline resample timed out after %d seconds" % timeout
    except OSError as exc:
        result["note"] = "baseline resample could not run: %s" % exc
    finally:
        try:
            os.unlink(temporary)
        except OSError:
            pass
    return result


def compare(baseline: Optional[Dict[str, Any]], actual: Dict[str, Any]) -> Dict[str, Any]:
    """Express the upscale as a multiple of the cheap alternative."""
    # A baseline that ran is not the same as a baseline that worked. The
    # duration is recorded before the exit code is examined, so a failed
    # conversion still carries a plausible-looking time — and comparing
    # against it would put a confident, meaningless multiple in the review.
    # Nothing is comparable unless the alternative actually produced an image.
    if (
        not baseline
        or not baseline.get("available")
        or baseline.get("exit_code") != 0
        or not baseline.get("output_width")
        or not baseline.get("duration_seconds")
    ):
        return {"comparable": False}

    comparison: Dict[str, Any] = {"comparable": True}
    base_seconds = baseline.get("duration_seconds") or 0.0
    real_seconds = actual.get("duration_seconds") or 0.0
    if base_seconds > 0 and real_seconds > 0:
        comparison["times_slower"] = round(real_seconds / base_seconds, 1)
        comparison["extra_seconds"] = round(real_seconds - base_seconds, 2)

    base_bytes = baseline.get("output_bytes") or 0
    real_bytes = actual.get("output_bytes") or 0
    if base_bytes > 0 and real_bytes > 0:
        comparison["times_larger"] = round(real_bytes / base_bytes, 2)

    base_dimensions = (baseline.get("output_width"), baseline.get("output_height"))
    real_dimensions = (actual.get("output_width"), actual.get("output_height"))
    comparison["same_dimensions"] = (
        all(base_dimensions) and all(real_dimensions) and base_dimensions == real_dimensions
    )
    if comparison.get("same_dimensions"):
        comparison["note"] = (
            "both produced the same pixel dimensions; the difference is entirely in "
            "what was put in those pixels"
        )
    return comparison


def which_sips() -> Optional[str]:
    """Where sips is, for the doctor report."""
    return SIPS if available() else shutil.which("sips")
