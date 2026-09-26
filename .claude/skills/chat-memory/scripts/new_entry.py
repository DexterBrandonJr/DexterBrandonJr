#!/usr/bin/env python3
"""Scaffold a new dated memory entry and keep INDEX.md in sync.

Usage:
    python3 new_entry.py <topic-slug> --title "<short title>" [--memory-dir <path>] [--summary "<one-line summary>"]

Handles the mechanical part (file creation, date-stamping, index
bookkeeping) so the format never drifts across months of entries.
Claude fills in the actual Decisions/Facts/Artifacts/Open threads
content after this runs — this script only guarantees the scaffolding.
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

ENTRY_TEMPLATE = """
## {date} — {entry_title}

**Decisions:**
**Facts / preferences:**
**Artifacts:**
**Open threads:**
"""

NEW_TOPIC_TEMPLATE = """# {title}

{entry}"""


def slugify(raw: str) -> str:
    slug = raw.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug


# A pointer line carries a real date; the template line inside the index's
# trailing comment says <YYYY-MM-DD> and never matches.
POINTER = re.compile(r"^- \[.*?\]\(topics/[^)]+\.md\) — updated (\d{4}-\d{2}-\d{2}) — ")


def update_index(index_path: Path, slug: str, title: str, summary: str, today: str):
    """Write the topic's pointer line and keep the whole index newest first.

    Updating a line in place left an older topic with a new date sitting below
    newer ones, and the order is the one thing the index is read for (the
    SessionStart hook injects it whole). So every pointer line is re-sorted by
    its date, descending and stable within a date, with the line just written
    first among today's. Lines that are not pointers, like the trailing
    comment block, stay where they are.
    """
    line = f"- [{title}](topics/{slug}.md) — updated {today} — {summary}"

    if not index_path.exists():
        index_path.write_text(line + "\n", encoding="utf-8")
        return

    lines = index_path.read_text(encoding="utf-8").splitlines()
    this_topic = re.compile(rf"^- \[.*?\]\(topics/{re.escape(slug)}\.md\) — ")
    pointers, others, first_slot, in_comment = [], [], None, False
    for existing_line in lines:
        stripped = existing_line.strip()
        if stripped.startswith("<!--"):
            in_comment = True
        if not in_comment and POINTER.match(existing_line):
            if first_slot is None:
                first_slot = len(others)
            if not this_topic.match(existing_line):
                pointers.append(existing_line)
        else:
            others.append(existing_line)
        if "-->" in stripped:
            in_comment = False

    pointers.insert(0, line)
    pointers.sort(key=lambda p: POINTER.match(p).group(1), reverse=True)
    slot = 0 if first_slot is None else first_slot
    new_lines = others[:slot] + pointers + others[slot:]
    index_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("topic", help="Topic slug or title, e.g. 'q3-pricing-revamp' or 'Q3 pricing revamp'")
    parser.add_argument("--title", required=True, help="Short title for this dated entry within the topic")
    parser.add_argument("--memory-dir", default=".claude/memory", help="Memory root directory (default: .claude/memory)")
    parser.add_argument("--summary", default="", help="One-line summary shown in INDEX.md (defaults to the entry title)")
    args = parser.parse_args()

    memory_dir = Path(args.memory_dir)
    topics_dir = memory_dir / "topics"
    topics_dir.mkdir(parents=True, exist_ok=True)

    slug = slugify(args.topic)
    if not slug:
        sys.exit(f"'{args.topic}' does not produce a valid topic slug.")

    topic_path = topics_dir / f"{slug}.md"
    today = date.today().isoformat()
    entry = ENTRY_TEMPLATE.format(date=today, entry_title=args.title).lstrip("\n")

    if topic_path.exists():
        with topic_path.open("a", encoding="utf-8") as f:
            f.write("\n" + entry)
        print(f"Appended entry to {topic_path}")
    else:
        topic_title = args.topic if args.topic != slug else args.topic.replace("-", " ").title()
        topic_path.write_text(NEW_TOPIC_TEMPLATE.format(title=topic_title, entry=entry), encoding="utf-8")
        print(f"Created {topic_path}")

    summary = args.summary or args.title
    index_path = memory_dir / "INDEX.md"
    display_title = args.topic if args.topic != slug else args.topic.replace("-", " ").title()
    update_index(index_path, slug, display_title, summary, today)
    print(f"Updated {index_path}")

    print(f"\nNow fill in the Decisions / Facts / Artifacts / Open threads fields in {topic_path}, "
          f"then commit and push — nothing persists across sessions until it's pushed.")


if __name__ == "__main__":
    main()
