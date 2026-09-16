"""The record: one line per job, appended and never rewritten.

Every question this tool can answer later — is a model getting slower, does
the engine lie about its scale factor, did that batch actually finish — is
answered from this file and nowhere else. So it holds the full context of
each job, not a summary: the inputs, the decision, the prediction made
beforehand, the measured outcome, and the score.

Format is JSON Lines: one self-describing JSON object per line. That survives
a crash mid-write better than a single large JSON document, can be appended
without reading what came before, and is greppable from a terminal.

No row is ever illustrative. If a row is in this file, it happened.
"""

from __future__ import annotations

import json
import os
import socket
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Iterator, List, Optional

try:  # Present on macOS and Linux; absent on Windows, where we degrade.
    import fcntl
except ImportError:  # pragma: no cover - the tool targets macOS.
    fcntl = None  # type: ignore[assignment]

SCHEMA_VERSION = 1

# Every status a row can carry. Anything else is a bug.
STATUS_OK = "ok"
STATUS_FAILED = "failed"
STATUS_REJECTED = "rejected"   # The gate refused it.
STATUS_SKIPPED = "skipped"     # Already done, or nothing to do.
ALL_STATUSES = (STATUS_OK, STATUS_FAILED, STATUS_REJECTED, STATUS_SKIPPED)


def now_iso() -> str:
    """Timestamp in Coordinated Universal Time, to the second."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str = "job") -> str:
    return "%s_%s" % (prefix, uuid.uuid4().hex[:12])


@dataclass
class Row:
    """One job, start to finish.

    Built incrementally: created before the work, filled in as the job runs,
    written once at the end. A job that dies before it can be written is
    recovered by the caller's error handler, which writes whatever it has.
    """

    id: str
    run_id: str
    status: str
    ts_start: str
    ts_end: Optional[str] = None
    duration_seconds: Optional[float] = None

    # What was asked for.
    action: str = "upscale"
    model: Optional[str] = None
    scale: Optional[int] = None
    tile_size: Optional[int] = None
    gpu_id: Optional[int] = None
    output_format: Optional[str] = None
    stage: int = 1

    # What went in.
    input_path: Optional[str] = None
    input_sha256: Optional[str] = None
    input_bytes: Optional[int] = None
    input_width: Optional[int] = None
    input_height: Optional[int] = None
    input_format: Optional[str] = None
    # Set when the input had to be converted before the engine could read it,
    # so a row says what actually went in, not only what was asked for.
    converted_input: Optional[Dict[str, Any]] = None

    # What came out.
    output_path: Optional[str] = None
    output_sha256: Optional[str] = None
    output_bytes: Optional[int] = None
    output_width: Optional[int] = None
    output_height: Optional[int] = None
    output_complete: Optional[bool] = None

    # How it went.
    exit_code: Optional[int] = None
    command: Optional[List[str]] = None
    stderr_tail: Optional[str] = None
    reason: Optional[str] = None          # Why rejected, skipped, or failed.
    # A short stable key for the failure class, so the record can be grouped
    # by cause without matching on prose that may be reworded later.
    reason_key: Optional[str] = None
    gate_checks: List[Dict[str, Any]] = field(default_factory=list)
    # One entry per invocation of the engine. More than one means a retry at a
    # smaller tile size, which is itself worth knowing about.
    attempts: List[Dict[str, Any]] = field(default_factory=list)

    # The prediction made before the work, and its score afterwards.
    prediction: Optional[Dict[str, Any]] = None
    score: Optional[Dict[str, Any]] = None
    counterfactual: Optional[Dict[str, Any]] = None

    # Where it ran.
    host: str = field(default_factory=socket.gethostname)
    tool_version: str = ""
    schema: int = SCHEMA_VERSION

    def finish(self, status: str, started_monotonic: Optional[float] = None) -> "Row":
        self.status = status
        self.ts_end = now_iso()
        if started_monotonic is not None:
            self.duration_seconds = round(time.monotonic() - started_monotonic, 3)
        return self

    def as_dict(self) -> Dict[str, Any]:
        return {key: value for key, value in self.__dict__.items()}


class Ledger:
    """Append-only access to the record."""

    def __init__(self, path: str) -> None:
        self.path = path

    def _ensure_parent(self) -> None:
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def append(self, row: "Row | Dict[str, Any]") -> None:
        """Write one row.

        Takes an exclusive lock so that a watch-folder run and a hand-typed
        command writing at the same moment cannot interleave half-lines. A
        single JSON row can exceed the size the operating system guarantees to
        append atomically, so the lock is doing real work, not ceremony.
        """
        payload = row.as_dict() if isinstance(row, Row) else dict(row)
        payload.setdefault("schema", SCHEMA_VERSION)
        line = json.dumps(payload, ensure_ascii=False, default=str) + "\n"
        self._ensure_parent()
        with open(self.path, "a", encoding="utf-8") as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
            finally:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def iter_rows(self) -> Iterator[Dict[str, Any]]:
        """Yield every row, tolerating damage.

        A line that will not parse is skipped rather than raising. The record
        is more useful with a hole in it than unreadable, and `doctor` reports
        the count so the damage is visible rather than silent.
        """
        if not os.path.isfile(self.path):
            return
        with open(self.path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except ValueError:
                    continue
                if isinstance(parsed, dict):
                    yield parsed

    def rows(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        collected = list(self.iter_rows())
        if limit is not None and limit > 0:
            return collected[-limit:]
        return collected

    def damaged_line_count(self) -> int:
        if not os.path.isfile(self.path):
            return 0
        damaged = 0
        with open(self.path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    json.loads(line)
                except ValueError:
                    damaged += 1
        return damaged

    def since(self, iso_timestamp: str) -> List[Dict[str, Any]]:
        return [r for r in self.iter_rows() if (r.get("ts_start") or "") >= iso_timestamp]

    def consecutive_failures(self) -> int:
        """How many jobs have failed in a row, most recent first.

        Drives the halt: a run of failures usually means something structural
        (the engine is gone, the disk is full, every model was deleted) and
        grinding through another hundred files will not fix it.
        """
        count = 0
        for row in reversed(self.rows()):
            status = row.get("status")
            if status == STATUS_OK:
                break
            if status == STATUS_FAILED:
                count += 1
                continue
            # Rejections and skips are not failures; they do not reset the
            # count either, because they did not prove anything works.
            continue
        return count


def summarize(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate rows into the numbers a human actually asks for."""
    rows = list(rows)
    counts = {status: 0 for status in ALL_STATUSES}
    durations: List[float] = []
    pixels_in = 0
    pixels_out = 0
    bytes_out = 0
    by_model: Dict[str, Dict[str, Any]] = {}
    failures: List[Dict[str, Any]] = []

    for row in rows:
        status = row.get("status") or "unknown"
        counts[status] = counts.get(status, 0) + 1

        duration = row.get("duration_seconds")
        if isinstance(duration, (int, float)) and status == STATUS_OK:
            durations.append(float(duration))

        width, height = row.get("input_width"), row.get("input_height")
        if width and height:
            pixels_in += int(width) * int(height)
        out_w, out_h = row.get("output_width"), row.get("output_height")
        if out_w and out_h:
            pixels_out += int(out_w) * int(out_h)
        if row.get("output_bytes"):
            bytes_out += int(row["output_bytes"])

        model = row.get("model") or "unknown"
        entry = by_model.setdefault(
            model, {"ok": 0, "failed": 0, "seconds": 0.0, "megapixels_out": 0.0}
        )
        if status == STATUS_OK:
            entry["ok"] += 1
            if isinstance(duration, (int, float)):
                entry["seconds"] += float(duration)
            if out_w and out_h:
                entry["megapixels_out"] += (int(out_w) * int(out_h)) / 1_000_000.0
        elif status == STATUS_FAILED:
            entry["failed"] += 1
            failures.append(
                {
                    "id": row.get("id"),
                    "input": row.get("input_path"),
                    "reason": row.get("reason") or row.get("stderr_tail"),
                    "exit_code": row.get("exit_code"),
                    "ts": row.get("ts_start"),
                }
            )

    durations.sort()
    median = durations[len(durations) // 2] if durations else None

    for entry in by_model.values():
        if entry["megapixels_out"] > 0 and entry["seconds"] > 0:
            entry["seconds_per_output_megapixel"] = round(
                entry["seconds"] / entry["megapixels_out"], 3
            )
        entry["seconds"] = round(entry["seconds"], 1)
        entry["megapixels_out"] = round(entry["megapixels_out"], 2)

    total = len(rows)
    attempted = counts.get(STATUS_OK, 0) + counts.get(STATUS_FAILED, 0)
    return {
        "rows": total,
        "counts": counts,
        "success_rate": round(counts.get(STATUS_OK, 0) / attempted, 4) if attempted else None,
        "median_seconds": median,
        "total_seconds": round(sum(durations), 1),
        "megapixels_in": round(pixels_in / 1_000_000.0, 2),
        "megapixels_out": round(pixels_out / 1_000_000.0, 2),
        "output_bytes": bytes_out,
        "by_model": by_model,
        "recent_failures": failures[-10:],
    }
