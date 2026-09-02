#!/usr/bin/env python3
"""Lint a SKILL.md for the mechanical mistakes that quietly kill skills.

Usage:
    python3 validate_skill.py <path-to-SKILL.md-or-skill-dir>

No third-party dependencies: frontmatter is parsed with a small manual
parser rather than requiring PyYAML, so this runs anywhere Python 3 does.
"""

import re
import sys
from pathlib import Path

BODY_LINE_SOFT_LIMIT = 500
REFERENCE_TOC_THRESHOLD = 300
GENERIC_VERBS = ("helps with", "assists with", "supports", "works with")

ERROR = "ERROR"
WARN = "WARN"
INFO = "INFO"


def resolve_skill_md(target: Path) -> Path:
    if target.is_dir():
        candidate = target / "SKILL.md"
        if not candidate.exists():
            sys.exit(f"No SKILL.md found in {target}")
        return candidate
    return target


def parse_frontmatter(text: str):
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not match:
        return None, text
    raw_frontmatter, body = match.groups()

    fields = {}
    current_key = None
    for line in raw_frontmatter.split("\n"):
        key_match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s?(.*)$", line)
        if key_match:
            current_key, value = key_match.groups()
            fields[current_key] = value.strip()
        elif current_key and line.strip():
            # Continuation line of a multi-line (folded) scalar value.
            fields[current_key] = (fields[current_key] + " " + line.strip()).strip()
    return fields, body


def check_frontmatter(fields, skill_dir: Path, findings):
    if fields is None:
        findings.append((ERROR, "No YAML frontmatter found (file must start with '---')."))
        return

    name = fields.get("name", "")
    description = fields.get("description", "")

    if not name:
        findings.append((ERROR, "Missing required 'name' field in frontmatter."))
    elif not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
        findings.append((WARN, f"name '{name}' should be lowercase-hyphenated (e.g. 'my-skill-name')."))
    elif skill_dir.name and name != skill_dir.name:
        findings.append((WARN, f"name '{name}' does not match its directory name '{skill_dir.name}' — confusing when installed elsewhere."))

    if not description:
        findings.append((ERROR, "Missing required 'description' field in frontmatter."))
    elif "TODO" in description:
        findings.append((ERROR, "description still contains a TODO placeholder — fill it in before shipping."))
    else:
        word_count = len(description.split())
        if word_count < 12:
            findings.append((WARN, f"description is only {word_count} words — likely too terse to state a real trigger condition. See references/description-formulas.md."))
        lowered = description.lower()
        if not re.search(r"\b(use|trigger|whenever|when the|when a|when this)\b", lowered):
            findings.append((WARN, "description doesn't visibly state a trigger condition (no 'use/trigger/whenever/when...' language) — it may read as a summary instead of a when-to-fire signal."))
        for verb in GENERIC_VERBS:
            if verb in lowered:
                findings.append((WARN, f"description uses the generic verb phrase '{verb}', which doesn't distinguish this skill from any other. Name the concrete domain/action instead."))
                break


def check_body(body: str, skill_dir: Path, findings):
    lines = body.strip("\n").split("\n")
    line_count = len(lines)
    if line_count > BODY_LINE_SOFT_LIMIT:
        findings.append((WARN, f"body is {line_count} lines (soft limit ~{BODY_LINE_SOFT_LIMIT}). Consider moving depth into references/ with a pointer."))
    else:
        findings.append((INFO, f"body is {line_count} lines."))

    todo_count = len(re.findall(r"\bTODO\b", body))
    if todo_count:
        findings.append((WARN, f"body still contains {todo_count} TODO placeholder(s) — fill in before shipping."))

    caps_commands = re.findall(r"\b(ALWAYS|NEVER)\b", body)
    if len(caps_commands) >= 5:
        findings.append((WARN, f"body uses ALWAYS/NEVER {len(caps_commands)} times with no visible reasoning nearby in most cases — consider explaining *why* instead of commanding; see advanced-techniques.md §7."))

    for script_path in re.findall(r"`(?:python3?\s+)?([\w./-]+\.py)[^`]*`", body):
        candidate = (skill_dir / script_path).resolve()
        if not str(candidate).startswith(str(skill_dir.resolve())):
            continue
        if not candidate.exists():
            findings.append((WARN, f"body mentions '{script_path}' as a script to run, but no such file exists at {candidate} (false positive if this was just an illustrative example, not a real pointer)."))

    for ref_path in re.findall(r"`(references/[\w./-]+\.md)`", body):
        candidate = skill_dir / ref_path
        if not candidate.exists():
            findings.append((WARN, f"body points to '{ref_path}', but no such file exists (false positive if this was just an illustrative example, not a real pointer)."))


def check_references(skill_dir: Path, findings):
    references_dir = skill_dir / "references"
    if not references_dir.is_dir():
        return
    for ref_file in sorted(references_dir.glob("*.md")):
        text = ref_file.read_text(encoding="utf-8", errors="ignore")
        line_count = len(text.strip("\n").split("\n"))
        if line_count > REFERENCE_TOC_THRESHOLD:
            has_toc = bool(re.search(r"(?im)^#{1,3}\s*table of contents", text))
            if not has_toc:
                findings.append((WARN, f"references/{ref_file.name} is {line_count} lines with no table of contents — add one so it's navigable rather than skimmed."))


def check_scripts(skill_dir: Path, findings):
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return
    for script_file in sorted(scripts_dir.glob("*.py")):
        if script_file.stat().st_size == 0:
            findings.append((WARN, f"scripts/{script_file.name} is empty."))


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)

    target = Path(sys.argv[1])
    if not target.exists():
        sys.exit(f"Path not found: {target}")

    skill_md = resolve_skill_md(target)
    skill_dir = skill_md.parent
    text = skill_md.read_text(encoding="utf-8")

    fields, body = parse_frontmatter(text)

    findings = []
    check_frontmatter(fields, skill_dir, findings)
    check_body(body, skill_dir, findings)
    check_references(skill_dir, findings)
    check_scripts(skill_dir, findings)

    order = {ERROR: 0, WARN: 1, INFO: 2}
    findings.sort(key=lambda f: order[f[0]])

    error_count = sum(1 for level, _ in findings if level == ERROR)
    warn_count = sum(1 for level, _ in findings if level == WARN)

    print(f"Validating {skill_md}\n")
    if not findings:
        print("No issues found.")
    for level, message in findings:
        print(f"[{level}] {message}")

    print(f"\n{error_count} error(s), {warn_count} warning(s).")
    sys.exit(1 if error_count else 0)


if __name__ == "__main__":
    main()
