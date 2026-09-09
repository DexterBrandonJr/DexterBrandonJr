#!/usr/bin/env python3
"""Rank the issues in a diagnostic report so the important one is obvious.

Usage:
    python3 triage.py <report.json>
    <tool> selfcheck --json | python3 triage.py -

Reads the standard report shape (an `issues` array of objects carrying
`signature`, `error_type`, `count`, `command`, `sample_message`, `first_seen`,
`last_seen`) and prints a worklist.

Ranking is deliberately simple and explainable: frequency dominates, with a
modest boost for issues still occurring recently. A bug hit fifty times is
worth real effort even if it has been around for weeks; a bug hit once may not
be worth any. Anything cleverer would be harder to argue with, and the point of
a triage order is that a human can disagree with it.
"""

import json
import sys
from datetime import datetime


def load(path: str) -> dict:
    text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        sys.exit(f"Not valid JSON: {exc}")


def days_ago(stamp: str) -> float:
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return (datetime.now() - datetime.strptime(stamp, fmt)).total_seconds() / 86400
        except (ValueError, TypeError):
            continue
    return 999.0


def score(issue: dict) -> float:
    count = int(issue.get("count", 1))
    recency = days_ago(str(issue.get("last_seen", "")))
    # Still happening this week counts for more than something that stopped.
    freshness = 1.5 if recency <= 7 else (1.0 if recency <= 30 else 0.6)
    return count * freshness


def main() -> int:
    if len(sys.argv) != 2:
        sys.exit(__doc__)

    report = load(sys.argv[1])
    issues = report.get("issues", [])
    runs = report.get("runs", {})

    tool = report.get("tool", "tool")
    print(f"{tool} triage")
    if runs:
        print(f"  {runs.get('runs', 0)} run(s), {runs.get('failures', 0)} failed "
              f"({runs.get('failure_rate', 0):.0%} failure rate)")

    if not issues:
        print("\n  No issues recorded. Nothing to patch.")
        return 0

    ranked = sorted(issues, key=score, reverse=True)
    print(f"\n  {len(ranked)} issue(s), highest priority first:\n")

    for position, issue in enumerate(ranked, start=1):
        print(f"  {position}. [{issue.get('signature', '?')}] "
              f"{issue.get('error_type', 'Error')} in `{tool} {issue.get('command', '?')}`")
        print(f"     seen {issue.get('count', '?')}x, "
              f"last {issue.get('last_seen', 'unknown')} "
              f"(priority score {score(issue):.1f})")
        message = str(issue.get("sample_message", "")).strip()
        if message:
            print(f"     {message[:160]}")
        print()

    capabilities = report.get("environment", {}).get("capabilities", {})
    missing = [name for name, ok in capabilities.items() if not ok]
    if missing:
        print(f"  Capabilities reported as unavailable: {', '.join(missing)}")
        print("  Check whether any issue above is simply that, rather than a defect.\n")

    print("  Work them in this order. For each: reproduce as a failing test FIRST,")
    print("  then fix the root cause, then verify the whole suite. Never patch an")
    print("  issue you could not reproduce -- report it as unreproduced instead.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
