#!/usr/bin/env python3
"""Scaffold a new Claude Skill directory with a known-good structure.

Usage:
    python3 scaffold_skill.py <skill-name> [--path <parent-dir>]

Creates <parent-dir>/<skill-name>/ with a SKILL.md template (frontmatter
filled in, body stubbed with the sections skill-builder recommends) plus
empty scripts/, references/, and assets/ directories.
"""

import argparse
import re
import sys
from pathlib import Path

TEMPLATE = """---
name: {name}
description: TODO — one clause on what this does, then a concrete, pushy
  clause on exactly when to use it (phrasings, contexts, even the ways
  people ask without the obvious keyword). See skill-builder's
  references/description-formulas.md before finalizing this.
---

# {title}

## Workflow

1. TODO — first step. If this step has one correct algorithm rather than
   requiring judgment, write it as a script in scripts/ and call it here
   instead of describing it in prose.
2. TODO

## Why (fill in only where a rule needs it)

TODO — for any hard rule, explain what breaks without it rather than
just asserting it. See skill-builder's references/advanced-techniques.md
section 7.
"""


def slugify(raw: str) -> str:
    slug = raw.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Skill name, e.g. 'sales-report'")
    parser.add_argument("--path", default=".", help="Parent directory to create the skill in (default: current directory)")
    args = parser.parse_args()

    name = slugify(args.name)
    if not name:
        sys.exit(f"'{args.name}' does not produce a valid skill name.")
    if name != args.name:
        print(f"Note: using normalized name '{name}' (lowercase-hyphenated).")

    skill_dir = Path(args.path) / name
    if skill_dir.exists():
        sys.exit(f"{skill_dir} already exists — refusing to overwrite.")

    (skill_dir / "scripts").mkdir(parents=True)
    (skill_dir / "references").mkdir()
    (skill_dir / "assets").mkdir()

    title = name.replace("-", " ").title()
    (skill_dir / "SKILL.md").write_text(TEMPLATE.format(name=name, title=title), encoding="utf-8")

    print(f"Scaffolded {skill_dir}/")
    print(f"  SKILL.md")
    print(f"  scripts/       (deterministic helpers go here)")
    print(f"  references/    (depth loaded on demand goes here)")
    print(f"  assets/        (templates/fonts/icons used in output go here)")
    print(f"\nNext: fill in the description first (references/description-formulas.md "
          f"in skill-builder), then the workflow.")


if __name__ == "__main__":
    main()
