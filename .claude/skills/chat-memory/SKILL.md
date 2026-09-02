---
name: chat-memory
description: Captures durable facts, decisions, and context from the current conversation into a persistent, git-tracked memory store, and loads relevant past memory back in so it carries across separate chats and sessions instead of evaporating when each one ends. Trigger this whenever the user asks to remember, save, log, or keep track of something for later; says "save this chat," "save our conversation," "remember this for next time," or "don't make me repeat context every time"; references "last time," "before," or "what we decided" as if Claude should already know; or wants to pick up earlier work in a brand-new chat — even when they never use the word "memory."
---

# Chat Memory

## Why this needs to be a file, not a hope

Nothing about a conversation survives past its own session unless it's written down somewhere Claude will actually go looking next time. In an environment like this one, where each session runs in a fresh, disposable container, that's even more literal: the *only* thing that outlives the container is whatever got committed and pushed to the repo. So "remember this across chats" translates concretely to: write it to a file, commit it, push it — and read that file back at the start of the next relevant conversation. Everything below is just the structure that makes that reliable instead of a pile of unsearchable notes.

## What to capture (and what deliberately not to)

The instinct to "save all prompts and responses" produces a verbatim transcript — which is cheap to write and expensive to ever use again. Reloading a raw transcript as context for a new chat mostly reloads noise: dead ends, restated questions, the back-and-forth of getting to an answer. What actually needs to survive is the distillation:

- **Decisions** — what was decided, and the one-line reason why (the reason is what lets future-you tell whether the decision still applies to a new situation).
- **Facts and preferences** — stable things learned about the user, the project, or the domain that will still be true next week.
- **Artifacts produced** — links to PRs, files, commits, or documents that came out of the conversation, so future-Claude can go read the real thing instead of a description of it.
- **Open threads** — anything left unresolved that a future session should pick back up.

If the user explicitly wants the verbatim record too (audit trail, "I want the actual transcript saved"), keep it — but as supplementary raw material in `raw/`, never as the thing future sessions are expected to read by default. The index and topic files are what gets loaded; the raw log is what's available if someone goes digging.

## Where memory lives

```
<memory-dir>/
├── INDEX.md              — one line per topic, always cheap to read in full
├── topics/<slug>.md       — the actual entries for one topic, read only when relevant
└── raw/<date>.md          — optional verbatim logs, read only if explicitly needed
```

This mirrors the same progressive-disclosure idea skills themselves use: the index is metadata-cheap and always worth a glance, a topic file is the equivalent of a skill body (loaded when it's actually relevant), and raw logs are the deepest, rarest-touched layer. Exact entry format is in `references/schema.md` — read it before hand-editing a memory file, since `scripts/new_entry.py` depends on the format staying consistent.

`<memory-dir>` defaults to `.claude/memory/` at the root of the current repo, seeded alongside this skill. **Before writing anything to it, check whether the repository is public.** A GitHub profile repo (like this one) and most personal repos default to public — anything committed there is visible to anyone. If the repo is public, or the content is at all sensitive (client details, credentials, anything the user wouldn't want on their public profile), don't write it into a repo-tracked memory folder at all: use `~/.claude/memory/` instead (pass `--memory-dir ~/.claude/memory` to the scripts below) if the environment persists the home directory, or say plainly that this environment can't durably store it privately and ask where it should go. Never guess past that warning — a memory system that leaks is worse than no memory system.

## Saving

1. Decide the topic this belongs under — reuse an existing slug from `INDEX.md` if one fits; a new slug otherwise.
2. Run:
   ```bash
   python3 .claude/skills/chat-memory/scripts/new_entry.py <topic-slug> --title "<short title>" --memory-dir <memory-dir>
   ```
   This creates `topics/<slug>.md` if it's new (or opens the existing one), appends a dated entry skeleton, and updates `INDEX.md`'s pointer line for that topic — all mechanically, so the index format never drifts no matter how many entries pile up over months. It prints the exact file and line range it just added.
3. Fill in the entry skeleton's Decisions / Facts / Artifacts / Open threads with the real content from this conversation, using your own judgment about what's actually durable per the "what to capture" section above — the script only handles the bookkeeping, not the judgment call.
4. Commit and push. An entry sitting unstaged in a container that's about to be reclaimed is exactly as gone as if it were never written.
5. State back, plainly, exactly what you just saved — not "saved it," the actual content. A memory entry gets trusted as an established fact by every future session that reads it, with no re-verification step; the one moment that catches a mis-paraphrase or a too-broad generalization before it calcifies into "fact" is the user reading it back right after you wrote it. This costs one sentence and is not optional just because the save itself was quick.

## Recalling

1. Read `INDEX.md` in full first — it's designed to stay small enough that this always costs almost nothing.
2. From the index, open only the specific `topics/<slug>.md` file(s) that look relevant to the current task. Don't read every topic file "just in case" — that defeats the entire point of splitting them out.
3. If it's not obvious from the index which topic covers something, run:
   ```bash
   python3 .claude/skills/chat-memory/scripts/search_memory.py "<query>" --memory-dir <memory-dir>
   ```
   for a keyword search across the index, topics, and raw logs, ranked by which topic file matched most.
4. Treat what you find as real prior context — reference it naturally rather than re-asking the user something already answered in memory.

## For truly automatic recall, pair this with a hook

A skill only fires when Claude judges the conversation calls for it — good for "the user just referenced something from before," not guaranteed for "load memory silently at the start of every single session regardless of what's asked." If the goal is the latter — memory loaded every time, no judgment call involved — that's a `SessionStart` hook (e.g., one that reads `INDEX.md` into context automatically), not a skill. Use the `update-config` skill to set one up; keep this skill for the save/recall workflow and the judgment about what's worth keeping, which is exactly the part a hook can't do.

## Keep the index honest

Over time an index with dozens of stale or duplicate-feeling topic slugs stops being cheap to scan, which is the one property it exists for. When adding an entry to a topic that's clearly merged with or superseded by another, consolidate them (move the content, delete the old file, fix the index) rather than letting near-duplicate topics accumulate — the same overfitting-to-the-moment trap as any other system that grows by unreviewed accretion.
