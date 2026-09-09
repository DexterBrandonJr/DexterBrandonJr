#!/usr/bin/env python3
"""Scan a filled-in memory entry for obvious secrets before it gets committed.

Usage:
    python3 scan_for_secrets.py <file>

Pattern-based, not full entropy analysis: deliberately biased toward
well-known credential *shapes* (AWS keys, GitHub/Slack tokens, PEM
private-key blocks, key:value assignments to secret-sounding field
names) rather than flagging every long string, so the check stays
useful instead of becoming noise that gets ignored.

Two severities:
- REVIEW: credentials that shouldn't be casually committed but are a
  judgment call in context (an API key might be a revoked test key,
  say). Prints a warning; the caller decides.
- NEVER: identity-critical secrets (SSNs and similar) that must not go
  into git history at all, on any repo, public or private -- history
  is effectively permanent, so "private" doesn't make these safe. This
  is not a judgment call; the finding means stop and store it elsewhere.

Exit 0 with nothing printed = clean. Exit 1 with findings printed =
fix before committing. This is a backstop, not a guarantee -- it
catches known shapes, not every possible secret.
"""

import re
import sys

REVIEW = "REVIEW"
NEVER = "NEVER"

PATTERNS = [
    (REVIEW, "AWS access key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (REVIEW, "GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    (REVIEW, "Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    (REVIEW, "PEM private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (REVIEW, "JWT-looking token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    (
        REVIEW,
        "key/secret/token/password assigned a value",
        re.compile(
            r"\b(api[_-]?key|secret|token|password|passwd|access[_-]?key)\b\s*[:=]\s*"
            r"['\"]?[A-Za-z0-9_\-/+]{8,}['\"]?",
            re.IGNORECASE,
        ),
    ),
    (
        NEVER,
        "SSN-shaped value (###-##-####)",
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    ),
]


def scan(text: str):
    findings = []
    lines = text.splitlines()
    for line_number, line in enumerate(lines, start=1):
        for severity, name, pattern in PATTERNS:
            match = pattern.search(line)
            if match:
                findings.append((line_number, severity, name, match.group(0)))
    return findings


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)

    path = sys.argv[1]
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        sys.exit(f"Could not read {path}: {e}")

    findings = scan(text)
    if not findings:
        print(f"No obvious secrets found in {path}.")
        sys.exit(0)

    never_findings = [f for f in findings if f[1] == NEVER]
    review_findings = [f for f in findings if f[1] == REVIEW]

    if never_findings:
        print(
            f"BLOCKING: identity-critical secret(s) found in {path}.\n"
            "These must not be committed to git -- public or private, it doesn't matter, "
            "history is effectively permanent. Remove them and store them somewhere that "
            "isn't version control (a password manager, an encrypted note, whatever the "
            "user already uses for this) before proceeding:\n"
        )
        for line_number, _, name, snippet in never_findings:
            print(f"  line {line_number}: {name}: {snippet}")
        print()

    if review_findings:
        print(f"Possible secret(s) found in {path} -- review before committing:\n")
        for line_number, _, name, snippet in review_findings:
            display = snippet if len(snippet) <= 60 else snippet[:57] + "..."
            print(f"  line {line_number}: {name}: {display}")

    sys.exit(1)


if __name__ == "__main__":
    main()
