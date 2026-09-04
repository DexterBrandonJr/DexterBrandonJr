# Global Setup (Personal Memory Across Every Project)

By default, `chat-memory` reads and writes `.claude/memory/` inside whatever repo you're in — one memory store per project. That's the right default when memory is about that project (its decisions, its conventions). It's the wrong default when what you actually want is memory that follows *you*, regardless of which repo you happen to be in, including repos that don't exist yet.

This file covers wiring up the second kind: a personal memory store at `~/.claude/memory`, auto-loaded at the start of every session on your machine.

## Why this needs local setup, not just installing the skill

Installing `chat-memory` itself (via `Save skill` on a `.skill` file, or a plugin) makes the *skill* available everywhere — Claude will know how to save and recall memory in any session. It does not, by itself, make a `SessionStart` hook fire everywhere: hooks live in `settings.json`, and a skill install doesn't touch your `~/.claude/settings.json` for you. That one file has to be edited once, by you, on each machine you use.

It also doesn't make `~/.claude/memory` durable everywhere: it's a real, persistent folder on a machine you control locally, but it does **not** survive an ephemeral remote/cloud session's container being reclaimed. On a remote session, only what's committed to a git repo survives — so cross-repo memory that needs to outlive a *remote* session still has to live in a repo, the same way project-scoped `chat-memory` already does. Global `~/.claude/memory` is for your own local machine(s) only.

## Setup (once per machine)

1. Copy `scripts/session_start_hook.sh` from this skill to `~/.claude/hooks/load-chat-memory.sh`:
   ```bash
   mkdir -p ~/.claude/hooks
   cp <this-skill's-path>/scripts/session_start_hook.sh ~/.claude/hooks/load-chat-memory.sh
   chmod +x ~/.claude/hooks/load-chat-memory.sh
   ```
2. Merge this into `~/.claude/settings.json` (merge — don't overwrite whatever hooks already exist there):
   ```json
   {
     "hooks": {
       "SessionStart": [
         { "hooks": [{ "type": "command", "command": "bash ~/.claude/hooks/load-chat-memory.sh", "timeout": 10 }] }
       ]
     }
   }
   ```
3. That's it — no `~/.claude/memory` directory needs to exist yet. The script no-ops silently until you actually save something there.

## How the resolution order plays out day to day

The bundled script checks, in order: an explicit `$CLAUDE_CHAT_MEMORY_DIR` override, then `<project>/.claude/memory` (project-local memory, if that repo has it — same file this skill uses everywhere else), then `~/.claude/memory` (personal, cross-project). So:

- In a repo that has its own `.claude/memory/` (like this one): that repo's memory loads, same as always.
- In any other repo, including a brand-new one you just created: your personal `~/.claude/memory` loads instead, automatically, with zero per-repo setup.

When you ask Claude to remember something and you want it to follow you everywhere rather than stay siloed to the current repo, say so explicitly ("save this to my personal memory, not this repo's") — the skill's `new_entry.py` takes `--memory-dir ~/.claude/memory` for exactly this.

## Multiple machines

`~/.claude/memory` doesn't sync between computers on its own. If you split time between a laptop and a desktop and want the same personal memory on both, point `CLAUDE_CHAT_MEMORY_DIR` at a small private git repo you clone onto each machine (and commit/push/pull as you would any other `chat-memory` store) instead of a bare local folder — everything else about the skill works the same either way, since it's already built around git-backed persistence.
