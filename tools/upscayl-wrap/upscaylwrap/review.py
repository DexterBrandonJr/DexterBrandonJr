"""The self-review: what the record says, written where the next run reads it.

Four questions, answered from the ledger and nothing else:

* **Right** — what the tool predicted correctly, and what worked.
* **Wrong** — what it got wrong, with the rows that prove it.
* **Could not have known** — failures that no amount of care would have
  prevented, kept separate so they do not contaminate the wrong list. A photo
  that was already corrupt before it arrived is not the tool's mistake.
* **Will do differently** — proposals, and only proposals.

That last word is load-bearing. This module never edits the configuration, and
never changes a setting because the numbers suggest it should. It writes a
file saying what it would change and why. A tool that tunes itself overnight
is a tool whose behaviour nobody can predict in the morning.
"""

from __future__ import annotations

import os
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

from .ledger import STATUS_FAILED, STATUS_OK, STATUS_REJECTED, STATUS_SKIPPED, summarize

# Failure causes that no configuration change would have prevented.
UNKNOWABLE_MARKERS = (
    "truncated",
    "is empty",
    "unrecognised image format",
    "cannot read",
    "cannot stat",
    "not a regular file",
)


def _is_unknowable(row: Dict[str, Any]) -> bool:
    text = " ".join(
        str(row.get(key) or "") for key in ("reason", "stderr_tail", "input_error")
    ).lower()
    return any(marker in text for marker in UNKNOWABLE_MARKERS)


def _percent(part: int, whole: int) -> str:
    if not whole:
        return "n/a"
    return "%.0f%%" % (100.0 * part / whole)


def build(rows: Iterable[Dict[str, Any]], *, window_label: str) -> Dict[str, Any]:
    """Turn ledger rows into the four lists plus supporting numbers."""
    rows = list(rows)
    stats = summarize(rows)

    right: List[str] = []
    wrong: List[str] = []
    unknowable: List[str] = []
    proposals: List[str] = []

    successes = [r for r in rows if r.get("status") == STATUS_OK]
    failures = [r for r in rows if r.get("status") == STATUS_FAILED]
    rejections = [r for r in rows if r.get("status") == STATUS_REJECTED]
    skips = [r for r in rows if r.get("status") == STATUS_SKIPPED]

    # --- scored predictions ------------------------------------------------
    scored = [r for r in rows if isinstance(r.get("score"), dict)]
    dimension_right = [
        r for r in scored if (r["score"].get("dimensions") or {}).get("verdict") == "right"
    ]
    dimension_wrong = [
        r for r in scored if (r["score"].get("dimensions") or {}).get("verdict") == "wrong"
    ]
    if dimension_right:
        right.append(
            "%d of %d jobs produced exactly the dimensions predicted before they ran (%s)."
            % (
                len(dimension_right),
                len(scored),
                _percent(len(dimension_right), len(scored)),
            )
        )
    if dimension_wrong:
        wrong.append(
            "%d job%s produced dimensions that did not match the prediction. This is the "
            "loud one: the engine did not do what it was asked. Rows: %s"
            % (
                len(dimension_wrong),
                "" if len(dimension_wrong) == 1 else "s",
                ", ".join(str(r.get("id")) for r in dimension_wrong[:5]),
            )
        )
        proposals.append(
            "Check whether the requested scale matches the chosen model's native scale. "
            "If they differ, either switch to a model trained at the scale you want, or "
            "set scale_policy to \"strict\" so the gate refuses the mismatch instead of "
            "letting it through with a warning."
        )

    duration_scores = [
        r["score"]["duration"] for r in scored if isinstance(r["score"].get("duration"), dict)
    ]
    slow = [d for d in duration_scores if (d.get("relative_error") or 0) > 0.5]
    if duration_scores:
        hits = [d for d in duration_scores if d.get("verdict") == "right"]
        right.append(
            "Timing predictions landed within tolerance on %d of %d jobs (%s)."
            % (len(hits), len(duration_scores), _percent(len(hits), len(duration_scores)))
        )
    if len(slow) >= 3:
        wrong.append(
            "%d jobs took more than half again as long as predicted. The machine is "
            "slower than its own recent history, which usually means thermal throttling, "
            "battery power, or something else competing for the graphics processor."
            % len(slow)
        )

    # --- outright failures -------------------------------------------------
    for row in failures:
        if _is_unknowable(row):
            unknowable.append(
                "%s — %s" % (
                    os.path.basename(str(row.get("input_path") or "unknown")),
                    (row.get("reason") or row.get("stderr_tail") or "").strip()[:200],
                )
            )
    real_failures = [r for r in failures if not _is_unknowable(r)]
    if real_failures:
        causes = Counter(
            (str(r.get("reason") or r.get("stderr_tail") or "unrecorded").strip()[:120])
            for r in real_failures
        )
        for cause, count in causes.most_common(5):
            wrong.append("%d job%s failed: %s" % (count, "" if count == 1 else "s", cause))

        exit_codes = Counter(r.get("exit_code") for r in real_failures)
        if exit_codes.get(0):
            wrong.append(
                "%d failures exited with status 0 — the engine reported success while "
                "producing nothing usable. Output verification caught these; exit codes "
                "alone would not have." % exit_codes[0]
            )

    # --- rejections --------------------------------------------------------
    if rejections:
        reasons = Counter(
            (str(r.get("reason") or "unrecorded").split(";")[0].strip()[:100])
            for r in rejections
        )
        for reason, count in reasons.most_common(5):
            right.append("The gate refused %d job%s: %s" % (count, "" if count == 1 else "s", reason))
        budget_rejections = [
            r for r in rejections if "megapixel budget" in str(r.get("reason") or "")
        ]
        if len(budget_rejections) >= 3:
            proposals.append(
                "%d jobs were refused for exceeding the megapixel budget. Either these "
                "photos genuinely should not be upscaled at this factor, or the budget is "
                "set too low for the work you actually do. Raise max_output_megapixels "
                "deliberately rather than per job." % len(budget_rejections)
            )

    # --- the counterfactual ------------------------------------------------
    compared = [
        r for r in rows
        if isinstance(r.get("counterfactual"), dict)
        and (r["counterfactual"].get("comparison") or {}).get("comparable")
    ]
    if compared:
        multiples = [
            r["counterfactual"]["comparison"].get("times_slower")
            for r in compared
            if r["counterfactual"]["comparison"].get("times_slower")
        ]
        if multiples:
            multiples.sort()
            middle = multiples[len(multiples) // 2]
            right.append(
                "Measured against a plain resample on %d sampled job%s, the model cost "
                "about %.0f times the time. That is the price of the detail it invents; "
                "the ledger now has the numbers to argue about whether it is worth it."
                % (len(compared), "" if len(compared) == 1 else "s", middle)
            )

    # --- throughput --------------------------------------------------------
    if successes:
        right.append(
            "%d image%s upscaled, %.1f megapixels produced, %.0f seconds of engine time."
            % (
                len(successes),
                "" if len(successes) == 1 else "s",
                stats.get("megapixels_out") or 0.0,
                stats.get("total_seconds") or 0.0,
            )
        )

    if skips:
        right.append(
            "%d file%s skipped because the output already existed — reruns are cheap."
            % (len(skips), "" if len(skips) == 1 else "s")
        )

    if not rows:
        right.append("Nothing ran in this window. Nothing to learn yet.")

    # --- proposals from the shape of the numbers ---------------------------
    by_model = stats.get("by_model") or {}
    rates = {
        name: entry.get("seconds_per_output_megapixel")
        for name, entry in by_model.items()
        if entry.get("seconds_per_output_megapixel")
    }
    if len(rates) >= 2:
        fastest = min(rates, key=lambda k: rates[k])
        slowest = max(rates, key=lambda k: rates[k])
        if rates[slowest] > rates[fastest] * 2:
            proposals.append(
                "Model %s runs %.1f times slower per megapixel than %s on this machine. "
                "If you cannot tell the results apart on your own photos, the faster one "
                "is the better default."
                % (slowest, rates[slowest] / rates[fastest], fastest)
            )

    failure_rate = 1.0 - (stats.get("success_rate") or 1.0)
    if failure_rate > 0.2 and len(failures) >= 3:
        proposals.append(
            "The failure rate in this window is %s. Run 'upscayl-wrap doctor' before the "
            "next batch; a rate this high is usually one cause, not many."
            % _percent(len(failures), len(failures) + len(successes))
        )

    return {
        "window": window_label,
        "stats": stats,
        "right": right,
        "wrong": wrong,
        "could_not_have_known": unknowable,
        "will_do_differently": proposals,
    }


def render_markdown(review: Dict[str, Any], *, generated_at: str) -> str:
    """Write the review as something a person will actually read."""
    stats = review.get("stats") or {}
    counts = stats.get("counts") or {}

    def section(title: str, items: List[str], empty: str) -> str:
        if not items:
            return "## %s\n\n%s\n" % (title, empty)
        body = "\n".join("- %s" % item for item in items)
        return "## %s\n\n%s\n" % (title, body)

    header = [
        "# Upscayl wrapper review — %s" % review.get("window", "unknown window"),
        "",
        "Generated %s from the ledger. Proposals only; nothing here was applied." % generated_at,
        "",
        "| Outcome | Count |",
        "| --- | --- |",
        "| Upscaled | %d |" % counts.get(STATUS_OK, 0),
        "| Failed | %d |" % counts.get(STATUS_FAILED, 0),
        "| Refused by the gate | %d |" % counts.get(STATUS_REJECTED, 0),
        "| Skipped | %d |" % counts.get(STATUS_SKIPPED, 0),
        "",
    ]

    parts = [
        "\n".join(header),
        section("Right", review.get("right") or [], "_Nothing to report._"),
        section("Wrong", review.get("wrong") or [], "_Nothing went wrong in this window._"),
        section(
            "Could not have known",
            review.get("could_not_have_known") or [],
            "_No failures of this kind._",
        ),
        section(
            "Will do differently",
            review.get("will_do_differently") or [],
            "_No changes proposed._",
        ),
    ]
    return "\n".join(parts).rstrip() + "\n"


def write(
    reviews_dir: str, markdown: str, *, date_stamp: str
) -> "tuple[str, str]":
    """Save the review, and update the pointer the next run reads."""
    os.makedirs(reviews_dir, exist_ok=True)
    dated = os.path.join(reviews_dir, "%s.md" % date_stamp)
    with open(dated, "w", encoding="utf-8") as handle:
        handle.write(markdown)
    latest = os.path.join(reviews_dir, "LATEST.md")
    with open(latest, "w", encoding="utf-8") as handle:
        handle.write(markdown)
    return dated, latest


def read_latest(reviews_dir: str) -> Optional[str]:
    latest = os.path.join(reviews_dir, "LATEST.md")
    if not os.path.isfile(latest):
        return None
    try:
        with open(latest, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return None
