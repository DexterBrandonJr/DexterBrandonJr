"""The gate: the rules that decide whether a job may run.

Every function here is pure. It takes facts that someone else gathered and
returns a decision — it never touches the filesystem, never runs a command,
and never mutates what it is given. That is what makes it testable without a
Mac, without Upscayl installed, and without any real photos.

The rules exist because the failure modes they prevent are all silent:

* An upscaler pointed at its own output directory will re-upscale its own
  results forever, and the only symptom is a disk that fills overnight.
* A 4x upscale of a 48-megapixel photo is a 768-megapixel image. Nothing
  warns you; the machine simply starts swapping.
* Overwriting the original with the upscale destroys the only copy of the
  input, and that is not recoverable from a ledger row.

The caller re-runs ``evaluate`` immediately before spawning the engine, not
only when the job was queued. Between queueing and running, a disk can fill
and a file can be replaced.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Severity of a failed check.
DENY = "deny"
WARN = "warn"

# Autonomy stages. A halt can lower this from anywhere; only a person raises it.
STAGE_APPROVE_EVERYTHING = 1
STAGE_WITHIN_APPROVED = 2
STAGE_ACT_ALONE = 3


@dataclass
class Check:
    """One rule's verdict."""

    name: str
    passed: bool
    severity: str = DENY
    detail: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "detail": self.detail,
        }


@dataclass
class Decision:
    """What the gate concluded, and why."""

    allowed: bool
    checks: List[Check] = field(default_factory=list)

    @property
    def denials(self) -> List[Check]:
        return [c for c in self.checks if not c.passed and c.severity == DENY]

    @property
    def warnings(self) -> List[Check]:
        return [c for c in self.checks if not c.passed and c.severity == WARN]

    @property
    def reason(self) -> str:
        """One line explaining the refusal, or an empty string if allowed."""
        return "; ".join(c.detail or c.name for c in self.denials)

    def as_dicts(self) -> List[Dict[str, Any]]:
        return [c.as_dict() for c in self.checks]


@dataclass
class JobFacts:
    """Everything the gate needs, gathered by the caller.

    Paths must already be resolved to absolute, symlink-free form. The gate
    does not resolve them itself, because resolving is filesystem access and
    the gate stays pure.
    """

    input_path: str
    output_path: str
    output_root: str

    # From probing the input.
    input_format: Optional[str] = None
    input_width: Optional[int] = None
    input_height: Optional[int] = None
    input_complete: Optional[bool] = None
    input_error: Optional[str] = None
    input_bytes: int = 0

    # The request.
    scale: int = 4
    model_name: Optional[str] = None
    model_usable: bool = False
    model_native_scale: Optional[int] = None
    output_format: str = "png"

    # The environment.
    output_exists: bool = False
    free_disk_bytes: Optional[int] = None
    engine_present: bool = False
    engine_executable: bool = False
    models_dir: Optional[str] = None
    input_has_alpha: Optional[bool] = None

    # Budgets and policy.
    max_output_megapixels: float = 400.0
    min_free_disk_mb: int = 2048
    readable_formats: frozenset = frozenset()
    writable_formats: frozenset = frozenset()
    # Very small inputs crash the engine as reliably as very large ones do.
    min_input_dimension: int = 32
    # "strict" refuses a scale the model was not trained for; "warn" allows it
    # and records that the output may not be the size that was asked for.
    scale_policy: str = "warn"

    # Autonomy.
    stage: int = STAGE_APPROVE_EVERYTHING
    halted: bool = False
    human_approved: bool = False
    approved_models: tuple = ()
    approved_max_scale: int = 4
    approved_roots: tuple = ()

    # Behaviour switches.
    force_overwrite: bool = False
    case_insensitive_paths: bool = field(
        default_factory=lambda: sys.platform == "darwin"
    )


def normalise(path: str, case_insensitive: bool) -> str:
    """Normalise a path for comparison.

    macOS formats its boot volume case-insensitively by default, so
    ``~/Pictures/Out`` and ``~/pictures/out`` are the same directory even
    though the strings differ. Comparing them as raw strings would let a job
    escape its output root by changing the case of one letter.
    """
    cleaned = os.path.normpath(path)
    return cleaned.casefold() if case_insensitive else cleaned


def is_within(child: str, parent: str, case_insensitive: bool = False) -> bool:
    """True when ``child`` is ``parent`` or sits underneath it."""
    if not parent:
        return False
    child_n = normalise(child, case_insensitive)
    parent_n = normalise(parent, case_insensitive)
    if child_n == parent_n:
        return True
    return child_n.startswith(parent_n.rstrip(os.sep) + os.sep)


def models_dir_acceptable(models_dir: str) -> bool:
    """Mirror the engine's own test on the models directory.

    Before it does anything else the engine searches the whole path it was
    given for the text "models" or "models2" and refuses to start if neither
    is there. The search is case-sensitive, so a directory called "Models"
    fails even on a Mac, where the filesystem itself does not care about the
    difference. Matching that exactly — rather than doing the more forgiving
    thing — is the point: a check looser than the engine's would pass a job
    the engine then rejects, which is the confusing failure this prevents.
    """
    return "models" in models_dir or "models2" in models_dir


def predicted_output_megapixels(facts: JobFacts) -> float:
    if not facts.input_width or not facts.input_height:
        return 0.0
    pixels = facts.input_width * facts.input_height * (facts.scale ** 2)
    return pixels / 1_000_000.0


def predicted_output_bytes(facts: JobFacts) -> int:
    """A deliberately pessimistic estimate of the output size.

    Used only for the disk-space check, where guessing low is the dangerous
    direction. A lossless PNG of a photograph runs far larger than the JPEG it
    came from, so this scales the input by the pixel ratio and then applies a
    format multiplier rather than assuming the output compresses as well as
    the input did.
    """
    if not facts.input_bytes:
        return 0
    pixel_ratio = facts.scale ** 2
    multiplier = {"png": 3.0, "webp": 1.2, "jpg": 1.0}.get(facts.output_format, 2.0)
    return int(facts.input_bytes * pixel_ratio * multiplier)


def evaluate(facts: JobFacts) -> Decision:
    """Run every rule and return the combined verdict."""
    checks: List[Check] = []

    def add(name: str, passed: bool, detail: str = "", severity: str = DENY) -> None:
        checks.append(Check(name=name, passed=passed, severity=severity, detail=detail))

    # --- the engine itself -------------------------------------------------
    add(
        "engine_present",
        facts.engine_present,
        "the Upscayl engine was not found — run 'upscayl-wrap doctor' for where it looked",
    )
    add(
        "engine_executable",
        facts.engine_executable or not facts.engine_present,
        "the engine was found but is not executable",
    )

    # The engine checks the *path* of the models directory for the word
    # "models" and refuses to start without it. That check happens before it
    # looks at anything else, so catching it here turns a baffling error into
    # a sentence that says what to do.
    add(
        "models_dir_accepted",
        facts.models_dir is None or models_dir_acceptable(facts.models_dir),
        "the engine requires the models directory's path to contain 'models' "
        "or 'models2', lower-case, and refuses to start otherwise; this one is %s"
        % facts.models_dir,
    )

    # --- the input ---------------------------------------------------------
    add(
        "input_readable",
        facts.input_error is None,
        "input cannot be read: %s" % (facts.input_error or ""),
    )
    add(
        "input_recognised",
        facts.input_format is not None,
        "input is not a recognised image format",
    )
    add(
        "input_format_supported",
        facts.input_format is None or facts.input_format in facts.readable_formats,
        "input format %s is not supported" % facts.input_format,
    )
    add(
        "input_has_dimensions",
        bool(facts.input_width and facts.input_height),
        "could not determine the input's dimensions, so its output size cannot be budgeted",
    )
    # Tiny images are not a safe edge case. A picture only a few pixels on one
    # side has been reported to reset the graphics device outright, the same
    # failure an enormous one causes.
    smallest = min(facts.input_width or 0, facts.input_height or 0)
    add(
        "input_large_enough",
        not (facts.input_width and facts.input_height) or smallest >= facts.min_input_dimension,
        "input is %sx%s; images under %d pixels on a side can reset the graphics "
        "processor. Enlarge it conventionally first."
        % (facts.input_width, facts.input_height, facts.min_input_dimension),
    )

    # A truncated input produces a truncated or garbage output, and the
    # engine will not necessarily complain.
    add(
        "input_not_truncated",
        facts.input_complete is not False,
        "input file is truncated or incomplete",
    )

    # --- the model and the scale -------------------------------------------
    add("model_selected", bool(facts.model_name), "no model was selected")
    add(
        "model_usable",
        facts.model_usable or not facts.model_name,
        "model %s is missing one of its two files (.param and .bin)" % facts.model_name,
    )
    add(
        "scale_in_range",
        1 <= facts.scale <= 16,
        "scale %s is outside the supported range of 1 to 16" % facts.scale,
    )
    native = facts.model_native_scale
    scale_matches = native is None or native == facts.scale
    add(
        "scale_matches_model",
        scale_matches,
        "model %s was trained at %sx but %sx was requested; the engine may "
        "resize afterwards, so the result can be softer than a native %sx"
        % (facts.model_name, native, facts.scale, native),
        severity=DENY if facts.scale_policy == "strict" else WARN,
    )
    # Writing a transparent image as a JPEG loses the transparency. The engine
    # prints a message saying it is converting to solid colour first, and then
    # does not do it, so every transparent area arrives black.
    add(
        "alpha_survives_format",
        not (facts.input_has_alpha and facts.output_format == "jpg"),
        "this image has transparency, and the engine writes transparent areas "
        "out as black when the output is a JPEG. Use --format png or webp.",
    )
    add(
        "output_format_writable",
        facts.output_format in facts.writable_formats,
        "cannot write %s; supported output formats are %s"
        % (facts.output_format, ", ".join(sorted(facts.writable_formats))),
    )

    # --- where the output goes ---------------------------------------------
    case_blind = facts.case_insensitive_paths
    same_file = normalise(facts.input_path, case_blind) == normalise(
        facts.output_path, case_blind
    )
    add(
        "output_is_not_input",
        not same_file,
        "refusing to write the upscale over its own original",
    )
    add(
        "output_within_root",
        is_within(facts.output_path, facts.output_root, case_blind),
        "output path %s escapes the output directory %s"
        % (facts.output_path, facts.output_root),
    )
    # The loop-prevention rule. Without it a watch folder pointed at its own
    # output will upscale its results, then upscale those, until the disk
    # fills. Nothing else catches this.
    add(
        "input_outside_output_root",
        not is_within(facts.input_path, facts.output_root, case_blind),
        "input %s sits inside the output directory %s, which would make the "
        "tool re-upscale its own results" % (facts.input_path, facts.output_root),
    )
    add(
        "output_free_or_forced",
        not facts.output_exists or facts.force_overwrite,
        "output already exists: %s (use --force to replace it)" % facts.output_path,
    )

    # --- budgets -----------------------------------------------------------
    predicted_mp = predicted_output_megapixels(facts)
    add(
        "within_pixel_budget",
        predicted_mp <= facts.max_output_megapixels,
        "predicted output of %.1f megapixels exceeds the %.1f megapixel budget "
        "(raise max_output_megapixels to allow it)"
        % (predicted_mp, facts.max_output_megapixels),
    )

    # A limit that has nothing to do with this machine. The encoder sizes its
    # buffer with 32-bit arithmetic, so past roughly 715 million pixels the
    # calculation overflows and the write fails — after the whole job has run.
    channels = 4 if facts.input_has_alpha else 3
    predicted_pixels = int(predicted_mp * 1_000_000)
    encoder_ceiling = (2 ** 31 - 1) // channels
    add(
        "within_encoder_limit",
        facts.output_format != "png" or predicted_pixels <= encoder_ceiling,
        "a %d megapixel output is past what the PNG encoder can address "
        "(about %d megapixels at %d channels); use --format webp or a smaller scale"
        % (predicted_mp, encoder_ceiling // 1_000_000, channels),
    )

    if facts.free_disk_bytes is None:
        add("within_disk_budget", True, "free disk space unknown", severity=WARN)
    else:
        needed = predicted_output_bytes(facts) + facts.min_free_disk_mb * 1024 * 1024
        add(
            "within_disk_budget",
            facts.free_disk_bytes >= needed,
            "not enough free disk: need about %d megabytes including the "
            "%d megabyte reserve, have %d"
            % (
                needed // (1024 * 1024),
                facts.min_free_disk_mb,
                facts.free_disk_bytes // (1024 * 1024),
            ),
        )

    # --- autonomy ----------------------------------------------------------
    add("not_halted", not facts.halted, "halted — clear it with 'upscayl-wrap resume'")

    if facts.stage >= STAGE_ACT_ALONE:
        add("stage_permits", True)
    elif facts.stage == STAGE_WITHIN_APPROVED:
        within_envelope = True
        detail = ""
        if facts.approved_models and facts.model_name not in facts.approved_models:
            within_envelope = False
            detail = "model %s is not in the approved set" % facts.model_name
        elif facts.scale > facts.approved_max_scale:
            within_envelope = False
            detail = "scale %sx exceeds the approved maximum of %sx" % (
                facts.scale,
                facts.approved_max_scale,
            )
        elif facts.approved_roots and not any(
            is_within(facts.input_path, root, case_blind) for root in facts.approved_roots
        ):
            within_envelope = False
            detail = "input is outside the approved directories"
        add(
            "stage_permits",
            within_envelope or facts.human_approved,
            detail + " — approve this run explicitly, or raise the stage",
        )
    else:
        add(
            "stage_permits",
            facts.human_approved,
            "stage 1 requires explicit approval for every job (pass --yes, or "
            "raise the stage with 'upscayl-wrap stage --set 2')",
        )

    allowed = not any(not c.passed and c.severity == DENY for c in checks)
    return Decision(allowed=allowed, checks=checks)
