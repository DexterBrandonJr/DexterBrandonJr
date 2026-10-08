#!/usr/bin/env python3
"""The never-lines, held by code instead of by the conversation.

Dex's lines -- trading stays paper, no Claude session places a live order,
the engine never moves money -- used to live only in chat, CLAUDE.md and the
hub. Claude Code's own documentation says a boundary stated in conversation
is not a stored rule: the auto-mode classifier re-reads it from the
transcript, and compaction can drop the message that stated it. This
PreToolUse hook makes the lines hold whatever the conversation remembers,
in every permission mode, including bypassPermissions.

It refuses, for Claude's tool calls only (Dex's own terminal is untouched):

  * a shell command that turns live trading on: WEBULL_ENV assigned live
    (inline, export, env, declare, or from Python), or a command run with
    the --i-mean-live flag. Live is Dex's own act, typed by him
    (docs/ACTIVATION.md, "Live, later").
  * any shell or file access to the live account map,
    ~/.config/trading-engine/accounts.json: only live placement reads it,
    and it holds account ids that do not belong in a transcript.
  * an env file written or edited to set WEBULL_ENV to live.
  * a broker order tool from any Webull connector: placing, or revoking, an
    instruction of any kind (stock, option, futures, crypto, event, algo).

It does not refuse reading the broker keys (the paper runs need them), and it
does not refuse searching for these words: `grep WEBULL_ENV=live docs/` is a
search, not an assignment.

Same file in trading-engine, wealth-engine and DexterBrandonJr; each repo's
tests feed it the cases. Accepted by Dex as hub backlog bl:443.
"""
from __future__ import annotations

import json
import re
import shlex
import sys

ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.DOTALL)
PY_ASSIGN = re.compile(
    r"""(environ\s*\[\s*["']WEBULL_ENV["']\s*\]\s*=|setdefault\(\s*["']WEBULL_ENV["']\s*,|putenv\(\s*["']WEBULL_ENV["']\s*,)\s*["']live["']""",
    re.IGNORECASE)
FILE_LIVE = re.compile(r"""^\s*(export\s+)?WEBULL_ENV\s*=\s*["']?live\b""", re.IGNORECASE | re.MULTILINE)
ACCOUNT_MAP = "trading-engine/accounts.json"
BROKER_ORDER_TOOL = re.compile(r"^mcp__.*webull.*__(place_\w+|revoke_instruction)$", re.IGNORECASE)
ENV_FILE = re.compile(r"(^|/)(\.env[^/]*|env\.sh|[^/]*\.env)$")
SEPARATORS = {";", "&&", "||", "|", "|&", "&", "(", ")", "{", "}", "\n"}
DECLARERS = {"export", "env", "declare", "typeset", "local", "readonly"}
SEARCHERS = {"grep", "egrep", "fgrep", "rg", "ag", "ack", "git"}

FILE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

WHY_LIVE = ("Live trading is Dex's own act, never a Claude tool call (bl:443). "
            "Stay on paper; if live is wanted, tell Dex the exact command to type himself.")
WHY_MAP = ("The live account map is Dex's alone (bl:443): only live placement reads it, "
           "and its account ids do not belong in a transcript.")
WHY_ORDER = ("Broker order tools are refused in every Claude session (bl:443): the engine "
             "never moves money. Place nothing; put the proposed order on the deck for Dex.")


def _is_live(value: str) -> bool:
    return value.strip().strip("'\"").lower() == "live"


def _segments(command: str) -> list[list[str]]:
    """The command split into simple commands, each a list of words."""
    lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    lexer.commenters = ""
    words: list[list[str]] = [[]]
    try:
        for token in lexer:
            if token in SEPARATORS:
                words.append([])
            else:
                words[-1].append(token)
    except ValueError:  # unbalanced quotes: judge the raw text instead
        return [command.split()]
    return [w for w in words if w]


def _shell_verdict(command: str) -> str | None:
    if PY_ASSIGN.search(command):
        return WHY_LIVE
    for words in _segments(command):
        i = 0
        while i < len(words) and ASSIGN.match(words[i]):  # leading NAME=value
            name, value = ASSIGN.match(words[i]).groups()
            if name == "WEBULL_ENV" and _is_live(value):
                return WHY_LIVE
            i += 1
        if i >= len(words):
            continue
        program = words[i].rsplit("/", 1)[-1]
        args = words[i + 1:]
        if program in DECLARERS:
            for arg in args:
                m = ASSIGN.match(arg)
                if m and m.group(1) == "WEBULL_ENV" and _is_live(m.group(2)):
                    return WHY_LIVE
        if program in SEARCHERS:
            continue
        if "--i-mean-live" in args:
            return WHY_LIVE
        if any(ACCOUNT_MAP in w for w in words):
            return WHY_MAP
    return None


def _text_of_file_call(tool_input: dict) -> str:
    parts = [str(tool_input.get(k, "")) for k in ("content", "new_string", "new_source")]
    for edit in tool_input.get("edits") or []:
        if isinstance(edit, dict):
            parts.append(str(edit.get("new_string", "")))
    return "\n".join(parts)


def verdict(event: dict) -> str | None:
    """The reason to refuse this tool call, or None to say nothing."""
    tool = str(event.get("tool_name") or "")
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}

    if BROKER_ORDER_TOOL.match(tool):
        return WHY_ORDER

    if tool in ("Bash", "PowerShell") or tool.endswith("__bash"):
        return _shell_verdict(str(tool_input.get("command", "")))

    if tool in FILE_TOOLS or tool == "Read":
        path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        if ACCOUNT_MAP in path:
            return WHY_MAP
        if tool != "Read" and ENV_FILE.search(path) and FILE_LIVE.search(_text_of_file_call(tool_input)):
            return WHY_LIVE
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0  # nothing to judge; the deny rules in settings.json still apply
    reason = verdict(event if isinstance(event, dict) else {})
    if reason:
        json.dump({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
