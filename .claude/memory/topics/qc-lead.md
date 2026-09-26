# Qc Lead

## 2026-09-26 — One chat leads QC over every repo

**Decisions:** Dex made this chat the QC lead for all his repos after about fifteen chats collided in one evening ("a lot of my chats were fighting against each other"). One writer per repo, everywhere: sessions work in their own clone, land changes by pull request and stop; the lead merges, deletes branches and reconciles every change against the design, folding good ideas in rather than overwriting them. Every repo's CLAUDE.md now tells Code sessions to read the hub first and keep that rule (the agency repo gets the one-writer rule only, not the personal hub). The private hub keeps the ledger: one verdict per change, and a pass that cannot close while anything is unread.

**Facts / preferences:** Dex: "In all the other chats just give me a prompt or command if you need me to do something." Anything that needs his hand is one copy-paste prompt or command. The root causes of the collisions: Code sessions in other repos never read the hub (only this repo's CLAUDE.md said to), and several Code sessions on the Mac shared one working folder until a rebase stuck under a merge.

**Artifacts:** Skill `.claude/skills/qc-lead/` and its `references/chat-report-prompt.md`; the hub repo's docs/QC.md. The first pass found and fixed a workflow file the Actions pause had made invalid (a job with two `if:` keys), and ported a fix stranded on a superseded branch onto main.

**Open threads:** Dex pastes the chat-report prompt into every open chat and pastes the blocks back here; the next pass gives each one a verdict. The weekly Thursday check-in runs a pass before it looks at pull requests.
