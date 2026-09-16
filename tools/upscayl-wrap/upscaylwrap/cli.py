"""The command surface.

Everything the tool can do is a subcommand here. The verbs are deliberately
plain — ``up``, ``batch``, ``watch``, ``doctor``, ``report`` — because the
command you reach for six months from now is the one you can guess.

Every subcommand takes ``--json`` and prints a machine-readable object instead
of prose, so the same tool drives both a terminal and a script.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from . import counterfactual as counterfactual_module
from . import imageprobe, launchagent, review as review_module
from .autonomy import Autonomy, STAGE_NAMES
from .config import Config, VERSION, discover, paths, pick_default_model
from .ledger import Ledger, STATUS_FAILED, STATUS_OK, STATUS_REJECTED, STATUS_SKIPPED, now_iso, summarize
from .runner import JobRequest, Runner, free_disk_bytes

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_REFUSED = 2      # The gate said no; nothing was wrong with the tool.
EXIT_NOT_READY = 3    # Upscayl is missing or unusable.


# --------------------------------------------------------------------------
# small output helpers
# --------------------------------------------------------------------------

def _emit(payload: Dict[str, Any], as_json: bool, text: str) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    elif text:
        print(text)


def _human_bytes(count: Optional[int]) -> str:
    if not count:
        return "0 B"
    size = float(count)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return "%.1f %s" % (size, unit) if unit != "B" else "%d B" % size
        size /= 1024
    return "%.1f TB" % size


def _context(args: argparse.Namespace):
    """Load everything a command needs, once."""
    app_paths = paths()
    app_paths.ensure()
    config = Config.load(getattr(args, "config_file", None))
    discovery = discover(config)
    ledger = Ledger(app_paths.ledger)
    autonomy = Autonomy(app_paths.state_file, app_paths.halt_file)
    return app_paths, config, discovery, ledger, autonomy


def _resolve(path: str) -> str:
    """Absolute, symlink-free, and expanded. The gate assumes this was done."""
    return os.path.realpath(os.path.abspath(os.path.expanduser(path)))


def _default_out_dir(config: Config, first_input: str) -> str:
    if config.out_dir:
        return _resolve(config.out_dir)
    base = first_input if os.path.isdir(first_input) else os.path.dirname(first_input)
    return _resolve(os.path.join(base, "upscaled"))


def output_path_for(
    input_path: str,
    out_root: str,
    scale: int,
    output_format: str,
    *,
    relative_to: Optional[str] = None,
    taken: Optional[set] = None,
) -> str:
    """Where a given input's result should go.

    Names are ``photo_4x.png`` rather than ``photo.png`` so that an upscale is
    never mistaken for its original in a folder listing.

    The engine's own batch mode has a naming flaw worth avoiding: two inputs
    that differ only by extension collapse onto one output name, and it only
    notices when the pair happen to be adjacent in sorted order. Here every
    planned name is checked against the ones already planned, and a collision
    keeps the original extension in the name.
    """
    stem, original_ext = os.path.splitext(os.path.basename(input_path))
    extension = imageprobe.OUTPUT_EXTENSION.get(output_format, ".png")

    subdirectory = ""
    if relative_to:
        relative = os.path.relpath(os.path.dirname(input_path), relative_to)
        if relative not in (".", ""):
            subdirectory = relative

    candidate = os.path.join(out_root, subdirectory, "%s_%dx%s" % (stem, scale, extension))
    if taken is not None and candidate in taken:
        suffix = original_ext.lstrip(".").lower() or "img"
        candidate = os.path.join(
            out_root, subdirectory, "%s_%s_%dx%s" % (stem, suffix, scale, extension)
        )
        counter = 2
        while candidate in taken:
            candidate = os.path.join(
                out_root,
                subdirectory,
                "%s_%s_%dx_%d%s" % (stem, suffix, scale, counter, extension),
            )
            counter += 1
    if taken is not None:
        taken.add(candidate)
    return candidate


def _select_model(args, config: Config, discovery) -> Optional[str]:
    if getattr(args, "model", None):
        return args.model
    chosen = pick_default_model(config, discovery)
    return chosen.name if chosen else None


def _collect_inputs(targets: Sequence[str], recursive: bool, skip_root: Optional[str]) -> List[str]:
    """Expand files and directories into a sorted list of candidate images.

    The output directory is skipped explicitly. Without that, a second run
    over the same folder would find its own results and the gate would have to
    refuse them one by one — correct, but noisy enough to hide real problems.
    """
    found: List[str] = []
    skip = _resolve(skip_root) if skip_root else None
    for target in targets:
        resolved = _resolve(target)
        if os.path.isfile(resolved):
            found.append(resolved)
            continue
        if not os.path.isdir(resolved):
            continue
        if recursive:
            for directory, subdirectories, filenames in os.walk(resolved):
                if skip and (_resolve(directory) == skip or _resolve(directory).startswith(skip + os.sep)):
                    subdirectories[:] = []
                    continue
                subdirectories[:] = [d for d in subdirectories if not d.startswith(".")]
                for name in sorted(filenames):
                    if name.startswith("."):
                        continue
                    found.append(os.path.join(directory, name))
        else:
            for name in sorted(os.listdir(resolved)):
                candidate = os.path.join(resolved, name)
                if name.startswith(".") or not os.path.isfile(candidate):
                    continue
                found.append(candidate)

    # Keep only things that are actually images, by content rather than name.
    images: List[str] = []
    for candidate in found:
        if skip and _resolve(candidate).startswith(skip + os.sep):
            continue
        try:
            with open(candidate, "rb") as handle:
                head = handle.read(64)
        except OSError:
            continue
        if imageprobe.sniff_format(head) in imageprobe.READABLE_FORMATS:
            images.append(candidate)
    return sorted(set(images))


# --------------------------------------------------------------------------
# doctor
# --------------------------------------------------------------------------

def _quarantine_state(path: str) -> Optional[bool]:
    """Is this file flagged as downloaded-from-the-internet?

    Upscayl's own install instructions tell people to right-click and Open the
    first time, which is the Gatekeeper prompt for exactly this attribute.
    Running the nested engine from a terminal is a different code path, so
    whether it is blocked is worth reporting rather than assuming.
    """
    if sys.platform != "darwin":
        return None
    try:
        completed = subprocess.run(
            ["/usr/bin/xattr", "-p", "com.apple.quarantine", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.returncode == 0


def _engine_responds(engine: str) -> Dict[str, Any]:
    """Ask the engine to describe itself.

    Its help screen exits non-zero by design, so the check is whether the
    usage banner appeared — not the exit code. Judging this by exit status
    would report a perfectly healthy engine as broken.
    """
    result: Dict[str, Any] = {"ran": False}
    try:
        completed = subprocess.run(
            [engine, "-h"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["error"] = str(exc)
        return result
    text = (completed.stderr or b"").decode("utf-8", "replace") + (
        completed.stdout or b""
    ).decode("utf-8", "replace")
    result["ran"] = True
    result["exit_code"] = completed.returncode
    result["looks_like_upscayl"] = "Usage: upscayl-bin" in text or "-n model-name" in text
    result["banner"] = text.strip().splitlines()[0][:200] if text.strip() else ""
    return result


def command_doctor(args) -> int:
    app_paths, config, discovery, ledger, autonomy = _context(args)
    checks: List[Dict[str, Any]] = []
    lines: List[str] = []

    def check(name: str, ok: Optional[bool], detail: str, fix: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail, "fix": fix})
        mark = "ok  " if ok else ("??  " if ok is None else "FAIL")
        lines.append("[%s] %-26s %s" % (mark, name, detail))
        if fix and not ok:
            lines.append("       fix: %s" % fix)

    check(
        "python",
        sys.version_info >= (3, 8),
        "Python %s at %s" % (platform.python_version(), sys.executable),
        "install Apple's Command Line Tools: xcode-select --install",
    )
    check(
        "platform",
        sys.platform == "darwin",
        "%s %s (%s)" % (platform.system(), platform.release(), platform.machine()),
        "this tool drives a macOS application; other platforms are untested",
    )

    if discovery.bin_path:
        check("engine found", True, discovery.bin_path)
        check(
            "engine executable",
            os.access(discovery.bin_path, os.X_OK),
            "executable bit %s" % ("set" if os.access(discovery.bin_path, os.X_OK) else "missing"),
            "chmod +x '%s'" % discovery.bin_path,
        )
        quarantined = _quarantine_state(discovery.bin_path)
        check(
            "engine not quarantined",
            (not quarantined) if quarantined is not None else None,
            "quarantine attribute %s"
            % ("present" if quarantined else "absent" if quarantined is not None else "not checked"),
            "open Upscayl once from Finder, or run: xattr -d com.apple.quarantine '%s'"
            % discovery.bin_path,
        )
        responds = _engine_responds(discovery.bin_path)
        check(
            "engine responds",
            bool(responds.get("looks_like_upscayl")),
            responds.get("banner") or responds.get("error") or "no output",
            "the binary was found but does not behave like upscayl-bin",
        )
    else:
        check(
            "engine found",
            False,
            "not found after %d locations" % len(discovery.searched_bin),
            "run tools/upscayl-wrap/install.sh, or: brew install --cask upscayl",
        )

    usable = discovery.usable_models
    check(
        "models",
        bool(usable),
        "%d usable in %s" % (len(usable), discovery.models_dir or "no directory found"),
        "install Upscayl, or point models_dir at a folder of .param/.bin pairs",
    )
    if usable:
        lines.append("       %s" % ", ".join(m.name for m in usable))

    chosen = pick_default_model(config, discovery)
    check(
        "default model",
        bool(chosen),
        "%s (native %sx)" % (chosen.name, chosen.native_scale) if chosen else "none available",
        "set default_model in %s" % app_paths.config_file,
    )

    for problem in discovery.problems:
        check("discovery", False, problem)

    check(
        "config",
        True,
        "%s%s" % (app_paths.config_file, "" if os.path.isfile(app_paths.config_file) else " (not written yet; defaults in use)"),
    )

    damaged = ledger.damaged_line_count()
    row_count = len(ledger.rows())
    check(
        "ledger",
        damaged == 0,
        "%d rows at %s%s"
        % (row_count, app_paths.ledger, ", %d damaged lines" % damaged if damaged else ""),
        "damaged lines are skipped on read; the file can be edited by hand if needed",
    )

    free = free_disk_bytes(app_paths.default_outbox)
    check(
        "disk",
        free is None or free > config.min_free_disk_mb * 1024 * 1024,
        "%s free" % _human_bytes(free) if free is not None else "unknown",
        "free space, or lower min_free_disk_mb",
    )

    check(
        "baseline tool",
        counterfactual_module.available(),
        "sips %s" % ("present" if counterfactual_module.available() else "absent (counterfactual comparisons will be skipped)"),
    )

    agent_installed = launchagent.is_installed()
    check(
        "background agent",
        None,
        "%s" % ("installed" if agent_installed else "not installed"),
        "install with: upscayl-wrap install-agent",
    )

    check("autonomy", not autonomy.state.halted, autonomy.describe(), "upscayl-wrap resume")

    failures = [c for c in checks if c["ok"] is False]
    ready = discovery.bin_path is not None and bool(usable) and not autonomy.state.halted

    summary = "%s — %d checks, %d failing" % (
        "READY" if ready else "NOT READY",
        len(checks),
        len(failures),
    )
    lines.append("")
    lines.append(summary)
    if not discovery.bin_path and getattr(args, "verbose", False):
        lines.append("")
        lines.append("Looked for the engine in:")
        lines.extend("  %s" % p for p in discovery.searched_bin)

    _emit(
        {
            "ready": ready,
            "version": VERSION,
            "checks": checks,
            "engine": discovery.bin_path,
            "models_dir": discovery.models_dir,
            "models": [m.as_dict() for m in discovery.models],
            "searched_bin": discovery.searched_bin,
            "searched_models": discovery.searched_models,
        },
        args.json,
        "\n".join(lines),
    )
    return EXIT_OK if ready else EXIT_NOT_READY


# --------------------------------------------------------------------------
# models
# --------------------------------------------------------------------------

def command_models(args) -> int:
    _, config, discovery, _, _ = _context(args)
    default = pick_default_model(config, discovery)
    lines = []
    if not discovery.models:
        lines.append("No models found. Looked in:")
        lines.extend("  %s" % d for d in discovery.searched_models)
    else:
        lines.append("%-26s %-8s %s" % ("MODEL", "NATIVE", "STATUS"))
        for model in discovery.models:
            marker = " (default)" if default and model.name == default.name else ""
            lines.append(
                "%-26s %-8s %s%s"
                % (
                    model.name,
                    "%sx" % model.native_scale if model.native_scale else "?",
                    "ready" if model.usable else "INCOMPLETE",
                    marker,
                )
            )
        lines.append("")
        lines.append("From %s" % discovery.models_dir)
    _emit(
        {
            "models": [m.as_dict() for m in discovery.models],
            "default": default.name if default else None,
            "models_dir": discovery.models_dir,
        },
        args.json,
        "\n".join(lines),
    )
    return EXIT_OK


# --------------------------------------------------------------------------
# upscaling
# --------------------------------------------------------------------------

def _run_jobs(args, targets: List[str], recursive: bool) -> int:
    app_paths, config, discovery, ledger, autonomy = _context(args)

    if not discovery.bin_path:
        _emit(
            {"error": "engine not found", "searched": discovery.searched_bin},
            args.json,
            "Upscayl's engine was not found. Run 'upscayl-wrap doctor' to see where it looked.",
        )
        return EXIT_NOT_READY

    model_name = _select_model(args, config, discovery)
    if not model_name:
        _emit(
            {"error": "no usable model"},
            args.json,
            "No usable model. Run 'upscayl-wrap doctor'.",
        )
        return EXIT_NOT_READY

    scale = args.scale or config.default_scale
    output_format = args.format or config.output_format

    first = _resolve(targets[0])
    out_root = _resolve(args.out) if args.out else _default_out_dir(config, first)

    inputs = _collect_inputs(targets, recursive, out_root)
    if not inputs:
        _emit({"jobs": [], "note": "no images found"}, args.json, "No images found.")
        return EXIT_OK

    relative_to = first if os.path.isdir(first) and recursive else None

    runner = Runner(
        config,
        discovery,
        ledger,
        autonomy,
        app_paths.quarantine_dir,
        dry_run=args.dry_run,
    )

    taken: set = set()
    results = []
    counts = {STATUS_OK: 0, STATUS_FAILED: 0, STATUS_REJECTED: 0, STATUS_SKIPPED: 0}
    lines: List[str] = []

    total = len(inputs)
    for index, input_path in enumerate(inputs, start=1):
        output_path = output_path_for(
            input_path, out_root, scale, output_format, relative_to=relative_to, taken=taken
        )
        request = JobRequest(
            input_path=input_path,
            output_path=output_path,
            output_root=out_root,
            scale=scale,
            model_name=model_name,
            output_format=output_format,
            tile_size=args.tile if args.tile is not None else config.tile_size,
            gpu_id=args.gpu if args.gpu is not None else config.gpu_id,
            compression=args.compression,
            tta=args.tta,
            force=args.force,
            human_approved=args.yes,
        )
        if not args.quiet and not args.json:
            print(
                "[%d/%d] %s" % (index, total, os.path.basename(input_path)),
                end=" ... ",
                flush=True,
            )
        result = runner.run(request)
        counts[result.status] = counts.get(result.status, 0) + 1
        if not args.quiet and not args.json:
            print(result.message or result.status)
        results.append(
            {
                "input": input_path,
                "output": output_path,
                "status": result.status,
                "message": result.message,
                "id": result.row.id,
            }
        )
        if result.status == STATUS_FAILED and not config.keep_going_on_error:
            lines.append("Stopping after the first failure (keep_going_on_error is off).")
            break
        if autonomy.state.halted:
            lines.append("Halted: %s" % (autonomy.state.halt_reason or ""))
            break

    lines.append("")
    lines.append(
        "%d upscaled, %d failed, %d refused, %d skipped  ->  %s"
        % (
            counts[STATUS_OK],
            counts[STATUS_FAILED],
            counts[STATUS_REJECTED],
            counts[STATUS_SKIPPED],
            out_root,
        )
    )
    refusals = [r for r in results if r["status"] == STATUS_REJECTED]
    if refusals:
        lines.append("")
        lines.append("Refused:")
        for refusal in refusals[:10]:
            lines.append("  %s — %s" % (os.path.basename(refusal["input"]), refusal["message"]))

    _emit(
        {"out_dir": out_root, "model": model_name, "scale": scale, "counts": counts, "jobs": results},
        args.json,
        "\n".join(lines),
    )

    if counts[STATUS_FAILED]:
        return EXIT_ERROR
    if counts[STATUS_OK] == 0 and counts[STATUS_REJECTED]:
        return EXIT_REFUSED
    return EXIT_OK


def command_up(args) -> int:
    return _run_jobs(args, args.inputs, recursive=False)


def command_batch(args) -> int:
    return _run_jobs(args, [args.directory], recursive=args.recursive)


# --------------------------------------------------------------------------
# the loop
# --------------------------------------------------------------------------

def command_watch(args) -> int:
    """Sweep the inbox, act on what is there, score it, review daily.

    Designed to be called repeatedly by the system scheduler rather than left
    running. A short-lived process that does one sweep cannot leak memory,
    cannot wedge, and restarts clean after a crash or a reboot.
    """
    app_paths, config, discovery, ledger, autonomy = _context(args)
    inbox = _resolve(args.inbox or config.inbox_dir or app_paths.default_inbox)
    out_root = _resolve(args.out or config.out_dir or app_paths.default_outbox)

    os.makedirs(inbox, exist_ok=True)
    os.makedirs(out_root, exist_ok=True)

    if autonomy.state.halted:
        _emit(
            {"halted": True, "reason": autonomy.state.halt_reason},
            args.json,
            "Halted: %s\nClear it with 'upscayl-wrap resume'." % (autonomy.state.halt_reason or ""),
        )
        return EXIT_REFUSED

    # Stage 1 means a person approves each job, so an unattended sweep must
    # not act. It reports what it would have done and stops.
    acting = autonomy.state.stage >= 2 or args.yes
    namespace = argparse.Namespace(
        **{
            **vars(args),
            "inputs": [inbox],
            "out": out_root,
            "dry_run": args.dry_run or not acting,
            "recursive": True,
        }
    )
    exit_code = _run_jobs(namespace, [inbox], recursive=True)

    # One review per day, written where the next sweep will read it.
    today = date.today().isoformat()
    if autonomy.state.last_review_date != today:
        rows = ledger.rows()
        built = review_module.build(rows[-500:], window_label="through %s" % today)
        markdown = review_module.render_markdown(built, generated_at=now_iso())
        review_module.write(app_paths.reviews_dir, markdown, date_stamp=today)
        autonomy.state.last_review_date = today
        autonomy.save()

    if not acting and not args.json:
        print(
            "\nStage 1: nothing was run. Raise the stage to let the watch folder act:\n"
            "  upscayl-wrap stage --set 2"
        )
    return exit_code


# --------------------------------------------------------------------------
# reading the record
# --------------------------------------------------------------------------

def command_report(args) -> int:
    app_paths, config, discovery, ledger, autonomy = _context(args)
    rows = ledger.rows()
    window = rows[-args.last :] if args.last else rows
    stats = summarize(window)
    counts = stats["counts"]

    if args.compact:
        text = "upscayl-wrap: %d ok, %d failed, %d refused | %s | %s" % (
            counts.get(STATUS_OK, 0),
            counts.get(STATUS_FAILED, 0),
            counts.get(STATUS_REJECTED, 0),
            autonomy.describe(),
            "engine ok" if discovery.bin_path else "ENGINE MISSING",
        )
        _emit({"summary": text, "stats": stats}, args.json, text)
        return EXIT_OK

    lines = [
        "upscayl-wrap %s — %s" % (VERSION, autonomy.describe()),
        "",
        "Jobs in this window: %d" % stats["rows"],
        "  upscaled  %d" % counts.get(STATUS_OK, 0),
        "  failed    %d" % counts.get(STATUS_FAILED, 0),
        "  refused   %d" % counts.get(STATUS_REJECTED, 0),
        "  skipped   %d" % counts.get(STATUS_SKIPPED, 0),
    ]
    if stats["median_seconds"]:
        lines.append("")
        lines.append("Median job: %.1f s, %.1f megapixels produced in total" % (stats["median_seconds"], stats["megapixels_out"]))
    if stats["by_model"]:
        lines.append("")
        lines.append("%-26s %-6s %-8s %s" % ("MODEL", "OK", "FAILED", "SEC/MEGAPIXEL"))
        for name, entry in sorted(stats["by_model"].items()):
            lines.append(
                "%-26s %-6d %-8d %s"
                % (name, entry["ok"], entry["failed"], entry.get("seconds_per_output_megapixel", "-"))
            )
    if stats["recent_failures"]:
        lines.append("")
        lines.append("Recent failures:")
        for failure in stats["recent_failures"][-5:]:
            lines.append(
                "  %s — %s"
                % (os.path.basename(str(failure.get("input") or "?")), str(failure.get("reason") or "")[:120])
            )
    _emit({"stats": stats, "autonomy": autonomy.state.as_dict()}, args.json, "\n".join(lines))
    return EXIT_OK


def command_ledger(args) -> int:
    app_paths, _, _, ledger, _ = _context(args)
    rows = ledger.rows(limit=args.tail)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
        return EXIT_OK
    if not rows:
        print("No rows yet at %s" % app_paths.ledger)
        return EXIT_OK
    for row in rows:
        print(
            "%s  %-9s %-22s %s"
            % (
                row.get("ts_start", "")[:19],
                row.get("status", ""),
                (row.get("model") or "")[:22],
                os.path.basename(str(row.get("input_path") or "")),
            )
        )
        if row.get("reason"):
            print("    %s" % str(row["reason"])[:160])
    return EXIT_OK


def command_review(args) -> int:
    app_paths, _, _, ledger, autonomy = _context(args)
    rows = ledger.rows()
    window = rows[-args.last :] if args.last else rows
    built = review_module.build(window, window_label="last %d jobs" % len(window))
    markdown = review_module.render_markdown(built, generated_at=now_iso())
    if args.write:
        dated, latest = review_module.write(
            app_paths.reviews_dir, markdown, date_stamp=date.today().isoformat()
        )
        autonomy.state.last_review_date = date.today().isoformat()
        autonomy.save()
        _emit({"review": built, "written": [dated, latest]}, args.json, markdown + "\nWritten to %s" % dated)
    else:
        _emit({"review": built}, args.json, markdown)
    return EXIT_OK


# --------------------------------------------------------------------------
# autonomy and settings
# --------------------------------------------------------------------------

def command_stage(args) -> int:
    _, _, discovery, _, autonomy = _context(args)
    if args.set is None:
        _emit(
            {"stage": autonomy.state.stage, "halted": autonomy.state.halted, "state": autonomy.state.as_dict()},
            args.json,
            "%s\n\n1 = %s\n2 = %s\n3 = %s"
            % (
                autonomy.describe(),
                STAGE_NAMES[1],
                STAGE_NAMES[2],
                STAGE_NAMES[3],
            ),
        )
        return EXIT_OK

    if args.set >= 2 and not autonomy.state.approved_models:
        # Moving off stage 1 without an envelope would make stage 2 identical
        # to stage 3, which defeats the point of having both.
        approved = [m.name for m in discovery.usable_models]
        autonomy.approve_envelope(models=approved, max_scale=args.max_scale or 4)

    ok, message = autonomy.set_stage(args.set)
    _emit({"ok": ok, "message": message, "state": autonomy.state.as_dict()}, args.json, message)
    return EXIT_OK if ok else EXIT_ERROR


def command_halt(args) -> int:
    _, _, _, _, autonomy = _context(args)
    reason = args.reason or "halted by hand"
    autonomy.halt(reason)
    _emit({"halted": True, "reason": reason}, args.json, "Halted: %s" % reason)
    return EXIT_OK


def command_resume(args) -> int:
    _, _, _, _, autonomy = _context(args)
    existed = autonomy.resume()
    message = (
        "Resumed. Stage is back to 1 (%s) — raise it again when you are satisfied the cause is fixed."
        % STAGE_NAMES[1]
        if existed
        else "Nothing was halted."
    )
    _emit({"resumed": existed, "stage": autonomy.state.stage}, args.json, message)
    return EXIT_OK


def command_config(args) -> int:
    app_paths, config, _, _, _ = _context(args)
    if args.set:
        for assignment in args.set:
            if "=" not in assignment:
                print("Expected key=value, got: %s" % assignment, file=sys.stderr)
                return EXIT_ERROR
            key, _, raw = assignment.partition("=")
            key = key.strip()
            if not hasattr(config, key):
                print("Unknown setting: %s" % key, file=sys.stderr)
                return EXIT_ERROR
            current = getattr(config, key)
            try:
                if isinstance(current, bool):
                    value: Any = raw.strip().lower() in ("1", "true", "yes", "on")
                elif isinstance(current, int) and not isinstance(current, bool):
                    value = int(raw)
                elif isinstance(current, float):
                    value = float(raw)
                else:
                    value = raw.strip() or None
            except ValueError:
                print("Could not read %r as a value for %s" % (raw, key), file=sys.stderr)
                return EXIT_ERROR
            setattr(config, key, value)
        written = config.save(getattr(args, "config_file", None))
        _emit({"config": config.__dict__, "file": written}, args.json, "Saved %s" % written)
        return EXIT_OK

    _emit(
        {"config": config.__dict__, "file": app_paths.config_file, "paths": app_paths.__dict__},
        args.json,
        json.dumps(config.__dict__, indent=2, sort_keys=True),
    )
    return EXIT_OK


def command_install_agent(args) -> int:
    app_paths, config, _, _, _ = _context(args)
    inbox = _resolve(args.inbox or config.inbox_dir or app_paths.default_inbox)
    out_root = _resolve(args.out or config.out_dir or app_paths.default_outbox)
    os.makedirs(inbox, exist_ok=True)
    os.makedirs(out_root, exist_ok=True)
    result = launchagent.install(
        inbox=inbox,
        out_dir=out_root,
        interval_seconds=args.interval,
        log_dir=app_paths.log_dir,
    )
    _emit(result, args.json, result.get("message", ""))
    return EXIT_OK if result.get("ok") else EXIT_ERROR


def command_uninstall_agent(args) -> int:
    result = launchagent.uninstall()
    _emit(result, args.json, result.get("message", ""))
    return EXIT_OK if result.get("ok") else EXIT_ERROR


# --------------------------------------------------------------------------
# argument parsing
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="upscayl-wrap",
        description="Drive Upscayl's upscaling engine from the command line, with a record of every job.",
    )
    parser.add_argument("--version", action="version", version="upscayl-wrap %s" % VERSION)
    parser.add_argument("--json", action="store_true", help="print machine-readable output")
    parser.add_argument("--config-file", dest="config_file", help="use a different config file")
    parser.add_argument("--quiet", action="store_true", help="print less")
    subparsers = parser.add_subparsers(dest="command")

    def add_job_flags(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("-o", "--out", help="output directory")
        sub.add_argument("-s", "--scale", type=int, help="output scale (default 4)")
        sub.add_argument("-m", "--model", help="model name; see 'upscayl-wrap models'")
        sub.add_argument("-f", "--format", choices=sorted(imageprobe.WRITABLE_FORMATS), help="output format")
        sub.add_argument("--tile", type=int, help="tile size; 0 is automatic, lower it if the engine runs out of memory")
        sub.add_argument("--gpu", type=int, help="graphics processor id")
        sub.add_argument("--compression", type=int, help="0-100; the engine rounds this to the nearest 10")
        sub.add_argument("--tta", action="store_true", help="test-time augmentation: slower, sometimes cleaner")
        sub.add_argument("--force", action="store_true", help="replace an existing output")
        sub.add_argument("--dry-run", action="store_true", help="check everything, run nothing")
        sub.add_argument("-y", "--yes", action="store_true", help="approve these jobs (required at stage 1)")

    doctor = subparsers.add_parser("doctor", help="check that everything needed is present and working")
    doctor.add_argument("-v", "--verbose", action="store_true", help="list every path searched")
    doctor.set_defaults(func=command_doctor)

    models = subparsers.add_parser("models", help="list the models available")
    models.set_defaults(func=command_models)

    up = subparsers.add_parser("up", help="upscale one or more images")
    up.add_argument("inputs", nargs="+", help="image files")
    add_job_flags(up)
    up.set_defaults(func=command_up)

    batch = subparsers.add_parser("batch", help="upscale a whole directory")
    batch.add_argument("directory")
    batch.add_argument("-r", "--recursive", action="store_true", help="include subdirectories")
    add_job_flags(batch)
    batch.set_defaults(func=command_batch)

    watch = subparsers.add_parser("watch", help="sweep the inbox once, then write the daily review")
    watch.add_argument("--inbox", help="directory to sweep")
    add_job_flags(watch)
    watch.set_defaults(func=command_watch, recursive=True)

    report = subparsers.add_parser("report", help="what the record says")
    report.add_argument("--last", type=int, default=0, help="only the last N jobs")
    report.add_argument("--compact", action="store_true", help="one line, suitable for a notification")
    report.set_defaults(func=command_report)

    ledger_parser = subparsers.add_parser("ledger", help="show recent rows from the record")
    ledger_parser.add_argument("--tail", type=int, default=20)
    ledger_parser.set_defaults(func=command_ledger)

    review_parser = subparsers.add_parser("review", help="right, wrong, could not have known, will do differently")
    review_parser.add_argument("--last", type=int, default=0, help="only the last N jobs")
    review_parser.add_argument("--write", action="store_true", help="save it alongside the ledger")
    review_parser.set_defaults(func=command_review)

    stage = subparsers.add_parser("stage", help="show or set how much the tool may do on its own")
    stage.add_argument("--set", type=int, choices=(1, 2, 3))
    stage.add_argument("--max-scale", type=int, help="the largest scale stage 2 may use unattended")
    stage.set_defaults(func=command_stage)

    halt = subparsers.add_parser("halt", help="stop the tool acting until a person clears it")
    halt.add_argument("--reason")
    halt.set_defaults(func=command_halt)

    resume = subparsers.add_parser("resume", help="clear a halt")
    resume.set_defaults(func=command_resume)

    config_parser = subparsers.add_parser("config", help="show or change settings")
    config_parser.add_argument("--set", action="append", metavar="KEY=VALUE")
    config_parser.set_defaults(func=command_config)

    install_agent = subparsers.add_parser("install-agent", help="run the watch sweep on a schedule")
    install_agent.add_argument("--inbox")
    install_agent.add_argument("--out")
    install_agent.add_argument("--interval", type=int, default=300, help="seconds between sweeps")
    install_agent.set_defaults(func=command_install_agent)

    uninstall_agent = subparsers.add_parser("uninstall-agent", help="stop the scheduled sweep")
    uninstall_agent.set_defaults(func=command_uninstall_agent)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return EXIT_OK
    # Subcommands that take no job flags still read some of them.
    for name, default in (
        ("yes", False),
        ("dry_run", False),
        ("quiet", False),
        ("json", False),
        ("out", None),
    ):
        if not hasattr(args, name):
            setattr(args, name, default)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return EXIT_ERROR
    except BrokenPipeError:  # e.g. piping into head
        return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
