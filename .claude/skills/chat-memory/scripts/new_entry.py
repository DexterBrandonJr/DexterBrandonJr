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


def update_index(index_path: Path, slug: str, title: str, summary: str, today: str):
    line = f"- [{title}](topics/{slug}.md) — updated {today} — {summary}"

    if not index_path.exists():
        index_path.write_text(line + "\n", encoding="utf-8")
        return

    lines = index_path.read_text(encoding="utf-8").splitlines()
    pattern = re.compile(rf"^- \[.*?\]\(topics/{re.escape(slug)}\.md\) — ")
    replaced = False
    new_lines = []
    for existing_line in lines:
        if pattern.match(existing_line):
            new_lines.append(line)
            replaced = True
        else:
            new_lines.append(existing_line)
    if not replaced:
        new_lines.insert(0, line)

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
