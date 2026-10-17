"""The builder plugin is whole, current and safe to publish.

    python3 plugins/tests/test_builder.py

Standard library only, so it runs on Dex's Mac, in a cloud session and in CI
alike. The never-lines guard it once carried was removed at Dex's word on
2026-10-16; its tests went with it.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "builder"
BUILD = ROOT / "plugins" / "build.py"


def _run(path: pathlib.Path, event) -> dict | None:
    out = subprocess.run([sys.executable, str(path)], input=json.dumps(event),
                         capture_output=True, text=True, timeout=10)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout) if out.stdout.strip() else None


def _frontmatter(path: pathlib.Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, f"{path} has no frontmatter"
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


class TheHooksLoad(unittest.TestCase):
    def test_every_hook_command_names_a_file_the_plugin_ships(self):
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
        for groups in hooks.values():
            for group in groups:
                for h in group["hooks"]:
                    rel = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\"\s]+)", h["command"]).group(1)
                    with self.subTest(file=rel):
                        self.assertTrue((PLUGIN / rel).is_file())

    def test_session_start_says_one_line_and_never_fails(self):
        out = _run(PLUGIN / "hooks" / "session_start.py", {})
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("/builder:boot", ctx)
        self.assertLess(len(ctx), 400)


class ThePluginIsWholeAndCurrent(unittest.TestCase):
    def test_the_copies_match_their_sources(self):
        out = subprocess.run([sys.executable, str(BUILD), "--check"], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_an_edit_to_a_source_skill_without_a_rebuild_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d)
            shutil.copytree(ROOT / ".claude", tmp / ".claude")
            shutil.copytree(ROOT / "plugins", tmp / "plugins")
            skill = tmp / ".claude" / "skills" / "tandem" / "SKILL.md"
            skill.write_text(skill.read_text() + "\nOne more line.\n")
            out = subprocess.run([sys.executable, str(tmp / "plugins" / "build.py"), "--check"],
                                 capture_output=True, text=True, timeout=60)
            self.assertEqual(out.returncode, 1)
            self.assertIn("stale skills/tandem/SKILL.md", out.stdout)
            rebuilt = subprocess.run([sys.executable, str(tmp / "plugins" / "build.py")],
                                     capture_output=True, text=True, timeout=60)
            self.assertIn("version", rebuilt.stdout)
            before = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"]
            after = json.loads((tmp / "plugins" / "builder" / ".claude-plugin" / "plugin.json").read_text())["version"]
            self.assertNotEqual(before, after, "a content change must raise the version or Cowork never sees it")

    def test_the_manifest_and_the_marketplace_agree(self):
        manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
        self.assertEqual(manifest["name"], "builder")
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
        entry = next(p for p in market["plugins"] if p["name"] == "builder")
        self.assertEqual((ROOT / entry["source"]).resolve(), PLUGIN.resolve())
        self.assertTrue(market.get("description") and market.get("owner"))

    def test_every_skill_names_itself_and_says_when(self):
        skills = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
        self.assertGreaterEqual(len(skills), 6)
        for path in skills:
            fm = _frontmatter(path)
            with self.subTest(skill=path.parent.name):
                self.assertEqual(fm.get("name"), path.parent.name)
                self.assertGreater(len(fm.get("description", "")), 80)

    def test_every_command_and_agent_says_what_it_is(self):
        for path in sorted((PLUGIN / "commands").glob("*.md")) + sorted((PLUGIN / "agents").glob("*.md")):
            with self.subTest(file=path.name):
                self.assertTrue(_frontmatter(path).get("description"))

    def test_no_skill_points_at_a_repo_path_the_plugin_cannot_reach(self):
        for path in (PLUGIN / "skills").glob("*/SKILL.md"):
            text = path.read_text(encoding="utf-8")
            for m in re.finditer(r"python3 (\S+\.py)", text):
                with self.subTest(skill=path.parent.name, script=m.group(1)):
                    target = m.group(1)
                    if target.startswith("${CLAUDE_SKILL_DIR}/"):
                        self.assertTrue((path.parent / target.split("/", 1)[1]).is_file())
                    else:
                        self.assertTrue(target.startswith("share/"), f"unreachable: {target}")

    def test_nothing_that_would_stop_cowork_installing_it(self):
        self.assertFalse((PLUGIN / "bin").exists(), "a top-level bin/ makes Cowork refuse the plugin")
        files = [p for p in PLUGIN.rglob("*") if p.is_file()]
        self.assertLess(len(files), 5000)
        self.assertLess(sum(p.stat().st_size for p in files), 200 * 1024 * 1024)


class NothingPersonalShips(unittest.TestCase):
    """This repo is public, and every install receives every file."""

    PATTERNS = {
        "an SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "a long account-like number": re.compile(r"(?<![\w.\-])\d{9,17}(?![\w.\-])"),
        "a key or token": re.compile(r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_-]{20,}\.)"),
        "a Supabase project ref": re.compile(r"\b[a-z]{20}\.supabase\.co\b"),
        "an email address": re.compile(r"[\w.+-]+@(?!anthropic\.com)[\w-]+\.[\w.]+"),
    }

    def test_no_file_carries_personal_data_or_a_secret(self):
        for path in PLUGIN.rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".json", ".py", ".html", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for what, pattern in self.PATTERNS.items():
                with self.subTest(file=str(path.relative_to(PLUGIN)), what=what):
                    hit = pattern.search(text)
                    self.assertIsNone(hit, f"{what}: {hit.group(0) if hit else ''}")


if __name__ == "__main__":
    unittest.main(verbosity=1)
