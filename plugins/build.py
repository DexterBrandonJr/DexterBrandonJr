#!/usr/bin/env python3
"""Build the `builder` plugin from the skills and the guard this repo already keeps.

The plugin is how Cowork gets what Code sessions here already have: Cowork
reads plugins from the claude.ai account and never this repo's `.claude/`,
so the skills and the never-lines hook have to be packaged to reach it. The
canonical copies stay where they are; this script copies them in, rewrites
repo-relative script paths to `${CLAUDE_SKILL_DIR}`, and bumps the plugin's
version whenever the packaged content changes. A set `version` pins every
install to it, so a change without a bump would never reach Cowork.

    python3 plugins/build.py           # rebuild, bump the version if anything changed
    python3 plugins/build.py --check   # exit 1 if the plugin is out of date (the test runs this)

Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import shutil
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"
PLUGIN = ROOT / "plugins" / "builder"
LOCK = ROOT / "plugins" / "builder.lock.json"
MANIFEST = PLUGIN / ".claude-plugin" / "plugin.json"
#: For Customize > Plugins > Upload plugin, when a marketplace will not add.
ZIP = ROOT / "plugins" / "builder.zip"

#: The skills Cowork needs to build the way Code builds here. Left out on
#: purpose: qc-lead (one lead, and it is the Code chat), chat-memory and
#: skill-builder (already on the account), autopatch (repo-bound).
PACKAGED = ("hub", "workhorse", "phased-build", "innovation-brief", "scenarios", "tandem")

#: Files from elsewhere in the repo that a packaged skill points at.
#: (source, destination inside the plugin, the text in SKILL.md that names it)
EXTRAS = (
    (".claude/skills/qc-lead/references/chat-report-prompt.md",
     "skills/hub/references/chat-report-prompt.md",
     ".claude/skills/qc-lead/references/chat-report-prompt.md"),
    (".claude/hooks/never_lines.py", "hooks/never_lines.py", None),
)

#: The parts of the plugin written by hand, hashed with the rest so an edit
#: to a command or the agent bumps the version too.
HAND_WRITTEN = ("README.md", "commands", "agents", "hooks/hooks.json", "hooks/session_start.py")


def _rewrite(skill: str, text: str) -> str:
    """Repo-relative paths become paths the installed plugin can resolve.

    Only a path to a file the skill itself ships is rewritten. A bare
    `.claude/skills/<name>/` can mean another repository's copy (workhorse
    points into the private `DexterBrandonJr/workhorse` that way) and stays
    as written.
    """
    base = SKILLS / skill

    def swap(m: re.Match) -> str:
        rest = m.group(1)
        return "${CLAUDE_SKILL_DIR}/" + rest if (base / rest).is_file() else m.group(0)

    text = re.sub(rf"\.claude/skills/{re.escape(skill)}/([\w./-]*[\w])", swap, text)
    # A command run from wherever the session happens to be needs the whole
    # path; a bare `references/x.md` mention is read relative to the skill.
    text = re.sub(r"(python3 )(scripts/[\w./-]*[\w])",
                  lambda m: m.group(1) + "${CLAUDE_SKILL_DIR}/" + m.group(2) if (base / m.group(2)).is_file() else m.group(0),
                  text)
    for _src, dst, named in EXTRAS:
        if named and dst.startswith(f"skills/{skill}/"):
            text = text.replace(named, "${CLAUDE_SKILL_DIR}/" + dst.split(f"skills/{skill}/", 1)[1])
    return text


def _expected() -> dict[str, bytes]:
    """Every generated file, keyed by its path inside the plugin."""
    out: dict[str, bytes] = {}
    for skill in PACKAGED:
        base = SKILLS / skill
        if not (base / "SKILL.md").is_file():
            raise SystemExit(f"missing skill: {base / 'SKILL.md'}")
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            if "__pycache__" in path.parts:
                continue
            rel = f"skills/{skill}/{path.relative_to(base).as_posix()}"
            data = path.read_bytes()
            if path.name == "SKILL.md":
                data = _rewrite(skill, data.decode("utf-8")).encode("utf-8")
            out[rel] = data
    for src, dst, _named in EXTRAS:
        out[dst] = (ROOT / src).read_bytes()
    return out


def _digest(files: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    hand: dict[str, bytes] = {}
    for item in HAND_WRITTEN:
        p = PLUGIN / item
        for f in ([p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else []):
            hand[f.relative_to(PLUGIN).as_posix()] = f.read_bytes()
    for rel, data in sorted({**files, **hand}.items()):
        h.update(rel.encode() + b"\0" + hashlib.sha256(data).digest())
    return h.hexdigest()


def _generated_on_disk() -> set[str]:
    found = set()
    for skill_dir in (PLUGIN / "skills").glob("*"):
        for f in skill_dir.rglob("*"):
            if f.is_file() and "__pycache__" not in f.parts:
                found.add(f.relative_to(PLUGIN).as_posix())
    if (PLUGIN / "hooks" / "never_lines.py").exists():
        found.add("hooks/never_lines.py")
    return found


def _zip_bytes() -> bytes:
    """The plugin folder as a zip whose bytes depend only on its contents.

    Fixed timestamps, sorted entries and no compression, so the same plugin zips to
    the same file and `--check` can compare it byte for byte.
    """
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for f in sorted(p for p in PLUGIN.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
            info = zipfile.ZipInfo("builder/" + f.relative_to(PLUGIN).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = (0o755 if f.suffix == ".py" else 0o644) << 16
            info.compress_type = zipfile.ZIP_STORED  # deflate output varies by zlib version
            z.writestr(info, f.read_bytes())
    return buf.getvalue()


def check() -> list[str]:
    """What is out of date, in words. Empty means the plugin matches its sources."""
    problems = []
    files = _expected()
    for rel, data in files.items():
        p = PLUGIN / rel
        if not p.is_file():
            problems.append(f"missing {rel}")
        elif p.read_bytes() != data:
            problems.append(f"stale {rel}")
    for rel in sorted(_generated_on_disk() - set(files)):
        problems.append(f"left over {rel}")
    lock = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    manifest = json.loads(MANIFEST.read_text())
    if lock.get("digest") != _digest(files):
        problems.append("content changed since the last build: run python3 plugins/build.py to bump the version")
    elif lock.get("version") != manifest.get("version"):
        problems.append(f"plugin.json version {manifest.get('version')} is not the built {lock.get('version')}")
    if not problems and (not ZIP.exists() or ZIP.read_bytes() != _zip_bytes()):
        problems.append("builder.zip does not match the plugin folder: run python3 plugins/build.py")
    return problems


def build() -> str:
    files = _expected()
    skills_dir = PLUGIN / "skills"
    if skills_dir.exists():
        shutil.rmtree(skills_dir)
    for rel, data in files.items():
        p = PLUGIN / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    (PLUGIN / "hooks" / "never_lines.py").chmod(0o755)
    digest = _digest(files)
    lock = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    manifest = json.loads(MANIFEST.read_text())
    version = manifest["version"]
    if lock.get("digest") and lock["digest"] != digest:
        major, minor, patch = (int(x) for x in version.split("."))
        version = f"{major}.{minor}.{patch + 1}"
    manifest["version"] = version
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    LOCK.write_text(json.dumps({"version": version, "digest": digest}, indent=2) + "\n")
    ZIP.write_bytes(_zip_bytes())
    return version


def main(argv: list[str]) -> int:
    if "--check" in argv:
        problems = check()
        for p in problems:
            print(p)
        print("builder plugin: up to date" if not problems else f"builder plugin: {len(problems)} problem(s)")
        return 1 if problems else 0
    print(f"builder plugin built, version {build()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
