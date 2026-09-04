#!/usr/bin/env python3
"""List existing memory topics before creating a new one.

Usage:
    python3 list_topics.py [--memory-dir <path>]

Read-only companion to new_entry.py: parses INDEX.md and prints each
topic's title, slug, last-updated date, and summary, so it's obvious
whether a similar topic already exists before adding a new one --
the "keep the index honest" step from SKILL.md, with tooling behind it.
"""

import argparse
import re
import sys
from pathlib import Path

INDEX_LINE = re.compile(
    r"^-\s*\[(?P<title>.*?)\]\(topics/(?P<slug>.*?)\.md\)\s*—\s*updated\s*(?P<date>\S+)\s*—\s*(?P<summary>.*)$"
)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--memory-dir", default=".claude/memory", help="Memory root directory (default: .claude/memory)")
    args = parser.parse_args()

    index_path = Path(args.memory_dir) / "INDEX.md"
    if not index_path.exists():
        print(f"No INDEX.md at {index_path} -- no topics yet.")
        return

    text = index_path.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    topics = []
    for line in text.splitlines():
        match = INDEX_LINE.match(line.strip())
        if match:
            topics.append(match.groupdict())

    if not topics:
        print("No topics yet.")
        return

    print(f"{len(topics)} topic(s) in {index_path}:\n")
    for t in topics:
        print(f"  {t['slug']}")
        print(f"    title:   {t['title']}")
        print(f"    updated: {t['date']}")
        print(f"    summary: {t['summary']}")
        print()


if __name__ == "__main__":
    main()
