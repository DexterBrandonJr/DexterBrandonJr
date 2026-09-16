"""Running one job, and proving afterwards that it worked.

The engine is ``upscayl-bin``, the Real-ESRGAN backend that ships inside the
Upscayl application. Its interface was read from its own source rather than
from documentation, and three things about it shape everything here.

**It has two different scale flags.** ``-z`` is the model's native scale and
``-s`` is the final output scale. They are not the same knob. The model always
runs at its own scale; ``-s`` resamples the result afterwards so the finished
image is exactly the original dimensions times the number given. On macOS the
native scale is auto-detected from the model's *name* and overwrites anything
passed to ``-z``, so this wrapper never passes ``-z`` — it would be ignored —
and always passes ``-s`` explicitly. Always passing it is what makes the
output size predictable, and a predictable size is what lets the scorer catch
the engine getting it wrong.

**It is driven one file at a time here, not in its own batch mode.** The
engine can take directories, but then a failure part-way through a hundred
photos leaves no record of which ones were done, and its output-naming
collision check only compares each file against the previous one in sorted
order, so two files sharing a basename can quietly overwrite. One invocation
per file costs a process launch and buys a ledger row, a fresh gate check, and
honest per-file timing.

**Its exit code is not enough on its own.** So the wrapper writes every output
to a temporary name, verifies it is a whole image of the expected size, and
only then renames it into place. A job that fails leaves nothing that looks
like a result, and the partial file is quarantined rather than deleted.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import counterfactual as counterfactual_module
from . import enginefaults
from . import gate as gate_module
from . import imageprobe, scorer
from .autonomy import Autonomy
from .config import Config, Discovery
from .ledger import (
    Ledger,
    Row,
    STATUS_FAILED,
    STATUS_OK,
    STATUS_REJECTED,
    STATUS_SKIPPED,
    new_id,
    now_iso,
)

# Written next to the final output while the engine works, then renamed on
# success. The leading dot keeps it out of the way in Finder.
TEMP_PREFIX = ".upscayl-wrap-tmp-"


@dataclass
class JobRequest:
    """One image to upscale, fully specified."""

    input_path: str
    output_path: str
    output_root: str
    scale: int
    model_name: str
    output_format: str = "png"
    tile_size: int = 0
    gpu_id: Optional[int] = None
    compression: Optional[int] = None
    tta: bool = False
    force: bool = False
    human_approved: bool = False


@dataclass
class JobResult:
    """What happened, and the row that was written about it."""

    status: str
    row: Row
    message: str = ""
    denials: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK


def free_disk_bytes(path: str) -> Optional[int]:
    """Space available on the volume that will hold the output."""
    target = path
    while target and not os.path.isdir(target):
        parent = os.path.dirname(target)
        if parent == target:
            break
        target = parent
    try:
        stats = os.statvfs(target or "/")
        return stats.f_bavail * stats.f_frsize
    except (OSError, AttributeError):
        return None


def build_command(
    engine: str,
    request: JobRequest,
    models_dir: str,
    temp_output: str,
    *,
    model_native_scale: Optional[int] = None,
    tile_override: Optional[int] = None,
    verbose: bool = True,
    jobs_spec: Optional[str] = None,
) -> List[str]:
    """Assemble the exact argument list, and nothing extra.

    ``-z`` is deliberately absent: on macOS the engine overwrites it by
    reading the scale out of the model's name, so passing it would suggest a
    control that does not exist.

    ``-r`` and ``-w`` are deliberately absent too. Either of them silently
    disables ``-s``, which would make the output a different size than the one
    predicted, with no error and no warning.

    ``-s`` is passed only when it would actually change something. The engine
    treats it as a resample applied *after* the model has run, so asking for
    4x from a model that is natively 4x would resample the result to the size
    it already is — a pointless filtering pass that can only soften the image.
    When the requested scale matches the model's own, the flag is left off and
    the model's native output is kept untouched. When the model's native scale
    cannot be determined from its name, the flag is passed, because forcing a
    known size is better than accepting an unknown one.

    ``-m`` is always absolute. The engine does not change directory before
    running, so a relative models path would be resolved against whatever
    directory the caller happened to be in.
    """
    command = [
        engine,
        "-i", request.input_path,
        "-o", temp_output,
        "-m", os.path.abspath(models_dir),
        "-n", request.model_name,
        "-f", request.output_format,
    ]
    if model_native_scale is None or model_native_scale != request.scale:
        command += ["-s", str(request.scale)]
    # The engine validates the tile size against a lower bound only, and the
    # desktop application omits the flag entirely rather than sending a zero.
    # Following that exactly avoids relying on how it treats a zero.
    tile = request.tile_size if tile_override is None else tile_override
    if tile and tile >= 32:
        command += ["-t", str(int(tile))]
    if request.gpu_id is not None:
        command += ["-g", str(request.gpu_id)]
    if jobs_spec:
        command += ["-j", jobs_spec]
    if request.compression is not None:
        # The engine rounds this to the nearest ten internally, so anything
        # finer than that is a false promise.
        command += ["-c", str(int(round(request.compression / 10.0) * 10))]
    if request.tta:
        command += ["-x"]
    if verbose:
        command += ["-v"]
    return command


def gather_facts(
    request: JobRequest,
    config: Config,
    discovery: Discovery,
    autonomy: Autonomy,
    info: imageprobe.ImageInfo,
) -> gate_module.JobFacts:
    """Collect everything the gate needs. All filesystem access lives here."""
    model = discovery.model_named(request.model_name)
    return gate_module.JobFacts(
        input_path=request.input_path,
        output_path=request.output_path,
        output_root=request.output_root,
        input_format=info.fmt,
        input_width=info.width,
        input_height=info.height,
        input_complete=info.complete,
        input_error=info.error,
        input_bytes=info.size_bytes,
        scale=request.scale,
        model_name=request.model_name,
        model_usable=bool(model and model.usable),
        model_native_scale=model.native_scale if model else None,
        output_format=request.output_format,
        output_exists=os.path.exists(request.output_path),
        free_disk_bytes=free_disk_bytes(request.output_path),
        models_dir=discovery.models_dir,
        input_has_alpha=info.has_alpha,
        engine_present=bool(discovery.bin_path),
        engine_executable=bool(
            discovery.bin_path and os.access(discovery.bin_path, os.X_OK)
        ),
        max_output_megapixels=config.max_output_megapixels,
        min_free_disk_mb=config.min_free_disk_mb,
        readable_formats=imageprobe.READABLE_FORMATS,
        writable_formats=imageprobe.WRITABLE_FORMATS,
        scale_policy="warn",
        stage=autonomy.state.stage,
        halted=autonomy.state.halted,
        human_approved=request.human_approved,
        approved_models=tuple(autonomy.state.approved_models),
        approved_max_scale=autonomy.state.approved_max_scale,
        approved_roots=tuple(autonomy.state.approved_roots),
        force_overwrite=request.force,
    )


def _quarantine(path: str, quarantine_dir: str) -> Optional[str]:
    """Move a failed or partial output out of the way, keeping it.

    Deleting evidence of a failure makes the next debugging session harder for
    no gain. A partial file is small, and knowing whether the engine wrote
    zero bytes or half an image is often the whole answer.
    """
    if not os.path.exists(path):
        return None
    try:
        os.makedirs(quarantine_dir, exist_ok=True)
        target = os.path.join(
            quarantine_dir, "%s-%s" % (time.strftime("%Y%m%d-%H%M%S"), os.path.basename(path))
        )
        shutil.move(path, target)
        return target
    except OSError:
        return None


class Runner:
    """Runs jobs, records them, and keeps the autonomy state honest."""

    def __init__(
        self,
        config: Config,
        discovery: Discovery,
        ledger: Ledger,
        autonomy: Autonomy,
        quarantine_dir: str,
        *,
        run_id: Optional[str] = None,
        dry_run: bool = False,
        on_event=None,
    ) -> None:
        self.config = config
        self.discovery = discovery
        self.ledger = ledger
        self.autonomy = autonomy
        self.quarantine_dir = quarantine_dir
        self.run_id = run_id or new_id("run")
        self.dry_run = dry_run
        self.on_event = on_event or (lambda *_args, **_kwargs: None)
        self._history: Optional[List[Dict[str, Any]]] = None

    # --- helpers -----------------------------------------------------------

    def history(self) -> List[Dict[str, Any]]:
        """Past rows, read once per run and reused for every prediction."""
        if self._history is None:
            self._history = self.ledger.rows()
        return self._history

    def _new_row(self, request: JobRequest, status: str) -> Row:
        from .config import VERSION

        return Row(
            id=new_id(),
            run_id=self.run_id,
            status=status,
            ts_start=now_iso(),
            model=request.model_name,
            scale=request.scale,
            tile_size=request.tile_size,
            gpu_id=request.gpu_id,
            output_format=request.output_format,
            stage=self.autonomy.state.stage,
            input_path=request.input_path,
            output_path=request.output_path,
            tool_version=VERSION,
        )

    def _record(self, row: Row) -> None:
        self.ledger.append(row)
        if self._history is not None:
            self._history.append(row.as_dict())

    # --- the one public entry point ---------------------------------------

    def run(self, request: JobRequest) -> JobResult:
        """Gate, predict, run, verify, score, record. In that order."""
        started_monotonic = time.monotonic()
        row = self._new_row(request, STATUS_REJECTED)

        # --- look at the input -------------------------------------------
        info = imageprobe.probe(request.input_path)
        row.input_bytes = info.size_bytes
        row.input_width = info.width
        row.input_height = info.height
        row.input_format = info.fmt

        # --- skip work already done --------------------------------------
        if os.path.exists(request.output_path) and not request.force:
            row.finish(STATUS_SKIPPED, started_monotonic)
            row.reason = "output already exists"
            self._record(row)
            self.on_event("skip", request, row)
            return JobResult(status=STATUS_SKIPPED, row=row, message="already done")

        # --- the gate -----------------------------------------------------
        facts = gather_facts(request, self.config, self.discovery, self.autonomy, info)
        decision = gate_module.evaluate(facts)
        row.gate_checks = decision.as_dicts()
        if not decision.allowed:
            row.finish(STATUS_REJECTED, started_monotonic)
            row.reason = decision.reason
            self._record(row)
            self.on_event("reject", request, row)
            return JobResult(
                status=STATUS_REJECTED,
                row=row,
                message=decision.reason,
                denials=[c.detail or c.name for c in decision.denials],
            )

        # --- the prediction, before anything runs -------------------------
        prediction = scorer.predict(
            made_at=now_iso(),
            input_width=info.width,
            input_height=info.height,
            input_bytes=info.size_bytes,
            scale=request.scale,
            output_format=request.output_format,
            model=request.model_name,
            history=self.history(),
        )
        row.prediction = prediction.as_dict()

        if self.dry_run:
            row.finish(STATUS_SKIPPED, started_monotonic)
            row.reason = "dry run: allowed by the gate, not executed"
            self._record(row)
            self.on_event("dry-run", request, row)
            return JobResult(status=STATUS_SKIPPED, row=row, message="would run")

        # --- prepare the destination --------------------------------------
        output_dir = os.path.dirname(request.output_path)
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as exc:
            row.finish(STATUS_FAILED, started_monotonic)
            row.reason = "cannot create output directory %s: %s" % (output_dir, exc)
            self._record(row)
            return JobResult(status=STATUS_FAILED, row=row, message=row.reason)

        extension = imageprobe.OUTPUT_EXTENSION.get(request.output_format, ".png")
        temp_output = os.path.join(output_dir, TEMP_PREFIX + row.id + extension)

        # --- re-check at the moment of acting ------------------------------
        # Between the check above and this line the disk may have filled or
        # the file may have been replaced. The gate is cheap; running the
        # engine on a full disk is not.
        facts = gather_facts(request, self.config, self.discovery, self.autonomy, info)
        recheck = gate_module.evaluate(facts)
        if not recheck.allowed:
            row.gate_checks = recheck.as_dicts()
            row.finish(STATUS_REJECTED, started_monotonic)
            row.reason = "conditions changed before starting: %s" % recheck.reason
            self._record(row)
            return JobResult(status=STATUS_REJECTED, row=row, message=row.reason)

        selected_model = self.discovery.model_named(request.model_name)
        native_scale = selected_model.native_scale if selected_model else None
        self.on_event("start", request, row)

        # --- run it, retrying smaller if the graphics processor gives out --
        #
        # Two of the engine's most common failures — running out of graphics
        # memory, and the graphics device being reset mid-job — are fixed by
        # doing the work in smaller pieces. The engine's own automatic tile
        # size tops out at 200 regardless of how much memory the machine has,
        # so on a large machine the first attempt deliberately asks for more
        # than that, and the ladder walks back down only if it has to.
        tile_size = request.tile_size
        attempts: List[Dict[str, Any]] = []
        engine_seconds = 0.0
        stderr_text = ""
        timed_out = False
        fault = None
        failure_reason: Optional[str] = None

        while True:
            command = build_command(
                self.discovery.bin_path or "",
                request,
                self.discovery.models_dir or "",
                temp_output,
                model_native_scale=native_scale,
                tile_override=tile_size,
            )
            row.command = list(command)
            row.tile_size = tile_size

            engine_started = time.monotonic()
            timed_out = False
            try:
                completed = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.config.timeout_seconds,
                )
                row.exit_code = completed.returncode
                stderr_text = completed.stderr.decode("utf-8", "replace")
            except subprocess.TimeoutExpired:
                timed_out = True
                row.exit_code = None
                stderr_text = "timed out after %d seconds" % self.config.timeout_seconds
            except OSError as exc:
                row.exit_code = None
                stderr_text = "could not start the engine: %s" % exc
            engine_seconds = time.monotonic() - engine_started

            # The engine prints everything, including its progress and its
            # success banner, to the error stream. Reading it is not optional:
            # its exit status is a constant zero once processing has begun.
            fault = enginefaults.find_fault(stderr_text)
            attempts.append(
                {
                    "tile_size": tile_size,
                    "seconds": round(engine_seconds, 3),
                    "exit_code": row.exit_code,
                    "fault": fault.key if fault else None,
                    "timed_out": timed_out,
                }
            )

            retry_possible = (
                fault is not None
                and fault.retry_smaller_tile
                and len(attempts) <= self.config.tile_retry_attempts
            )
            if not retry_possible:
                break
            smaller = enginefaults.next_tile_size(tile_size)
            if smaller is None:
                break
            # Clear the failed attempt's leftovers before trying again.
            try:
                os.unlink(temp_output)
            except OSError:
                pass
            self.on_event("retry", request, row)
            tile_size = smaller

        row.stderr_tail = stderr_text.strip()[-2000:] or None
        row.attempts = attempts

        # --- verify, rather than trust the exit code -----------------------
        if timed_out:
            failure_reason = (
                "timed out after %d seconds — the engine can hang with no error "
                "and no exit" % self.config.timeout_seconds
            )
        elif row.exit_code is None:
            failure_reason = stderr_text.strip()[:300] or "the engine did not run"
        elif row.exit_code != 0:
            # A non-zero status can only come from start-up validation, which
            # means the problem is the arguments, the models directory or the
            # graphics device — never the picture.
            failure_reason = "the engine refused to start (status %d): %s" % (
                row.exit_code,
                (stderr_text.strip().splitlines() or ["no message"])[-1][:300],
            )
        elif fault is not None:
            # The important branch. The engine has exited successfully and may
            # well have written a perfectly valid image; it is just not a
            # picture of anything. Only its error output reveals that.
            failure_reason = enginefaults.describe(fault, stderr_text)
            row.reason_key = fault.key
        elif not os.path.exists(temp_output):
            failure_reason = "the engine reported success but wrote no output file"

        output_info: Optional[imageprobe.ImageInfo] = None
        if failure_reason is None:
            output_info = imageprobe.probe(temp_output)
            row.output_bytes = output_info.size_bytes
            row.output_width = output_info.width
            row.output_height = output_info.height
            row.output_complete = output_info.complete
            if output_info.error:
                failure_reason = (
                    "the engine reported success but the output is not a readable "
                    "image: %s" % output_info.error
                )
            elif output_info.complete is False:
                failure_reason = (
                    "the engine reported success but the output is truncated"
                )
            elif output_info.size_bytes == 0:
                failure_reason = "the engine reported success but the output is empty"

        if failure_reason is not None:
            quarantined = _quarantine(temp_output, self.quarantine_dir)
            row.finish(STATUS_FAILED, started_monotonic)
            row.reason = failure_reason
            if quarantined:
                row.reason += " (partial output kept at %s)" % quarantined
            self._record(row)
            self.autonomy.consider_failures(
                self.ledger.consecutive_failures(), self.config.failure_halt_threshold
            )
            self.on_event("fail", request, row)
            return JobResult(status=STATUS_FAILED, row=row, message=failure_reason)

        # --- score the prediction before moving the file -------------------
        row.score = scorer.score(
            prediction,
            actual_width=row.output_width,
            actual_height=row.output_height,
            actual_bytes=row.output_bytes,
            actual_duration=engine_seconds,
            scored_at=now_iso(),
        )

        # --- the counterfactual, on a sample -------------------------------
        job_index = self.autonomy.next_job_index()
        if counterfactual_module.should_run(job_index, self.config.counterfactual_every):
            baseline = counterfactual_module.run_baseline(
                request.input_path, prediction.output_width or 0
            )
            row.counterfactual = {
                "baseline": baseline,
                "comparison": counterfactual_module.compare(
                    baseline,
                    {
                        "duration_seconds": engine_seconds,
                        "output_bytes": row.output_bytes,
                        "output_width": row.output_width,
                        "output_height": row.output_height,
                    },
                ),
            }

        # --- publish the result atomically ---------------------------------
        try:
            os.replace(temp_output, request.output_path)
        except OSError as exc:
            quarantined = _quarantine(temp_output, self.quarantine_dir)
            row.finish(STATUS_FAILED, started_monotonic)
            row.reason = "could not move the finished image into place: %s" % exc
            if quarantined:
                row.reason += " (result kept at %s)" % quarantined
            self._record(row)
            return JobResult(status=STATUS_FAILED, row=row, message=row.reason)

        row.output_sha256 = imageprobe.sha256_file(request.output_path)
        row.input_sha256 = (
            imageprobe.sha256_file(request.input_path)
            if os.path.isfile(request.input_path)
            else None
        )
        row.finish(STATUS_OK, started_monotonic)
        self._record(row)
        self.on_event("done", request, row)

        message = "%dx%d in %.1fs" % (
            row.output_width or 0,
            row.output_height or 0,
            row.duration_seconds or 0.0,
        )
        if (row.score or {}).get("verdict") == "wrong":
            message += " — WARNING: not the size that was asked for"
        return JobResult(status=STATUS_OK, row=row, message=message)
