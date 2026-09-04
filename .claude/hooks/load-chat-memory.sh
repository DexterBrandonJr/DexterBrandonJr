#!/usr/bin/env bash
# SessionStart hook: auto-loads .claude/memory/INDEX.md into context so the
# chat-memory skill's index is available every session without relying on
# Claude judging that the skill should trigger. No-ops silently if the
# memory store doesn't exist yet.
set -euo pipefail

root="${CLAUDE_PROJECT_DIR:-.}"
index_file="$root/.claude/memory/INDEX.md"

if [ ! -f "$index_file" ]; then
  exit 0
fi

content="$(cat "$index_file")"
jq -n --arg ctx "Chat memory index (.claude/memory/INDEX.md), auto-loaded at session start. Treat this as prior context from earlier chats; open the matching file under .claude/memory/topics/ if something here is relevant to the current task.

$content" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
