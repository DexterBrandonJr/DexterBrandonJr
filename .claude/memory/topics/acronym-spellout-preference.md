# Acronym Spellout Preference

## 2026-09-06 — Spell out and explain all acronyms in responses

**Decisions:** Every acronym or initialism in a response gets spelled out in full plus a plain-language description of what it means, not just expanded once and left otherwise unexplained. Applies going forward in this chat/repo -- e.g. "CLI (Command Line Interface, a program you control by typing commands instead of clicking)" rather than just "CLI" or a bare expansion with no explanation of what it actually does.
**Facts / preferences:** Dex wants this retained across sessions, not just applied to one reply. This is currently only enforced via this repo's chat-memory (auto-loaded each session start here) -- if he wants it to apply in other repos/chats too, that would need the global `~/.claude/settings.json` SessionStart hook setup described in chat-memory's references/global-setup.md, which hasn't been set up.
**Artifacts:** None.
**Open threads:** Whether this should be promoted to the global hook so it applies outside this specific chat/repo -- ask if it comes up.
