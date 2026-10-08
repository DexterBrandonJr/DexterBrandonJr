"""The builder plugin is whole, current, safe to publish, and its guard holds in Cowork.

    python3 plugins/tests/test_builder.py

Standard library only, so it runs on Dex's Mac, in a cloud session and in CI
alike. Every guard case comes in a pair: the act, and the harmless thing that
looks like it. A guard that blocks too much gets switched off, which is the
same failure a week later.
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
HOOK = PLUGIN / "hooks" / "never_lines.py"

#: The shell tools Cowork and Claude Code expose. Cowork's workspace shell is
#: an MCP tool; Claude Code's is Bash (PowerShell on Windows).
SHELLS = ("Bash", "PowerShell", "mcp__workspace__bash")


def _run(path: pathlib.Path, event) -> dict | None:
    out = subprocess.run([sys.executable, str(path)], input=json.dumps(event),
                         capture_output=True, text=True, timeout=10)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout) if out.stdout.strip() else None


def _shell(cmd, tool="Bash"):
    return {"tool_name": tool, "tool_input": {"command": cmd}}


REFUSED_COMMANDS = [
    "WEBULL_ENV=live PYTHONPATH=src python scripts/execute_approved.py --i-mean-live",
    "export WEBULL_ENV=live && python scripts/execute_approved.py",
    "export WEBULL_ENV='live'",
    'env WEBULL_ENV="live" python -m trading_engine',
    "cd /tmp; WEBULL_ENV=LIVE python x.py",
    "timeout 60 python scripts/execute_approved.py --i-mean-live",
    """python -c 'import os; os.environ["WEBULL_ENV"]="live"; import run'""",
    "cat ~/.config/trading-engine/accounts.json",
]
ALLOWED_COMMANDS = [
    "WEBULL_ENV=paper PYTHONPATH=src python scripts/execute_approved.py",
    "grep -rn WEBULL_ENV=live docs/ scripts/",
    "grep -rn -- --i-mean-live scripts/",
    "rg 'trading-engine/accounts.json' docs",
    "git log -S'--i-mean-live' --oneline",
    "python3 plugins/tests/test_builder.py",
]
REFUSED_CALLS = [
    {"tool_name": "Read", "tool_input": {"file_path": "/Users/dex/.config/trading-engine/accounts.json"}},
    {"tool_name": "Write", "tool_input": {"file_path": "/repo/.env", "content": "A=1\nWEBULL_ENV=live\n"}},
    {"tool_name": "Edit", "tool_input": {"file_path": "/Users/dex/.config/trading-engine/env.sh",
                                         "old_string": "export WEBULL_ENV=paper", "new_string": "export WEBULL_ENV=live"}},
    {"tool_name": "mcp__Webull__place_stock_instruction", "tool_input": {}},
    {"tool_name": "mcp__claude_ai_Webull__place_option_single_instruction", "tool_input": {}},
    {"tool_name": "mcp__Webull__revoke_instruction", "tool_input": {}},
]
ALLOWED_CALLS = [
    {"tool_name": "Write", "tool_input": {"file_path": "/repo/.env", "content": "WEBULL_ENV=paper\n"}},
    {"tool_name": "Edit", "tool_input": {"file_path": "/repo/docs/ACTIVATION.md",
                                         "old_string": "x", "new_string": "Live needs `WEBULL_ENV=live` in the shell"}},
    {"tool_name": "mcp__Webull__get_account_positions", "tool_input": {}},
    {"tool_name": "mcp__Webull__create_watchlist", "tool_input": {}},
]


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


class TheGuardHoldsOnBothSurfaces(unittest.TestCase):
    def assertRefused(self, event):
        out = _run(HOOK, event)
        self.assertIsNotNone(out, f"let a never-line through: {json.dumps(event)[:90]}")
        decision = out["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("bl:443", decision["permissionDecisionReason"])

    def test_every_shell_refuses_the_act(self):
        for tool in SHELLS:
            for cmd in REFUSED_COMMANDS:
                with self.subTest(tool=tool, cmd=cmd):
                    self.assertRefused(_shell(cmd, tool))

    def test_every_shell_lets_the_lookalike_through(self):
        for tool in SHELLS:
            for cmd in ALLOWED_COMMANDS:
                with self.subTest(tool=tool, cmd=cmd):
                    self.assertIsNone(_run(HOOK, _shell(cmd, tool)))

    def test_file_and_broker_calls(self):
        for event in REFUSED_CALLS:
            with self.subTest(event=event["tool_name"]):
                self.assertRefused(event)
        for event in ALLOWED_CALLS:
            with self.subTest(event=event["tool_name"]):
                self.assertIsNone(_run(HOOK, event))

    def test_bad_input_is_not_a_crash(self):
        out = subprocess.run([sys.executable, str(HOOK)], input="not json",
                             capture_output=True, text=True, timeout=10)
        self.assertEqual((out.returncode, out.stdout), (0, ""))

    def test_the_matcher_reaches_every_tool_the_guard_judges(self):
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
        group = next(g for g in hooks["PreToolUse"] if any("never_lines.py" in h["command"] for h in g["hooks"]))
        for tool in SHELLS + ("Write", "Edit", "MultiEdit", "Read", "mcp__Webull__place_stock_instruction",
                              "mcp__claude_ai_Webull__revoke_instruction"):
            with self.subTest(tool=tool):
                self.assertTrue(re.fullmatch(group["matcher"], tool), f"matcher misses {tool}")
        for tool in ("WebFetch", "mcp__Supabase__execute_sql", "mcp__github__merge_pull_request"):
            with self.subTest(tool=tool):
                self.assertFalse(re.fullmatch(group["matcher"], tool), f"matcher needlessly runs on {tool}")

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
