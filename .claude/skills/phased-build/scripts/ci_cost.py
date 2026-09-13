#!/usr/bin/env python3
"""What one merge costs in continuous-integration minutes, before you spend it.

Continuous integration on a private repository is billed per *job*, rounded up
to the whole minute. A seven-job matrix therefore costs seven minutes whether
its jobs ran for twenty seconds or four -- job count is the price, compute time
is nearly irrelevant. That is unintuitive enough that it is worth computing
rather than remembering, which is why this is a script and not a paragraph.

Counts the jobs each workflow runs per event, expands matrices, notes which
workflows can be skipped by a paths filter and which cancel superseded runs,
and prints the floor cost of one pull-request-and-merge cycle.

    python3 ci_cost.py [repo-root]
    python3 ci_cost.py [repo-root] --used 1894 --included 3000

**Scheduled runs are the half that surprises you.** The merge cycle is the
number everyone quotes, and on a repository whose product IS a scheduled loop
it is the smaller half: a job that runs every day costs about thirty minutes a
month whether or not anybody merges anything. With `--used` this prints the
monthly floor for the schedule alone, what is left after it, and how many
merges that actually buys -- which is the number that decides whether a build
can go ahead today.

Exit code is 0 always; this reports, it does not gate. A budget check that
could fail a run would be one more way for the loop to stop, and the loop
stopping is the thing the budget exists to prevent.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    sys.exit("needs PyYAML: pip install pyyaml")


def matrix_size(job: dict) -> int:
    """How many jobs one definition actually expands into."""
    matrix = (job.get("strategy") or {}).get("matrix")
    if not isinstance(matrix, dict):
        return 1
    size = 1
    for key, values in matrix.items():
        # `include`/`exclude` adjust an existing product rather than multiply it;
        # counting them as dimensions would badly overstate the total.
        if key in ("include", "exclude"):
            continue
        if isinstance(values, list) and values:
            size *= len(values)
    extra = matrix.get("include")
    if isinstance(extra, list):
        size += len(extra)
    return size


def triggers(on) -> dict:
    """`on:` is a string, a list, or a map depending on how it was written."""
    if isinstance(on, str):
        return {on: {}}
    if isinstance(on, list):
        return {name: {} for name in on}
    if isinstance(on, dict):
        return {k: (v or {}) for k, v in on.items()}
    return {}


def main(root: Path, *, used: int = -1, included: int = 2000) -> int:
    workflows = sorted((root / ".github" / "workflows").glob("*.y*ml"))
    if not workflows:
        print(f"no workflows under {root}/.github/workflows")
        return 0

    pr_jobs = main_jobs = sched_jobs = 0
    rows = []
    for path in workflows:
        try:
            spec = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError as err:
            rows.append((path.name, "?", "UNPARSEABLE", str(err)[:40], "", ""))
            continue
        jobs = spec.get("jobs") or {}
        # PyYAML reads a bare `on:` key as the boolean True.
        on = triggers(spec.get("on", spec.get(True, {})))
        count = sum(matrix_size(j) for j in jobs.values() if isinstance(j, dict))

        on_pr = "pull_request" in on
        on_main = "push" in on
        skippable = any("paths" in (v or {}) or "paths-ignore" in (v or {})
                        for v in on.values() if isinstance(v, dict))
        cancels = "concurrency" in spec

        if on_pr:
            pr_jobs += count
        if on_main:
            main_jobs += count
        # Scheduled work is the half nobody quotes. A job on a daily cron costs
        # its jobs every day whether or not anyone merges, and on a repository
        # whose product IS the loop that is most of the bill.
        if "schedule" in on:
            sched_jobs += count

        rows.append((
            path.name, count,
            ",".join(k for k in on) or "—",
            "skippable" if skippable else "every commit" if (on_pr or on_main) else "",
            "cancels" if cancels else ("NO CANCEL" if on_pr else ""),
            "scheduled" if "schedule" in on else "",
        ))

    width = max(len(r[0]) for r in rows)
    print(f"{'workflow':<{width}}  jobs  triggers")
    for name, count, trig, skip, cancel, sched in rows:
        notes = " ".join(x for x in (skip, cancel, sched) if x)
        print(f"{name:<{width}}  {str(count):>4}  {trig:<34} {notes}")

    cycle = pr_jobs + main_jobs
    print()
    print(f"One pull request, one push to the default branch: "
          f"{pr_jobs} + {main_jobs} = {cycle} jobs")
    print(f"Billed per job rounded up: at least {cycle} minutes per merge cycle.")
    if cycle:
        print(f"A 2,000-minute month is ~{math.floor(2000 / cycle)} merges "
              f"before anything scheduled is counted.")
    print()
    print("Levers, cheapest first: paths-ignore for commits that cannot break a")
    print("test (a system that commits its own record needs this); a concurrency")
    print("group so superseded pushes stop; a narrower matrix on pull requests.")
    if used >= 0:
        budget(cycle, sched_jobs, used, included)
    return 0


def budget(cycle: int, scheduled_jobs: int, used: int, included: int) -> int:
    """What the schedule costs a month, and how many merges the rest buys."""
    monthly_schedule = scheduled_jobs * 30
    left = max(0, included - used)
    print()
    print(f"Scheduled work alone: {scheduled_jobs} job(s) a day "
          f"= about {monthly_schedule} billed minutes a month.")
    print(f"Used {used} of {included} included; {left} left this month.")
    if cycle:
        merges = (left - monthly_schedule) // cycle
        if merges >= 0:
            print(f"After the schedule, that is about {merges} more merge(s) "
                  f"at {cycle} minutes each.")
        else:
            # The cliff, named before it arrives. A budget set to stop usage
            # does not bill -- it STOPS, and the scheduled loop goes dark
            # until the month resets.
            print(f"WARNING: the schedule alone wants {monthly_schedule} and "
                  f"only {left} is left. Batch into fewer, larger pull "
                  f"requests, and say so rather than discovering it at 90%.")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    root = Path(args[0]) if args and not args[0].startswith("-") else Path(".")

    def flag(name: str, default: int) -> int:
        if name not in args:
            return default
        try:
            return int(args[args.index(name) + 1])
        except (IndexError, ValueError):
            sys.exit(f"{name} needs a number")

    raise SystemExit(main(root, used=flag("--used", -1), included=flag("--included", 2000)))
