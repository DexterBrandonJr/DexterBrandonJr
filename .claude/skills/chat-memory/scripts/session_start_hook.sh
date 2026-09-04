#!/usr/bin/env bash
# SessionStart hook for the chat-memory skill.
#
# Auto-loads a memory index into context at session start, so recall
# doesn't depend on Claude judging that the chat-memory skill should
# trigger. No-ops silently (exit 0, no output) whenever there's nothing
# to load, so it's safe to install before any memory store exists.
#
# Which store it loads, in order:
#   1. $CLAUDE_CHAT_MEMORY_DIR, if set explicitly.
#   2. <project>/.claude/memory, if the current repo has one (a
#      project-local store wins when present -- it's the more specific
#      one for whatever you're working on right now).
#   3. ~/.claude/memory, if it exists (personal memory that follows you
#      across every project on this machine).
#   4. Nothing found -> no-op.
#
# Deploy this same file at two layers as needed:
#   - <project>/.claude/hooks/... + a SessionStart hook in
#     <project>/.claude/settings.json, for a memory store committed to
#     that specific repo.
#   - ~/.claude/hooks/... + a SessionStart hook in ~/.claude/settings.json,
#     for personal memory that should load in every project on this
#     machine. See references/global-setup.md in this skill.
#
# No hard dependency on jq: falls back to python3, then to a
# dependency-free pure-shell JSON escaper, so it still works on a
# machine with neither installed.

set -euo pipefail

project_root="${CLAUDE_PROJECT_DIR:-.}"

if [ -n "${CLAUDE_CHAT_MEMORY_DIR:-}" ]; then
  memory_dir="$CLAUDE_CHAT_MEMORY_DIR"
elif [ -f "$project_root/.claude/memory/INDEX.md" ]; then
  memory_dir="$project_root/.claude/memory"
elif [ -f "$HOME/.claude/memory/INDEX.md" ]; then
  memory_dir="$HOME/.claude/memory"
else
  exit 0
fi

index_file="$memory_dir/INDEX.md"
[ -f "$index_file" ] || exit 0

content="$(cat "$index_file")"
message="Chat memory index ($index_file), auto-loaded at session start. Treat this as prior context from earlier chats; open the matching file under $memory_dir/topics/ if something here is relevant to the current task.

$content"

if command -v jq >/dev/null 2>&1; then
  jq -n --arg ctx "$message" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
elif command -v python3 >/dev/null 2>&1; then
  MESSAGE="$message" python3 -c '
import json, os
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": os.environ["MESSAGE"]}}))
'
else
  escaped=${message//\\/\\\\}
  escaped=${escaped//\"/\\\"}
  escaped=${escaped//$'\r'/}
  escaped=$(printf '%s' "$escaped" | sed ':a;N;$!ba;s/\n/\\n/g')
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}' "$escaped"
fi
