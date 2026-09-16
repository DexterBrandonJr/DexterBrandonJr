"""Staged autonomy, and the halt.

Three stages:

1. **Approve everything.** Nothing runs without a person saying so on the
   spot. This is where a new install starts.
2. **Adjust within what was approved.** The tool runs on its own, but only
   inside an envelope a person set: these models, up to this scale, on files
   under these directories. Anything outside still needs approval.
3. **Act alone.** The watch folder runs unattended.

The asymmetry is the point. Any part of the system can *lower* the stage — a
run of failures, a missing engine, a disk filling up — and it takes effect
immediately. Only a person can raise it, and only by typing a command. A
system that could promote itself back after halting would have no halt at all.

The halt is a file on disk rather than a flag in memory, so it survives a
crash, a reboot, and the next scheduled run.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .ledger import now_iso

STAGE_APPROVE_EVERYTHING = 1
STAGE_WITHIN_APPROVED = 2
STAGE_ACT_ALONE = 3

STAGE_NAMES = {
    STAGE_APPROVE_EVERYTHING: "approve everything",
    STAGE_WITHIN_APPROVED: "adjust within what was approved",
    STAGE_ACT_ALONE: "act alone",
}


@dataclass
class State:
    """Mutable runtime state, kept beside the ledger."""

    stage: int = STAGE_APPROVE_EVERYTHING
    halted: bool = False
    halt_reason: Optional[str] = None
    halted_at: Optional[str] = None
    # Raised by a person; recorded so the review can show how long the tool
    # has been trusted at this level.
    stage_set_at: Optional[str] = None
    stage_set_by: Optional[str] = None
    job_counter: int = 0
    last_review_date: Optional[str] = None

    # The envelope that stage 2 operates inside.
    approved_models: List[str] = field(default_factory=list)
    approved_max_scale: int = 4
    approved_roots: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Autonomy:
    """Reads and writes the state file, and owns the halt."""

    def __init__(self, state_file: str, halt_file: str) -> None:
        self.state_file = state_file
        self.halt_file = halt_file
        self.state = self._load()

    # --- persistence -------------------------------------------------------

    def _load(self) -> State:
        state = State()
        if os.path.isfile(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as handle:
                    raw = json.load(handle)
            except (OSError, ValueError):
                raw = {}
            for key, value in (raw or {}).items():
                if hasattr(state, key):
                    setattr(state, key, value)
        # The halt file is the authority. If it exists, the tool is halted
        # regardless of what the state file claims, because the file is what
        # a person or a crashed run can leave behind.
        if os.path.isfile(self.halt_file):
            state.halted = True
            if not state.halt_reason:
                try:
                    with open(self.halt_file, "r", encoding="utf-8") as handle:
                        state.halt_reason = handle.read().strip() or "halted"
                except OSError:
                    state.halt_reason = "halted"
        return state

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        temporary = self.state_file + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(self.state.as_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, self.state_file)

    # --- the halt ----------------------------------------------------------

    def halt(self, reason: str) -> None:
        """Stop acting, now, and drop to stage 1.

        Callable from anywhere: the runner on repeated failures, the gate on a
        missing engine, a person at the terminal.
        """
        self.state.halted = True
        self.state.halt_reason = reason
        self.state.halted_at = now_iso()
        self.state.stage = STAGE_APPROVE_EVERYTHING
        os.makedirs(os.path.dirname(self.halt_file), exist_ok=True)
        with open(self.halt_file, "w", encoding="utf-8") as handle:
            handle.write("%s\n%s\n" % (self.state.halted_at, reason))
        self.save()

    def resume(self) -> bool:
        """Clear the halt. A person does this; nothing else may.

        The stage is deliberately left at 1 afterwards. Coming back from a
        halt at the same autonomy level it was halted from would skip the step
        where somebody checks that the cause is actually fixed.
        """
        existed = os.path.isfile(self.halt_file)
        try:
            os.unlink(self.halt_file)
        except OSError:
            pass
        self.state.halted = False
        self.state.halt_reason = None
        self.state.halted_at = None
        self.save()
        return existed

    # --- the stage ---------------------------------------------------------

    def set_stage(self, stage: int, by: str = "human") -> "tuple[bool, str]":
        if stage not in STAGE_NAMES:
            return False, "stage must be 1, 2 or 3"
        if stage > self.state.stage and self.state.halted:
            return False, (
                "cannot raise the stage while halted (%s) — fix the cause, then "
                "'upscayl-wrap resume'" % (self.state.halt_reason or "no reason recorded")
            )
        previous = self.state.stage
        self.state.stage = stage
        self.state.stage_set_at = now_iso()
        self.state.stage_set_by = by
        self.save()
        return True, "stage %d (%s) — was %d (%s)" % (
            stage,
            STAGE_NAMES[stage],
            previous,
            STAGE_NAMES.get(previous, "unknown"),
        )

    def approve_envelope(
        self,
        *,
        models: Optional[List[str]] = None,
        max_scale: Optional[int] = None,
        roots: Optional[List[str]] = None,
    ) -> None:
        """Record what stage 2 is allowed to do without asking again."""
        if models is not None:
            self.state.approved_models = list(models)
        if max_scale is not None:
            self.state.approved_max_scale = int(max_scale)
        if roots is not None:
            self.state.approved_roots = [os.path.abspath(os.path.expanduser(r)) for r in roots]
        self.save()

    # --- counters ----------------------------------------------------------

    def next_job_index(self) -> int:
        self.state.job_counter += 1
        self.save()
        return self.state.job_counter

    def consider_failures(self, consecutive: int, threshold: int) -> Optional[str]:
        """Halt if failures are piling up.

        Returns the halt reason when it fires, so the caller can print it once
        rather than discovering it on the next run.
        """
        if threshold > 0 and consecutive >= threshold:
            reason = (
                "%d jobs failed in a row — something structural is wrong "
                "(check 'upscayl-wrap doctor' and the last few ledger rows)"
                % consecutive
            )
            self.halt(reason)
            return reason
        return None

    def describe(self) -> str:
        if self.state.halted:
            return "HALTED (%s) since %s" % (
                self.state.halt_reason or "no reason recorded",
                self.state.halted_at or "unknown",
            )
        return "stage %d — %s" % (
            self.state.stage,
            STAGE_NAMES.get(self.state.stage, "unknown"),
        )
