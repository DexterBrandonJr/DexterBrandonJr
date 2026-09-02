#!/usr/bin/env python3
"""Keyword search across a chat-memory store.

Usage:
    python3 search_memory.py "<query>" [--memory-dir <path>]

Searches INDEX.md, topics/*.md, and raw/*.md case-insensitively and
prints matches grouped by file, with a per-topic-file match count at
the end so it's obvious which topic file to actually open next —
faster and more reliable than reading every topic file to check.
"""

import argparse
import sys
from pathlib import Path


def search_file(path: Path, query_lower: str):
    matches = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return matches
    for line_number, line in enumerate(lines, start=1):
        if query_lower in line.lower():
            matches.append((line_number, line.strip()))
    return matches


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("query", help="Keyword or phrase to search for")
    parser.add_argument("--memory-dir", default=".claude/memory", help="Memory root directory (default: .claude/memory)")
    args = parser.parse_args()

    memory_dir = Path(args.memory_dir)
    if not memory_dir.is_dir():
        sys.exit(f"No memory directory at {memory_dir}")

    query_lower = args.query.lower()
    candidates = []
    index_path = memory_dir / "INDEX.md"
    if index_path.exists():
        candidates.append(index_path)
    candidates.extend(sorted((memory_dir / "topics").glob("*.md")))
    candidates.extend(sorted((memory_dir / "raw").glob("*.md")))

    total_matches = 0
    per_file_counts = []

    for path in candidates:
        matches = search_file(path, query_lower)
        if not matches:
            continue
        total_matches += len(matches)
        per_file_counts.append((path, len(matches)))
        print(f"\n{path} ({len(matches)} match(es)):")
        for line_number, text in matches:
            print(f"  {line_number}: {text}")

    if total_matches == 0:
        print(f"No matches for '{args.query}' in {memory_dir}.")
        return

    print(f"\n--- {total_matches} total match(es) across {len(per_file_counts)} file(s) ---")
    for path, count in sorted(per_file_counts, key=lambda pair: -pair[1]):
        print(f"  {count:>3}  {path}")


if __name__ == "__main__":
    main()
