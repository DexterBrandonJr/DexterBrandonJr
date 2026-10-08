#!/usr/bin/env python3
"""One line at the start of every session: boot the hub, read the handoffs.

The rule lives in the `tandem` skill; this only makes sure the session that
loaded the plugin hears it before its first reply, which a skill alone does
not guarantee. Never fails: a hook that could stop a session from starting
would be a new way to lose one.
"""
import json
import sys

LINE = (
    "Builder plugin: before work that touches Dex, his projects or his preferences, "
    "run /builder:boot (hub_boot with surface 'cowork' in Cowork, 'code' in Claude Code) "
    "and read the handoffs addressed to this surface. The tandem skill has the rules."
)

try:
    json.dump({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": LINE}}, sys.stdout)
except Exception:  # noqa: BLE001 -- see the docstring
    pass
sys.exit(0)
